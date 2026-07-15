"""Base interface for delivery target adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Type

from pydantic import BaseModel, ValidationError

from core.targets.models import TargetConfig


class DeliveryAdapter(ABC):
    config_model: Type[BaseModel]

    def parse_config(self, target: TargetConfig) -> BaseModel:
        try:
            return self.config_model.model_validate(self.normalize_config(target.config))
        except ValidationError as exc:
            raise ValueError(exc.errors(include_url=False)) from exc

    def normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        return dict(config)

    @abstractmethod
    def validate(self, target: TargetConfig) -> dict:
        """Validate target connectivity and credentials."""

    @abstractmethod
    def deliver(self, target: TargetConfig, file: Path, metadata: dict[str, Any]) -> None:
        """Deliver one file. Retry policy is handled outside adapters."""
