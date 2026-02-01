#!/bin/bash
set -e

echo "Starting Avahi daemon for scanner discovery..."

# Create dbus directory if it doesn't exist
mkdir -p /var/run/dbus

# Start dbus (required for Avahi)
if [ ! -f /var/run/dbus/pid ]; then
    dbus-daemon --system --fork 2>/dev/null || true
fi

# Start Avahi daemon directly
/usr/sbin/avahi-daemon --daemonize 2>/dev/null || echo "Note: Avahi may already be running or failed to start"

# Wait a moment for Avahi to initialize
sleep 2

echo "Starting Scan2Target application..."
# Start the main application - main.py liegt jetzt direkt in /app
exec uvicorn main:app --host 0.0.0.0 --port 8000
