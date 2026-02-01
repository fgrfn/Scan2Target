#!/bin/bash
# Quick debug script for scanner connectivity issues

set -e

echo "============================================================"
echo "Scan2Target Scanner Debug Tool"
echo "============================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if container is running
if ! docker ps | grep -q scan2target; then
    echo -e "${RED}✗ Container 'scan2target' is not running${NC}"
    echo "Start with: docker-compose up -d"
    exit 1
fi

echo -e "${GREEN}✓ Container is running${NC}"
echo ""

# 1. Check Health Status
echo "============================================================"
echo "1. Health Monitor Status"
echo "============================================================"
curl -s http://localhost:8000/api/v1/devices/health/status | python3 -m json.tool || echo "Failed to get health status"
echo ""

# 2. Recent Logs
echo "============================================================"
echo "2. Recent Startup Logs"
echo "============================================================"
docker logs --tail 50 scan2target 2>&1 | grep -E "(STARTUP|Starting|ready)" || echo "No startup logs found"
echo ""

# 3. Health Check Logs
echo "============================================================"
echo "3. Recent Health Check Logs"
echo "============================================================"
docker logs --tail 100 scan2target 2>&1 | grep -E "(HEALTH|ONLINE|OFFLINE|Health check)" | tail -20 || echo "No health check logs found"
echo ""

# 4. Scanner Discovery Logs
echo "============================================================"
echo "4. Scanner Discovery"
echo "============================================================"
docker logs --tail 200 scan2target 2>&1 | grep -E "(Scanner discovery|airscan-discover|found.*scanner)" | tail -10 || echo "No discovery logs found"
echo ""

# 5. Errors
echo "============================================================"
echo "5. Recent Errors"
echo "============================================================"
docker logs --tail 200 scan2target 2>&1 | grep -i error | tail -10 || echo -e "${GREEN}No errors found${NC}"
echo ""

# 6. Test scanner command directly in container
echo "============================================================"
echo "6. Direct Scanner Test (airscan-discover)"
echo "============================================================"
docker exec scan2target airscan-discover 2>&1 || echo "Failed to run airscan-discover"
echo ""

# 7. Check log files
echo "============================================================"
echo "7. Persistent Log File Status"
echo "============================================================"
if docker exec scan2target test -f /var/log/scan2target/app.log; then
    echo -e "${GREEN}✓ Log file exists${NC}"
    echo "Last 10 lines:"
    docker exec scan2target tail -10 /var/log/scan2target/app.log 2>&1
else
    echo -e "${YELLOW}! Log file not found${NC}"
fi
echo ""

# 8. Registered Devices
echo "============================================================"
echo "8. Registered Scanners"
echo "============================================================"
curl -s http://localhost:8000/api/v1/devices | python3 -m json.tool || echo "Failed to get devices"
echo ""

# Summary
echo "============================================================"
echo "Summary & Recommendations"
echo "============================================================"

# Count online/offline scanners
ONLINE=$(curl -s http://localhost:8000/api/v1/devices | grep -o '"status": "online"' | wc -l)
OFFLINE=$(curl -s http://localhost:8000/api/v1/devices | grep -o '"status": "offline"' | wc -l)
TOTAL=$((ONLINE + OFFLINE))

if [ "$TOTAL" -eq 0 ]; then
    echo -e "${YELLOW}! No scanners registered${NC}"
    echo "  → Add scanner via Web UI or API"
elif [ "$OFFLINE" -gt 0 ]; then
    echo -e "${YELLOW}! $OFFLINE of $TOTAL scanner(s) offline${NC}"
    echo "  → Check scanner power and network connection"
    echo "  → Check firewall settings"
    echo "  → Wait for next health check (every 60s)"
    echo "  → View logs: docker logs -f scan2target"
else
    echo -e "${GREEN}✓ All $TOTAL scanner(s) online${NC}"
fi

echo ""
echo "For more details:"
echo "  docker logs -f scan2target                     # Live logs"
echo "  docker exec scan2target tail -f /var/log/scan2target/app.log  # Detailed logs"
echo "  docker exec scan2target grep ERROR /var/log/scan2target/app.log  # All errors"
echo ""
echo "============================================================"
