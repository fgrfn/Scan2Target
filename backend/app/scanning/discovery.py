"""Scanner discovery via airscan-discover and scanimage -L."""
from __future__ import annotations

import logging
import re
import subprocess

logger = logging.getLogger(__name__)

SCAN_PROFILES = [
    {"id": "doc_200_gray_pdf",  "name": "Document 200 DPI (Gray)", "dpi": 200, "color_mode": "Gray",  "format": "pdf",  "source": "Flatbed"},
    {"id": "doc_200_gray_adf",  "name": "Document 200 DPI (ADF)",  "dpi": 200, "color_mode": "Gray",  "format": "pdf",  "source": "ADF"},
    {"id": "color_300_pdf",     "name": "Color 300 DPI",            "dpi": 300, "color_mode": "Color", "format": "pdf",  "source": "Flatbed"},
    {"id": "gray_150_pdf",      "name": "Grayscale 150 DPI",        "dpi": 150, "color_mode": "Gray",  "format": "pdf",  "source": "Flatbed"},
    {"id": "photo_600_jpeg",    "name": "Photo 600 DPI",            "dpi": 600, "color_mode": "Color", "format": "jpeg", "source": "Flatbed"},
]


def _timeout() -> int:
    from app.app_settings.service import get_setting
    return get_setting("command_timeout", 15)


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def discover_airscan() -> list[dict]:
    """Discover eSCL/AirScan scanners via airscan-discover."""
    try:
        r = _run(["airscan-discover"], _timeout())
        devices = []
        for line in r.stdout.splitlines():
            # Format: "  Name = URI"
            m = re.match(r"\s+(.+?)\s*=\s*(airscan:.+)", line)
            if m:
                name, uri = m.group(1).strip(), m.group(2).strip()
                devices.append({"uri": uri, "name": name,
                                "connection_type": "eSCL", "make": None, "model": None})
        return devices
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.debug("airscan-discover not available: %s", exc)
        return []
    except Exception as exc:
        logger.warning("airscan-discover error: %s", exc)
        return []


def discover_sane() -> list[dict]:
    """Discover SANE backends via scanimage -L."""
    try:
        r = _run(["scanimage", "-L"], _timeout())
        devices = []
        for line in r.stdout.splitlines():
            m = re.match(r"device\s+`([^']+)'\s+is\s+a\s+(.*)", line)
            if m:
                uri, desc = m.group(1), m.group(2)
                conn = "eSCL" if "airscan" in uri else ("USB" if "usb" in uri.lower() else "Network")
                devices.append({"uri": uri, "name": desc.split(" ")[0] or uri,
                                "connection_type": conn, "make": None, "model": None})
        return devices
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.debug("scanimage not available: %s", exc)
        return []
    except Exception as exc:
        logger.warning("scanimage -L error: %s", exc)
        return []


def discover_all() -> list[dict]:
    """Merge airscan + SANE discovery, de-duplicate by URI."""
    seen: set[str] = set()
    result: list[dict] = []
    for d in discover_airscan() + discover_sane():
        if d["uri"] not in seen:
            seen.add(d["uri"])
            result.append(d)
    return result


def check_scanner_online(uri: str, timeout: int = 5) -> bool:
    """Quick reachability check.

    For eSCL/airscan URIs (contain an http:// URL) we GET /ScannerCapabilities —
    this is fast, auth-free, and reliable without needing scanimage.
    For other URI types (USB, etc.) we fall back to scanimage -L.
    """
    import re as _re
    import requests as _req

    m = _re.search(r'(https?://[^\s]+)', uri)
    if m:
        base = m.group(1).rstrip('/')
        try:
            r = _req.get(f"{base}/ScannerCapabilities", timeout=timeout)
            return r.status_code == 200
        except Exception:
            return False
    # Fallback: check if URI appears in scanimage device list
    try:
        r = _run(["scanimage", "-L"], timeout)
        return uri in r.stdout
    except Exception:
        return False
