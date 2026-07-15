"""Target persistence and adapter-based delivery orchestration."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import List

from core.targets.adapters import get_adapter, normalize_target_type
from core.targets.models import TargetConfig
from core.targets.repository import TargetRepository

logger = logging.getLogger(__name__)


class TargetManager:
    """Create, validate and deliver targets through isolated adapters."""

    def __init__(self):
        self.repo = TargetRepository()

    @staticmethod
    def _target_type_key(target_type: str) -> str:
        return normalize_target_type(target_type)

    def list_targets(self) -> List[TargetConfig]:
        return self.repo.list()

    def create_target(self, target: TargetConfig, validate: bool = True) -> TargetConfig:
        self._ensure_supported(target)
        if validate:
            result = self._validate_target_config(target)
            if result.get("status") != "ok":
                raise ValueError(
                    f"Connection test failed: {result.get('message', 'Unable to connect')}"
                )
        return self.repo.create(target)

    def update_target(
        self, target_id: str, target: TargetConfig, validate: bool = True
    ) -> TargetConfig:
        target.id = target_id
        self._ensure_supported(target)
        if validate:
            result = self._validate_target_config(target)
            if result.get("status") != "ok":
                raise ValueError(
                    f"Connection test failed: {result.get('message', 'Unable to connect')}"
                )
        return self.repo.update(target)

    def delete_target(self, target_id: str) -> None:
        self.repo.delete(target_id)

    @staticmethod
    def _adapter(target: TargetConfig):
        adapter = get_adapter(target.type)
        if not adapter:
            raise ValueError(f"Unsupported target type: {target.type}")
        return adapter

    def _ensure_supported(self, target: TargetConfig) -> None:
        adapter = self._adapter(target)
        # Parse before storing so invalid typed configuration fails early even
        # when the caller intentionally skips a network connectivity test.
        adapter.parse_config(target)

    def _validate_target_config(self, target: TargetConfig) -> dict:
        return self._adapter(target).validate(target)

    def test_target(self, target_id: str) -> dict:
        target = self.repo.get(target_id)
        if not target:
            return {"target_id": target_id, "status": "error", "message": "Target not found"}
        result = self._validate_target_config(target)
        return {"target_id": target_id, **result}

    def deliver_once(self, target_id: str, file_path: str, metadata: dict) -> None:
        """Perform exactly one delivery attempt; retry policy lives elsewhere."""
        target = self.repo.get(target_id)
        if not target or not target.enabled:
            raise ValueError(f"Target {target_id} not found or disabled")
        file = Path(file_path)
        if not file.is_file():
            raise FileNotFoundError(f"File {file_path} not found")
        adapter = self._adapter(target)
        adapter.deliver(target, file, metadata)
        logger.info("Delivery to %s via %s completed", target.name, self._target_type_key(target.type))

    def deliver(
        self,
        target_id: str,
        file_path: str,
        metadata: dict,
        max_retries: int = 1,
    ) -> None:
        """Compatibility wrapper for callers not yet using the persistent queue."""
        last_error: Exception | None = None
        for attempt in range(max(1, max_retries)):
            try:
                self.deliver_once(target_id, file_path, metadata)
                return
            except Exception as exc:
                last_error = exc
                if attempt + 1 < max_retries:
                    time.sleep(min(2**attempt, 8))
        raise RuntimeError(f"Delivery failed: {last_error}") from last_error
