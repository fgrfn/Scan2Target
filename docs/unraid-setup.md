# Scan2Target - Unraid Template Konfiguration

## Erforderliche Umgebungsvariablen

Fügen Sie diese Variablen in Ihrer Unraid-Docker-Template hinzu:

### 1. SCAN2TARGET_DATA_DIR
- **Name:** SCAN2TARGET_DATA_DIR
- **Key:** SCAN2TARGET_DATA_DIR
- **Value:** /data
- **Beschreibung:** Datenverzeichnis für Scans und Datenbank

### 2. SCAN2TARGET_DB_PATH
- **Name:** SCAN2TARGET_DB_PATH
- **Key:** SCAN2TARGET_DB_PATH
- **Value:** /data/db/scan2target.db
- **Beschreibung:** Pfad zur SQLite-Datenbank

### 3. SCAN2TARGET_SECRET_KEY (bereits vorhanden)
- **Name:** SCAN2TARGET_SECRET_KEY
- **Key:** SCAN2TARGET_SECRET_KEY
- **Value:** [Generieren Sie einen sicheren Schlüssel]
- **Beschreibung:** Verschlüsselungsschlüssel für Passwörter

### 4. SCAN2TARGET_REQUIRE_AUTH (optional)
- **Name:** SCAN2TARGET_REQUIRE_AUTH
- **Key:** SCAN2TARGET_REQUIRE_AUTH
- **Value:** false
- **Beschreibung:** Authentifizierung aktivieren (true/false)

## Wichtige Netzwerk-Einstellungen für Scanner-Erkennung

⚠️ **WICHTIG:** Für die Scanner-Erkennung sollten Sie:

### Option 1: Host-Netzwerk (Empfohlen)
- **Network Type:** Host
- **Vorteil:** Scanner-Discovery funktioniert automatisch (mDNS/Avahi)
- **Nachteil:** Container verwendet die Netzwerk-Ports des Hosts direkt

### Option 2: Custom Network mit macvlan (Ihre aktuelle Konfiguration)
- **Network Type:** Custom: eth0.30
- **Fixed IP:** 10.10.30.74
- **Vorteil:** Eigene IP-Adresse für den Container
- **Problem:** mDNS/Avahi funktioniert oft NICHT (Scanner-Discovery schlägt fehl)
- **Lösung:** Scanner manuell über IP-Adresse hinzufügen

### Option 3: Bridge mit Port-Mapping
- **Network Type:** Bridge
- **Port:** 8000:8000
- **Nachteil:** Scanner-Discovery funktioniert NICHT
- **Lösung:** Scanner manuell über IP-Adresse hinzufügen

## Vollständige Unraid-Template-Konfiguration

```xml
<?xml version="1.0"?>
<Container version="2">
  <Name>Scan2Target</Name>
  <Repository>ghcr.io/fgrfn/scan2target:dev</Repository>
  <Registry>https://ghcr.io/</Registry>
  <Network>host</Network>
  <Shell>sh</Shell>
  <Privileged>false</Privileged>
  <Support>https://github.com/fgrfn/Scan2Target</Support>
  <Project>https://github.com/fgrfn/Scan2Target</Project>
  <Overview>Web-based scanner-to-target routing system</Overview>
  <Category>Productivity:</Category>
  <WebUI>http://[IP]:8000</WebUI>
  <Icon>https://raw.githubusercontent.com/fgrfn/Scan2Target/main/app/web/public/icon-192.png</Icon>
  
  <Config Name="Data Directory" Target="/data" Default="/mnt/user/appdata/Scan2Target" Mode="rw" Description="Persistent data storage" Type="Path" Display="always" Required="true" Mask="false">/mnt/user/appdata/Scan2Target</Config>
  
  <Config Name="Secret Key" Target="SCAN2TARGET_SECRET_KEY" Default="changeme-generate-a-secure-random-key" Mode="" Description="Encryption key for passwords (CHANGE THIS!)" Type="Variable" Display="always" Required="true" Mask="true">changeme-generate-a-secure-random-key</Config>
  
  <Config Name="Data Directory Path" Target="SCAN2TARGET_DATA_DIR" Default="/data" Mode="" Description="Application data directory" Type="Variable" Display="advanced" Required="false" Mask="false">/data</Config>
  
  <Config Name="Database Path" Target="SCAN2TARGET_DB_PATH" Default="/data/db/scan2target.db" Mode="" Description="SQLite database file path" Type="Variable" Display="advanced" Required="false" Mask="false">/data/db/scan2target.db</Config>
  
  <Config Name="Require Authentication" Target="SCAN2TARGET_REQUIRE_AUTH" Default="false" Mode="" Description="Enable user authentication (true/false)" Type="Variable" Display="advanced" Required="false" Mask="false">false</Config>
</Container>
```

## Schnelle Lösung für Ihre aktuelle Konfiguration

Fügen Sie in Unraid unter "Show more settings..." diese Variablen hinzu:

1. **Variable hinzufügen:** Klicken Sie auf "+ Add another Path, Port, Variable, Label or Device"
2. **Config Type:** Variable
3. **Name:** Data Directory Path
4. **Key:** SCAN2TARGET_DATA_DIR
5. **Value:** /data

6. Wiederholen Sie für:
   - **Key:** SCAN2TARGET_DB_PATH
   - **Value:** /data/db/scan2target.db

## Scanner-Erkennung mit Custom Network

Da Sie ein Custom Network (eth0.30) verwenden, wird die automatische Scanner-Discovery wahrscheinlich **nicht funktionieren**. Sie müssen Scanner manuell hinzufügen:

### 1. Finden Sie die IP-Adresse Ihres Scanners
- In den Drucker/Scanner-Einstellungen
- Im Router (DHCP-Liste)
- Mit einem IP-Scanner (z.B. Fing, Advanced IP Scanner)

### 2. Testen Sie die Scanner-URL
```bash
# Im Container ausführen:
docker exec Scan curl http://SCANNER_IP:8080/eSCL/ScannerCapabilities
```

### 3. Scanner manuell über die Web-UI hinzufügen
- Gehen Sie zu: http://10.10.30.74:8000
- Geräte → "Scanner hinzufügen"
- URI: `airscan:escl:MeinScanner:http://SCANNER_IP:8080/eSCL/`
- Name: Beliebiger Name für Ihren Scanner

### 4. ODER über die API:
```bash
curl -X POST http://10.10.30.74:8000/api/v1/devices/add \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "airscan:escl:MeinScanner:http://192.168.1.100:8080/eSCL/",
    "name": "HP ENVY 6400",
    "device_type": "scanner",
    "make": "HP",
    "model": "ENVY 6400",
    "connection_type": "eSCL (Network)"
  }'
```

## Empfehlung

Für die beste Erfahrung mit automatischer Scanner-Erkennung:

**Ändern Sie Network Type auf "Host"** in Ihrer Unraid-Docker-Konfiguration.

Dann ist die Anwendung erreichbar unter: `http://UNRAID_SERVER_IP:8000`
