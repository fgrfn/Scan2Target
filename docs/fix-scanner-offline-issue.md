# Fix: Scanner offline nach Container-Restart

## Problem

Scanner wurden nach einem Docker-Container-Neustart als offline angezeigt, auch wenn sie verfügbar waren.

### Ursachen

1. **Einmalige Prüfung beim Start**: Scanner-Discovery erfolgte nur einmal beim Startup
2. **Timing-Problem**: Scanner war beim Start möglicherweise noch nicht bereit
3. **Keine Wiederholung**: Bei Fehlschlag keine erneuten Versuche
4. **Fehlende Logs**: Schwierig zu debuggen, was beim Start passierte

## Lösung

### 1. Robuste Scanner-Discovery beim Start

**Datei:** [`app/api/devices.py`](../app/api/devices.py)

- **Mehrfache Versuche**: Bis zu 3 Versuche mit Delays (0s, 2s, 5s)
- **Intelligente Retry-Logik**: Nur wiederholen, wenn keine Scanner gefunden wurden
- **Detailliertes Logging**: Jeder Versuch wird geloggt

```python
def init_scanner_cache():
    max_attempts = 3
    delays = [0, 2, 5]
    
    for attempt in range(max_attempts):
        # Warten zwischen Versuchen
        if attempt > 0:
            time.sleep(delays[attempt])
        
        # Scanner suchen
        devices = scanner_manager.list_devices()
        
        if devices:
            # Erfolg!
            return
```

### 2. Automatisches Health-Monitoring

**Datei:** [`app/core/scanning/health.py`](../app/core/scanning/health.py)

- **Background-Task**: Läuft kontinuierlich im Hintergrund
- **Regelmäßige Checks**: Alle 60 Sekunden (konfigurierbar)
- **Status-Tracking**: Erkennt Online/Offline-Änderungen
- **Automatische Recovery**: Findet Scanner, die später online kommen

### 3. Umfassendes Logging

**Dateien:**
- [`app/core/logging_config.py`](../app/core/logging_config.py) (neu)
- [`docs/logging.md`](../docs/logging.md) (neu)

**Features:**
- Console-Logging (für `docker logs`)
- Persistentes File-Logging (`/var/log/scan2target/app.log`)
- Automatische Log-Rotation (10 MB pro File, 5 Backups)
- DEBUG-Level in Files, INFO in Console

### 4. Docker-Integration

**Datei:** [`docker-compose.yml`](../docker-compose.yml)

Neue Konfiguration:

```yaml
volumes:
  # Neue: Persistente Logs
  - scan2target-logs:/var/log/scan2target

environment:
  # Neue: Log-Verzeichnis
  - SCAN2TARGET_LOG_DIR=/var/log/scan2target
  
  # Neue: Health-Check Intervalle
  - SCAN2TARGET_HEALTH_CHECK_INTERVAL=60
  - SCAN2TARGET_SCANNER_CHECK_INTERVAL=30
```

## Was passiert jetzt beim Start?

### Startup-Sequenz

```
1. Container startet
   ↓
2. Logging wird initialisiert
   → Console + File-Handler
   ↓
3. Datenbank initialisieren
   ↓
4. Scanner-Cache initialisieren
   → Versuch 1: Sofort
   → Wenn leer: Versuch 2 nach 2s
   → Wenn leer: Versuch 3 nach 5s
   → Logging: Alle gefundenen Scanner
   ↓
5. Health-Monitor starten
   → Background-Task
   → Prüft alle 60s
   ↓
6. App bereit!
```

### Laufender Betrieb

```
Jede Minute (konfigurierbar):
  ┌─────────────────────────────┐
  │ Health-Monitor Check         │
  │                             │
  │ 1. Registrierte Scanner     │
  │    aus DB laden             │
  │                             │
  │ 2. Verfügbare Scanner       │
  │    erkennen (airscan)       │
  │                             │
  │ 3. Status vergleichen       │
  │    - War offline, jetzt on? │
  │    - War online, jetzt off? │
  │                             │
  │ 4. Änderungen loggen        │
  │    ✓ Scanner XY ist ONLINE  │
  │    ✗ Scanner AB ist OFFLINE │
  │                             │
  │ 5. DB aktualisieren         │
  │    (last_seen timestamp)    │
  └─────────────────────────────┘
```

## Beispiel-Logs

### Erfolgreicher Start

```
2026-02-01 10:00:00 - __main__ - INFO - Starting Scan2Target...
2026-02-01 10:00:01 - api.devices - INFO - [STARTUP] Initializing scanner cache (attempt 1/3)...
2026-02-01 10:00:02 - core.scanning.manager - INFO - Scanner discovery complete: 1 device(s) found
2026-02-01 10:00:02 - api.devices - INFO - [STARTUP] ✓ Scanner cache initialized with 1 device(s)
2026-02-01 10:00:02 - api.devices - INFO - [STARTUP]   - HP ENVY 6400 series (eSCL (Network))
2026-02-01 10:00:02 - core.scanning.health - INFO - Scanner health monitor started (check interval: 60s)
2026-02-01 10:00:02 - __main__ - INFO - Scan2Target is ready!
```

### Scanner kommt später online

```
2026-02-01 10:00:00 - __main__ - INFO - Starting Scan2Target...
2026-02-01 10:00:01 - api.devices - INFO - [STARTUP] Initializing scanner cache (attempt 1/3)...
2026-02-01 10:00:02 - api.devices - WARNING - [STARTUP] No scanners found on attempt 1
2026-02-01 10:00:02 - api.devices - INFO - [STARTUP] Retry 2/3 - waiting 2s...
2026-02-01 10:00:04 - core.scanning.manager - INFO - Scanner discovery complete: 0 device(s) found
2026-02-01 10:00:04 - api.devices - WARNING - [STARTUP] No scanners found on attempt 2
2026-02-01 10:00:04 - api.devices - INFO - [STARTUP] Retry 3/3 - waiting 5s...
2026-02-01 10:00:09 - core.scanning.manager - INFO - Scanner discovery complete: 0 device(s) found
2026-02-01 10:00:09 - api.devices - WARNING - [STARTUP] Scanner cache initialized with 0 devices after 3 attempts
2026-02-01 10:00:09 - api.devices - INFO - [STARTUP] Scanner health monitor will continue checking...
2026-02-01 10:00:09 - core.scanning.health - INFO - Scanner health monitor started (check interval: 60s)
2026-02-01 10:00:09 - __main__ - INFO - Scan2Target is ready!

# 60 Sekunden später...
2026-02-01 10:01:09 - core.scanning.health - INFO - Checking 1 registered scanner(s)...
2026-02-01 10:01:10 - core.scanning.health - INFO - ✓ Scanner 'HP ENVY 6400 series' is now ONLINE
2026-02-01 10:01:10 - core.scanning.health - INFO - Health check complete: 1/1 scanner(s) online
```

## Konfiguration

### Umgebungsvariablen

```yaml
# docker-compose.yml oder .env
environment:
  # Health-Check Intervall (Sekunden)
  SCAN2TARGET_HEALTH_CHECK_INTERVAL: 60
  
  # Scanner-Cache Intervall (Sekunden)
  SCAN2TARGET_SCANNER_CHECK_INTERVAL: 30
  
  # Log-Verzeichnis
  SCAN2TARGET_LOG_DIR: /var/log/scan2target
```

### Empfohlene Werte

- **USB-Scanner**: `HEALTH_CHECK_INTERVAL=30` (schnellere Erkennung)
- **Netzwerk-Scanner**: `HEALTH_CHECK_INTERVAL=60` (Standard)
- **Viele Scanner**: `HEALTH_CHECK_INTERVAL=120` (weniger Last)

## Debugging

### Logs anzeigen

```bash
# Console Logs (Live)
docker logs -f scan2target

# Startup-Logs
docker logs scan2target | grep STARTUP

# Health-Check Logs
docker logs scan2target | grep -E "(ONLINE|OFFLINE|Health check)"

# Persistente Logs (detailliert)
docker exec scan2target tail -f /var/log/scan2target/app.log

# Debug-Logs für Scanner-Discovery
docker exec scan2target grep "airscan-discover" /var/log/scan2target/app.log
```

### Health-Status prüfen

```bash
# API-Endpoint
curl http://localhost:8000/api/v1/devices/health/status

# Antwort
{
  "monitor_active": true,
  "check_interval": 60,
  "last_check": 1738531200,
  "total_scanners": 1,
  "online_scanners": 1,
  "offline_scanners": 0,
  "scanners": [...]
}
```

### Manuellen Check erzwingen

```bash
# Einzelnen Scanner prüfen
curl http://localhost:8000/api/v1/devices/{device_id}/check
```

## Vorteile der Lösung

### 1. Robustheit
✅ Mehrfache Versuche beim Start  
✅ Kontinuierliche Überwachung im Betrieb  
✅ Automatische Recovery bei Netzwerkproblemen  

### 2. Transparenz
✅ Detaillierte Logs für Debugging  
✅ Persistente Logs überleben Container-Neustarts  
✅ Klar strukturierte Log-Ausgaben  

### 3. Konfigurierbarkeit
✅ Intervalle anpassbar  
✅ Log-Verzeichnis konfigurierbar  
✅ Keine Code-Änderungen nötig  

### 4. Monitoring-fähig
✅ API-Endpoints für Status-Abfragen  
✅ Strukturierte Logs parsbar  
✅ Health-Check-Endpoint vorhanden  

## Migration

### Existierende Installation aktualisieren

```bash
# 1. Container stoppen
docker-compose down

# 2. Code aktualisieren (git pull oder neue Version)
git pull

# 3. Container neu bauen
docker-compose build

# 4. Container starten
docker-compose up -d

# 5. Logs überprüfen
docker logs -f scan2target
```

**Keine Datenverluste**: Datenbank und Scanner-Konfigurationen bleiben erhalten.

### Neue Volumes

Das neue Log-Volume wird automatisch erstellt:

```bash
# Prüfen
docker volume ls | grep scan2target

# Sollte zeigen:
# scan2target-data
# scan2target-logs
```

## Testing

### Test-Szenarien

1. **Scanner vorhanden beim Start**
   - ✅ Scanner wird im ersten Versuch gefunden
   - ✅ Cache wird sofort gefüllt
   - ✅ Status: online

2. **Scanner kommt später**
   - ✅ Start-Versuche schlagen fehl
   - ✅ Health-Monitor findet Scanner nach 60s
   - ✅ Status wechselt von offline → online

3. **Scanner geht offline**
   - ✅ Health-Monitor erkennt Ausfall
   - ✅ Status wechselt von online → offline
   - ✅ Log-Meldung erscheint

4. **Scanner kommt wieder online**
   - ✅ Health-Monitor erkennt Rückkehr
   - ✅ Status wechselt von offline → online
   - ✅ `last_seen` wird aktualisiert

## Bekannte Limitationen

1. **Startup-Delay**: Erste Scanner-Discovery dauert bis zu 9 Sekunden (0+2+5s Delays)
   - **Akzeptabel**: Nur beim Start, danach kontinuierliche Überwachung

2. **Discovery-Time**: `airscan-discover` hat 15s Timeout
   - **Normal**: Netzwerk-Scanner brauchen Zeit zum Antworten

3. **Health-Check Latenz**: Änderungen werden erst beim nächsten Check erkannt
   - **Konfigurierbar**: Intervall kann auf 30s reduziert werden

## Support

Bei Problemen:

1. **Logs sammeln**: Siehe [Logging Guide](logging.md)
2. **Health-Status prüfen**: `curl http://localhost:8000/api/v1/devices/health/status`
3. **Issue erstellen**: Mit Logs und Health-Status

## Weiterführende Dokumentation

- [Logging Guide](logging.md) - Detaillierte Logging-Dokumentation
- [Scanner Health Monitoring](scanner-health-monitoring.md) - Health-Monitor Details
- [Docker Setup](docker.md) - Docker-Konfiguration
