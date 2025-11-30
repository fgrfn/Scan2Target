# RaspScan - Scan Hub

RaspScan is a network scan server that centralizes scanning for network and USB devices. Trigger scans remotely via API or web interface and automatically route scanned documents to network targets (SMB shares, email, webhooks). Works on Linux servers, Raspberry Pi, and virtual machines.

## Contents
- `docs/architecture.md` — system architecture, API overview, security model.
- `docs/implementation_plan.md` — roadmap from MVP to v1.0.
- `app/` — backend (FastAPI), core modules, and web UI skeleton.
- `installer/` — installation helper and systemd unit template.

## Installation & Autostart

### Automated Installation (Recommended)
1. Clone the repository and run the installer:
   ```bash
   git clone https://github.com/yourusername/RaspScan.git
   cd RaspScan
   sudo ./installer/install.sh
   ```

The installer automatically:
- ✅ Installs system dependencies (SANE, ImageMagick, Node.js)
- ✅ Creates Python virtual environment
- ✅ Installs Python dependencies
- ✅ Builds Web UI production bundle
- ✅ Sets up systemd service (auto-start on boot, standard HTTP port 80)
- ✅ Configures automatic cleanup cron job (daily at 3 AM)
- ✅ Creates database and default admin user

2. Access RaspScan at: `http://YOUR_SERVER_IP` (no port needed - runs on port 80)

### Manual Setup
If you prefer manual installation:
1. Install dependencies: `sudo apt install avahi-daemon sane-utils sane-airscan python3-venv smbclient ssh imagemagick nodejs npm`
2. Create virtualenv: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. Build Web UI: `cd app/web && npm install && npm run build && cd ../..`
4. Copy service file: `sudo cp installer/raspscan.service /etc/systemd/system/`
5. Edit service paths in `/etc/systemd/system/raspscan.service`
6. Enable service: `sudo systemctl enable --now raspscan`
7. Setup cleanup: `chmod +x scripts/cleanup.sh && (crontab -l; echo "0 3 * * * $(pwd)/scripts/cleanup.sh") | crontab -`

## Quick Start

After installation:
1. Access Web UI at `http://YOUR_SERVER_IP`
2. Login with default credentials (username: `admin`, password: `admin`)
3. **⚠️ CHANGE THE DEFAULT PASSWORD IMMEDIATELY!**
4. Click "Discover Scanners" to find your scanner
5. Configure a target (SMB share, email, etc.)
6. Start scanning!

### Development Mode
For local development with hot-reload:
```bash
# Backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0

# Frontend (in separate terminal)
cd app/web
npm run dev
```

## System Requirements

- **Hardware:** Linux server, VM, or Raspberry Pi (2GB+ RAM recommended)
- **OS:** Debian-based Linux (Debian, Ubuntu, Raspberry Pi OS)
- **Network:** Wired or WiFi connection
- **Scanner:** USB or network scanner with SANE/eSCL support

## Authentication

### Default User
On first startup, RaspScan creates a default admin user:
- **Username:** `admin`
- **Password:** `admin`
- **⚠️ SECURITY:** Change this password immediately after first login!

### Login
```bash
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@raspscan.local",
    "is_admin": true
  }
}
```

### Using Protected Endpoints
Include the token in the `Authorization` header:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost/api/v1/scan/start
```

### Authentication Configuration
By default, authentication is **optional**. To require authentication for all API calls:

Create `.env` file:
```bash
RASPSCAN_REQUIRE_AUTH=true
RASPSCAN_JWT_SECRET=your-secret-key-here
RASPSCAN_JWT_EXPIRATION=3600
```

Or set environment variables:
```bash
export RASPSCAN_REQUIRE_AUTH=true
```

## Database & Persistence

RaspScan uses SQLite for data persistence:
- **Database file:** `raspscan.db` (created automatically)
- **Location:** Current working directory or set via `RASPSCAN_DATABASE_PATH`

Stored data:
- User accounts and sessions
- Job history (scan jobs)
- Target configurations (SMB, SFTP, email, webhooks)
- Device configurations (manually added scanners)
- Scan profiles with quality settings

### Backup
```bash
# Backup database
cp raspscan.db raspscan.db.backup

# Or use SQLite backup
sqlite3 raspscan.db ".backup raspscan_backup.db"
```

For HTTPS, place RaspScan behind Caddy or nginx with TLS termination and enable IP allowlists via configuration.

## Web UI Features

The `app/web` directory includes a modern Svelte + Vite single-page interface with:
- **🌍 Multi-language support:** English and German (more languages easily added)
- **📱 Responsive design:** Works on desktop, tablet, and mobile
- **🎨 Modern glassmorphism styling**
- **⭐ Favorites system:** Mark frequently used scanners and targets
- **📊 Live scan preview:** Real-time thumbnails (50% size, click to expand)
- **🔄 Upload retry:** One-click retry for failed uploads
- **📈 Status tracking:** Separate scan and upload status indicators
- **🚀 PWA support:** Install as native app
- **🔍 Scan preview:** Low-res preview before full scan (100 DPI grayscale)
- **☁️ Cloud targets:** Configure Google Drive, Dropbox, OneDrive, Nextcloud
- **📊 Statistics dashboard:** Visual analytics with charts and metrics

To run locally:
```bash
cd app/web
npm install
npm run dev
```

Build assets with `npm run build`; serve the resulting `dist/` directory via Caddy/nginx or mount it as static files in the FastAPI app.

## Scanner Setup

### Auto-Discovery (Recommended)
RaspScan automatically detects scanners via SANE:
- **USB Scanners:** Connected via any USB port
- **Network Scanners:** eSCL/AirScan devices on the local network
- **Multi-function Devices:** Devices supporting both print and scan

Discovery endpoint:
```bash
curl http://localhost/api/v1/devices/discover
```

### How It Works
- **USB Detection:** SANE backends detect USB scanners (HPAIO, EPSON, etc.)
- **Network Detection:** Uses eSCL/AirScan protocol for wireless scanners
- **Duplicate Filtering:** Automatically prefers eSCL over legacy protocols for best compatibility
- **Status Monitoring:** Scanner availability cached (30s TTL) for fast UI updates

### Adding Scanners
1. Click "Discover Scanners" in the Scan section
2. Select detected device and click "Add"
3. Scanner is saved to database for future use

### Scan Profiles
Optimized profiles for different use cases:
- **Document @200 DPI (Gray):** Smallest size, best for text (~100-300 KB/page)
- **Multi-Page Document (ADF):** 🆕 Automatic document feeder support - scan multiple pages into one PDF
- **Color @300 DPI:** Standard quality for mixed content (~300-600 KB/page)
- **Grayscale @150 DPI:** Fast scans, very small files (~80-200 KB/page)
- **Photo @600 DPI:** High quality for photos (~1-3 MB/page)

### Multi-Page Scanning (ADF)
Automatic Document Feeder support:
- Scans until ADF is empty
- Combines all pages into single PDF
- Automatic page detection
- Safety limit: 100 pages per job

### Compression
All PDFs are automatically compressed using JPEG compression:
- Quality settings: 75-95% depending on profile
- Reduces file sizes by 90-98% vs uncompressed TIFF
- Empty A4 page: ~50-100 KB (vs 33+ MB uncompressed)

## Scan Targets

Configure destinations for scanned documents. RaspScan supports 9 target types:

### Supported Target Types
1. **SMB/CIFS** - Windows/Samba network shares
2. **SFTP** - Secure file transfer via SSH
3. **Email** - Send scans via SMTP
4. **Paperless-ngx** - Document management system integration
5. **Webhook** - Custom HTTP endpoints
6. **Google Drive** - Upload to Google Drive via OAuth2
7. **Dropbox** - Upload to Dropbox via OAuth2
8. **OneDrive** - Upload to Microsoft OneDrive via OAuth2
9. **Nextcloud** - Upload to Nextcloud via WebDAV

All targets support:
- ⭐ Favorites (mark frequently used targets)
- 🔍 Connection testing before save
- 🔄 Automatic retry on upload failure (3 attempts with exponential backoff)
- 📝 Detailed error messages

### SMB/CIFS Share
```bash
curl -X POST http://localhost/api/v1/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NAS Documents",
    "type": "SMB",
    "config": {
      "host": "//nas.local/scans",
      "username": "scanner",
      "password": "secret"
    }
  }'
```

### Email
```bash
curl -X POST http://localhost/api/v1/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Email to Archive",
    "type": "Email",
    "config": {
      "connection": "archive@example.com",
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "username": "scanner@example.com",
      "password": "app-password",
      "from": "scanner@example.com",
      "use_tls": true
    }
  }'
```

### SFTP Target
```bash
curl -X POST http://localhost/api/v1/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SFTP Server",
    "type": "SFTP",
    "config": {
      "connection": "user@server.example.com",
      "host": "server.example.com",
      "port": 22,
      "username": "user",
      "password": "password",
      "remote_path": "/uploads/scans"
    }
  }'
```

**Note**: Password is optional - if omitted, SSH key authentication will be used. Requires `sshpass` for password authentication: `sudo apt install sshpass`

### Paperless-ngx Integration
```bash
curl -X POST http://localhost/api/v1/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Paperless Archive",
    "type": "Paperless-ngx",
    "config": {
      "connection": "http://paperless.local:8000",
      "api_token": "your-api-token"
    }
  }'
```

### Webhook Target
```bash
curl -X POST http://localhost/api/v1/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Custom Webhook",
    "type": "Webhook",
    "config": {
      "connection": "https://example.com/webhook"
    }
  }'
```

### Cloud Storage Targets

#### Google Drive
```bash
curl -X POST http://localhost/api/v1/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Google Drive Scans",
    "type": "Google Drive",
    "config": {
      "access_token": "ya29.a0AfH6...",
      "folder_id": "1a2b3c4d5e6f",
      "connection": "/Scans"
    }
  }'
```

**Getting OAuth2 Token:**
1. Create project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Google Drive API
3. Create OAuth 2.0 credentials (Desktop app)
4. Use OAuth playground or script to get access token
5. Optional: Specify `folder_id` for target folder (leave empty for root)

#### Dropbox
```bash
curl -X POST http://localhost/api/v1/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Dropbox Scans",
    "type": "Dropbox",
    "config": {
      "access_token": "sl.BQx...",
      "folder_path": "/Documents/Scans",
      "connection": "/Documents/Scans"
    }
  }'
```

**Getting OAuth2 Token:**
1. Create app in [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Generate access token
3. Set `folder_path` for target directory (leave empty for root)

#### OneDrive
```bash
curl -X POST http://localhost/api/v1/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OneDrive Scans",
    "type": "OneDrive",
    "config": {
      "access_token": "EwBwA8l6...",
      "folder_path": "/Documents/Scans",
      "connection": "/Documents/Scans"
    }
  }'
```

**Getting OAuth2 Token:**
1. Register app in [Azure AD Portal](https://portal.azure.com/)
2. Add Microsoft Graph API permissions (Files.ReadWrite)
3. Generate access token via OAuth2 flow
4. Set `folder_path` for target directory

#### Nextcloud
```bash
curl -X POST http://localhost/api/v1/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nextcloud Archive",
    "type": "Nextcloud",
    "config": {
      "webdav_url": "https://cloud.example.com/remote.php/dav/files/username/",
      "username": "scanner",
      "password": "app-password",
      "upload_path": "/Scans",
      "connection": "https://cloud.example.com"
    }
  }'
```

**Setup:**
1. Get WebDAV URL from Nextcloud: Settings → WebDAV
2. Create app password: Settings → Security → Devices & sessions
3. Set `upload_path` for target directory (default: /Scans)

### Connection Testing
All targets are automatically tested before saving:
```bash
curl -X POST http://localhost/api/v1/targets/{target_id}/test
```

Or use the Web UI:
1. Configure target details
2. Click "Test & Save" to validate connection first
3. Or click "Save without test" if server is temporarily offline

### Advanced Features

### Real-Time Updates (WebSocket)
RaspScan supports WebSocket connections for real-time job status updates:

```javascript
const ws = new WebSocket('ws://YOUR_SERVER_IP/api/v1/ws');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  if (message.type === 'job_update') {
    console.log('Job updated:', message.data);
    // message.data contains: id, status, device_id, target_id, etc.
  }
};
```

**Benefits:**
- ⚡ Instant status updates (no polling delay)
- 📉 Reduced server load
- 🔋 Better battery life for mobile devices

The Web UI automatically uses WebSocket for live updates with polling as fallback.

### Webhook Notifications
Get notified when scans complete:
```bash
curl -X POST http://localhost/api/v1/scan/start \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "scanner_id",
    "profile_id": "document_200_pdf",
    "target_id": "target_id",
    "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  }'
```

Webhook payload:
```json
{
  "job_id": "uuid",
  "status": "completed",
  "timestamp": "2025-11-30T12:00:00+00:00",
  "metadata": {
    "pages": 5,
    "file_size": 245678,
    "format": "pdf",
    "profile": "document_200_pdf",
    "thumbnail": "/tmp/scan_thumb.jpg"
  }
}
```

### Live Scan Previews
Automatic thumbnail generation and display:
- 400x400px preview created for each scan
- Displayed at 50% size in Active Scans section
- Click thumbnail to expand to 100% (click again to shrink)
- Available in webhook notification metadata
- Stored temporarily with scan output (cleaned up after 7 days)

### Progressive Web App (PWA)
Install RaspScan as native app:
1. Open web interface in browser
2. Click "Install" prompt or browser menu → "Install App"
3. Launch from home screen/desktop
4. Works offline with cached interface
5. Push notifications for scan completion (future)

**Features:**
- Standalone app window (no browser UI)
- Home screen icon
- Offline support
- Fast loading with Service Worker cache
- Mobile-optimized interface

### Automatic Document Detection
Profiles support automatic optimization:
- Auto paper size detection
- Color/grayscale auto-selection
- DPI recommendation based on content
- Blank page detection (ADF mode)

## Maintenance & Cleanup

### Automatic Cleanup
RaspScan automatically manages disk space:
- **Successful scans:** Files deleted immediately after upload
- **Thumbnails:** Kept 7 days for UI preview (10-50 KB each)
- **Failed uploads:** Kept 30 days for manual retry
- **Cron job:** Runs daily at 3:00 AM (set up by installer)

### Manual Cleanup
```bash
# Run cleanup manually
cd /home/florian/RaspScan
python3 -m app.core.cleanup

# Check disk usage
curl http://localhost/api/v1/maintenance/disk-usage

# Trigger cleanup via API
curl -X POST http://localhost/api/v1/maintenance/cleanup
```

### View Cleanup Logs
```bash
tail -f /var/log/raspscan-cleanup.log
```

### Upload Retry
If upload fails (e.g., network issue):
1. Scan completes successfully, file stored locally
2. Error shown in History and Active Scans with separate status indicators:
   - Scan: ✅ Done
   - Upload: ❌ Failed
3. Click "🔄 Retry" button in Active Scans or "🔄 Retry Upload" in History
4. System attempts upload with 3 retries (exponential backoff: 2s, 4s, 8s)
5. File deleted automatically after successful retry

**Status Display:**
- **During Scan:** Scan: 🔄 Running, Upload: ⏸️ Waiting
- **Scan Failed:** Scan: ❌ Failed, Upload: ⏸️ Skipped
- **Upload Failed:** Scan: ✅ Done, Upload: ❌ Failed (with Retry button)
- **All Success:** Scan: ✅ Done, Upload: ✅ Done

## Service Management

```bash
# Start service
sudo systemctl start raspscan

# Stop service
sudo systemctl stop raspscan

# Restart service
sudo systemctl restart raspscan

# View status
sudo systemctl status raspscan

# View logs
sudo journalctl -u raspscan -f

# Disable auto-start
sudo systemctl disable raspscan
```

## Internationalization (i18n)

RaspScan Web UI supports multiple languages:

**Available Languages:**
- 🇬🇧 English (EN) - Default
- 🇩🇪 German (DE)

**Features:**
- Language selector in top-right corner of navigation bar
- Preference saved in browser localStorage
- Instant language switching (no page reload)
- All UI elements translated (navigation, buttons, status messages, etc.)

**Adding New Languages:**
Edit `app/web/src/App.svelte` and add your language to the `translations` object:
```javascript
const translations = {
  en: { /* English translations */ },
  de: { /* German translations */ },
  fr: { /* Your French translations */ }
};
```

Then add the language option to NavBar.svelte dropdown.

## Home Assistant Integration

RaspScan's open API makes integration easy:

```yaml
# configuration.yaml
rest_command:
  raspscan_quick_scan:
    url: "http://SERVER_IP/api/v1/scan/start"
    method: POST
    content_type: "application/json"
    payload: >
      {
        "device_id": "airscan:escl:HP_ENVY:http://...",
        "profile_id": "document_200_pdf",
        "target_id": "nas_documents"
      }

button:
  - platform: template
    name: "Quick Document Scan"
    icon: mdi:scanner
    press:
      - service: rest_command.raspscan_quick_scan

sensor:
  - platform: rest
    name: RaspScan Active Jobs
    resource: "http://SERVER_IP/api/v1/history"
    value_template: >
      {{ value_json | selectattr('status', 'in', ['queued', 'running']) | list | length }}
    scan_interval: 5
```

## New Features

### 🔍 Scan Preview
Get a quick low-resolution preview before running the full scan:

```bash
curl -X POST http://localhost/api/v1/scan/preview \
  -H "Content-Type: application/json" \
  -d '{"device_id": "scanner_id"}'
```

**Features:**
- 100 DPI grayscale preview (fast scan in ~3-5 seconds)
- Base64-encoded JPEG returned in response
- Perfect for checking document alignment
- Available in Web UI with "Preview Scan" button

**Web UI:**
1. Select scanner
2. Click "Preview Scan" button
3. View low-res preview in modal
4. Click "Proceed to Full Scan" or adjust document and preview again

### 📊 Statistics & Dashboard
Comprehensive scan analytics and insights:

```bash
# Overview statistics
curl http://localhost/api/v1/stats/overview

# Timeline (last 30 days)
curl http://localhost/api/v1/stats/timeline?days=30

# Scanner usage stats
curl http://localhost/api/v1/stats/scanners

# Target usage stats
curl http://localhost/api/v1/stats/targets

# Hourly distribution
curl http://localhost/api/v1/stats/hourly
```

**Dashboard Metrics:**
- 📈 Total scans (all time, today, this week, this month)
- ✅ Success rate percentage
- 📊 Average scans per day
- 🏆 Most used scanner and target
- 📅 Daily timeline (last 30 days with success/failure breakdown)
- 🕐 Hourly distribution (scan activity by hour of day 0-23)
- 📱 Per-scanner and per-target statistics

**Web UI Dashboard:**
- Visual stat cards with key metrics
- Timeline table showing daily scan counts
- Bar chart for hourly distribution
- Scanner and target usage lists with success rates

### ☁️ Cloud Storage Support
Upload scans directly to cloud storage providers:

**Supported Providers:**
- **Google Drive** - OAuth2 authentication, specify folder ID
- **Dropbox** - OAuth2 authentication, folder path
- **OneDrive** - OAuth2 via Microsoft Graph API
- **Nextcloud** - WebDAV authentication

See "Cloud Storage Targets" section above for configuration examples.

## API Endpoints

### Scanner Management
- `GET /api/v1/devices` - List all devices
- `POST /api/v1/devices/discover` - Discover scanners
- `POST /api/v1/devices/{id}/favorite` - Toggle favorite
- `DELETE /api/v1/devices/{id}` - Remove device

### Scan Operations
- `POST /api/v1/scan/start` - Start scan job
- `POST /api/v1/scan/preview` - 🆕 Get low-res preview scan
- `GET /api/v1/scan/profiles` - List scan profiles
- `GET /api/v1/history` - List scan history
- `POST /api/v1/history/{job_id}/retry-upload` - Retry failed upload

### Target Management
- `GET /api/v1/targets` - List targets
- `POST /api/v1/targets` - Create target (auto-validates connection)
- `POST /api/v1/targets/{id}/test` - Test target connection
- `PUT /api/v1/targets/{id}` - Update target
- `DELETE /api/v1/targets/{id}` - Delete target

### Statistics & Analytics
- `GET /api/v1/stats/overview` - 🆕 Overview statistics
- `GET /api/v1/stats/timeline` - 🆕 Daily scan timeline
- `GET /api/v1/stats/scanners` - 🆕 Scanner usage stats
- `GET /api/v1/stats/targets` - 🆕 Target usage stats
- `GET /api/v1/stats/hourly` - 🆕 Hourly distribution

### Maintenance
- `GET /api/v1/maintenance/disk-usage` - Get disk usage stats
- `POST /api/v1/maintenance/cleanup` - Trigger manual cleanup

### WebSocket (Real-Time Updates)
- `WS /api/v1/ws` - WebSocket endpoint for live job and scanner updates

Full API documentation: `http://YOUR_SERVER_IP/docs`
