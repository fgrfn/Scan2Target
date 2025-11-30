# Printer Management - Quick Start

## Neue Features

### ✅ Drucker werden NIEMALS automatisch hinzugefügt
- Alle Drucker müssen manuell über Discovery oder Manual Setup hinzugefügt werden
- Volle Kontrolle über welche Drucker konfiguriert werden

### ✅ Drucker Discovery
- USB-Drucker werden automatisch erkannt (jeder USB-Port)
- Wireless/Network-Drucker werden via AirPrint/IPP gefunden
- Zeigt Status: "Configured" oder "Not Added"

### ✅ Drucker löschen
- Drucker können jederzeit entfernt werden
- Löscht die Printer-Konfiguration aus CUPS
- Keine Rückstände

## Workflow

### 1. Drucker finden
```
Settings → Printer Management → "Discover Printers"
```

**Was passiert:**
- Scannt nach USB-Druckern (an allen Ports)
- Scannt nach Wireless-Druckern im Netzwerk (via mDNS/DNS-SD)
- Zeigt URI, Typ (USB/Network), Status (Configured/Not Added)

### 2. Drucker hinzufügen
**Option A: Via Discovery (empfohlen)**
1. Klicke "Discover Printers"
2. Wähle Drucker aus der Liste
3. Klicke "Add Printer"
4. Drucker wird zu CUPS hinzugefügt mit IPP Everywhere Driver

**Option B: Manuell**
1. Gehe zu "Manual Setup (Advanced)"
2. Gib URI ein: `usb://HP/ENVY%206400` oder `ipp://printer.local`
3. Gib Namen ein: `My_Printer` (keine Leerzeichen!)
4. Klicke "Add Manually"

### 3. Drucker nutzen
```
Print → Choose printer → Upload file → Print
```

### 4. Drucker entfernen
**Option A: Via Print Section**
1. Gehe zu "Print" Section
2. Unter "Configured Printers" finde deinen Drucker
3. Klicke "Remove"
4. Bestätige die Löschung

**Option B: Via API**
```bash
curl -X DELETE http://localhost:8000/api/v1/printers/Printer_Name
```

## API Endpoints

### Discovery
```bash
GET /api/v1/printers/discover
```

**Response:**
```json
[
  {
    "uri": "usb://HP/ENVY%206400?serial=ABC123",
    "type": "USB",
    "make": "HP",
    "model": "ENVY 6400",
    "name": "HP ENVY 6400",
    "supported": true,
    "configured": false,
    "status": "Available"
  },
  {
    "uri": "dnssd://HP%20Envy._ipp._tcp.local/",
    "type": "Network (AirPrint)",
    "make": "HP",
    "model": "Envy",
    "name": "HP Envy",
    "supported": true,
    "configured": true,
    "status": "Configured"
  }
]
```

### List Configured Printers
```bash
GET /api/v1/printers/
```

**Response:**
```json
[
  {
    "id": "HP_Envy_6400",
    "name": "HP Envy 6400",
    "status": "idle",
    "uri": "usb://HP/ENVY%206400?serial=ABC123",
    "type": "USB",
    "is_default": false
  }
]
```

### Add Printer
```bash
POST /api/v1/printers/add
Content-Type: application/json

{
  "uri": "usb://HP/ENVY%206400?serial=ABC123",
  "name": "HP_Envy_6400",
  "description": "USB - ENVY 6400"
}
```

**Response:**
```json
{
  "status": "added",
  "name": "HP_Envy_6400"
}
```

### Remove Printer
```bash
DELETE /api/v1/printers/HP_Envy_6400
```

**Response:**
```json
{
  "status": "removed",
  "printer_id": "HP_Envy_6400"
}
```

## Wichtige Hinweise

### Printer Names
- **Keine Leerzeichen** - wird automatisch zu Unterstrichen konvertiert
- Nur `a-z A-Z 0-9 _ -` erlaubt
- Beispiele:
  - ✅ `HP_Envy_6400`
  - ✅ `My-Printer-1`
  - ❌ `My Printer` (wird zu `My_Printer`)
  - ❌ `Printer@Home` (wird zu `Printer_Home`)

### Drucker-Status
- **idle** - Bereit zum Drucken
- **processing** - Druckt gerade
- **stopped** - Pausiert oder Fehler

### Configured vs Available
- **Configured** - Drucker ist bereits in CUPS eingerichtet
- **Available** - Drucker wurde gefunden aber noch nicht hinzugefügt
- **Not Added** - Badge für nicht-konfigurierte Drucker

### Default Printer
- **Kein** Drucker wird automatisch als Default gesetzt
- Muss manuell über CUPS Web Interface gesetzt werden: `http://raspberry-pi:631`
- Oder via CLI: `lpadmin -d Printer_Name`

## Troubleshooting

### "No devices found"
```bash
# CUPS installiert?
lpinfo -v

# Wenn nicht:
sudo apt install cups cups-browsed

# USB-Drucker angeschlossen?
lsusb | grep -i printer

# Wireless im gleichen Netzwerk?
avahi-browse -a -t | grep -i printer
```

### "Failed to add printer"
```bash
# Berechtigungen prüfen
groups
# Sollte enthalten: lp lpadmin

# Falls nicht:
sudo usermod -a -G lp,lpadmin $USER
# Dann neu einloggen!

# CUPS läuft?
systemctl status cups
```

### "Failed to remove printer"
```bash
# Printer existiert?
lpstat -p

# Manuell löschen:
sudo lpadmin -x Printer_Name
```

### Discovery findet USB-Drucker nicht
```bash
# Drucker abstecken und wieder anstecken
# CUPS Logs prüfen:
sudo tail -f /var/log/cups/error_log

# USB Backend prüfen:
ls -la /usr/lib/cups/backend/usb
# Sollte ausführbar sein (755)
```

## Best Practices

### 1. Erst Discovery, dann Manual
- Versuche immer zuerst "Discover Printers"
- Manual Setup nur wenn Discovery fehlschlägt oder spezielle URIs nötig sind

### 2. Aussagekräftige Namen
- Verwende klare Namen: `Office_Laser`, `Home_Color`, `Production_HP`
- Nicht: `Printer1`, `Test`, `abc`

### 3. Test-Seite drucken
```bash
POST /api/v1/printers/{printer_id}/test
```

### 4. Regelmäßig aufräumen
- Entferne ungenutzte Drucker
- Halte Liste übersichtlich

## Siehe auch

- **CUPS Troubleshooting:** `PRINTER_TROUBLESHOOTING.md`
- **Quick Fix:** `QUICK_FIX.md`
- **Full Docs:** `README.md`
