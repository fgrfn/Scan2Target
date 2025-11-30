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
            Includes both:
            - Unconfigured devices (available to add)
            - Already configured printers (marked as 'configured')
            
        Notes:
            - USB printers: Auto-detected via usb:// URIs (e.g., usb://HP/ENVY%206400)
            - Wireless/Network printers: Detected via dnssd:// (AirPrint/IPP) or ipp://
            - Scanner-only devices won't appear here (use SANE for scanners)
        """
        devices = []
        configured_uris = set()
        
        # First, get list of already configured printers
        try:
            configured_printers = self.list_printers()
            for printer in configured_printers:
                configured_uris.add(printer.get('uri', ''))
        except Exception as e:
            print(f"Warning: Could not list configured printers: {e}")
        
        try:
            # Query CUPS for available devices (USB, network, etc.)
            result = subprocess.run(
                ['lpinfo', '-v'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=15
            )
            
            if result.returncode != 0:
                print(f"lpinfo -v failed with code {result.returncode}: {result.stderr}")
                # If lpinfo fails, still return configured printers
                return self._get_configured_as_discovered()
            
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                    
                # Parse different line formats from lpinfo -v:
                # "direct usb://HP/ENVY%206400?serial=..."
                # "network dnssd://..."
                # "network ipp://..."
                uri = None
                device_type = 'Unknown'
                
                if line.startswith('direct '):
                    uri = line[7:].strip()  # Remove "direct "
                    device_type = 'USB' if uri.startswith('usb://') else 'Direct'
                elif line.startswith('network '):
                    uri = line[8:].strip()  # Remove "network "
                    device_type = 'Network'
                else:
                    # Try to extract URI from other formats
                    parts = line.split(None, 1)
                    if len(parts) == 2 and '://' in parts[1]:
                        uri = parts[1]
                        if 'usb://' in uri:
                            device_type = 'USB'
                        elif 'network' in parts[0].lower() or 'dnssd' in uri or 'ipp' in uri:
                            device_type = 'Network'
                
                if not uri:
                    continue
                
                # Extract make and model from URI
                make = 'Unknown'
                model = 'Printer'
                
                if uri.startswith('usb://'):
                    # Parse: usb://HP/ENVY%206400?serial=...
                    match = re.search(r'usb://([^/]+)/([^?]+)', uri)
                    if match:
                        make = match.group(1).replace('%20', ' ').replace('%', ' ')
                        model = match.group(2).replace('%20', ' ').replace('%', ' ')
                    device_type = 'USB'
                elif uri.startswith('dnssd://'):
                    # Parse: dnssd://HP%20Envy%206400._ipp._tcp.local/
                    match = re.search(r'dnssd://([^._]+)', uri)
                    if match:
                        name = match.group(1).replace('%20', ' ').replace('%', ' ')
                        model = name
                        make = 'Network'
                    device_type = 'Network (AirPrint)'
                elif uri.startswith('ipp://') or uri.startswith('ipps://'):
                    # Parse: ipp://printer.local:631/ipp/print
                    match = re.search(r'ipp[s]?://([^:/]+)', uri)
                    if match:
                        model = match.group(1)
                        make = 'Network'
                    device_type = 'Network (IPP)'
                elif uri.startswith('socket://'):
                    match = re.search(r'socket://([^:/]+)', uri)
                    if match:
                        model = match.group(1)
                        make = 'Network'
                    device_type = 'Network (TCP/IP)'
                
                is_configured = uri in configured_uris
                
                devices.append({
                    'uri': uri,
                    'type': device_type,
                    'make': make,
                    'model': model,
                    'name': f"{make} {model}".strip(),
                    'supported': True,
                    'configured': is_configured,
                    'status': 'Configured' if is_configured else 'Available'
                })
                
        except FileNotFoundError:
            print("ERROR: lpinfo command not found. CUPS is not installed!")
            print("Install CUPS: sudo apt install cups cups-browsed")
            # Return configured printers if discovery fails
            return self._get_configured_as_discovered()
        except subprocess.TimeoutExpired as e:
            print(f"Error discovering devices (timeout): {e}")
            return self._get_configured_as_discovered()
        except Exception as e:
            print(f"Unexpected error in discover_devices: {e}")
            
        # If no devices found, at least show configured printers
        if not devices:
            print("No devices found via lpinfo, showing configured printers")
            return self._get_configured_as_discovered()
            
        return devices
    
    def _get_configured_as_discovered(self) -> List[dict]:
        """Convert configured printers to discovery format as fallback."""
        devices = []
        try:
            configured = self.list_printers()
            for printer in configured:
                devices.append({
                    'uri': printer.get('uri', 'unknown'),
                    'type': 'Configured',
                    'make': printer.get('name', 'Unknown').split()[0] if printer.get('name') else 'Unknown',
                    'model': ' '.join(printer.get('name', 'Printer').split()[1:]) if printer.get('name') else 'Printer',
                    'name': printer.get('name', 'Unknown Printer'),
                    'supported': True,
                    'configured': True,
                    'status': printer.get('status', 'unknown')
                })
        except Exception as e:
            print(f"Could not get configured printers: {e}")
        return devices

    def list_printers(self) -> List[dict]:
        """
        List already configured printers in CUPS.
        
        Returns:
            List of configured printers with status and connection type.
        """
        printers = []
        try:
            # Query configured printers
            result = subprocess.run(
                ['lpstat', '-p'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=5
            )
            
            if result.returncode != 0:
                print(f"lpstat -p failed: {result.stderr}")
                return []
            
            if not result.stdout.strip():
                print("No printers configured in CUPS")
                return []
            
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                    
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
                    device_type = 'Unknown'
                    
                    if uri_result.returncode == 0:
                        uri_match = re.search(r'device for \S+: (.+)', uri_result.stdout)
                        if uri_match:
                            uri = uri_match.group(1).strip()
                            
                            # Determine connection type from URI
                            if uri.startswith('usb://'):
                                device_type = 'USB'
                            elif uri.startswith('dnssd://'):
                                device_type = 'Network (AirPrint)'
                            elif uri.startswith('ipp://') or uri.startswith('ipps://'):
                                device_type = 'Network (IPP)'
                            elif uri.startswith('socket://'):
                                device_type = 'Network (TCP/IP)'
                            elif uri.startswith('lpd://'):
                                device_type = 'Network (LPD)'
                            else:
                                device_type = 'Other'
                    
                    printers.append({
                        'id': name,
                        'name': name.replace('_', ' '),
                        'status': status,
                        'uri': uri,
                        'type': device_type,
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
                            
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"Error listing printers: {e}")
        except Exception as e:
            print(f"Unexpected error in list_printers: {e}")
            
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
