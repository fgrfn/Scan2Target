#!/bin/bash
set -e

# Start Avahi daemon for mDNS scanner discovery
if command -v avahi-daemon &>/dev/null; then
    mkdir -p /var/run/avahi-daemon
    avahi-daemon --no-rlimits --daemonize 2>/dev/null || true
fi

# Ensure data directories exist
mkdir -p /data/db /var/log/scan2target /tmp/scan2target

cd /app

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level warning \
    --no-access-log
