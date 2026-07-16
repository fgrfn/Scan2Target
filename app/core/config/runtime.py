"""Small persisted runtime overrides that can safely change without redeploying."""
from __future__ import annotations

import json
import threading
from pathlib import Path

from core.config.settings import get_settings


class RuntimeConfig:
    """Persist mutable operator settings below the configured data directory."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._path = Path(get_settings().data_dir) / "config" / "runtime.json"
        self._values = self._load()

    def _load(self) -> dict:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, ValueError, TypeError):
            return {}

    @property
    def auth_enabled(self) -> bool:
        value = self._values.get("require_auth")
        return bool(value) if isinstance(value, bool) else get_settings().require_auth

    def set_auth_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._values["require_auth"] = bool(enabled)
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self._path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(self._values, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            temporary.replace(self._path)


_runtime_config: RuntimeConfig | None = None


def get_runtime_config() -> RuntimeConfig:
    global _runtime_config
    if _runtime_config is None:
        _runtime_config = RuntimeConfig()
    return _runtime_config
