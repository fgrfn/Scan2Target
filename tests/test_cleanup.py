"""Cleanup regression tests."""
from __future__ import annotations

from core.cleanup import CleanupManager


def test_cleanup_all_handles_missing_scan_directory(tmp_path):
    manager = CleanupManager()
    manager.scan_dir = tmp_path / "not-created"

    result = manager.cleanup_all()

    assert result == {
        "thumbnails": {"deleted": 0, "freed_bytes": 0},
        "scans": {"deleted": 0, "freed_bytes": 0},
        "total_freed_mb": 0,
        "total_deleted": 0,
    }


def test_cleanup_helpers_report_zero_for_missing_scan_directory(tmp_path):
    manager = CleanupManager()
    manager.scan_dir = tmp_path / "not-created"

    assert manager.cleanup_old_thumbnails() == {"deleted": 0, "freed_bytes": 0}
    assert manager.cleanup_old_failed_scans() == {"deleted": 0, "freed_bytes": 0}
