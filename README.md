<div align="center">

[![Version](https://img.shields.io/github/v/release/fgrfn/Scan2Target?label=version)](https://github.com/fgrfn/Scan2Target/releases)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue)](https://github.com/fgrfn/Scan2Target/pkgs/container/scan2target)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

# Scan2Target

Web-based scan server. Control network/USB scanners and route documents to SMB, email, cloud storage, Paperless-ngx, or webhooks.

</div>

---

## Quick Start

### Docker (recommended)

```bash
docker compose up -d
```

Access at `http://YOUR_SERVER_IP:8000` — no login required by default (enable in Settings → Authentication).

### Pre-built image

```bash
docker run -d \
  --name scan2target \
  --network host \
  -v scan2target-data:/data \
  ghcr.io/fgrfn/scan2target:latest
```

> **`--network host` is required** for mDNS scanner discovery (Avahi/eSCL). Without it, scanners can still be added manually by IP.

---

## Configuration

All runtime settings (auth, log level, intervals) are adjustable in the **Settings** page — no restart needed.

| Environment variable | Default | Description |
|---|---|---|
| `SCAN2TARGET_DATABASE_PATH` | `/data/db/scan2target.db` | SQLite DB path |
| `SCAN2TARGET_DATA_DIR` | `/data` | Persistent data root |
| `SCAN2TARGET_LOG_DIR` | `/var/log/scan2target` | Log directory |
| `SCAN2TARGET_JWT_SECRET` | auto-generated | Signing secret for JWT tokens |

The JWT secret is auto-persisted to `/data/.scan2target/secret.key` if not provided via env. It survives container restarts as long as the volume exists.

**Docker Secret (production):**
```bash
mkdir secrets && openssl rand -base64 32 > secrets/scan2target_secret_key
# then uncomment the secrets block in docker-compose.yml
```

---

## Scanner Setup

### Auto-discovery
Click **Discover** in the Devices page. Requires `--network host`.

### Manual add
Use the `airscan:escl:` URI format:
```
airscan:escl:HP_ENVY_6400:http://192.168.1.10:8080/eSCL
```

---

## Targets

| Type | Notes |
|---|---|
| **SMB / CIFS** | `//server/share` — Windows/Samba shares |
| **SFTP** | SSH file transfer |
| **Email** | SMTP with attachments |
| **Paperless-ngx** | POST to REST API |
| **Webhook** | Custom HTTP endpoint |
| **Google Drive** | OAuth2 |
| **Dropbox** | OAuth2 |
| **OneDrive** | OAuth2 |
| **Nextcloud** | WebDAV |

---

## Scan Profiles

| ID | DPI | Color | Format | Source |
|---|---|---|---|---|
| `doc_200_gray_pdf` | 200 | Gray | PDF | Flatbed |
| `doc_200_gray_adf` | 200 | Gray | PDF | ADF |
| `color_300_pdf` | 300 | Color | PDF | Flatbed |
| `gray_150_pdf` | 150 | Gray | PDF | Flatbed |
| `photo_600_jpeg` | 600 | Color | JPEG | Flatbed |

---

## Home Assistant Integration

Mark a scanner and a target as **Favorite**, then:

```yaml
rest_command:
  scan_document:
    url: "http://YOUR_SERVER_IP:8000/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "doc_200_gray_pdf"}'
```

Full example config: [`examples/homeassistant_config.yaml`](examples/homeassistant_config.yaml)  
Detailed guide: [`docs/homeassistant.md`](docs/homeassistant.md)

---

## API

Swagger UI: `http://YOUR_SERVER_IP:8000/docs`

Key endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/scan/start` | POST | Start a scan job |
| `/api/v1/scan/preview` | POST | Low-res preview image |
| `/api/v1/scan/batch-page` | POST | Scan one page for batch assembly |
| `/api/v1/scan/batch` | POST | Combine batch pages and deliver |
| `/api/v1/devices/discover` | GET | Auto-discover scanners |
| `/api/v1/homeassistant/scan` | POST | HA trigger |
| `/api/v1/homeassistant/status` | GET | HA status sensor |
| `/api/v1/ws` | WS | Real-time job + scanner updates |

---

## Service Management

```bash
# Docker
docker compose up -d
docker compose logs -f
docker compose down

# systemd (native install)
sudo systemctl status scan2target
sudo journalctl -u scan2target -f
```

---

## Logs

```bash
docker logs -f scan2target
# or persistent file log:
docker exec scan2target tail -f /var/log/scan2target/app.log
```

---

## Unraid

See [`docs/unraid-setup.md`](docs/unraid-setup.md).

---

## License

MIT — see [LICENSE](LICENSE).


[![Version](https://img.shields.io/github/v/release/fgrfn/Scan2Target?label=version)](https://github.com/fgrfn/Scan2Target/releases)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://github.com/fgrfn/Scan2Target/pkgs/container/scan2target)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)

**Modern web-based scan server for network and USB scanners**

Control scanners remotely and route documents to SMB shares, email, cloud storage, or webhooks.

[Features](#-features) • [Quick Start](#-quick-start) • [Docker](#-docker-deployment) • [Documentation](#-documentation)

</div>

---

**📚 Learning Project:** Created with AI/Copilot assistance as a learning exercise for modern web development, REST APIs, and system integration.

---

## ✨ Features

### 🖨️ **Scanner Management**
- Auto-discovery of USB and network scanners (SANE/eSCL)
- Automatic health monitoring and reconnection
- Support for flatbed, ADF, and duplex scanning
- Real-time status updates via WebSocket

### 🎯 **9 Target Types**
- **SMB/CIFS** - Windows/Samba network shares
- **SFTP** - Secure SSH file transfer
- **Email** - SMTP delivery with attachments
- **Paperless-ngx** - Document management system
- **Webhook** - Custom HTTP endpoints
- **Google Drive** - OAuth2 cloud storage
- **Dropbox** - OAuth2 cloud storage
- **OneDrive** - OAuth2 cloud storage
- **Nextcloud** - WebDAV integration

### 📊 **Analytics & Monitoring**
- Comprehensive statistics dashboard
- Hourly scan distribution (browser timezone)
- Scanner/target usage analytics
- Success rates and daily averages
- 30-day timeline tracking

### 🔒 **Security & Reliability**
- Encrypted credentials (Fernet AES-128)
- Automatic retry on failed uploads
- Persistent logging across restarts
- JWT authentication with secure password hashing
- HTTPS support via reverse proxy

### 🌐 **Modern Web Interface**
- Progressive Web App (PWA) - install as native app
- Multi-language support (English/German)
- Real-time updates via WebSocket
- Low-resolution preview before scanning
- Mobile-optimized interface
- Cancel running scans instantly

### 🏠 **Home Assistant Integration**
- REST API for automation
- Voice command support
- NFC tag triggering
- Status sensors
- Actionable notifications

---

## 🚀 Quick Start

### Option 1: Docker (empfohlen) 🐳

```bash
# 1. Repository klonen
git clone https://github.com/fgrfn/Scan2Target.git
cd Scan2Target

# 2. Mit Docker Compose starten
docker-compose up -d

# 3. Logs anschauen
docker-compose logs -f
```

**Zugriff:** `http://YOUR_SERVER_IP:8000`

**Standard-Login:** `admin` / `admin` (**sofort ändern!**)

---

### Option 2: Native Installation

```bash
# 1. Repository klonen
git clone https://github.com/fgrfn/Scan2Target.git
cd Scan2Target

# 2. Installer ausführen
sudo ./installer/install.sh
```

**Zugriff:** `http://YOUR_SERVER_IP`

**Standard-Login:** `admin` / `admin` (**sofort ändern!**)

---

### Pre-built Docker Images

Images werden automatisch via GitHub Actions gebaut:

```bash
# Latest Version pullen
docker pull ghcr.io/fgrfn/scan2target:latest

# Spezifische Version
docker pull ghcr.io/fgrfn/scan2target:v0.1.0

# Container starten
docker run -d \
  --name scan2target \
  --network host \
  -v scan2target-data:/data \
  ghcr.io/fgrfn/scan2target:latest
```

---

## 🐳 Docker Deployment

### Docker Compose (empfohlen)

```bash
# 1. Repository klonen
git clone https://github.com/fgrfn/Scan2Target.git
cd Scan2Target

# 2. Services starten (kein .env nötig — Encryption Key wird automatisch generiert)
docker compose up -d

# 3. Logs ansehen
docker compose logs -f

# 4. Services stoppen
docker compose down
```

### Docker CLI

```bash
# Image bauen
docker build -t scan2target:latest .

# Container starten
docker run -d \
  --name scan2target \
  --network host \
  -v scan2target-data:/data \
  -v /dev/bus/usb:/dev/bus/usb \
  --device /dev/bus/usb \
  scan2target:latest
```

### Konfiguration

**Environment-Variablen:**

| Variable | Beschreibung | Standard |
|----------|--------------|----------|
| `SCAN2TARGET_JWT_SECRET` | JWT Signing Secret (optional, auto-generated) | auto |
| `SCAN2TARGET_REQUIRE_AUTH` | Authentifizierung erzwingen | `false` |
| `SCAN2TARGET_DATA_DIR` | Datenverzeichnis | `/data` |
| `SCAN2TARGET_DATABASE_PATH` | Datenbankpfad | `/data/db/scan2target.db` |
| `SCAN2TARGET_HEALTH_CHECK_INTERVAL` | Health-Check Intervall (Sekunden) | `60` |

**Volumes:**
- `/data` - Persistenter Speicher für DB und Scans (**REQUIRED**)
- `/dev/bus/usb` - USB-Zugriff für Scanner

⚠️ **WICHTIG:** Niemals ein Volume auf `/app` mounten - dies überschreibt den Code!

**Netzwerk:**
- `host` Modus erforderlich für Scanner-Discovery (mDNS/Avahi)

### Security Setup (Production)

The encryption key is auto-generated on first start and stored at `/data/.scan2target/encryption.key`. For the JWT secret you can optionally pin one:

```bash
# Optional: Pin JWT secret via environment variable
export SCAN2TARGET_JWT_SECRET="$(openssl rand -base64 32)"

# For native installation:
sudo nano /etc/systemd/system/scan2target.service
# Add: Environment="SCAN2TARGET_JWT_SECRET=your-secret"

sudo systemctl daemon-reload
sudo systemctl restart scan2target
```

---

## 📖 Usage

### 1️⃣ Scanner hinzufügen

1. Web UI öffnen
2. "Scan"-Bereich öffnen
3. "Discover Scanners" klicken
4. Scanner aus Liste auswählen
5. "Add Scanner" klicken

### 2️⃣ Target hinzufügen

1. "Targets"-Bereich öffnen
2. Target-Typ wählen (SMB, Email, Cloud, etc.)
3. Verbindungsdaten eingeben:
   - **SMB:** Share-Pfad (`//nas.local/scans`), Benutzername, Passwort
   - **Email:** Empfänger, SMTP-Server, Credentials
   - **Cloud:** OAuth2-Tokens, Ordnerpfade
4. "Test & Save" klicken zur Verbindungsprüfung
5. Target ist gespeichert und einsatzbereit

### 3️⃣ Scan starten

1. Scanner aus Dropdown auswählen
2. Scan-Profil wählen (Document, Photo, ADF)
3. Ziel-Destination auswählen
4. "Start Scan" klicken
5. Fortschritt in "Active Scans" beobachten

---

## 📊 Scan-Profile

| Profil | Auflösung | Farbe | Verwendung | Dateigröße |
|--------|-----------|-------|------------|------------|
| **Document 200 DPI** (`doc_200_gray_pdf`) | 200 DPI | Grau | Textdokumente, Flatbed | ~150 KB/Seite |
| **Document 200 DPI ADF** (`doc_200_gray_adf`) | 200 DPI | Grau | Automatischer Einzug | Ein PDF |
| **Color 300 DPI** (`color_300_pdf`) | 300 DPI | Farbe | Standard-Qualität | ~400 KB/Seite |
| **Grayscale 150 DPI** (`gray_150_pdf`) | 150 DPI | Grau | Schnelle Scans | ~80 KB/Seite |
| **Photo 600 DPI** (`photo_600_jpeg`) | 600 DPI | Farbe | Hohe Qualität | ~2 MB/Seite |

---

## 🎯 Target-Typen

### Lokale & Netzwerk
1. **SMB/CIFS** - Windows/Samba Shares
2. **SFTP** - SSH File Transfer

### Email & Dokumente
3. **Email** - SMTP Delivery
4. **Paperless-ngx** - Document Management

### Cloud-Speicher (OAuth2)
5. **Google Drive** - Google Cloud Storage
6. **Dropbox** - Dropbox Cloud
7. **OneDrive** - Microsoft Cloud
8. **Nextcloud** - WebDAV Integration

### Custom
9. **Webhook** - Benutzerdefinierte HTTP Endpoints

Alle Targets testen die Verbindung vor dem Speichern und unterstützen automatisches Retry bei Fehlern.

---

## 🔧 Service Management

### Native Installation (systemd)

```bash
sudo systemctl start scan2target    # Start
sudo systemctl stop scan2target     # Stop
sudo systemctl restart scan2target  # Restart
sudo systemctl status scan2target   # Status
sudo journalctl -u scan2target -f   # Logs
```

### Docker Installation

```bash
# Docker Compose
docker compose up -d           # Start
docker compose down            # Stop
docker compose restart         # Restart
docker compose ps              # Status
docker compose logs -f         # Logs

# Docker CLI
docker start scan2target       # Start
docker stop scan2target        # Stop
docker restart scan2target     # Restart
docker ps                      # Status
docker logs -f scan2target     # Logs
```

---

## 🏠 Home Assistant Integration

Trigger scans from Home Assistant automations, buttons, voice commands, or NFC tags.

**Voraussetzungen:**
- Scanner als "Favorite" in der Web UI markieren
- Target als "Favorite" in der Web UI markieren

### Quick Setup

```yaml
# configuration.yaml
rest_command:
  scan_document:
    url: "http://YOUR_SERVER_IP:8000/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "document"}'
  
  scan_multipage:
    url: "http://YOUR_SERVER_IP:8000/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "adf", "source": "ADF"}'

script:
  # Flatbed Scan (einzelne Seite)
  scan_flatbed:
    alias: "Scan Flatbed"
    icon: mdi:file-document-outline
    sequence:
      - service: rest_command.scan_document
      - service: notify.persistent_notification
        data:
          title: "Scan gestartet"
          message: "Flatbed-Scan läuft..."
  
  # ADF Scan (mehrere Seiten)
  scan_adf:
    alias: "Scan ADF (Multi-page)"
    icon: mdi:file-document-multiple-outline
    sequence:
      - service: rest_command.scan_multipage
      - service: notify.persistent_notification
        data:
          title: "Scan gestartet"
          message: "ADF-Scan läuft..."
```

### Features

- ✅ REST Commands für alle Scan-Profile
- ✅ Status-Sensor mit Real-Time Updates
- ✅ Voice Commands & NFC Tag Support
- ✅ Actionable Notifications
- ✅ Geplante automatische Scans

📖 **Vollständige Dokumentation:** [docs/homeassistant.md](docs/homeassistant.md)  
📋 **Beispiel-Configs:** [examples/homeassistant_config.yaml](examples/homeassistant_config.yaml)

---

## 🔌 API

Vollständige REST API mit Swagger Dokumentation: `http://YOUR_SERVER_IP/docs`

### Key Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/v1/scan/start` | POST | Scan starten |
| `/api/v1/scan/preview` | POST | Quick Preview |
| `/api/v1/history/{job_id}/cancel` | POST | Laufenden Job abbrechen |
| `/api/v1/devices/discover` | GET | Scanner suchen |
| `/api/v1/stats/overview` | GET | Statistiken abrufen |
| `/api/v1/homeassistant/scan` | POST | Home Assistant Trigger |
| `/api/v1/homeassistant/status` | GET | HA Status Sensor |
| `/api/v1/ws` | WebSocket | Real-Time Updates |

---

## 🐛 Troubleshooting

### Scanner zeigt sich als offline nach Neustart

Das Scanner Health Monitoring System prüft automatisch alle 60 Sekunden die Verfügbarkeit. Falls ein Scanner nach Container-Neustart offline erscheint:

1. **60 Sekunden warten** - Der Health Monitor erkennt ihn automatisch
2. **Logs prüfen**: `docker logs -f scan2target`
3. **Manueller Check**: `curl http://localhost:8000/api/v1/devices/{device_id}/check`
4. **Debug-Tool**: `./scripts/debug-scanner.sh`

Siehe: [Scanner Health Monitoring Guide](docs/scanner-health-monitoring.md)

### Logs ansehen

```bash
# Live Console-Logs
docker logs -f scan2target

# Persistente detaillierte Logs
docker exec scan2target tail -f /var/log/scan2target/app.log

# Quick Debug
./scripts/debug-scanner.sh
```

Siehe: [Logging Guide](docs/logging.md)

### Häufige Probleme

**Scanner wird nicht gefunden:**
- Scanner eingeschaltet und mit Netzwerk verbunden?
- Firewall erlaubt mDNS/Scanner-Traffic?
- Bei Netzwerk-Scannern: Gleiche Netzwerk/VLAN?
- Auf Health-Check warten (alle 60s)

**Container kann Scanner nicht erreichen:**
- `network_mode: host` in docker-compose.yml verwenden
- Für USB-Scanner: Device Mappings aktivieren

**Health Monitor läuft nicht:**
```bash
curl http://localhost:8000/api/v1/devices/health/status
# Sollte zeigen: "monitor_active": true
```

---

## 💻 Development

```bash
# Backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0

# Frontend
cd app/web
npm run dev
```

---

## 📚 Documentation

### Guides & Tutorials
- **[Docker Guide](docs/docker.md)** - Vollständiger Docker Deployment Guide
- **[Docker Quick Reference](DOCKER_QUICKREF.md)** - Häufige Befehle
- **[GitHub Container Registry](docs/github-container-registry.md)** - Pre-built Images & CI/CD
- **[Scanner Health Monitoring](docs/scanner-health-monitoring.md)** - Auto-Recovery & Monitoring
- **[Logging Guide](docs/logging.md)** - Umfassende Logging-Dokumentation
- **[Scanner Offline Fix](docs/scanner-health-monitoring.md)** - Scanner-Monitoring Dokumentation

### API & Integration
- **[API Documentation](http://YOUR_SERVER_IP/docs)** - Swagger/OpenAPI Docs
- **[Home Assistant](docs/homeassistant.md)** - Integration Guide

### Architecture
- **[Architecture](docs/architecture.md)** - System-Architektur
- **[Implementation Plan](docs/implementation_plan.md)** - Implementierungsplan

---

## 📝 License

MIT License - Siehe [LICENSE](LICENSE) Datei

---

## 🤝 Contributing

Dies ist ein Lernprojekt. Contributions sind willkommen!

---

## ⚠️ Security Notes

- ✅ Standard-Passwort **sofort ändern**
- ✅ Encryption Key in Production setzen
- ✅ HTTPS via Reverse Proxy verwenden (Caddy/nginx)
- ✅ `SCAN2TARGET_REQUIRE_AUTH=true` für Pflicht-Authentifizierung

---

<div align="center">

**Entwickelt mit ❤️ und AI/Copilot**

⭐ Wenn dir dieses Projekt gefällt, gib uns einen Star!

[⬆ Nach oben](#-scan2target)

</div>
