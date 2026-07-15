"""Validation tests for paths and manual multi-page requests."""
from __future__ import annotations

import pytest

from core.validation import sanitize_filename_prefix, validate_batch_pages


def test_filename_prefix_rejects_path_traversal():
    with pytest.raises(ValueError):
        sanitize_filename_prefix("../../etc/passwd")
    with pytest.raises(ValueError):
        sanitize_filename_prefix("folder\\scan")


def test_filename_prefix_normalizes_untrusted_characters():
    assert sanitize_filename_prefix(" Rechnung: Juli 2026 ") == "Rechnung_ Juli 2026"


def test_batch_limits_page_count_and_size(monkeypatch):
    monkeypatch.setenv("SCAN2TARGET_MAX_BATCH_PAGES", "2")
    monkeypatch.setenv("SCAN2TARGET_MAX_BATCH_PAGE_MB", "1")
    monkeypatch.setenv("SCAN2TARGET_MAX_REQUEST_SIZE_MB", "2")

    from core.config.settings import get_settings

    get_settings.cache_clear()
    validate_batch_pages(["data:image/png;base64,AAAA", "data:image/png;base64,AAAA"])
    with pytest.raises(ValueError, match="at most 2"):
        validate_batch_pages(["AAAA", "AAAA", "AAAA"])
    with pytest.raises(ValueError, match="single page"):
        validate_batch_pages(["A" * (2 * 1024 * 1024)])
    get_settings.cache_clear()
