#!/bin/bash
set -e

# Check if main.py exists in /app
if [ ! -f "/app/main.py" ]; then
    echo "=========================================="
    echo "ERROR: Application files not found!"
    echo "=========================================="
    echo ""
    echo "The /app directory does not contain the application code."
    echo "This usually happens when you incorrectly mount a volume to /app."
    echo ""
    echo "SOLUTION:"
    echo "  1. Remove any volume mapping to /app"
    echo "  2. Use /data for persistent data storage instead"
    echo ""
    echo "CORRECT Docker volume configuration:"
    echo "  -v /mnt/user/appdata/Scan2Target:/data"
    echo ""
    echo "INCORRECT (DO NOT USE):"
    echo "  -v /mnt/user/appdata/Scan2Target:/app"
    echo ""
    echo "For Unraid users:"
    echo "  Container Path should be: /data"
    echo "  Host Path can be: /mnt/user/appdata/Scan2Target"
    echo ""
    echo "=========================================="
    exit 1
fi

echo "Starting Avahi daemon for scanner discovery..."

# Create dbus directory if it doesn't exist
mkdir -p /var/run/dbus

# Start dbus (required for Avahi)
if [ ! -f /var/run/dbus/pid ]; then
    dbus-daemon --system --fork 2>/dev/null || true
fi

# Start Avahi daemon directly
/usr/sbin/avahi-daemon --daemonize 2>/dev/null || echo "Note: Avahi may already be running or failed to start"

# Wait for Avahi to initialize and discover network devices
# Increased wait time to ensure scanner discovery is complete before app starts
sleep 5

echo "Starting Scan2Target application..."
# Start the main application - main.py liegt jetzt direkt in /app
exec uvicorn main:app --host 0.0.0.0 --port 8000
