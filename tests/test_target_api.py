"""Regression tests for target API logging."""
from __future__ import annotations

import asyncio
import logging

from api import targets


def test_create_target_does_not_log_configuration_secrets(monkeypatch, caplog):
    target = targets.Target(
        id="archive",
        type="sftp",
        name="Archive",
        config={
            "host": "storage.example.test",
            "username": "scanner",
            "password": "top-secret-password",
            "api_token": "top-secret-token",
        },
    )

    class FakeManager:
        def create_target(self, target_config, validate=True):
            return target_config

    monkeypatch.setattr(targets, "TargetManager", FakeManager)
    caplog.set_level(logging.DEBUG, logger=targets.__name__)

    result = asyncio.run(targets.create_target(target, validate=False))

    assert result.id == "archive"
    assert "Creating target: Archive (type: sftp)" in caplog.text
    assert "top-secret-password" not in caplog.text
    assert "top-secret-token" not in caplog.text
    assert "storage.example.test" not in caplog.text
