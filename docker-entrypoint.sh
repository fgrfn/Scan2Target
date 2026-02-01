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

# Ensure any previous Avahi instance is stopped cleanly (handles fast restarts)
if pgrep -x avahi-daemon >/dev/null 2>&1; then
    echo "Stopping existing Avahi daemon..."
    avahi-daemon --kill 2>/dev/null || pkill -TERM avahi-daemon || true
    sleep 2
fi

# Remove stale PID files and sockets that would block startup
rm -f /var/run/avahi-daemon/pid
rm -f /var/run/avahi-daemon/socket

# Ensure dbus is running
if ! pgrep -x dbus-daemon >/dev/null 2>&1; then
    echo "Starting dbus..."
    dbus-daemon --system --fork 2>/dev/null || true
    sleep 1
fi

# Start Avahi daemon with error checking
echo "Starting Avahi daemon..."
if /usr/sbin/avahi-daemon --daemonize 2>&1; then
    echo "✓ Avahi daemon started successfully"
    
    # Wait for Avahi to initialize and discover network devices
    # Critical: mDNS needs time to propagate on the network
    echo "Waiting 10 seconds for mDNS scanner discovery..."
    sleep 10
else
    echo "⚠️  WARNING: Avahi daemon failed to start! Scanner discovery may not work."
    echo "⚠️  Network scanners will NOT be auto-discovered."
    sleep 2
fi

echo "Starting Scan2Target application..."
# Start the main application - main.py liegt jetzt direkt in /app
exec uvicorn main:app --host 0.0.0.0 --port 8000
