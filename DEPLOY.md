# Deployment - Änderungen anwenden

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

## Wichtig

Nach jedem Code-Update muss das Docker-Image neu gebaut werden, damit die Änderungen wirksam werden!

## Logs überprüfen

Nach dem Neustart sollten Sie diese Logs sehen:

```
Starting Scan2Target...
Database initialized
[STARTUP] Initializing scanner cache (attempt 1/3)...
[STARTUP] ✓ Scanner cache initialized with X device(s)
Health monitor started (interval: 60s)
Scan2Target is ready!
```

Wenn beim ersten Versuch keine Scanner gefunden werden:

```
[STARTUP] No scanners found on attempt 1
[STARTUP] Retry 2/3 - waiting 2s...
```

Und nach 60 Sekunden sollte der Health-Monitor Scanner finden:

```
✓ Scanner 'XY' is now ONLINE
Health check complete: 1/1 scanner(s) online
```
