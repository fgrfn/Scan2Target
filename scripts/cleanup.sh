#!/bin/bash
# Scan2Target daily cleanup — triggers the maintenance API endpoint.
# Add to crontab: 0 3 * * * /opt/scan2target/scripts/cleanup.sh

HOST="${SCAN2TARGET_HOST:-localhost}"
PORT="${SCAN2TARGET_PORT:-8000}"
LOG="/var/log/scan2target-cleanup.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') Running cleanup..." >> "$LOG"

result=$(curl -sf -X POST "http://${HOST}:${PORT}/api/v1/maintenance/cleanup" \
    -H "Content-Type: application/json" 2>&1)

if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') Cleanup done: ${result}" >> "$LOG"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') Cleanup failed: ${result}" >> "$LOG"
fi

# Rotate log if > 10 MB
if [ -f "$LOG" ]; then
    size=$(stat -c%s "$LOG" 2>/dev/null || stat -f%z "$LOG" 2>/dev/null || echo 0)
    if [ "$size" -gt 10485760 ]; then
        mv "$LOG" "${LOG}.old"
        echo "$(date '+%Y-%m-%d %H:%M:%S') Log rotated." > "$LOG"
    fi
fi
