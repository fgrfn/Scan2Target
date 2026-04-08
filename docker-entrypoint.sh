#!/bin/bash
set -e

# ── Data directories ──────────────────────────────────────────────────────────
mkdir -p /data/db /var/log/scan2target /tmp/scan2target

# ── Avahi (mDNS scanner discovery) ───────────────────────────────────────────
# Avahi requires host networking (network_mode: host) and a writable /run.
# It will silently do nothing if unavailable — scanner discovery falls back
# to manual configuration.
if command -v avahi-daemon &>/dev/null; then
    mkdir -p /var/run/avahi-daemon
    if avahi-daemon --no-rlimits --daemonize 2>/dev/null; then
        echo "[entrypoint] avahi-daemon started — mDNS discovery enabled"
    else
        echo "[entrypoint] avahi-daemon failed to start (OK in bridge-network mode — use manual scanner IPs)"
    fi
fi

# ── Optional tool availability warnings ──────────────────────────────────────
for cmd in scanimage airscan-discover convert smbclient sftp; do
    command -v "$cmd" &>/dev/null || echo "[entrypoint] WARN: $cmd not found — related features disabled"
done

cd /app

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level warning \
    --no-access-log
