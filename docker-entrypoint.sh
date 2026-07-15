#!/bin/sh
set -eu

if [ ! -f /app/main.py ]; then
    echo "ERROR: /app/main.py not found. Mount persistent data at /data, not /app." >&2
    exit 1
fi

RUN_USER="${SCAN2TARGET_RUN_USER:-scan2target}"
mkdir -p /run/dbus /run/avahi-daemon /data/scans /data/db /data/auth /data/logs /var/log/scan2target /tmp/scan2target/scans

if [ "$(id -u)" = "0" ]; then
    chown -R "$RUN_USER:$RUN_USER" /data /var/log/scan2target /tmp/scan2target

    rm -f /run/dbus/pid /run/avahi-daemon/pid /run/avahi-daemon/socket
    pkill -x avahi-daemon 2>/dev/null || true
    pkill -x dbus-daemon 2>/dev/null || true

    if dbus-daemon --system --fork; then
        echo "dbus started"
    else
        echo "WARNING: dbus failed to start; mDNS discovery may be unavailable" >&2
    fi

    if avahi-daemon --daemonize --no-chroot; then
        echo "Avahi started"
    else
        echo "WARNING: Avahi failed to start; scanners can still be configured manually" >&2
    fi

    exec gosu "$RUN_USER" uvicorn main:app --host 0.0.0.0 --port 8000
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000
