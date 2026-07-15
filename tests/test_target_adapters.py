"""Target adapter regression tests."""
from __future__ import annotations

import subprocess

from core.targets.adapters.registry import get_adapter, normalize_target_type
from core.targets.models import TargetConfig


def test_all_supported_target_types_have_adapters():
    for target_type in [
        "smb",
        "sftp",
        "email",
        "paperless",
        "webhook",
        "google-drive",
        "dropbox",
        "onedrive",
        "nextcloud",
    ]:
        assert get_adapter(target_type) is not None
    assert normalize_target_type("paperless-ngx") == "paperless"
    assert normalize_target_type("Google Drive") == "google-drive"


def test_smb_password_is_not_exposed_in_process_arguments(monkeypatch):
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    target = TargetConfig(
        id="smb",
        type="smb",
        name="SMB",
        config={
            "connection": "//fileserver/scans",
            "username": "scanner",
            "password": "super-secret-password",
        },
    )
    result = get_adapter("smb").validate(target)
    assert result["status"] == "ok"
    assert "super-secret-password" not in " ".join(captured["args"])
    assert "-A" in captured["args"]


def test_sftp_password_uses_environment_not_arguments(monkeypatch):
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    target = TargetConfig(
        id="sftp",
        type="sftp",
        name="SFTP",
        config={"host": "fileserver", "username": "scanner", "password": "secret"},
    )
    result = get_adapter("sftp").validate(target)
    assert result["status"] == "ok"
    assert "secret" not in " ".join(captured["args"])
    assert captured["env"]["SSHPASS"] == "secret"
    assert captured["args"][:2] == ["sshpass", "-e"]
