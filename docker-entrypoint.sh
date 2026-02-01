#!/bin/bash
set -e

echo "Starting Avahi daemon for scanner discovery..."
# Start Avahi daemon for mDNS/scanner discovery
service avahi-daemon start

# Wait a moment for Avahi to initialize
sleep 2

echo "Starting Scan2Target application..."
# Start the main application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
