"""Target management and delivery handlers."""
from __future__ import annotations
from typing import List

from app.core.targets.models import TargetConfig


class TargetManager:
    """Create, update, and test targets; delegate delivery."""

    def __init__(self):
        self._targets: dict[str, TargetConfig] = {}

    def list_targets(self) -> List[TargetConfig]:
        return list(self._targets.values())

    def create_target(self, target: TargetConfig) -> TargetConfig:
        self._targets[target.id] = target
        return target

    def update_target(self, target_id: str, target: TargetConfig) -> TargetConfig:
        self._targets[target_id] = target
        return target

    def delete_target(self, target_id: str) -> None:
        self._targets.pop(target_id, None)

    def test_target(self, target_id: str) -> dict:
        # TODO: perform connectivity test based on target type
        return {"target_id": target_id, "status": "ok"}

    def deliver(self, target_id: str, file_path: str, metadata: dict) -> None:
        # TODO: route to appropriate handler (SMB, SFTP, Email, Paperless, Webhook)
        pass
