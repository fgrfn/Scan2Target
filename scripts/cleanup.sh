#!/bin/bash
# Scan2Target daily cleanup cron job
# Add to crontab: 0 3 * * * /opt/scan2target/scripts/cleanup.sh

cd /opt/scan2target

# Run cleanup
python3 -m app.core.cleanup >> /var/log/scan2target-cleanup.log 2>&1

# Rotate log if larger than 10MB
LOG_FILE="/var/log/scan2target-cleanup.log"
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null)
    if [ "$LOG_SIZE" -gt 10485760 ]; then
        mv "$LOG_FILE" "$LOG_FILE.old"
        echo "$(date): Log rotated" > "$LOG_FILE"
    fi
fi
