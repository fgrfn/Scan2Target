#!/bin/bash
# Scanner Diagnose-Tool

echo "================================"
echo "Scan2Target Scanner-Diagnose"
echo "================================"
echo ""

echo "1. Netzwerk-Status"
echo "-------------------"
echo "Container-Netzwerk-Modus:"
docker inspect scan2target --format '{{.HostConfig.NetworkMode}}'
echo ""

echo "2. Avahi-Daemon-Status"
echo "----------------------"
docker exec scan2target service avahi-daemon status 2>&1 | head -5
echo ""

echo "3. airscan-discover (eSCL/AirScan-Scanner)"
echo "-------------------------------------------"
echo "Suche nach Netzwerk-Scannern mit eSCL-Unterstützung..."
docker exec scan2target timeout 10 airscan-discover 2>&1
echo ""

echo "4. scanimage -L (SANE-Backends)"
echo "--------------------------------"
echo "Suche nach USB- und anderen SANE-Scannern..."
docker exec scan2target timeout 10 scanimage -L 2>&1
echo ""

echo "5. SANE-Backends"
echo "----------------"
docker exec scan2target ls -la /etc/sane.d/ 2>&1 | head -10
echo ""

echo "6. Netzwerk-Scanner-Dienste (mDNS)"
echo "-----------------------------------"
echo "Hinweis: Benötigt avahi-utils, wird bei fehlendem Paket übersprungen..."
docker exec scan2target which avahi-browse > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Suche nach _uscan._tcp (Scanner-Dienste)..."
    docker exec scan2target timeout 5 avahi-browse -rt _uscan._tcp 2>&1 | head -20
    echo ""
    echo "Suche nach _uscans._tcp (sichere Scanner-Dienste)..."
    docker exec scan2target timeout 5 avahi-browse -rt _uscans._tcp 2>&1 | head -20
else
    echo "avahi-browse nicht installiert. Installieren Sie: apt-get install avahi-utils"
fi
echo ""

echo "================================"
echo "Manuelle Scanner-Hinzufügung"
echo "================================"
echo ""
echo "Falls Ihr Scanner nicht gefunden wurde, können Sie ihn manuell hinzufügen:"
echo ""
echo "Beispiel für eSCL-Scanner (häufigste Methode):"
echo "curl -X POST http://localhost:8000/api/v1/devices/add \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo "    \"uri\": \"airscan:escl:MeinScanner:http://SCANNER_IP:8080/eSCL/\","
echo "    \"name\": \"Mein Scanner\","
echo "    \"device_type\": \"scanner\","
echo "    \"make\": \"HP\","
echo "    \"model\": \"ENVY 6400\","
echo "    \"connection_type\": \"eSCL (Network)\""
echo "  }'"
echo ""
echo "Weitere Informationen: docs/scanner_manual_setup.md"
echo ""

echo "================================"
echo "Netzwerk-Tests"
echo "================================"
echo ""
read -p "Scanner-IP-Adresse eingeben (oder Enter zum Überspringen): " SCANNER_IP

if [ ! -z "$SCANNER_IP" ]; then
    echo ""
    echo "Teste Verbindung zu $SCANNER_IP..."
    docker exec scan2target ping -c 3 "$SCANNER_IP" 2>&1
    echo ""
    
    echo "Teste eSCL-Endpunkt (Port 8080)..."
    docker exec scan2target curl -m 5 "http://$SCANNER_IP:8080/eSCL/ScannerCapabilities" 2>&1 | head -10
    echo ""
    
    echo "Teste alternativen Port (80)..."
    docker exec scan2target curl -m 5 "http://$SCANNER_IP/eSCL/ScannerCapabilities" 2>&1 | head -10
    echo ""
fi

echo "Diagnose abgeschlossen."
