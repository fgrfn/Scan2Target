from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path


class BaseProvider(ABC):
    """All target providers implement this interface."""

    @abstractmethod
    def test(self, config: dict) -> None:
        """Test connectivity. Raise an exception with a clear message on failure."""

    @abstractmethod
    def deliver(self, config: dict, file_path: Path, filename: str) -> None:
        """Deliver file_path to the target. Raise on failure."""
