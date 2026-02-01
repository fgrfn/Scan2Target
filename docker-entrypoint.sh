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
    avahi-daemon --kill 2>/dev/null || pkill -9 avahi-daemon || true
    # Wait longer for complete shutdown
    sleep 3
fi

# Aggressive cleanup of stale files
rm -f /var/run/avahi-daemon/pid
rm -f /var/run/avahi-daemon/socket
rm -rf /var/run/avahi-daemon/*

# Ensure dbus is running
if ! pgrep -x dbus-daemon >/dev/null 2>&1; then
    echo "Starting dbus..."
    DBUS_OUTPUT=$(dbus-daemon --system --fork 2>&1)
    if [ $? -ne 0 ]; then
        echo "⚠️  dbus start failed: $DBUS_OUTPUT"
    fi
    sleep 2
fi

# Verify dbus is running
if ! pgrep -x dbus-daemon >/dev/null 2>&1; then
    echo "⚠️  WARNING: dbus is not running! Avahi requires dbus."
fi

# Start Avahi daemon with error checking and retry
echo "Starting Avahi daemon..."
MAX_AVAHI_RETRIES=3
AVAHI_RETRY=0

while [ $AVAHI_RETRY -lt $MAX_AVAHI_RETRIES ]; do
    # Capture both stdout and stderr for debugging
    AVAHI_OUTPUT=$(/usr/sbin/avahi-daemon --daemonize 2>&1)
    AVAHI_EXIT=$?
    
    if [ $AVAHI_EXIT -eq 0 ]; then
        echo "✓ Avahi daemon started successfully"
        
        # Verify it's actually running
        if pgrep -x avahi-daemon >/dev/null 2>&1; then
            echo "✓ Avahi process verified running (PID: $(pgrep -x avahi-daemon))"
        else
            echo "⚠️  Warning: Avahi reported success but process not found"
        fi
        
        # Wait for Avahi to initialize and discover network devices
        # Critical: mDNS needs time to propagate on the network
        echo "Waiting 12 seconds for mDNS scanner discovery..."
        sleep 12
        break
    else
        AVAHI_RETRY=$((AVAHI_RETRY + 1))
        echo "❌ Avahi start failed (Exit code: $AVAHI_EXIT)"
        echo "📋 Error output: $AVAHI_OUTPUT"
        
        # Additional diagnostics
        echo "🔍 Diagnostics:"
        echo "  - dbus running: $(pgrep -x dbus-daemon >/dev/null && echo 'YES' || echo 'NO')"
        echo "  - Avahi PID file exists: $(test -f /var/run/avahi-daemon/pid && echo 'YES' || echo 'NO')"
        echo "  - Avahi socket exists: $(test -S /var/run/avahi-daemon/socket && echo 'YES' || echo 'NO')"
        
        if [ $AVAHI_RETRY -lt $MAX_AVAHI_RETRIES ]; then
            echo "⚠️  Avahi start failed, retry $AVAHI_RETRY/$MAX_AVAHI_RETRIES in 3 seconds..."
            sleep 3
            # Clean up again before retry
            echo "🧹 Cleaning up for retry..."
            pkill -9 avahi-daemon 2>/dev/null || true
            rm -rf /var/run/avahi-daemon/*
            sleep 1
        else
            echo "⚠️  WARNING: Avahi daemon failed to start after $MAX_AVAHI_RETRIES attempts!"
            echo "⚠️  Network scanners will NOT be auto-discovered."
            echo "⚠️  Application will start anyway - scanners can be added manually."
            sleep 2
        fi
    fi
done

echo "Starting Scan2Target application..."
# Start the main application - main.py liegt jetzt direkt in /app
exec uvicorn main:app --host 0.0.0.0 --port 8000
