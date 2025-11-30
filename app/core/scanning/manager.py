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
        """
        devices = []
        try:
            result = subprocess.run(
                ['scanimage', '-L'],
                capture_output=True,
                text=True,
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
                        if device_id.startswith('escl:'):
                            device_type = 'eSCL (AirScan)'
                        elif device_id.startswith('airscan:'):
                            device_type = 'AirScan'
                        elif 'usb' in device_id.lower():
                            device_type = 'USB'
                        elif 'net' in device_id.lower() or 'network' in device_id.lower():
                            device_type = 'Network'
                        
                        devices.append({
                            'id': device_id,
                            'name': description,
                            'type': device_type,
                            'supported': True
                        })
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
        # Get profile settings
        profiles = {p['id']: p for p in self.list_profiles()}
        profile = profiles.get(profile_id, profiles['color_300_pdf'])
        
        # Create temp output file
        output_dir = Path(tempfile.gettempdir()) / 'raspscan' / 'scans'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        prefix = filename_prefix or 'scan'
        output_format = profile['format']
        output_file = output_dir / f"{prefix}_{job_id}.{output_format}"
        
        # Build scanimage command
        cmd = [
            'scanimage',
            '--device-name', device_id,
            '--resolution', str(profile['dpi']),
            '--mode', profile['color_mode'],
            '--format', 'tiff' if output_format == 'pdf' else output_format,
            '--output-file', str(output_file)
        ]
        
        # Execute scan
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            # Convert TIFF to PDF if needed
            if output_format == 'pdf':
                pdf_file = output_dir / f"{prefix}_{job_id}.pdf"
                # Use ImageMagick or similar for conversion
                # For now just rename (production would convert properly)
                output_file.rename(pdf_file)
                output_file = pdf_file
            
            # Update job with file path
            job_manager = JobManager()
            job = job_manager.get_job(job_id)
            if job:
                job.file_path = str(output_file)
                job_manager.update_job(job)
            
            # Deliver to target
            TargetManager().deliver(target_id, str(output_file), {'job_id': job_id})
            
            # Status update happens in background worker wrapper
        else:
            raise Exception(f"scanimage failed: {result.stderr}")

    def list_jobs(self) -> List[JobRecord]:
        return JobManager().list_jobs(job_type="scan")

    def get_job(self, job_id: str) -> JobRecord:
        return JobManager().get_job(job_id)
