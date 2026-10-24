"""Validation tests for paths and manual multi-page requests."""
from __future__ import annotations

import pytest

import core.validation as validation
from core.validation import (
    UnsafeWebhookURLError,
    sanitize_filename_prefix,
    validate_batch_pages,
    validate_webhook_url,
)


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


@pytest.mark.parametrize(
    "url",
    ["https://example.com:not-a-port/hook", "https://example.com:70000/hook"],
)
def test_webhook_rejects_invalid_port_before_dns_lookup(monkeypatch, url):
    monkeypatch.setattr(
        validation,
        "get_settings",
        lambda: type("Settings", (), {"allow_private_webhooks": False})(),
    )
    monkeypatch.setattr(
        validation.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: pytest.fail("DNS lookup must not run for an invalid port"),
    )

    with pytest.raises(UnsafeWebhookURLError, match="invalid port"):
        validate_webhook_url(url)


@pytest.mark.parametrize(
    ("url", "expected_port"),
    [("http://example.com/hook", 80), ("https://example.com/hook", 443)],
)
def test_webhook_uses_scheme_specific_default_port(monkeypatch, url, expected_port):
    requested_ports = []
    monkeypatch.setattr(
        validation,
        "get_settings",
        lambda: type("Settings", (), {"allow_private_webhooks": False})(),
    )

    def resolve(_host, port, **_kwargs):
        requested_ports.append(port)
        return [(None, None, None, None, ("93.184.216.34", port))]

    monkeypatch.setattr(validation.socket, "getaddrinfo", resolve)

    assert validate_webhook_url(url) == url
    assert requested_ports == [expected_port]
