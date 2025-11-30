# Neues Device Management System

## Problem gelöst ✅

**Vorher:**
- Scanner erschienen nach Discovery, verschwanden beim Reload
- Keine permanente Speicherung von Geräten
- Keine explizite Bestätigung erforderlich

**Jetzt:**
- Geräte werden nur nach manueller Bestätigung hinzugefügt
- Permanente Speicherung in Datenbank
- Geräte bleiben nach Reload sichtbar
- Einfaches Entfernen möglich

## Neuer Workflow

### 1. Discovery (zeigt nur verfügbare Geräte)
```bash
GET /api/v1/devices/discover
```

**Response:**
```json
[
  {
    "uri": "escl:http://10.10.10.146:80",
    "name": "HP ENVY 6400 flatbed scanner",
    "make": "HP",
    "model": "ENVY 6400 flatbed scanner",
    "connection_type": "eSCL (AirScan)",
    "device_type": "scanner",
    "supported": true,
    "already_added": false
  },
  {
    "uri": "usb://HP/ENVY%206400",
    "name": "HP ENVY 6400",
    "make": "HP",
    "model": "ENVY 6400",
    "connection_type": "USB",
    "device_type": "printer",
    "supported": true,
    "already_added": false
  }
]
```

**Wichtig:** Diese Geräte werden **NICHT automatisch hinzugefügt**! Sie sind nur sichtbar für die Auswahl.

### 2. Gerät hinzufügen (nach Auswahl durch User)
```bash
POST /api/v1/devices/add
Content-Type: application/json

{
  "uri": "escl:http://10.10.10.146:80",
  "name": "HP ENVY 6400 Scanner",
  "device_type": "scanner",
  "make": "HP",
  "model": "ENVY 6400",
  "connection_type": "eSCL (AirScan)",
  "description": "Wireless scanner in office"
}
```

**Response:**
```json
{
  "id": "HP_ENVY_6400_Scanner",
  "device_type": "scanner",
  "name": "HP ENVY 6400 Scanner",
  "uri": "escl:http://10.10.10.146:80",
  "make": "HP",
  "model": "ENVY 6400",
  "connection_type": "eSCL (AirScan)",
  "description": "Wireless scanner in office",
  "is_active": true,
  "status": "added"
}
```

### 3. Gespeicherte Geräte anzeigen
```bash
GET /api/v1/devices/
```

**Response:**
```json
[
  {
    "id": "HP_ENVY_6400_Scanner",
    "device_type": "scanner",
    "name": "HP ENVY 6400 Scanner",
    "uri": "escl:http://10.10.10.146:80",
    "make": "HP",
    "model": "ENVY 6400",
    "connection_type": "eSCL (AirScan)",
    "description": "Wireless scanner in office",
    "is_active": true,
    "status": "online"
  }
]
```

**Wichtig:** Diese Liste bleibt nach Reload/Neustart erhalten!

### 4. Gerät entfernen
```bash
DELETE /api/v1/devices/HP_ENVY_6400_Scanner
```

**Response:**
```json
{
  "status": "removed",
  "device_id": "HP_ENVY_6400_Scanner",
  "device_type": "scanner"
}
```

## WebUI Integration

Die WebUI muss angepasst werden:

### Settings/Devices Section

**Zwei Bereiche:**

#### 1. Discovery (oben)
```
[Discover Devices] Button

┌─────────────────────────────────────────────────────────────┐
│ Discovered Devices (not added yet)                         │
├─────────────────────────────────────────────────────────────┤
│ ☐ HP ENVY 6400 Scanner                                      │
│   eSCL (AirScan) - escl:http://10.10.10.146:80             │
│   [Add Device]                                               │
├─────────────────────────────────────────────────────────────┤
│ ☐ HP ENVY 6400 Printer (USB)                               │
│   USB - usb://HP/ENVY%206400                                │
│   [Add Device]  [Already Added]                             │
└─────────────────────────────────────────────────────────────┘
```

#### 2. Your Devices (unten)
```
┌─────────────────────────────────────────────────────────────┐
│ Your Devices (permanently added)                            │
├─────────────────────────────────────────────────────────────┤
│ 🖨️ HP_Office_Printer                                        │
│   Printer | Network (IPP) | Status: online                  │
│   [Remove]                                                   │
├─────────────────────────────────────────────────────────────┤
│ 📄 HP_ENVY_6400_Scanner                                     │
│   Scanner | eSCL (AirScan) | Status: online                 │
│   [Remove]                                                   │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints Übersicht

| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/api/v1/devices/discover` | GET | Scannt nach verfügbaren Geräten (nicht persistent) |
| `/api/v1/devices/` | GET | Listet permanent hinzugefügte Geräte |
| `/api/v1/devices/add` | POST | Fügt Gerät permanent hinzu (MANUELL!) |
| `/api/v1/devices/{id}` | GET | Details zu einem Gerät |
| `/api/v1/devices/{id}` | DELETE | Entfernt Gerät permanent |

## Altes vs. Neues System

### Alt (Problem)
```
User → Click "Discover" 
    → Backend findet Scanner
    → Scanner erscheinen in UI
User → Reload page
    → Scanner verschwinden wieder ❌
```

### Neu (Lösung)
```
User → Click "Discover" 
    → Backend findet Scanner
    → Scanner in "Discovered Devices" Bereich
    → Badge: "Not Added Yet"
User → Select Scanner + Click "Add Device"
    → POST /api/v1/devices/add
    → Scanner in Datenbank gespeichert
    → Scanner erscheint in "Your Devices"
User → Reload page
    → Scanner bleibt in "Your Devices" ✅
User → Click "Remove"
    → DELETE /api/v1/devices/{id}
    → Scanner aus DB gelöscht
```

## Migration

### Bestehende Drucker migrieren

Falls du bereits Drucker in CUPS hast, musst du sie manuell zur neuen Device-Registry hinzufügen:

```bash
# Liste alle CUPS-Drucker
lpstat -p

# Für jeden Drucker:
curl -X POST http://localhost:8000/api/v1/devices/add \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "usb://HP/ENVY%206400",
    "name": "HP Office Printer",
    "device_type": "printer",
    "connection_type": "USB"
  }'
```

## Vorteile

✅ **Explizite Kontrolle** - Nichts wird automatisch hinzugefügt
✅ **Persistenz** - Geräte bleiben nach Neustart erhalten
✅ **Unified Management** - Drucker und Scanner in einem System
✅ **Status Tracking** - Online/Offline Status für jedes Gerät
✅ **Einfaches Entfernen** - Ein Click zum Löschen
✅ **Fehlermeldungen** - Wenn Gerät nicht erreichbar
✅ **Duplicate Prevention** - Verhindert doppelte Einträge

## Nächste Schritte

1. **WebUI anpassen** - Neue Endpoints integrieren
2. **Service neu starten** - `sudo systemctl restart raspscan`
3. **Testen:**
   - Discovery ausführen
   - Gerät auswählen und hinzufügen
   - Seite neu laden → Gerät sollte bleiben
   - Gerät entfernen → sollte verschwinden

## Troubleshooting

**Problem:** Discovery findet keine Geräte
```bash
# CUPS prüfen
lpinfo -v

# SANE prüfen
scanimage -L

# Berechtigungen
groups
# Sollte: lp, lpadmin
```

**Problem:** Gerät kann nicht hinzugefügt werden
- Prüfe ob URI korrekt ist
- Prüfe ob Gerät erreichbar ist
- Prüfe Logs: `journalctl -u raspscan -f`

**Problem:** Gerät zeigt "offline" obwohl online
- Discovery nochmal ausführen
- Gerät aus-/einschalten
- CUPS/SANE neu starten
