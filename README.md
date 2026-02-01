# Scan2Target

Modern web-based scan server for network and USB scanners. Control scanners remotely and route documents to SMB shares, email, cloud storage, or webhooks.

**📚 Learning Project:** Created with AI/Copilot assistance as a learning exercise for modern web development, REST APIs, and system integration.

## Features

- 🖨️ **Auto-Discovery** - USB and network scanners (SANE/eSCL)
- 🎯 **9 Target Types** - SMB, SFTP, Email, Paperless-ngx, Webhooks, Google Drive, Dropbox, OneDrive, Nextcloud
- 🌍 **Multi-Language** - English/German UI with complete translations
- 📊 **Statistics** - Comprehensive analytics dashboard:
  - Hourly scan distribution (browser timezone)
  - Scanner/target usage statistics
  - Success rates and daily averages
  - 30-day timeline tracking
- 🔒 **Secure** - Encrypted credentials (Fernet AES-128)
- 🔄 **Auto-Retry** - Failed uploads retry automatically
- 📱 **PWA** - Install as native app
- 🔍 **Preview** - Low-res preview before full scan
- ⚡ **Real-Time** - WebSocket live updates with timezone conversion
- ❌ **Job Control** - Cancel running scans instantly

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/fgrfn/Scan2Target.git
cd Scan2Target

# Generate secure encryption key
echo "SCAN2TARGET_SECRET_KEY=$(openssl rand -base64 32)" > .env

# Start with Docker Compose
docker-compose up -d
```

Access at: `http://YOUR_SERVER_IP:8000`

**Default Login:** `admin` / `admin` (**change immediately!**)

### Option 2: Native Installation

```bash
git clone https://github.com/fgrfn/Scan2Target.git
cd Scan2Target
sudo ./installer/install.sh
```

Access at: `http://YOUR_SERVER_IP`

**Default Login:** `admin` / `admin` (**change immediately!**)

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/fgrfn/Scan2Target.git
cd Scan2Target

# 2. Create environment file
cat > .env << 'EOF'
SCAN2TARGET_SECRET_KEY=$(openssl rand -base64 32)
SCAN2TARGET_REQUIRE_AUTH=true
EOF

# 3. Start services
docker compose up -d

# 4. View logs
docker compose logs -f

# 5. Stop services
docker compose down
```

### Using Docker CLI

```bash
# Build image
docker build -t scan2target:latest .

# Run container
docker run -d \
  --name scan2target \
  --network host \
  -v scan2target-data:/data \
  -v /dev/bus/usb:/dev/bus/usb \
  --device /dev/bus/usb \
  -e SCAN2TARGET_SECRET_KEY="$(openssl rand -base64 32)" \
  -e SCAN2TARGET_REQUIRE_AUTH=true \
  scan2target:latest
```

### Pre-built Images

Images are automatically built and published to GitHub Container Registry:

```bash
# Pull latest image
docker pull ghcr.io/fgrfn/scan2target:latest

# Pull specific version
docker pull ghcr.io/fgrfn/scan2target:v0.1.0

# Run pre-built image
docker run -d \
  --name scan2target \
  --network host \
  -v scan2target-data:/data \
  -e SCAN2TARGET_SECRET_KEY="your-secret-key-here" \
  ghcr.io/fgrfn/scan2target:latest
```

### Docker Configuration

**Environment Variables:**
- `SCAN2TARGET_SECRET_KEY` - Encryption key for credentials (required in production)
- `SCAN2TARGET_REQUIRE_AUTH` - Force authentication (default: true)
- `SCAN2TARGET_DATA_DIR` - Data directory path (default: /data)
- `SCAN2TARGET_DB_PATH` - Database file path (default: /data/db/scan2target.db)
- `SCAN2TARGET_SCANNER_CHECK_INTERVAL` - Scanner reachability check interval in seconds (default: 30)

**Volumes:**
- `/data` - Persistent storage for database and scans (**REQUIRED**)
- `/dev/bus/usb` - USB device access for scanners

⚠️ **IMPORTANT:** Do NOT mount any volume to `/app` - this will overwrite the application code and cause startup failures. Always use `/data` for persistent storage.

**Network:**
- `host` network mode required for scanner discovery (mDNS/Avahi)

### Security Setup (Production)

```bash
# Generate encryption key
export SCAN2TARGET_SECRET_KEY=$(openssl rand -base64 32)

# For native installation: Add to service file
sudo nano /etc/systemd/system/scan2target.service
# Add: Environment="SCAN2TARGET_SECRET_KEY=your-key-here"

# Restart
sudo systemctl daemon-reload
sudo systemctl restart scan2target
```

## Requirements

### Docker (Recommended)
- Docker 20.10+ or Docker Desktop
- Docker Compose v2.0+
- 2GB+ RAM recommended
- Scanner with SANE or eSCL support

### Native Installation
- Linux (Debian/Ubuntu/Raspberry Pi OS)
- 2GB+ RAM recommended
- Scanner with SANE or eSCL support

## Usage

### 1. Add Scanner
1. Open Web UI
2. Go to "Scan" section
3. Click "Discover Scanners"
4. Select discovered scanner
5. Click "Add Scanner"

### 2. Add Target
1. Go to "Targets" section
2. Click target type (SMB, Email, Cloud, etc.)
3. Fill in connection details:
   - **SMB:** Share path (`//nas.local/scans`), username, password
   - **Email:** Recipient, SMTP server, credentials
   - **Cloud:** OAuth2 tokens, folder paths
4. Click "Test & Save" to validate connection
5. Target is saved and ready to use

### 3. Start Scan
1. Select scanner from dropdown
2. Choose scan profile (Document, Photo, ADF)
3. Select target destination
4. Click "Start Scan"
5. Monitor progress in "Active Scans"

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

## Troubleshooting

### Error: "Could not import module 'main'"

**Problem:** Container fails to start with error: `ERROR: Error loading ASGI app. Could not import module "main".`

**Cause:** A volume is incorrectly mounted to `/app`, overwriting the application code.

**Solution:**
1. Check your Docker volume configuration
2. Ensure you're mapping to `/data`, NOT `/app`

**Correct configuration:**
```bash
# Docker CLI
-v /mnt/user/appdata/Scan2Target:/data

# Docker Compose
volumes:
  - /mnt/user/appdata/Scan2Target:/data
```

**For Unraid users:**
- Container Path: `/data` ✅
- Host Path: `/mnt/user/appdata/Scan2Target`

**NEVER use:**
- Container Path: `/app` ❌

### Scanner Discovery Not Working

If scanners aren't automatically discovered:
1. Ensure `--network host` is used
2. Manually add scanner via IP address in the UI
3. Check scanner is on the same network

For more help, check the [docs/docker.md](docs/docker.md) guide.

## Home Assistant Integration

Trigger scans from Home Assistant automations, buttons, voice commands, or NFC tags.

**Quick Setup:**
```yaml
# configuration.yaml
rest_command:
  scan_document:
    url: "http://YOUR_SERVER_IP/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "document"}'
  
  scan_multipage:
    url: "http://YOUR_SERVER_IP/api/v1/homeassistant/scan"
    method: POST
    content_type: "application/json"
    payload: '{"scanner_id": "favorite", "target_id": "favorite", "profile": "adf", "source": "ADF"}'

script:
  # Flatbed scan (single page)
  scan_flatbed:
    alias: "Scan Flatbed"
    icon: mdi:file-document-outline
    sequence:
      - service: rest_command.scan_document
      - service: notify.persistent_notification
        data:
          title: "Scan started"
          message: "Flatbed scan in progress..."
  
  # ADF scan (multiple pages)
  scan_adf:
    alias: "Scan ADF (Multi-page)"
    icon: mdi:file-document-multiple-outline
    sequence:
      - service: rest_command.scan_multipage
      - service: notify.persistent_notification
        data:
          title: "Scan started"
          message: "ADF scan in progress..."
```

**Features:**
- ✅ REST commands for all scan profiles
- ✅ Status sensor with real-time updates
- ✅ Voice commands & NFC tag support
- ✅ Actionable notifications
- ✅ Scheduled automatic scans

📖 **Full documentation:** [docs/homeassistant.md](docs/homeassistant.md)  
📋 **Example configs:** [examples/homeassistant_config.yaml](examples/homeassistant_config.yaml)

## API

Full REST API with Swagger docs at: `http://YOUR_SERVER_IP/docs`

**Key Endpoints:**
- `POST /api/v1/scan/start` - Start scan
- `POST /api/v1/scan/preview` - Quick preview
- `POST /api/v1/history/{job_id}/cancel` - Cancel running job
- `GET /api/v1/devices/discover` - Find scanners
- `GET /api/v1/stats/overview` - Statistics
- `POST /api/v1/homeassistant/scan` - Home Assistant trigger
- `GET /api/v1/homeassistant/status` - HA status sensor
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

- **Docker Guide:** [docs/docker.md](docs/docker.md) - Complete Docker deployment guide
- **Docker Quick Ref:** [DOCKER_QUICKREF.md](DOCKER_QUICKREF.md) - Common commands
- **GitHub Container Registry:** [docs/github-container-registry.md](docs/github-container-registry.md) - Pre-built images & CI/CD
- **API:** `http://YOUR_SERVER_IP/docs` - Swagger/OpenAPI docs
- **Home Assistant:** [docs/homeassistant.md](docs/homeassistant.md) - Integration guide
- **Architecture:** [docs/architecture.md](docs/architecture.md)
- **Implementation:** [docs/implementation_plan.md](docs/implementation_plan.md)

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
