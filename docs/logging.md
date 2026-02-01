# Logging Guide

## Übersicht

Scan2Target loggt alle wichtigen Ereignisse sowohl in die **Console** (Docker logs) als auch in **persistente Logfiles** im Container.

## Log-Speicherorte

### Console Logs (Docker)

```bash
# Live-Logs anzeigen
docker logs -f scan2target

# Letzte 100 Zeilen
docker logs --tail 100 scan2target

# Seit bestimmter Zeit
docker logs --since 30m scan2target
```

### Persistente Logfiles

**Speicherort im Container:** `/var/log/scan2target/app.log`

**Volume:** `scan2target-logs`

```bash
# Logfile im Container lesen
docker exec scan2target tail -f /var/log/scan2target/app.log

# Logfile auf Host kopieren
docker cp scan2target:/var/log/scan2target/app.log ./scan2target.log

# Gesamtes Log-Verzeichnis kopieren
docker cp scan2target:/var/log/scan2target ./logs
```

### Log-Rotation

Logfiles werden automatisch rotiert:
- **Maximale Größe pro File:** 10 MB
- **Anzahl Backups:** 5 Dateien
- **Gesamtgröße:** ~50 MB

Dateien:
```
/var/log/scan2target/
  ├── app.log          (aktuell)
  ├── app.log.1        (vorheriger)
  ├── app.log.2
  ├── app.log.3
  ├── app.log.4
  └── app.log.5        (ältester)
```

## Log-Levels

### Console (stdout/stderr)
- **Level:** INFO und höher
- **Verwendung:** Wichtige Ereignisse, Fehler, Warnungen
- **Sichtbar via:** `docker logs`

### File (app.log)
- **Level:** DEBUG und höher
- **Verwendung:** Alle Details inkl. Debug-Informationen
- **Sichtbar via:** Filesystem-Zugriff

## Wichtige Log-Kategorien

### Startup Logs

```
2026-02-01 10:00:00 - __main__ - INFO - ============================================================
2026-02-01 10:00:00 - __main__ - INFO - Starting Scan2Target...
2026-02-01 10:00:00 - __main__ - INFO - ============================================================
2026-02-01 10:00:01 - __main__ - INFO - Database initialized
2026-02-01 10:00:01 - api.devices - INFO - [STARTUP] Initializing scanner cache (attempt 1/3)...
2026-02-01 10:00:02 - core.scanning.manager - INFO - Scanner discovery complete: 1 device(s) found
2026-02-01 10:00:02 - api.devices - INFO - [STARTUP] ✓ Scanner cache initialized with 1 device(s)
2026-02-01 10:00:02 - api.devices - INFO - [STARTUP]   - HP ENVY 6400 series (eSCL (Network))
2026-02-01 10:00:02 - core.scanning.health - INFO - Scanner health monitor started (check interval: 60s)
2026-02-01 10:00:02 - __main__ - INFO - ============================================================
2026-02-01 10:00:02 - __main__ - INFO - Scan2Target is ready!
2026-02-01 10:00:02 - __main__ - INFO - ============================================================
```

### Health Check Logs

```
2026-02-01 10:01:00 - core.scanning.health - INFO - Checking 1 registered scanner(s)...
2026-02-01 10:01:01 - core.scanning.health - INFO - ✓ Scanner 'HP ENVY 6400 series' is now ONLINE
2026-02-01 10:01:01 - core.scanning.health - INFO - Health check complete: 1/1 scanner(s) online
```

### Scanner Discovery Logs (DEBUG Level)

```
2026-02-01 10:00:01 - core.scanning.manager - DEBUG - Starting scanner discovery...
2026-02-01 10:00:01 - core.scanning.manager - DEBUG - Running airscan-discover...
2026-02-01 10:00:02 - core.scanning.manager - DEBUG - airscan-discover return code: 0
2026-02-01 10:00:02 - core.scanning.manager - DEBUG - airscan-discover output:
[devices]
HP ENVY 6400 series [059A50] = http://10.10.30.146:8080/eSCL/, eSCL
2026-02-01 10:00:02 - core.scanning.manager - DEBUG - Parsing device line: HP ENVY 6400 series [059A50] = http://10.10.30.146:8080/eSCL/, eSCL
2026-02-01 10:00:02 - core.scanning.manager - DEBUG - Found scanner: HP ENVY 6400 series (ID: airscan:escl:HP_ENVY_6400_series:http://10.10.30.146:8080/eSCL/, Type: eSCL (Network))
2026-02-01 10:00:02 - core.scanning.manager - INFO - airscan-discover found 1 scanner(s)
2026-02-01 10:00:02 - core.scanning.manager - INFO - Scanner discovery complete: 1 device(s) found
```

### Error Logs

```
2026-02-01 10:00:01 - api.devices - WARNING - [STARTUP] No scanners found on attempt 1
2026-02-01 10:00:01 - api.devices - INFO - [STARTUP] Retry 2/3 - waiting 2s...
```

## Troubleshooting mit Logs

### Scanner wird nicht gefunden

1. **Prüfen Sie Startup-Logs:**
   ```bash
   docker logs scan2target | grep STARTUP
   ```

2. **Suchen nach Scanner-Discovery:**
   ```bash
   docker logs scan2target | grep "Scanner discovery"
   ```

3. **Debug-Logs im Filesystem:**
   ```bash
   docker exec scan2target grep -A 10 "airscan-discover" /var/log/scan2target/app.log
   ```

### Health-Check funktioniert nicht

```bash
# Health-Check Logs anzeigen
docker logs scan2target | grep HEALTH

# Oder im Logfile
docker exec scan2target grep HEALTH /var/log/scan2target/app.log
```

### Fehlersuche (Errors)

```bash
# Alle Fehler anzeigen
docker logs scan2target | grep ERROR

# Fehler mit Stacktrace im Logfile
docker exec scan2target grep -A 20 ERROR /var/log/scan2target/app.log
```

## Log-Analyse-Befehle

### Statistiken

```bash
# Anzahl Scanner-Discoveries
docker logs scan2target | grep -c "Scanner discovery complete"

# Anzahl Health-Checks
docker logs scan2target | grep -c "Health check complete"

# Fehler zählen
docker logs scan2target | grep -c ERROR
```

### Zeitbasierte Analyse

```bash
# Logs der letzten Stunde
docker logs --since 1h scan2target

# Logs zwischen bestimmten Zeitpunkten
docker logs --since "2026-02-01T10:00:00" --until "2026-02-01T11:00:00" scan2target
```

### Nach Pattern suchen

```bash
# Alle Scanner-Namen finden
docker exec scan2target grep -o "Scanner '[^']*'" /var/log/scan2target/app.log | sort -u

# Alle URIs finden
docker exec scan2target grep -o "URI: [^ ]*" /var/log/scan2target/app.log | sort -u
```

## Konfiguration

### Log-Verzeichnis ändern

```yaml
# docker-compose.yml
environment:
  - SCAN2TARGET_LOG_DIR=/custom/log/path

volumes:
  - ./my-logs:/custom/log/path
```

### Log-Level ändern (programmatisch)

Im Code können Sie das Log-Level für spezifische Module anpassen:

```python
import logging

# Für ein bestimmtes Modul
logging.getLogger('core.scanning.manager').setLevel(logging.DEBUG)

# Für die gesamte App
logging.getLogger().setLevel(logging.DEBUG)
```

## Best Practices

### 1. Startup-Probleme debuggen

```bash
# Komplette Startup-Sequenz
docker logs scan2target 2>&1 | grep -E "(Starting|STARTUP|Health monitor)"
```

### 2. Scanner-Status überwachen

```bash
# Live-Monitoring
docker logs -f scan2target | grep -E "(ONLINE|OFFLINE|Health check)"
```

### 3. Performance-Probleme

```bash
# Timing-Informationen
docker logs scan2target | grep TIMING
```

### 4. Logs für Support sammeln

```bash
#!/bin/bash
# collect-logs.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="scan2target_logs_${TIMESTAMP}"

mkdir -p "$OUTPUT_DIR"

# Docker Console Logs
docker logs scan2target > "$OUTPUT_DIR/docker.log" 2>&1

# Persistente Logfiles
docker cp scan2target:/var/log/scan2target "$OUTPUT_DIR/"

# System-Info
docker inspect scan2target > "$OUTPUT_DIR/container_info.json"
docker-compose config > "$OUTPUT_DIR/compose_config.yml"

# Archivieren
tar czf "${OUTPUT_DIR}.tar.gz" "$OUTPUT_DIR"
echo "Logs gesammelt in: ${OUTPUT_DIR}.tar.gz"
```

### 5. Logs regelmäßig prüfen

```bash
# Cronjob (täglich um 23:00)
0 23 * * * docker logs --tail 1000 scan2target > /backup/scan2target_$(date +\%Y\%m\%d).log
```

## Log-Format

```
<Timestamp> - <Logger Name> - <Level> - <Message>
```

**Beispiel:**
```
2026-02-01 10:00:00 - core.scanning.health - INFO - Scanner health monitor started (check interval: 60s)
```

**Komponenten:**
- `2026-02-01 10:00:00`: Zeitstempel (UTC)
- `core.scanning.health`: Logger-Name (Modul)
- `INFO`: Log-Level
- Rest: Log-Nachricht

## Volume-Verwaltung

### Logs sichern

```bash
# Volume-Daten auf Host kopieren
docker run --rm -v scan2target-logs:/logs -v $(pwd):/backup alpine tar czf /backup/logs-backup.tar.gz /logs
```

### Logs löschen (bei Problemen)

```bash
# Container stoppen
docker-compose down

# Volume löschen
docker volume rm scan2target-logs

# Neu starten
docker-compose up -d
```

### Logs inspizieren ohne Container

```bash
# Temporären Container mit Volume starten
docker run --rm -it -v scan2target-logs:/logs alpine sh

# Im Container:
cd /logs/scan2target
ls -lh
cat app.log
```

## Monitoring Integration

### Beispiel: Log-Monitoring mit tail

```bash
# Automatisches Alert bei Errors
docker logs -f scan2target | while read line; do
  if echo "$line" | grep -q ERROR; then
    echo "ALERT: Error detected - $line" | mail -s "Scan2Target Error" admin@example.com
  fi
done
```

### Beispiel: Prometheus Exporter (optional)

Logs können mit Tools wie `promtail` oder `fluentd` geparst und an Monitoring-Systeme gesendet werden.

## FAQ

**Q: Wo finde ich die Logs nach einem Container-Neustart?**  
A: Persistente Logs bleiben im Volume `scan2target-logs` erhalten. Console-Logs gehen verloren.

**Q: Wie groß werden die Logfiles?**  
A: Maximal ~50 MB durch automatische Rotation (5 x 10 MB).

**Q: Kann ich Logs auf dem Host speichern?**  
A: Ja, binden Sie ein Host-Verzeichnis ein:
```yaml
volumes:
  - ./logs:/var/log/scan2target
```

**Q: Wie ändere ich das Log-Level?**  
A: Derzeit über Code. Eine Umgebungsvariable `SCAN2TARGET_LOG_LEVEL` könnte hinzugefügt werden.

**Q: Werden sensible Daten geloggt?**  
A: Nein, Passwörter und Secrets werden nicht geloggt. URIs und IPs erscheinen in DEBUG-Logs.
