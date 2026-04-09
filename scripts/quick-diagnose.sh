#!/bin/bash
# Quick scanner test script for your Docker server
# Run this on your Unraid server: bash diagnose.sh

echo "================================"
echo "Scan2Target Scanner-Diagnose"
echo "================================"
echo ""

# Check if container is running
if ! docker ps | grep -q scan2target; then
    echo "❌ Container 'scan2target' läuft nicht!"
    echo "Starten Sie den Container und versuchen Sie es erneut."
    exit 1
fi

echo "✓ Container läuft"
echo ""

echo "1. Avahi-Daemon Status"
echo "----------------------"
docker exec scan2target service avahi-daemon status 2>&1 | head -3
echo ""

echo "2. Scanner-Suche mit airscan-discover"
echo "--------------------------------------"
echo "Suche läuft (10 Sekunden)..."
docker exec scan2target timeout 10 airscan-discover 2>&1
echo ""

echo "3. Scanner-Suche mit scanimage -L"
echo "----------------------------------"
docker exec scan2target timeout 10 scanimage -L 2>&1
echo ""

echo "4. Netzwerk-Modus"
echo "-----------------"
NETWORK_MODE=$(docker inspect scan2target --format '{{.HostConfig.NetworkMode}}')
echo "Network Mode: $NETWORK_MODE"

if [ "$NETWORK_MODE" != "host" ]; then
    echo "⚠️  WARNUNG: Network Mode ist nicht 'host'!"
    echo "   Scanner-Discovery funktioniert nur mit 'host' Network Mode."
    echo "   Ändern Sie die Netzwerk-Einstellung auf 'Host' in Unraid."
fi
echo ""

echo "================================"
echo "Manuelle Scanner-Konfiguration"
echo "================================"
echo ""
echo "Falls keine Scanner gefunden wurden, können Sie einen Scanner"
echo "manuell über die IP-Adresse hinzufügen:"
echo ""
read -p "Scanner-IP-Adresse (oder Enter zum Überspringen): " SCANNER_IP

if [ ! -z "$SCANNER_IP" ]; then
    echo ""
    echo "Teste Verbindung zu $SCANNER_IP..."
    
    # Ping test
    if docker exec scan2target ping -c 2 "$SCANNER_IP" >/dev/null 2>&1; then
        echo "✓ Scanner ist erreichbar (Ping erfolgreich)"
    else
        echo "❌ Scanner ist nicht erreichbar (Ping fehlgeschlagen)"
        echo "   Prüfen Sie die IP-Adresse und Firewall-Einstellungen"
    fi
    
    echo ""
    echo "Teste eSCL-Endpunkt (Port 8080)..."
    RESPONSE=$(docker exec scan2target curl -s -m 3 "http://$SCANNER_IP:8080/eSCL/ScannerCapabilities" 2>&1)
    
    if echo "$RESPONSE" | grep -q "scan:ScannerCapabilities\|Version\|MakeAndModel"; then
        echo "✓ eSCL-Scanner gefunden auf Port 8080!"
        echo ""
        echo "Scanner manuell hinzufügen mit:"
        echo ""
        echo "curl -X POST http://localhost:8000/api/v1/devices/add \\"
        echo "  -H 'Content-Type: application/json' \\"
        echo "  -d '{"
        echo "    \"uri\": \"airscan:escl:Scanner:http://$SCANNER_IP:8080/eSCL/\","
        echo "    \"name\": \"Mein Scanner\","
        echo "    \"device_type\": \"scanner\","
        echo "    \"make\": \"HP\","
        echo "    \"model\": \"Scanner\","
        echo "    \"connection_type\": \"eSCL (Network)\""
        echo "  }'"
    else
        echo "⚠️  Kein eSCL auf Port 8080"
        echo ""
        echo "Versuche Port 80..."
        RESPONSE=$(docker exec scan2target curl -s -m 3 "http://$SCANNER_IP/eSCL/ScannerCapabilities" 2>&1)
        
        if echo "$RESPONSE" | grep -q "scan:ScannerCapabilities\|Version\|MakeAndModel"; then
            echo "✓ eSCL-Scanner gefunden auf Port 80!"
            echo ""
            echo "Scanner manuell hinzufügen mit:"
            echo ""
            echo "curl -X POST http://localhost:8000/api/v1/devices/add \\"
            echo "  -H 'Content-Type: application/json' \\"
            echo "  -d '{"
            echo "    \"uri\": \"airscan:escl:Scanner:http://$SCANNER_IP/eSCL/\","
            echo "    \"name\": \"Mein Scanner\","
            echo "    \"device_type\": \"scanner\","
            echo "    \"make\": \"HP\","
            echo "    \"model\": \"Scanner\","
            echo "    \"connection_type\": \"eSCL (Network)\""
            echo "  }'"
        else
            echo "❌ Kein eSCL-Scanner gefunden"
            echo ""
            echo "Mögliche Probleme:"
            echo "  - Scanner unterstützt kein eSCL/AirScan"
            echo "  - Scanner ist ausgeschaltet"
            echo "  - Falsche IP-Adresse"
            echo "  - Firewall blockiert Port 80/8080"
        fi
    fi
fi

echo ""
echo "================================"
echo "Weitere Hilfe"
echo "================================"
echo "Siehe: docs/scanner_manual_setup.md"
echo ""
