# Scanner Health Monitoring

## Problem

Nach einem Neustart des Docker-Containers erscheinen Scanner als offline, auch wenn sie verfügbar sind. Dies geschieht, weil:

1. Der Scanner beim Start des Containers möglicherweise noch nicht erreichbar ist
2. Nur eine einmalige Prüfung beim Start durchgeführt wird
3. Keine kontinuierliche Überwachung der Scanner-Verfügbarkeit erfolgt

## Lösung

Ein automatischer Health-Check-Service wurde implementiert, der:

- **Automatisch** die Erreichbarkeit aller registrierten Scanner prüft
- **Kontinuierlich** im Hintergrund läuft
- **Statusänderungen** erkennt und loggt
- **Konfigurierbar** ist über Umgebungsvariablen

## Features

### Automatische Überwachung

Der Health-Monitor prüft regelmäßig alle registrierten Scanner und aktualisiert deren Status:

```
[HEALTH] Checking 1 registered scanner(s)...
[HEALTH] ✓ Scanner 'HP ENVY 6400 series' is now ONLINE
[HEALTH] Status: 1/1 scanner(s) online
```

### Konfiguration

Über Umgebungsvariablen können Sie das Verhalten anpassen:

```yaml
# docker-compose.yml oder .env
environment:
  # Intervall für Health-Checks (in Sekunden)
  SCAN2TARGET_HEALTH_CHECK_INTERVAL: 60  # Standard: 60 Sekunden
  
  # Intervall für Scanner-Cache (in Sekunden)
  SCAN2TARGET_SCANNER_CHECK_INTERVAL: 30  # Standard: 30 Sekunden
```

### API Endpoints

#### Health-Status abrufen

Zeigt den Gesamtstatus aller Scanner:

```bash
GET /api/v1/devices/health/status
```

Response:
```json
{
  "monitor_active": true,
  "check_interval": 60,
  "last_check": 1738531200,
  "total_scanners": 1,
  "online_scanners": 1,
  "offline_scanners": 0,
  "scanners": [
    {
      "id": "HP_ENVY_6400",
      "name": "HP ENVY 6400 series",
      "uri": "airscan:escl:HP_ENVY_6400:http://10.10.30.146:8080/eSCL/",
      "online": true,
      "last_check": "2026-02-01T10:30:00",
      "last_seen": "2026-02-01T10:30:00"
    }
  ]
}
```

#### Einzelnen Scanner prüfen

Sofortige Prüfung eines spezifischen Scanners:

```bash
GET /api/v1/devices/{device_id}/check
```

Response (online):
```json
{
  "online": true,
  "device_id": "HP_ENVY_6400",
  "message": "Scanner is online and ready"
}
```

Response (offline):
```json
{
  "online": false,
  "device_id": "HP_ENVY_6400",
  "message": "Scanner is offline or not responding",
  "suggestion": "Check if scanner is powered on and connected to network"
}
```

## Architektur

### Komponenten

1. **ScannerHealthMonitor** (`core/scanning/health.py`)
   - Hintergrund-Service für kontinuierliche Überwachung
   - Asyncio-basiert, non-blocking
   - Globale Singleton-Instanz

2. **API Integration** (`api/devices.py`)
   - Verwendet Health-Monitor für Status-Abfragen
   - Neue Endpoints für Health-Checks
   - Fallback auf Cache bei Bedarf

3. **Lifecycle Management** (`main.py`)
   - Startet Health-Monitor beim App-Start
   - Stoppt Monitor beim Shutdown
   - Konfigurierbar über Umgebungsvariablen

### Ablauf

```
App Start
  ↓
Scanner Cache initialisieren
  ↓
Health Monitor starten
  ↓
┌─────────────────────────────────┐
│  Background Loop (60s Intervall) │
│                                  │
│  1. Alle Scanner aus DB laden    │
│  2. Verfügbare Scanner erkennen  │
│  3. Status vergleichen           │
│  4. Änderungen loggen            │
│  5. DB aktualisieren (last_seen) │
│  6. Warten...                    │
└─────────────────────────────────┘
  ↓
App Shutdown
  ↓
Health Monitor stoppen
```

## Verwendung

### Nach Container-Restart

Der Health-Monitor startet automatisch und prüft alle registrierten Scanner:

1. **Sofort beim Start**: Initiale Scanner-Cache-Erstellung
2. **Nach 60 Sekunden**: Erste automatische Health-Check
3. **Alle 60 Sekunden**: Kontinuierliche Überwachung

### Manuelle Prüfung

Sie können jederzeit manuell prüfen:

```bash
# Alle Scanner
curl http://localhost:8000/api/v1/devices/health/status

# Einzelner Scanner
curl http://localhost:8000/api/v1/devices/HP_ENVY_6400/check
```

### Logs überwachen

```bash
# Docker Logs
docker logs -f scan2target

# Relevante Log-Meldungen
[STARTUP] Initializing scanner cache...
[STARTUP] Health monitor started (interval: 60s)
[HEALTH] Checking 1 registered scanner(s)...
[HEALTH] ✓ Scanner 'HP ENVY 6400' is now ONLINE
[HEALTH] Status: 1/1 scanner(s) online
```

## Fehlerbehebung

### Scanner bleibt offline

1. **Prüfen Sie die Logs**:
   ```bash
   docker logs scan2target | grep HEALTH
   ```

2. **Manuelle Prüfung**:
   ```bash
   curl http://localhost:8000/api/v1/devices/{device_id}/check
   ```

3. **Netzwerk prüfen**:
   - Ist der Scanner eingeschaltet?
   - Ist der Scanner im gleichen Netzwerk?
   - Firewall-Regeln prüfen

4. **Scanner neu hinzufügen**:
   - Scanner entfernen
   - Scanner neu erkennen lassen
   - Scanner wieder hinzufügen

### Health-Monitor läuft nicht

1. **Status prüfen**:
   ```bash
   curl http://localhost:8000/api/v1/devices/health/status
   ```
   
   Sollte `"monitor_active": true` zeigen

2. **Container neu starten**:
   ```bash
   docker-compose restart
   ```

### Zu häufige/seltene Checks

Passen Sie das Intervall an:

```yaml
# docker-compose.yml
environment:
  SCAN2TARGET_HEALTH_CHECK_INTERVAL: 30  # Sekunden
```

```bash
# Container neu starten
docker-compose up -d
```

## Best Practices

1. **Intervall-Konfiguration**:
   - USB-Scanner: 30-60 Sekunden
   - Netzwerk-Scanner: 60-120 Sekunden
   - Viele Scanner: längere Intervalle

2. **Monitoring**:
   - Regelmäßig Logs prüfen
   - Health-Status-Endpoint überwachen
   - Bei Problemen Intervall anpassen

3. **Performance**:
   - Standard-Intervalle sind für die meisten Setups optimal
   - Kürzere Intervalle = mehr Netzwerk-Traffic
   - Längere Intervalle = langsamere Erkennung

## Technische Details

### Dependency Injection

Der Health-Monitor wird als Singleton verwaltet:

```python
from core.scanning.health import get_health_monitor

# In API-Endpoints
health_monitor = get_health_monitor()
status = health_monitor.get_scanner_status(uri)
```

### Async-Safe

Alle Operations sind async-safe und blockieren nicht:

```python
# Automatische Thread-Pool-Verwendung
available_scanners = await asyncio.to_thread(scanner_manager.list_devices)

# Sofortige Prüfung
is_online = await health_monitor.check_scanner_now(uri)
```

### Status-Cache

Der Health-Monitor verwendet einen internen Cache:

```python
_scanner_status = {
    'scanner_uri': {
        'online': True,
        'last_check': datetime.now(),
        'name': 'HP ENVY 6400'
    }
}
```

## Migration

Keine Migration erforderlich! Das Feature ist:

- **Abwärtskompatibel**: Alle bestehenden APIs funktionieren weiter
- **Opt-in**: Konfiguration ist optional, Defaults sind sinnvoll
- **Keine DB-Änderungen**: Verwendet bestehende `last_seen` Spalte

Einfach Container neu starten:

```bash
docker-compose pull
docker-compose up -d
```
