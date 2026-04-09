"""Scanning orchestration and backend abstraction."""
from __future__ import annotations
from typing import List
import uuid
import subprocess
import re
import os
import tempfile
import logging
from pathlib import Path

from core.jobs.manager import JobManager
from core.jobs.models import JobRecord, JobStatus
from core.targets.manager import TargetManager
from core.worker import get_worker

logger = logging.getLogger(__name__)


class ScannerManager:
    """High-level entrypoint for scan operations."""

    def list_devices(self) -> List[dict]:
        """
        Discover SANE scanners (USB, network eSCL/AirScan).
        
        Uses 'airscan-discover' to find eSCL scanners (more reliable than scanimage -L).
        Supports both USB SANE backends and eSCL (AirScan) for network scanners.
        
        Filters duplicate devices by preferring:
        1. eSCL (AirScan) network scanners (most reliable)
        2. USB scanners (direct connection)
        3. Other network protocols
        """
        import logging
        logger = logging.getLogger(__name__)
        
        devices = []
        device_groups = {}  # Group by normalized name to detect duplicates
        
        logger.debug("Starting scanner discovery...")
        
        try:
            # Use airscan-discover instead of scanimage -L (more reliable)
            logger.debug("Running airscan-discover...")
            result = subprocess.run(
                ['airscan-discover'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=15
            )
            
            logger.debug(f"airscan-discover return code: {result.returncode}")
            
            if result.returncode == 0:
                logger.debug(f"airscan-discover output:\n{result.stdout}")
                
                # Parse airscan-discover output
                # Format: "HP ENVY 6400 series [059A50] = http://10.10.30.146:8080/eSCL/, eSCL"
                in_devices_section = False
                
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    
                    if line == '[devices]':
                        in_devices_section = True
                        continue
                    
                    if not in_devices_section or not line or line.startswith('['):
                        continue
                    
                    # Parse device line: "HP ENVY 6400 series [059A50] = http://..., eSCL"
                    if '=' in line:
                        logger.debug(f"Parsing device line: {line}")
                        name_part, url_part = line.split('=', 1)
                        name_part = name_part.strip()
                        url_part = url_part.strip()
                        
                        # Extract URL and protocol
                        parts = url_part.split(',')
                        url = parts[0].strip()
                        protocol = parts[1].strip() if len(parts) > 1 else 'Unknown'
                        
                        # Extract device name and serial
                        name_match = re.match(r'(.+?)\s*\[([^\]]+)\]', name_part)
                        if name_match:
                            device_name = name_match.group(1).strip()
                            serial = name_match.group(2).strip()
                        else:
                            device_name = name_part
                            serial = None
                        
                        # Determine device type and priority
                        device_type = 'Unknown'
                        priority = 99
                        
                        if protocol == 'eSCL':
                            if '127.0.0.1' in url or '::1' in url or 'USB' in name_part:
                                device_type = 'eSCL (USB)'
                                priority = 2
                            else:
                                device_type = 'eSCL (Network)'
                                priority = 1
                        elif protocol == 'WSD':
                            device_type = 'WSD (Network)'
                            priority = 3
                        
                        # Build SANE device ID for airscan
                        # Format: airscan:escl:Device Name:URL
                        device_id = f"airscan:escl:{device_name.replace(' ', '_')}:{url}"
                        
                        logger.debug(f"Found scanner: {device_name} (ID: {device_id}, Type: {device_type})\")")
                        
                        # Use base name for grouping (without serial)
                        base_name = device_name
                        
                        # Group by base name
                        if base_name not in device_groups:
                            device_groups[base_name] = []
                        
                        device_groups[base_name].append({
                            'id': device_id,
                            'name': f"{device_name} [{serial}]" if serial else device_name,
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
                
                logger.info(f"airscan-discover found {len(devices)} scanner(s)")
                        
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.error(f"Error discovering scanners with airscan-discover: {e}", exc_info=True)
            # SANE/scanimage not installed or not accessible
        
        logger.info(f"Scanner discovery complete: {len(devices)} device(s) found")
        return devices

    def list_profiles(self) -> List[dict]:
        """
        Return available scan profiles.
        
        For now returns hardcoded defaults.
        TODO: Store in SQLite/config file for user customization.
        """
        return [
            {
                'id': 'document_200_pdf',
                'name': 'Document @200 DPI (Small)',
                'dpi': 200,
                'color_mode': 'Gray',
                'paper_size': 'A4',
                'format': 'pdf',
                'quality': 80,
                'source': 'Flatbed',
                'batch_scan': False,
                'auto_detect': True,
                'description': 'Best for text documents - smallest size'
            },
            {
                'id': 'document_adf_200_pdf',
                'name': 'Multi-Page Document (ADF)',
                'dpi': 200,
                'color_mode': 'Gray',
                'paper_size': 'A4',
                'format': 'pdf',
                'quality': 80,
                'source': 'ADF',
                'batch_scan': True,
                'auto_detect': True,
                'description': 'Scan multiple pages from document feeder'
            },
            {
                'id': 'color_300_pdf',
                'name': 'Color @300 DPI (Medium)',
                'dpi': 300,
                'color_mode': 'Color',
                'paper_size': 'A4',
                'format': 'pdf',
                'quality': 85,
                'source': 'Flatbed',
                'batch_scan': False,
                'auto_detect': True,
                'description': 'Good quality for mixed content'
            },
            {
                'id': 'gray_150_pdf',
                'name': 'Grayscale @150 DPI (Fast)',
                'dpi': 150,
                'color_mode': 'Gray',
                'paper_size': 'A4',
                'format': 'pdf',
                'quality': 75,
                'source': 'Flatbed',
                'batch_scan': False,
                'auto_detect': True,
                'description': 'Quick scans, very small size'
            },
            {
                'id': 'photo_600_jpeg',
                'name': 'Photo @600 DPI (High Quality)',
                'dpi': 600,
                'color_mode': 'Color',
                'paper_size': 'A4',
                'format': 'jpeg',
                'quality': 95,
                'source': 'Flatbed',
                'batch_scan': False,
                'auto_detect': False,
                'description': 'Best quality for photos'
            }
        ]

    def start_scan(self, device_id: str, profile_id: str, target_id: str, filename_prefix: str | None, webhook_url: str | None = None) -> str:
        """
        Start a scan job in the background.
        
        Creates job and submits to background worker for async execution.
        Optionally sends webhook notification on completion.
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
                job_id, device_id, profile_id, target_id, filename_prefix, webhook_url
            )
        
        worker.submit_task(job_id, scan_task)
            
        return job_id
    
    def _execute_scan(self, job_id: str, device_id: str, profile_id: str, target_id: str, filename_prefix: str | None, webhook_url: str | None = None):
        """
        Execute the actual scan using scanimage.
        Supports multi-page scanning (ADF), automatic document detection, and webhook notifications.
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
            
            logger.info(f"Starting scan with profile: {profile}")
            
            # Create temp output file
            output_dir = Path(tempfile.gettempdir()) / 'scan2target' / 'scans'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            prefix = filename_prefix or 'scan'
            output_format = profile['format']
            batch_scan = profile.get('batch_scan', False)
            source = profile.get('source', 'Flatbed')
            
            scanned_files = []
            page_num = 1
            
            # For ADF batch scans, use scanimage --batch mode to scan all pages at once
            if batch_scan and source == 'ADF':
                logger.info(f"Using --batch mode for ADF scanning")
                batch_pattern = output_dir / f"{prefix}_{job_id}_page%03d.tiff"
                
                # Build scanimage command with --batch
                cmd = [
                    'scanimage',
                    '--device-name', device_id,
                    '--resolution', str(profile['dpi']),
                    '--mode', profile['color_mode'],
                    '--format', 'tiff',
                    '--source', source,
                    '--batch=' + str(batch_pattern)
                ]
                
                logger.debug(f"Executing batch scan command: {' '.join(cmd)}")
                logger.debug(f"Output pattern: {batch_pattern}")
                
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minutes for batch scanning
                    )
                    
                    if result.returncode != 0:
                        error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                        logger.error(f"Batch scan error: {error_msg}")
                        raise Exception(f"Batch scan failed: {error_msg}")
                    
                    # Find all scanned files matching the pattern
                    scanned_files = sorted(output_dir.glob(f"{prefix}_{job_id}_page*.tiff"))
                    
                    if not scanned_files:
                        raise Exception("No pages were scanned in batch mode")
                    
                    logger.info(f"Batch scan completed: {len(scanned_files)} page(s)")
                    for idx, tiff_file in enumerate(scanned_files, 1):
                        file_size = tiff_file.stat().st_size
                        logger.debug(f"  Page {idx}: {tiff_file} ({file_size} bytes)")
                    
                    # Generate thumbnail from first page
                    try:
                        thumbnail_file = output_dir / f"{prefix}_{job_id}_thumb.jpg"
                        subprocess.run(
                            [
                                'convert',
                                str(scanned_files[0]),
                                '-thumbnail', '400x400>',
                                '-quality', '80',
                                str(thumbnail_file)
                            ],
                            capture_output=True,
                            timeout=10
                        )
                        if thumbnail_file.exists():
                            logger.debug(f"Thumbnail generated: {thumbnail_file} ({thumbnail_file.stat().st_size} bytes)")
                    except Exception as e:
                        logger.warning(f"Warning: Failed to generate thumbnail: {e}")
                        
                except subprocess.TimeoutExpired:
                    raise Exception("Batch scan timeout after 5 minutes")
            
            # For single page or manual multi-page scanning
            else:
                # Multi-page scanning loop (for manual page-by-page)
                while True:
                    # Scan to TIFF first (most compatible)
                    if batch_scan:
                        tiff_file = output_dir / f"{prefix}_{job_id}_page{page_num:03d}.tiff"
                    else:
                        tiff_file = output_dir / f"{prefix}_{job_id}.tiff"
                
                    # Build scanimage command
                    cmd = [
                        'scanimage',
                        '--device-name', device_id,
                        '--resolution', str(profile['dpi']),
                        '--mode', profile['color_mode'],
                        '--format', 'tiff'
                    ]
                    
                    # Add source if supported (ADF vs Flatbed)
                    if source and source != 'Flatbed':
                        cmd.extend(['--source', source])
                    
                    # Note: Don't use --batch-prompt for ADF as it's interactive
                    # Instead, we scan one page at a time and stop when we get an error
                    
                    logger.debug(f"Executing scan command (page {page_num}): {' '.join(cmd)}")
                    logger.debug(f"Output file: {tiff_file}")
                    
                    # Execute scan
                    try:
                        with open(tiff_file, 'wb') as f:
                            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=False, timeout=120)
                        
                        if result.returncode != 0:
                            # Check if ADF is empty (normal end of batch scan)
                            error_msg = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
                            
                            # Common ADF empty messages
                            adf_empty_indicators = [
                                'out of documents',
                                'no documents',
                                'document feeder is empty',
                                'adf empty',
                                'no more pages',
                                'end of document',
                                'error during device i/o',  # HP scanners return this when ADF is empty
                                'device i/o error'
                            ]
                            
                            if batch_scan and any(indicator in error_msg.lower() for indicator in adf_empty_indicators):
                                logger.info(f"ADF empty (detected: '{error_msg}'), batch scan complete.")
                                # Check if a file was created before the error
                                if tiff_file.exists():
                                    file_size = tiff_file.stat().st_size
                                    if file_size > 0:
                                        logger.debug(f"Page {page_num} was partially scanned before ADF empty: {tiff_file} ({file_size} bytes)")
                                        scanned_files.append(tiff_file)
                                        logger.info(f"Total pages scanned: {len(scanned_files)}")
                                    else:
                                        logger.warning(f"Page {page_num} file is empty, removing")
                                        tiff_file.unlink()
                                        logger.info(f"Total pages scanned: {len(scanned_files)}")
                                else:
                                    logger.warning(f"No file created for page {page_num}")
                                    logger.info(f"Total pages scanned: {len(scanned_files)}")
                                break
                            
                            logger.error(f"Scan failed: {error_msg}")
                            raise Exception(f"scanimage failed: {error_msg}")
                        
                        file_size = tiff_file.stat().st_size if tiff_file.exists() else 0
                        
                        # Check if file is actually empty (sometimes scan "succeeds" but creates empty file)
                        if file_size == 0:
                            logger.info(f"Page {page_num}: Empty file, assuming ADF is empty")
                            tiff_file.unlink()
                            if batch_scan and page_num > 1:
                                logger.info(f"ADF empty, batch scan complete. Scanned {page_num - 1} pages.")
                                break
                            else:
                                raise Exception("Scanner returned empty file")
                        
                        logger.info(f"Page {page_num} scanned successfully: {tiff_file} ({file_size} bytes)")
                        scanned_files.append(tiff_file)
                        
                    except subprocess.TimeoutExpired:
                        logger.warning(f"Scan timeout on page {page_num}")
                        if batch_scan and page_num > 1:
                            logger.info(f"Assuming ADF is empty. Scanned {page_num - 1} pages.")
                            break
                        raise Exception("Scan timeout")
                    
                    # Generate thumbnail immediately after first page scan (for live preview)
                    if page_num == 1:
                        try:
                            thumbnail_file = output_dir / f"{prefix}_{job_id}_thumb.jpg"
                            subprocess.run(
                                [
                                    'convert',
                                    str(tiff_file),
                                    '-thumbnail', '400x400>',
                                    '-quality', '80',
                                    str(thumbnail_file)
                                ],
                                capture_output=True,
                                timeout=10
                            )
                            if thumbnail_file.exists():
                                logger.debug(f"Live preview thumbnail generated: {thumbnail_file} ({thumbnail_file.stat().st_size} bytes)")
                        except Exception as e:
                            logger.warning(f"Warning: Failed to generate live preview thumbnail: {e}")
                    
                    # If not batch mode, stop after first page
                    if not batch_scan:
                        break
                    
                    page_num += 1
                    
                    # Safety limit for batch scanning
                    if page_num > 100:
                        logger.warning("Warning: Reached 100-page limit for batch scanning")
                        break
            
            if not scanned_files:
                raise Exception("No pages were scanned successfully")
            
            logger.info(f"Scan completed: {len(scanned_files)} page(s)")
            
            # Convert TIFF(s) to requested format
            final_file = None
            if output_format == 'pdf':
                pdf_file = output_dir / f"{prefix}_{job_id}.pdf"
                logger.info(f"Converting {len(scanned_files)} TIFF(s) to PDF: {pdf_file}")
                
                # Get quality setting from profile (default 85)
                quality = str(profile.get('quality', 85))
                
                # Use ImageMagick convert with compression
                # For multi-page PDFs, all TIFF files are combined into one PDF
                convert_cmd = ['convert']
                
                # Add all TIFF files as input
                for tiff in scanned_files:
                    convert_cmd.append(str(tiff))
                
                # Add compression settings
                convert_cmd.extend([
                    '-compress', 'JPEG',
                    '-quality', quality,
                    '-density', str(profile['dpi']),
                ])
                
                # For grayscale, add additional compression
                if profile['color_mode'] == 'Gray':
                    convert_cmd.extend(['-colorspace', 'Gray'])
                
                # Add output file
                convert_cmd.append(str(pdf_file))
                
                logger.debug(f"PDF conversion command: {' '.join(convert_cmd)}")
                
                convert_result = subprocess.run(
                    convert_cmd,
                    capture_output=True,
                    text=True,
                    timeout=180  # Longer timeout for multi-page
                )
                
                if convert_result.returncode == 0 and pdf_file.exists():
                    total_tiff_size = sum(f.stat().st_size for f in scanned_files)
                    pdf_size = pdf_file.stat().st_size
                    ratio = (1 - pdf_size / total_tiff_size) * 100 if total_tiff_size > 0 else 0
                    logger.info(f"PDF conversion successful: {pdf_file}")
                    logger.info(f"  Pages: {len(scanned_files)}")
                    logger.info(f"  Size: {pdf_size:,} bytes (saved {ratio:.1f}%)")
                    
                    # Remove TIFF files after successful conversion
                    for tiff in scanned_files:
                        tiff.unlink()
                    
                    final_file = pdf_file
                else:
                    logger.warning(f"Warning: PDF conversion failed: {convert_result.stderr}")
                    # Keep first TIFF file as fallback
                    final_file = scanned_files[0] if scanned_files else None
            elif output_format == 'jpeg':
                # JPEG only supports single page, use first page
                tiff_file = scanned_files[0]
                jpeg_file = output_dir / f"{prefix}_{job_id}.jpg"
                logger.info(f"Converting TIFF to JPEG: {jpeg_file}")
                
                if len(scanned_files) > 1:
                    logger.warning(f"Warning: JPEG format only supports single page, using page 1 of {len(scanned_files)}")
                
                # Get quality setting from profile (default 90)
                quality = str(profile.get('quality', 90))
                
                convert_result = subprocess.run(
                    ['convert', str(tiff_file), '-quality', quality, str(jpeg_file)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if convert_result.returncode == 0 and jpeg_file.exists():
                    tiff_size = tiff_file.stat().st_size
                    jpeg_size = jpeg_file.stat().st_size
                    ratio = (1 - jpeg_size / tiff_size) * 100 if tiff_size > 0 else 0
                    logger.info(f"JPEG conversion successful: {jpeg_file}")
                    logger.info(f"  Size: {jpeg_size:,} bytes (saved {ratio:.1f}%)")
                    
                    # Remove TIFF files
                    for tiff in scanned_files:
                        tiff.unlink()
                    
                    final_file = jpeg_file
                else:
                    logger.warning(f"Warning: JPEG conversion failed: {convert_result.stderr}")
                    final_file = tiff_file
            
            # Update job with file path
            job = job_manager.get_job(job_id)
            if job:
                job.file_path = str(final_file)
                # Store thumbnail path if it exists
                if thumbnail_file and thumbnail_file.exists():
                    job.thumbnail_path = str(thumbnail_file)
                job.status = JobStatus.completed
                job_manager.update_job(job)
            
            logger.info(f"Delivering scan to target: {target_id}")
            
            # Generate thumbnail preview
            thumbnail_file = None
            try:
                thumbnail_file = output_dir / f"{prefix}_{job_id}_thumb.jpg"
                subprocess.run(
                    [
                        'convert',
                        str(final_file) + '[0]',  # First page only
                        '-thumbnail', '400x400>',
                        '-quality', '80',
                        str(thumbnail_file)
                    ],
                    capture_output=True,
                    timeout=10
                )
                if thumbnail_file.exists():
                    logger.debug(f"Thumbnail generated: {thumbnail_file} ({thumbnail_file.stat().st_size} bytes)")
            except Exception as e:
                logger.warning(f"Warning: Failed to generate thumbnail: {e}")
            
            # Deliver to target
            try:
                TargetManager().deliver(target_id, str(final_file), {'job_id': job_id})
                
                # Update job status to completed
                job = job_manager.get_job(job_id)
                if job:
                    job.status = JobStatus.completed
                    job.message = None
                    job_manager.update_job(job)
                
                logger.info(f"✓ Scan job {job_id} completed successfully")
                
                # Clean up local files after successful upload
                try:
                    if final_file.exists():
                        final_file.unlink()
                        logger.debug(f"✓ Deleted scan file: {final_file}")
                    
                    # Keep thumbnail for preview in UI (small file ~10-50KB)
                    # Thumbnails can be cleaned up separately with a cron job if needed
                    
                except Exception as cleanup_error:
                    logger.warning(f"Warning: Failed to delete scan file: {cleanup_error}")
                
            except Exception as delivery_error:
                logger.warning(f"⚠️ Delivery failed for job {job_id}: {delivery_error}")
                
                # Mark job as completed but with delivery failure
                job = job_manager.get_job(job_id)
                if job:
                    job.status = JobStatus.completed  # Scan was successful
                    job.message = f"Upload failed: {str(delivery_error)}"
                    job_manager.update_job(job)
                
                logger.warning(f"⚠️ Scan completed but delivery failed. File kept locally for retry: {final_file}")
                # Don't raise - scan was successful, just delivery failed
                # File is kept for manual retry
            
            # Send webhook notification if configured
            if webhook_url:
                self._send_webhook_notification(
                    webhook_url,
                    job_id,
                    'completed',
                    {
                        'pages': len(scanned_files),
                        'file_size': final_file.stat().st_size if final_file else 0,
                        'format': output_format,
                        'profile': profile_id,
                        'thumbnail': str(thumbnail_file) if thumbnail_file and thumbnail_file.exists() else None
                    }
                )
            
        except Exception as e:
            logger.error(f"Scan error for job {job_id}: {e}")
            import traceback
            traceback.print_exc()
            
            # Update job status to failed
            job = job_manager.get_job(job_id)
            if job:
                job.status = JobStatus.failed
                job.message = str(e)
                job_manager.update_job(job)
            
            # Send webhook notification for failure
            if webhook_url:
                self._send_webhook_notification(
                    webhook_url,
                    job_id,
                    'failed',
                    {'error': str(e)}
                )
            
            raise
    
    def _send_webhook_notification(self, webhook_url: str, job_id: str, status: str, metadata: dict):
        """Send webhook notification with job status."""
        try:
            import json
            import urllib.request
            
            payload = {
                'job_id': job_id,
                'status': status,
                'timestamp': subprocess.run(['date', '-Iseconds'], capture_output=True, text=True).stdout.strip(),
                'metadata': metadata
            }
            
            logger.info(f"Sending webhook notification to {webhook_url}")
            
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                logger.info(f"Webhook notification sent successfully: {response.status}")
        except Exception as e:
            logger.warning(f"Warning: Failed to send webhook notification: {e}")

    def list_jobs(self) -> List[JobRecord]:
        return JobManager().list_jobs(job_type="scan")

    def get_job(self, job_id: str) -> JobRecord:
        return JobManager().get_job(job_id)
