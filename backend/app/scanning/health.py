"""Background scanner health monitor."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.scanning.discovery import check_scanner_online

logger = logging.getLogger(__name__)


class HealthMonitor:
    def __init__(self, check_interval: int = 60) -> None:
        self.check_interval = check_interval
        self._status: dict[str, dict] = {}  # uri → {online, last_check, name}
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._loop(), name="health-monitor")
        logger.info("Health monitor started (interval=%ds)", self.check_interval)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        startup_fast = 5 * 60  # first 5 minutes: faster checks
        elapsed = 0
        while True:
            interval = 15 if elapsed < startup_fast else self.check_interval
            await asyncio.sleep(interval)
            elapsed += interval
            await self._check_all()

    async def _check_all(self) -> None:
        from app.devices.service import get_all_uris, touch_last_seen, get_device_by_uri
        from app.ws.manager import get_ws_manager

        uris = await asyncio.to_thread(get_all_uris)
        ws = get_ws_manager()

        for uri in uris:
            prev = self._status.get(uri, {}).get("online")
            online = await asyncio.to_thread(check_scanner_online, uri)
            self._status[uri] = {"online": online, "last_check": datetime.now(timezone.utc).isoformat()}

            dev = await asyncio.to_thread(get_device_by_uri, uri)
            if online and dev:
                await asyncio.to_thread(touch_last_seen, dev["id"])

            if prev != online:
                name = dev["name"] if dev else uri
                logger.info("Scanner %r → %s", name, "ONLINE" if online else "OFFLINE")
                await ws.broadcast_scanner(uri, online, name)

    def get_status(self, uri: str) -> dict:
        return self._status.get(uri, {"online": None, "last_check": None})

    def get_all_status(self) -> dict[str, dict]:
        return dict(self._status)

    async def check_now(self, uri: str) -> bool:
        online = await asyncio.to_thread(check_scanner_online, uri)
        self._status[uri] = {"online": online, "last_check": datetime.now(timezone.utc).isoformat()}
        return online


_monitor: HealthMonitor | None = None


def get_health_monitor(check_interval: int = 60) -> HealthMonitor:
    global _monitor
    if _monitor is None:
        _monitor = HealthMonitor(check_interval)
    return _monitor
