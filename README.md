# RaspScan - Scan Hub

RaspScan is a Raspberry Pi-based scan server that centralizes scanning for network and USB devices. Trigger scans remotely via API or web interface and automatically route scanned documents to network targets (SMB shares, email, webhooks).

## Contents
- `docs/architecture.md` — system architecture, API overview, security model.
- `docs/implementation_plan.md` — roadmap from MVP to v1.0.
- `app/` — backend (FastAPI), core modules, and web UI skeleton.
- `installer/` — installation helper and systemd unit template.

## Installation & Autostart
1. From the repository root run the installer with sudo to set up dependencies, a virtualenv, and a systemd service:
   ```bash
   sudo ./installer/install.sh
   ```
   This writes `/etc/systemd/system/raspscan.service`, enables it at boot, and starts the API on port 8000.
2. If you prefer manual setup, edit and copy `installer/raspscan.service` to `/etc/systemd/system/` and adjust `User`, `WorkingDirectory`, and paths to your deployment location, then enable it with `sudo systemctl enable --now raspscan`.

## Quick Start (manual)
1. Install dependencies: `sudo apt install cups cups-browsed avahi-daemon sane-utils sane-airscan python3-venv smbclient imagemagick`.
2. Create Python virtualenv and install API requirements: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
3. Run backend: `uvicorn app.main:app --reload`.
4. On first start, a default admin user is created (username: `admin`, password: `admin`).
5. **⚠️ CHANGE THE DEFAULT PASSWORD IMMEDIATELY!**
6. Access API at `http://localhost:8000/api/v1` and health check at `/health`.

## Authentication

### Default User
On first startup, RaspScan creates a default admin user:
- **Username:** `admin`
- **Password:** `admin`
- **⚠️ SECURITY:** Change this password immediately after first login!

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
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
  http://localhost:8000/api/v1/scan/start
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

## Web UI (modern Svelte preview)
The `app/web` directory now includes a modern Svelte + Vite single-page interface with glassmorphism styling. To run locally:

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
curl http://localhost:8000/api/v1/devices/discover
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

Configure destinations for scanned documents:

### SMB/CIFS Share
```bash
curl -X POST http://localhost:8000/api/v1/targets \
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
curl -X POST http://localhost:8000/api/v1/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Email to Archive",
    "type": "EMAIL",
    "config": {
      "to": "archive@example.com",
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_user": "scanner@example.com",
      "smtp_password": "app-password"
    }
  }'
```

### Connection Testing
All targets are automatically tested before saving:
```bash
curl -X POST http://localhost:8000/api/v1/targets/{target_id}/test
```

## Advanced Features

### Webhook Notifications
Get notified when scans complete:
```bash
curl -X POST http://localhost:8000/api/v1/scan/start \
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
Automatic thumbnail generation:
- 400x400px preview created for each scan
- Available in webhook notification metadata
- Stored temporarily with scan output

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
