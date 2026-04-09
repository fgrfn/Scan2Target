# Scanner manuell hinzufügen

Wenn Ihr Scanner nicht automatisch gefunden wird, können Sie ihn manuell über die API hinzufügen.

## Methode 1: eSCL/AirScan Scanner (empfohlen für Netzwerk-Scanner)

Die meisten modernen Netzwerk-Scanner unterstützen eSCL (Apple AirScan). 

### Scanner-URL finden:

```bash
# Im Docker-Container ausführen:
docker exec scan2target airscan-discover
```

Falls nichts gefunden wird, testen Sie die URL manuell:

```bash
# Testen Sie ob Ihr Scanner eSCL unterstützt:
curl http://IHR_SCANNER_IP:8080/eSCL/ScannerCapabilities

# Oder probieren Sie andere Ports:
curl http://IHR_SCANNER_IP/eSCL/ScannerCapabilities
curl http://IHR_SCANNER_IP:80/eSCL/ScannerCapabilities
```

### Manuell hinzufügen (via API):

```bash
curl -X POST http://localhost:8000/api/v1/devices/add \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "airscan:escl:MeinScanner:http://192.168.1.100:8080/eSCL/",
    "name": "Mein Scanner",
    "device_type": "scanner",
    "make": "HP",
    "model": "ENVY 6400",
    "connection_type": "eSCL (Network)"
  }'
```

**URI-Format:** `airscan:escl:<NAME>:<URL>`
- `<NAME>`: Beliebiger Name (keine Leerzeichen, verwenden Sie `_`)
- `<URL>`: Die vollständige eSCL-URL (mit `/eSCL/` am Ende)

## Methode 2: HP-Drucker mit hpaio Backend

```bash
# Scanner-IP herausfinden und testen:
docker exec scan2target hp-probe -bnet

# Oder direkt mit IP:
curl -X POST http://localhost:8000/api/v1/devices/add \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "hpaio:/net/HP_LaserJet?ip=192.168.1.100",
    "name": "HP LaserJet Netzwerk",
    "device_type": "scanner",
    "make": "HP",
    "model": "LaserJet",
    "connection_type": "Network (HP)"
  }'
```

## Methode 3: Andere SANE Backends

```bash
# Verfügbare Backends anzeigen:
docker exec scan2target scanimage -L

# Beispiele:
# Canon PIXMA (USB): "pixma:04A91820_247F69"
# Epson (Netzwerk): "net:192.168.1.100:epson2:ES-1200C"
```

## Debugging

### Scanner im Netzwerk finden:

```bash
# 1. Netzwerk-Scanner suchen (mDNS/Bonjour):
docker exec scan2target avahi-browse -rt _scanner._tcp
docker exec scan2target avahi-browse -rt _uscan._tcp
docker exec scan2target avahi-browse -rt _uscans._tcp

# 2. eSCL-Dienste finden:
docker exec scan2target avahi-browse -rt _http._tcp | grep -i scan

# 3. Port-Scan auf Scanner-IP:
nmap -p 80,8080,8443,443,9100 192.168.1.100
```

### SANE-Konfiguration testen:

```bash
# SANE-Backends anzeigen:
docker exec scan2target scanimage -L

# Einen spezifischen Scanner testen:
docker exec scan2target scanimage --device-name "airscan:escl:MeinScanner:http://192.168.1.100:8080/eSCL/" --test

# Test-Scan (erstellt PNM-Datei):
docker exec scan2target scanimage --device-name "airscan:escl:..." --format=png > /tmp/test.png
```

### Avahi/mDNS prüfen:

```bash
# Avahi-Daemon Status:
docker exec scan2target service avahi-daemon status

# Falls nicht läuft:
docker exec scan2target service avahi-daemon start

# mDNS-Auflösung testen:
docker exec scan2target avahi-resolve-host-name MyScanner.local
```

## Häufige Probleme

### Scanner wird nicht gefunden

1. **Firewall blockiert**: 
   - Port 5353 (mDNS) muss offen sein
   - Scanner-Ports (8080, 80, 443) müssen erreichbar sein

2. **Netzwerk-Isolation**:
   - Docker muss `network_mode: host` verwenden
   - Scanner und Docker-Host müssen im gleichen Subnetz sein

3. **Scanner unterstützt kein eSCL**:
   - Ältere Scanner benötigen oft proprietäre Backends
   - Prüfen Sie HPLIP (HP), sane-backends (Epson, Canon, etc.)

### Scanner kann nicht scannen

1. **Falsche URI**:
   - Prüfen Sie ob die URL korrekt ist (mit `/eSCL/` am Ende)
   - Testen Sie die URL im Browser

2. **Authentifizierung erforderlich**:
   - Manche Scanner benötigen Login
   - Dies wird derzeit nicht unterstützt

3. **Scanner ist belegt**:
   - Scanner kann nur von einem Client gleichzeitig verwendet werden
   - Andere Anwendungen schließen

## Beispiel-Konfigurationen

### HP ENVY 6400 (Netzwerk):
```json
{
  "uri": "airscan:escl:HP_ENVY_6400:http://192.168.1.50:8080/eSCL/",
  "name": "HP ENVY 6400 Büro",
  "device_type": "scanner",
  "make": "HP",
  "model": "ENVY 6400 series",
  "connection_type": "eSCL (Network)"
}
```

### Canon PIXMA (USB):
```json
{
  "uri": "pixma:04A91820_247F69",
  "name": "Canon PIXMA MG5200",
  "device_type": "scanner",
  "make": "Canon",
  "model": "PIXMA MG5200",
  "connection_type": "USB"
}
```

### Epson WorkForce (Netzwerk):
```json
{
  "uri": "epson2:net:192.168.1.100",
  "name": "Epson WorkForce Pro",
  "device_type": "scanner",
  "make": "Epson",
  "model": "WorkForce Pro WF-3720",
  "connection_type": "Network (SANE)"
}
```
