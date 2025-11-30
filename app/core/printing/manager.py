"""CUPS printing integration."""
from __future__ import annotations
from typing import List
import uuid
import subprocess
import re
from pathlib import Path

from fastapi import UploadFile

from app.core.jobs.manager import JobManager
from app.core.jobs.models import JobRecord, JobStatus


class PrinterManager:
    """Wrapper around CUPS operations."""

    def discover_devices(self) -> List[dict]:
        """
        Discover available USB and network printers.
        
        Returns:
            List of discovered devices with URI, make/model, and connection type.
            
        Notes:
            - USB printers: Auto-detected via usb:// URIs (e.g., usb://HP/ENVY%206400)
            - Wireless/Network printers: Detected via dnssd:// (AirPrint/IPP) or ipp://
            - Scanner-only devices won't appear here (use SANE for scanners)
        """
        devices = []
        try:
            # Query CUPS for available devices (USB, network, etc.)
            result = subprocess.run(
                ['lpinfo', '-v'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('direct ') or line.startswith('network '):
                        # Parse: "direct usb://HP/ENVY%206400?serial=..." or "network dnssd://..."
                        parts = line.split(' ', 1)
                        if len(parts) == 2:
                            uri = parts[1]
                            device_type = 'unknown'
                            
                            if uri.startswith('usb://'):
                                device_type = 'USB'
                                # Extract manufacturer and model from USB URI
                                match = re.search(r'usb://([^/]+)/([^?]+)', uri)
                                if match:
                                    make = match.group(1).replace('%20', ' ')
                                    model = match.group(2).replace('%20', ' ').replace('%', ' ')
                                else:
                                    make, model = 'Unknown', 'USB Printer'
                            elif uri.startswith('dnssd://') or uri.startswith('ipp://'):
                                device_type = 'Network'
                                # Extract name from DNS-SD or IPP URI
                                match = re.search(r'//([^/]+)', uri)
                                make, model = 'Network', match.group(1) if match else 'Printer'
                            elif uri.startswith('socket://'):
                                device_type = 'Network'
                                make, model = 'Network', 'TCP/IP Printer'
                            else:
                                continue
                                
                            devices.append({
                                'uri': uri,
                                'type': device_type,
                                'make': make,
                                'model': model,
                                'name': f"{make} {model}",
                                'supported': True
                            })
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"Error discovering devices: {e}")
            
        return devices

    def list_printers(self) -> List[dict]:
        """
        List already configured printers in CUPS.
        
        Returns:
            List of configured printers with status.
        """
        printers = []
        try:
            # Query configured printers
            result = subprocess.run(
                ['lpstat', '-p'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    # Parse: "printer HP_Envy is idle.  enabled since..."
                    match = re.match(r'printer (\S+) is (\S+)', line)
                    if match:
                        name = match.group(1)
                        status = match.group(2)  # idle, processing, stopped
                        
                        # Get printer URI/device
                        uri_result = subprocess.run(
                            ['lpstat', '-v', name],
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        uri = 'unknown'
                        if uri_result.returncode == 0:
                            uri_match = re.search(r'device for \S+: (.+)', uri_result.stdout)
                            if uri_match:
                                uri = uri_match.group(1)
                        
                        printers.append({
                            'id': name,
                            'name': name.replace('_', ' '),
                            'status': status,
                            'uri': uri,
                            'is_default': False
                        })
            
            # Check for default printer
            default_result = subprocess.run(
                ['lpstat', '-d'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if default_result.returncode == 0:
                default_match = re.search(r'system default destination: (\S+)', default_result.stdout)
                if default_match:
                    default_name = default_match.group(1)
                    for printer in printers:
                        if printer['id'] == default_name:
                            printer['is_default'] = True
                            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"Error listing printers: {e}")
            
        return printers

    def list_jobs(self, printer_id: str) -> List[JobRecord]:
        return JobManager().list_jobs(job_type="print", printer_id=printer_id)

    def submit_job(self, printer_id: str, upload: UploadFile, options: dict) -> str:
        """
        Submit a print job to CUPS.
        
        Saves uploaded file to temp storage and submits via 'lp' command.
        """
        job_id = str(uuid.uuid4())
        job_manager = JobManager()
        
        try:
            # Save uploaded file to temp directory
            temp_dir = Path('/tmp/raspscan/print')
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = temp_dir / f"{job_id}_{upload.filename}"
            with open(file_path, 'wb') as f:
                content = upload.file.read()
                f.write(content)
            
            # Build lp command
            cmd = ['lp', '-d', printer_id, '-t', f'RaspScan_{job_id}']
            
            # Add options
            if 'copies' in options:
                cmd.extend(['-n', str(options['copies'])])
            if 'duplex' in options:
                cmd.extend(['-o', f"sides={options['duplex']}"])
            if 'color' in options:
                cmd.extend(['-o', f"ColorModel={options['color']}"])
            
            # Add file path
            cmd.append(str(file_path))
            
            # Submit to CUPS
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Extract CUPS job ID from output: "request id is HP_Envy-123 (1 file(s))"
                cups_job_match = re.search(r'request id is [^-]+-([0-9]+)', result.stdout)
                cups_job_id = cups_job_match.group(1) if cups_job_match else 'unknown'
                
                job_manager.create_job(
                    job_id=job_id,
                    job_type="print",
                    printer_id=printer_id,
                    status=JobStatus.running,
                )
                job_manager.get_job(job_id).file_path = str(file_path)
                job_manager.get_job(job_id).message = f"CUPS job {cups_job_id}"
            else:
                raise Exception(f"lp command failed: {result.stderr}")
                
        except Exception as e:
            job_manager.create_job(
                job_id=job_id,
                job_type="print",
                printer_id=printer_id,
                status=JobStatus.failed,
            )
            job_manager.get_job(job_id).message = str(e)
            raise
            
        return job_id

    def print_test_page(self, printer_id: str) -> str:
        """
        Print a test page to verify printer functionality.
        """
        job_id = str(uuid.uuid4())
        
        try:
            # Use CUPS test page command
            result = subprocess.run(
                ['lp', '-d', printer_id, '/usr/share/cups/data/testprint'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                JobManager().create_job(
                    job_id=job_id,
                    job_type="print",
                    printer_id=printer_id,
                    status=JobStatus.running,
                )
            else:
                raise Exception(f"Test page failed: {result.stderr}")
        except Exception as e:
            JobManager().create_job(
                job_id=job_id,
                job_type="print",
                printer_id=printer_id,
                status=JobStatus.failed,
            )
            JobManager().get_job(job_id).message = str(e)
            
        return job_id

    def add_printer(self, uri: str, name: str, description: str | None = None) -> None:
        """
        Add a printer to CUPS.
        
        Args:
            uri: Device URI (e.g., usb://HP/ENVY%206400 or ipp://printer.local/ipp/print)
            name: Printer name for CUPS (will be sanitized)
            description: Optional human-readable description
            
        Notes:
            - For modern printers, CUPS can often auto-select the correct driver (IPP Everywhere)
            - For older USB printers, you may need to specify a PPD file
            - Use 'lpinfo -m' to list available PPD drivers
        """
        try:
            # Sanitize printer name (no spaces, special chars)
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
            
            # Try to add printer with auto driver selection (-m everywhere)
            # -p: printer name, -v: device URI, -E: enable printer, -m: driver model
            cmd = [
                'lpadmin',
                '-p', safe_name,
                '-v', uri,
                '-m', 'everywhere',  # IPP Everywhere (works for most modern printers)
                '-E'  # Enable the printer
            ]
            
            if description:
                cmd.extend(['-D', description])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise Exception(f"lpadmin failed: {result.stderr}")
                
            # Set as default if it's the first printer
            printers = self.list_printers()
            if len(printers) == 1:
                subprocess.run(['lpadmin', '-d', safe_name], timeout=5)
                
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            raise Exception(f"Failed to add printer: {e}")
