"""Scanning orchestration and backend abstraction."""
from __future__ import annotations
from typing import List
import uuid
import subprocess
import re
import os
import tempfile
from pathlib import Path

from app.core.jobs.manager import JobManager
from app.core.jobs.models import JobRecord, JobStatus
from app.core.targets.manager import TargetManager
from app.core.worker import get_worker


class ScannerManager:
    """High-level entrypoint for scan operations."""

    def list_devices(self) -> List[dict]:
        """
        Discover SANE scanners (USB, network eSCL/AirScan).
        
        Uses 'scanimage -L' to list available devices.
        Supports both USB SANE backends and eSCL (AirScan) for network scanners.
        
        Filters duplicate devices by preferring:
        1. eSCL (AirScan) network scanners (most reliable)
        2. USB scanners (direct connection)
        3. Other network protocols
        """
        devices = []
        device_groups = {}  # Group by normalized name to detect duplicates
        
        try:
            result = subprocess.run(
                ['scanimage', '-L'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',  # Replace invalid UTF-8 bytes with �
                timeout=15
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    # Parse: "device `escl:http://192.168.1.100:80' is a HP ENVY 6400 flatbed scanner"
                    # or: "device `hpaio:/usb/HP_ENVY_6400?serial=...' is a ..."
                    match = re.match(r"device `([^']+)' is a (.+)", line)
                    if match:
                        device_id = match.group(1)
                        description = match.group(2)
                        
                        device_type = 'Unknown'
                        priority = 99
                        
                        if device_id.startswith('escl:'):
                            # eSCL over network - highest priority for network
                            if '127.0.0.1' in device_id or 'USB' in device_id:
                                device_type = 'eSCL (USB)'
                                priority = 2
                            else:
                                device_type = 'eSCL (Network)'
                                priority = 1
                        elif device_id.startswith('airscan:'):
                            device_type = 'AirScan'
                            priority = 1
                        elif 'hpaio:/usb' in device_id.lower():
                            device_type = 'USB (HPAIO)'
                            priority = 2
                        elif 'usb' in device_id.lower():
                            device_type = 'USB'
                            priority = 2
                        elif 'hpaio:/net' in device_id.lower():
                            device_type = 'Network (HPAIO)'
                            priority = 3
                        elif 'net' in device_id.lower() or 'network' in device_id.lower():
                            device_type = 'Network'
                            priority = 3
                        
                        # Normalize device name (remove model/serial specifics)
                        # Extract base model name from description
                        base_name = description.split('flatbed')[0].strip()
                        base_name = re.sub(r'\[.*?\]', '', base_name).strip()  # Remove [serial]
                        base_name = re.sub(r'\s+', ' ', base_name)  # Normalize whitespace
                        
                        # Group by base name
                        if base_name not in device_groups:
                            device_groups[base_name] = []
                        
                        device_groups[base_name].append({
                            'id': device_id,
                            'name': description,
                            'type': device_type,
                            'priority': priority,
                            'supported': True
                        })
                
                # For each device group, keep only the best option
                for base_name, group_devices in device_groups.items():
                    # Sort by priority (lower = better)
                    group_devices.sort(key=lambda d: d['priority'])
                    
                    # Keep the best device (lowest priority number)
                    best_device = group_devices[0]
                    
                    # If we have both USB and Network, keep both but mark preference
                    has_usb = any(d['priority'] == 2 for d in group_devices)
                    has_network = any(d['priority'] == 1 for d in group_devices)
                    
                    if has_usb and has_network:
                        # Keep one USB and one Network option
                        usb_device = next((d for d in group_devices if d['priority'] == 2), None)
                        network_device = next((d for d in group_devices if d['priority'] == 1), None)
                        
                        if network_device:
                            network_device['name'] = f"{base_name} (Network - Recommended)"
                            devices.append(network_device)
                        if usb_device:
                            usb_device['name'] = f"{base_name} (USB)"
                            devices.append(usb_device)
                    else:
                        # Only one connection type available
                        devices.append(best_device)
                        
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"Error discovering scanners: {e}")
            # SANE/scanimage not installed or not accessible
            
        return devices

    def list_profiles(self) -> List[dict]:
        """
        Return available scan profiles.
        
        For now returns hardcoded defaults.
        TODO: Store in SQLite/config file for user customization.
        """
        return [
            {
                'id': 'color_300_pdf',
                'name': 'Color @300 DPI',
                'dpi': 300,
                'color_mode': 'Color',
                'paper_size': 'A4',
                'format': 'pdf'
            },
            {
                'id': 'gray_150_pdf',
                'name': 'Grayscale @150 DPI',
                'dpi': 150,
                'color_mode': 'Gray',
                'paper_size': 'A4',
                'format': 'pdf'
            },
            {
                'id': 'photo_600_jpeg',
                'name': 'Photo @600 DPI',
                'dpi': 600,
                'color_mode': 'Color',
                'paper_size': 'A4',
                'format': 'jpeg'
            }
        ]

    def start_scan(self, device_id: str, profile_id: str, target_id: str, filename_prefix: str | None) -> str:
        """
        Start a scan job in the background.
        
        Creates job and submits to background worker for async execution.
        """
        job_id = str(uuid.uuid4())
        job_manager = JobManager()
        job_manager.create_job(
            job_id=job_id,
            job_type="scan",
            device_id=device_id,
            target_id=target_id,
            status=JobStatus.queued,
        )
        
        # Submit to background worker for async execution
        worker = get_worker()
        
        async def scan_task():
            """Async wrapper for scan execution."""
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                self._execute_scan, 
                job_id, device_id, profile_id, target_id, filename_prefix
            )
        
        worker.submit_task(job_id, scan_task)
            
        return job_id
    
    def _execute_scan(self, job_id: str, device_id: str, profile_id: str, target_id: str, filename_prefix: str | None):
        """
        Execute the actual scan using scanimage.
        
        WARNING: This runs synchronously. In production, use a background worker.
        """
        job_manager = JobManager()
        
        try:
            # Update job status
            job = job_manager.get_job(job_id)
            if job:
                job.status = JobStatus.running
                job_manager.update_job(job)
            
            # Get profile settings
            profiles = {p['id']: p for p in self.list_profiles()}
            profile = profiles.get(profile_id, profiles['color_300_pdf'])
            
            print(f"Starting scan with profile: {profile}")
            
            # Create temp output file
            output_dir = Path(tempfile.gettempdir()) / 'raspscan' / 'scans'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            prefix = filename_prefix or 'scan'
            output_format = profile['format']
            
            # Scan to TIFF first (most compatible)
            tiff_file = output_dir / f"{prefix}_{job_id}.tiff"
            
            # Build scanimage command
            cmd = [
                'scanimage',
                '--device-name', device_id,
                '--resolution', str(profile['dpi']),
                '--mode', profile['color_mode'],
                '--format', 'tiff'
            ]
            
            print(f"Executing scan command: {' '.join(cmd)}")
            print(f"Output file: {tiff_file}")
            
            # Execute scan
            with open(tiff_file, 'wb') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=False, timeout=120)
            
            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='replace') if result.stderr else 'Unknown error'
                print(f"Scan failed: {error_msg}")
                raise Exception(f"scanimage failed: {error_msg}")
            
            print(f"Scan completed successfully: {tiff_file} ({tiff_file.stat().st_size} bytes)")
            
            # Convert TIFF to requested format if needed
            final_file = tiff_file
            if output_format == 'pdf':
                pdf_file = output_dir / f"{prefix}_{job_id}.pdf"
                print(f"Converting TIFF to PDF: {pdf_file}")
                
                # Use ImageMagick convert
                convert_result = subprocess.run(
                    ['convert', str(tiff_file), str(pdf_file)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if convert_result.returncode == 0 and pdf_file.exists():
                    print(f"PDF conversion successful: {pdf_file} ({pdf_file.stat().st_size} bytes)")
                    tiff_file.unlink()  # Remove TIFF after successful conversion
                    final_file = pdf_file
                else:
                    print(f"Warning: PDF conversion failed, using TIFF: {convert_result.stderr}")
                    # Keep TIFF file as fallback
            elif output_format == 'jpeg':
                jpeg_file = output_dir / f"{prefix}_{job_id}.jpg"
                print(f"Converting TIFF to JPEG: {jpeg_file}")
                
                convert_result = subprocess.run(
                    ['convert', str(tiff_file), '-quality', '90', str(jpeg_file)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if convert_result.returncode == 0 and jpeg_file.exists():
                    print(f"JPEG conversion successful: {jpeg_file} ({jpeg_file.stat().st_size} bytes)")
                    tiff_file.unlink()  # Remove TIFF
                    final_file = jpeg_file
                else:
                    print(f"Warning: JPEG conversion failed, using TIFF: {convert_result.stderr}")
            
            # Update job with file path
            job = job_manager.get_job(job_id)
            if job:
                job.file_path = str(final_file)
                job.status = JobStatus.completed
                job_manager.update_job(job)
            
            print(f"Delivering scan to target: {target_id}")
            
            # Deliver to target
            TargetManager().deliver(target_id, str(final_file), {'job_id': job_id})
            
            print(f"Scan job {job_id} completed successfully")
            
        except Exception as e:
            print(f"Scan error for job {job_id}: {e}")
            import traceback
            traceback.print_exc()
            
            # Update job status to failed
            job = job_manager.get_job(job_id)
            if job:
                job.status = JobStatus.failed
                job.message = str(e)
                job_manager.update_job(job)
            
            raise

    def list_jobs(self) -> List[JobRecord]:
        return JobManager().list_jobs(job_type="scan")

    def get_job(self, job_id: str) -> JobRecord:
        return JobManager().get_job(job_id)
