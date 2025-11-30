# Scan2Target

Modern web-based scan server for network and USB scanners. Control scanners remotely and route documents to SMB shares, email, cloud storage, or webhooks.

**📚 Learning Project:** Created with AI/Copilot assistance as a learning exercise for modern web development, REST APIs, and system integration.

## Features

- 🖨️ **Auto-Discovery** - USB and network scanners (SANE/eSCL)
- 🎯 **9 Target Types** - SMB, SFTP, Email, Paperless-ngx, Webhooks, Google Drive, Dropbox, OneDrive, Nextcloud
- 🌍 **Multi-Language** - English/German UI
- 📊 **Statistics** - Usage tracking and analytics
- 🔒 **Secure** - Encrypted credentials (Fernet AES-128)
- 🔄 **Auto-Retry** - Failed uploads retry automatically
- 📱 **PWA** - Install as native app
- 🔍 **Preview** - Low-res preview before full scan
- ⚡ **Real-Time** - WebSocket live updates

## Quick Start

```bash
git clone https://github.com/fgrfn/Scan2Target.git
cd Scan2Target
sudo ./installer/install.sh
```

Access at: `http://YOUR_SERVER_IP`

**Default Login:** `admin` / `admin` (**change immediately!**)

### Security Setup (Production)

```bash
# Generate encryption key
export SCAN2TARGET_SECRET_KEY=$(openssl rand -base64 32)

# Add to service file
sudo nano /etc/systemd/system/scan2target.service
# Add: Environment="SCAN2TARGET_SECRET_KEY=your-key-here"

# Restart
sudo systemctl daemon-reload
sudo systemctl restart scan2target
```

## Requirements

- Linux (Debian/Ubuntu/Raspberry Pi OS)
- 2GB+ RAM recommended
- Scanner with SANE or eSCL support

## Usage

### 1. Add Scanner
1. Open Web UI
2. Go to "Scannen" section
3. Click "🔍 Scanner suchen"
4. Select discovered scanner
5. Click "Scanner hinzufügen"

### 2. Add Target
1. Go to "Ziele" section
2. Click target type (SMB, Email, Cloud, etc.)
3. Fill in connection details:
   - **SMB:** Share path (`//nas.local/scans`), username, password
   - **Email:** Recipient, SMTP server, credentials
   - **Cloud:** OAuth2 tokens, folder paths
4. Click "Testen & Speichern" to validate connection
5. Target is saved and ready to use

### 3. Start Scan
1. Select scanner from dropdown
2. Choose scan profile (Document, Photo, ADF)
3. Select target destination
4. Click "Scan starten"
5. Monitor progress in "Aktive Scans"

## Scan Profiles

- **Document @200 DPI (Gray)** - Text documents (~150 KB/page)
- **Multi-Page (ADF)** - Automatic feeder, one PDF
- **Color @300 DPI** - Standard quality (~400 KB/page)
- **Photo @600 DPI** - High quality (~2 MB/page)

## Target Types

1. **SMB/CIFS** - Windows/Samba shares
2. **SFTP** - SSH file transfer
3. **Email** - SMTP delivery
4. **Paperless-ngx** - Document management
5. **Webhook** - Custom HTTP endpoints
6. **Google Drive** - OAuth2
7. **Dropbox** - OAuth2
8. **OneDrive** - OAuth2
9. **Nextcloud** - WebDAV

All targets test connection before save and support auto-retry on failure.

## Service Management

```bash
sudo systemctl start scan2target    # Start
sudo systemctl stop scan2target     # Stop
sudo systemctl restart scan2target  # Restart
sudo systemctl status scan2target   # Status
sudo journalctl -u scan2target -f   # Logs
```

## API

Full REST API with Swagger docs at: `http://YOUR_SERVER_IP/docs`

**Key Endpoints:**
- `POST /api/v1/scan/start` - Start scan
- `POST /api/v1/scan/preview` - Quick preview
- `GET /api/v1/devices/discover` - Find scanners
- `GET /api/v1/stats/overview` - Statistics
- `WS /api/v1/ws` - Real-time updates

## Development

```bash
# Backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0

# Frontend
cd app/web
npm run dev
```

## Documentation

- **API:** `http://YOUR_SERVER_IP/docs`
- **Architecture:** `docs/architecture.md`
- **Implementation:** `docs/implementation_plan.md`

## Tech Stack

- **Backend:** FastAPI, Python 3.12
- **Frontend:** Svelte, Vite
- **Database:** SQLite
- **Scanner:** SANE, eSCL/AirScan
- **Encryption:** Fernet (AES-128-CBC + HMAC)

## License

MIT License - See LICENSE file

## Contributing

This is a learning project. Contributions welcome!

---

**⚠️ Security Notes:**
- Change default password immediately
- Set encryption key in production
- Use HTTPS via reverse proxy (Caddy/nginx)
- Enable `SCAN2TARGET_REQUIRE_AUTH=true` for mandatory auth
