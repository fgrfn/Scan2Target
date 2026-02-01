"""Scanner health monitoring and automatic recovery."""
import asyncio
import time
from typing import Dict, List
from datetime import datetime
import subprocess

from core.devices.repository import DeviceRepository
from core.scanning.manager import ScannerManager


class ScannerHealthMonitor:
    """
    Monitors scanner health and automatically updates device status.
    
    Features:
    - Periodic scanner availability checks
    - Automatic status updates (online/offline)
    - Configurable check intervals
    - Non-blocking background operation
    """
    
    def __init__(self, check_interval: int = 60):
        """
        Initialize health monitor.
        
        Args:
            check_interval: Seconds between health checks (default: 60)
        """
        self.check_interval = check_interval
        self.is_running = False
        self._task = None
        self._last_check = 0
        self._scanner_status: Dict[str, Dict] = {}
        
    async def start(self):
        """Start the health monitoring background task."""
        if self.is_running:
            print("[HEALTH] Scanner health monitor already running")
            return
            
        self.is_running = True
        self._task = asyncio.create_task(self._monitor_loop())
        print(f"[HEALTH] Scanner health monitor started (interval: {self.check_interval}s)")
    
    async def stop(self):
        """Stop the health monitoring background task."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("[HEALTH] Scanner health monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.is_running:
            try:
                await self._check_scanners()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[HEALTH] Error in monitor loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_scanners(self):
        """Check all registered scanners and update their status."""
        try:
            device_repo = DeviceRepository()
            registered_devices = device_repo.list_devices(device_type='scanner', active_only=True)
            
            if not registered_devices:
                print("[HEALTH] No registered scanners to check")
                return
            
            print(f"[HEALTH] Checking {len(registered_devices)} registered scanner(s)...")
            
            # Discover currently available scanners
            scanner_manager = ScannerManager()
            available_scanners = await asyncio.to_thread(scanner_manager.list_devices)
            available_uris = {scanner['id'] for scanner in available_scanners}
            
            # Check each registered device
            for device in registered_devices:
                was_online = self._scanner_status.get(device.uri, {}).get('online', False)
                is_online = device.uri in available_uris
                
                # Update status cache
                self._scanner_status[device.uri] = {
                    'online': is_online,
                    'last_check': datetime.now(),
                    'name': device.name
                }
                
                # Log status changes
                if is_online != was_online:
                    if is_online:
                        print(f"[HEALTH] ✓ Scanner '{device.name}' is now ONLINE")
                        # Update last_seen in database
                        device_repo.update_last_seen(device.id)
                    else:
                        print(f"[HEALTH] ✗ Scanner '{device.name}' is now OFFLINE")
            
            self._last_check = time.time()
            
            # Summary
            online_count = sum(1 for s in self._scanner_status.values() if s['online'])
            total_count = len(registered_devices)
            print(f"[HEALTH] Status: {online_count}/{total_count} scanner(s) online")
            
        except Exception as e:
            print(f"[HEALTH] Error checking scanners: {e}")
    
    def get_scanner_status(self, uri: str) -> Dict:
        """
        Get cached status for a specific scanner.
        
        Returns:
            Dict with 'online', 'last_check' keys, or empty dict if unknown
        """
        return self._scanner_status.get(uri, {})
    
    def get_all_status(self) -> Dict[str, Dict]:
        """Get cached status for all scanners."""
        return self._scanner_status.copy()
    
    async def check_scanner_now(self, uri: str) -> bool:
        """
        Immediately check if a specific scanner is reachable.
        
        Args:
            uri: Scanner URI (SANE device ID)
            
        Returns:
            True if scanner is online, False otherwise
        """
        try:
            print(f"[HEALTH] Checking scanner: {uri}")
            scanner_manager = ScannerManager()
            available_scanners = await asyncio.to_thread(scanner_manager.list_devices)
            available_uris = {scanner['id'] for scanner in available_scanners}
            
            is_online = uri in available_uris
            
            # Update cache
            self._scanner_status[uri] = {
                'online': is_online,
                'last_check': datetime.now()
            }
            
            # Update database if online
            if is_online:
                device_repo = DeviceRepository()
                # Find device by URI
                devices = device_repo.list_devices(device_type='scanner', active_only=True)
                for device in devices:
                    if device.uri == uri:
                        device_repo.update_last_seen(device.id)
                        break
            
            return is_online
            
        except Exception as e:
            print(f"[HEALTH] Error checking scanner {uri}: {e}")
            return False


# Global instance
_health_monitor: ScannerHealthMonitor = None


def get_health_monitor(check_interval: int = 60) -> ScannerHealthMonitor:
    """
    Get or create the global health monitor instance.
    
    Args:
        check_interval: Seconds between checks (only used when creating)
    """
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = ScannerHealthMonitor(check_interval)
    return _health_monitor
