# Deployment - Änderungen anwenden

## Problem: Scanner wird nach Neustart nicht gefunden

**Ursache:** mDNS/Avahi-Discovery braucht Zeit (10-30 Sekunden), bis Scanner im Netzwerk erkannt werden.

**Lösung:** 
1. Längere Delays beim Startup (3s, 8s, 15s, 25s)
2. Schnelle Health-Checks (alle 15s) in den ersten 5 Minuten
3. Danach normale Intervalle (60s)

## Docker Container neu bauen und starten

```bash
# 1. Container stoppen
docker-compose down

# 2. Image neu bauen (mit den neuen Änderungen)
docker-compose build --no-cache

# 3. Container starten
docker-compose up -d

# 4. Logs verfolgen
docker-compose logs -f
```

## Oder als Ein-Zeilen-Befehl

```bash
docker-compose down && docker-compose build --no-cache && docker-compose up -d && docker-compose logs -f
```

## Was passiert jetzt beim Start?

### Startup-Sequenz (bis zu 51 Sekunden)

```
Start
  ↓
Versuch 1 (sofort + 3s Wartezeit)
  ↓
Versuch 2 (nach 3s + 8s Wartezeit) 
  ↓
Versuch 3 (nach 11s + 15s Wartezeit)
  ↓
Versuch 4 (nach 26s + 25s Wartezeit)
  ↓
Health Monitor startet
  ↓
Erste 5 Minuten: Prüfung alle 15 Sekunden
  ↓
Danach: Prüfung alle 60 Sekunden
```

### Erwartete Logs bei erfolgreichem Start

```
[STARTUP] Initializing scanner cache (attempt 1/4)...
[STARTUP] No scanners found on attempt 1
[STARTUP] Retry 2/4 - waiting 8s...
[STARTUP] Initializing scanner cache (attempt 2/4)...
airscan-discover found 1 scanner(s)
[STARTUP] ✓ Scanner cache initialized with 1 device(s)
Health monitor started (interval: 60s)
Note: Using 15s intervals for first 5 minutes to detect scanners quickly
```

### Wenn Scanner erst später erkannt wird

```
[STARTUP] Scanner cache initialization completed with 0 devices after 4 attempts
Health monitor started (interval: 60s)

# 15 Sekunden später...
✓ Scanner 'HP ENVY 6400' is now ONLINE
```

## Logs überprüfen

```bash
# Nach dem Neustart
docker-compose logs -f | grep -E "(STARTUP|Scanner|ONLINE|OFFLINE)"

# Sollte zeigen:
# - 4 Startup-Versuche mit steigenden Delays
# - Scanner-Discovery Ergebnisse
# - Health-Monitor findet Scanner spätestens nach 15s
```

## Troubleshooting

Wenn Scanner immer noch nicht gefunden wird:

```bash
# 1. mDNS/Avahi im Container prüfen
docker exec scan2target ps aux | grep avahi

# 2. Direkter airscan-discover Test
docker exec scan2target airscan-discover

# 3. Netzwerk prüfen
docker exec scan2target ping -c 3 <SCANNER_IP>

# 4. Scanner manuell hinzufügen
# URI Format: airscan:escl:ScannerName:http://<IP>:8080/eSCL/
```

## Timing-Parameter anpassen

Falls 51 Sekunden zu lang sind oder Scanner noch später erkannt werden:

```yaml
# docker-compose.yml
environment:
  # Standard Health-Check Intervall (nach 5 Minuten)
  SCAN2TARGET_HEALTH_CHECK_INTERVAL: 60
```

Im Code können Sie die Delays anpassen:
- `app/api/devices.py`: delays-Array ändern
- `app/core/scanning/health.py`: `_fast_check_duration` und fast check interval ändern

