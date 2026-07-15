"""Validation helpers for untrusted scan input and outbound webhooks."""
from __future__ import annotations

import ipaddress
import re
import socket
import unicodedata
from urllib.parse import urlparse

from core.config.settings import get_settings


_FILENAME_RE = re.compile(r"[^\w .()\-]+", flags=re.UNICODE)


class UnsafeWebhookURLError(ValueError):
    """Raised when a webhook URL targets a disallowed network address."""


def sanitize_filename_prefix(value: str | None, default: str = "scan") -> str:
    """Return a safe filename prefix without path traversal characters."""
    if value is None:
        return default

    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized:
        return default
    if any(char in normalized for char in ("/", "\\", "\x00")) or ".." in normalized:
        raise ValueError("Filename must not contain path separators or '..'")

    sanitized = _FILENAME_RE.sub("_", normalized).strip(" ._")
    if not sanitized:
        raise ValueError("Filename does not contain any usable characters")
    return sanitized[:128]


def validate_batch_pages(page_urls: list[str]) -> None:
    """Enforce page count and encoded request-size limits."""
    settings = get_settings()
    if len(page_urls) > settings.max_batch_pages:
        raise ValueError(f"A batch may contain at most {settings.max_batch_pages} pages")

    max_page_bytes = settings.max_batch_page_mb * 1024 * 1024
    max_total_bytes = settings.max_request_size_mb * 1024 * 1024
    total = 0
    for page in page_urls:
        encoded = page.split(",", 1)[1] if "," in page else page
        estimated_bytes = (len(encoded) * 3) // 4
        if estimated_bytes > max_page_bytes:
            raise ValueError(f"A single page may not exceed {settings.max_batch_page_mb} MB")
        total += estimated_bytes
    if total > max_total_bytes:
        raise ValueError(f"Batch payload may not exceed {settings.max_request_size_mb} MB")


def validate_webhook_url(url: str) -> str:
    """Validate webhook scheme and block local/private SSRF targets by default."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeWebhookURLError("Webhook URL must use http or https")
    if parsed.username or parsed.password:
        raise UnsafeWebhookURLError("Webhook URL must not contain embedded credentials")

    settings = get_settings()
    if settings.allow_private_webhooks:
        return url

    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as exc:
        raise UnsafeWebhookURLError("Webhook hostname could not be resolved") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise UnsafeWebhookURLError(
                "Webhook target resolves to a private or local address; "
                "set SCAN2TARGET_ALLOW_PRIVATE_WEBHOOKS=true only on trusted networks"
            )
    return url
