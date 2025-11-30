# Quick Fix - CUPS Installation fehlt

## Problem
```
Error discovering devices: [Errno 2] No such file or directory: 'lpinfo'
```

## Lösung
CUPS ist nicht installiert. Installiere es:

```bash
sudo apt update
sudo apt install cups cups-browsed avahi-daemon
```

## Nach der Installation

### 1. Services starten
```bash
sudo systemctl enable cups
sudo systemctl start cups
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon
```

### 2. Benutzer zu CUPS-Gruppen hinzufügen
```bash
sudo usermod -a -G lp florian
sudo usermod -a -G lpadmin florian
```

**Wichtig:** Nach dem Hinzufügen zu Gruppen **neu einloggen** oder:
```bash
# Gruppen neu laden
su - florian
```

### 3. RaspScan neu starten
```bash
sudo systemctl restart raspscan
```

### 4. Testen
```bash
# CUPS direkt testen
lpinfo -v

# Sollte zeigen:
# direct usb://... (falls USB-Drucker angeschlossen)
# network dnssd://... (falls Wireless-Drucker im Netzwerk)

# API testen
curl http://localhost:8000/api/v1/printers/discover
```

## Schnell-Installation (Komplett)

Falls du das Installationsskript noch nicht ausgeführt hast:

```bash
cd ~/RaspScan
sudo bash installer/install.sh
```

Das Skript installiert automatisch:
- Python und Dependencies
- CUPS und SANE
- Avahi für Netzwerk-Discovery
- Node.js und npm
- Baut die Web UI
- Richtet systemd Service ein

## Prüfe ob CUPS läuft

```bash
# CUPS Status
systemctl status cups

# Port 631 sollte offen sein
sudo ss -tulpn | grep 631

# CUPS Web Interface (optional)
# http://10.10.10.175:631
```

## USB-Drucker prüfen

```bash
# Zeige USB-Geräte
lsusb

# Sollte deinen Drucker zeigen, z.B.:
# Bus 001 Device 004: ID 03f0:xxxx Hewlett-Packard HP Envy 6400

# CUPS Device Discovery
lpinfo -v | grep usb
```

Falls kein USB-Drucker erscheint:
1. Drucker abstecken und wieder anstecken
2. Logs prüfen: `sudo tail -f /var/log/cups/error_log`
3. Drucker einschalten und im "Ready" Status

## Wireless-Drucker prüfen

```bash
# Avahi Service Status
systemctl status avahi-daemon

# Netzwerk-Drucker suchen
avahi-browse -a -t | grep -i printer

# Oder mit IPP
ippfind
```

Falls nichts gefunden wird:
1. Drucker und Raspberry Pi im selben Netzwerk?
2. Drucker unterstützt AirPrint/IPP?
3. Firewall blockiert mDNS (Port 5353)?

## Finale Checks

Nach CUPS-Installation:

```bash
# 1. Services laufen?
systemctl status cups
systemctl status avahi-daemon
systemctl status raspscan

# 2. Berechtigungen OK?
groups florian
# Sollte enthalten: lp lpadmin

# 3. Discovery funktioniert?
lpinfo -v

# 4. Web UI neu laden
# http://10.10.10.175:8000
# "Discover Printers" klicken
```

## Falls es immer noch nicht funktioniert

Siehe: `PRINTER_TROUBLESHOOTING.md` für ausführliche Fehlersuche.
