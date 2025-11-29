"""Target configuration models."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class TargetConfig(BaseModel):
    id: str
    type: str
    name: str
    config: dict
    enabled: bool = True
    description: Optional[str] = None
