# RaspScan

RaspScan is a Raspberry Pi-based scan and print server that centralizes scanning for devices without physical scan buttons (e.g., HP Envy 6400) and exposes AirPrint/IPP printing via CUPS.

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
1. Install dependencies: `sudo apt install cups cups-browsed avahi-daemon sane-utils sane-airscan python3-venv smbclient`.
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
- Job history (scans and prints)
- Target configurations (SMB, SFTP, etc.)
- Scan profiles

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

## Printer Setup

### Auto-Discovery (Recommended)
RaspScan automatically detects:
- **USB Printers:** Connected to any USB port (no need to specify which port)
- **Wireless Printers:** AirPrint/IPP devices on the local network (via DNS-SD/mDNS)

Use the Settings page in the web UI or the API endpoint:
```bash
curl http://localhost:8000/api/v1/printers/discover
```

### How It Works
- **USB Detection:** CUPS automatically detects USB printers when plugged in. The system identifies manufacturer, model, and creates a device URI (e.g., `usb://HP/ENVY%206400`).
- **Wireless Detection:** Uses Avahi/mDNS to discover network printers advertising AirPrint/IPP services.
- **Scanner vs Printer:** Multi-function devices (like HP Envy 6400) appear in both printer and scanner lists if they support both protocols. Wireless scanners use eSCL/AirScan (SANE backend), while printers use IPP/AirPrint.

### Adding Printers
1. Click "Discover Printers" in Settings
2. Select detected device and click "Add"
3. CUPS automatically selects the appropriate driver (IPP Everywhere for modern printers)

For manual setup, use URIs like:
- USB: `usb://HP/ENVY%206400`
- Network: `ipp://printer.local/ipp/print`
- AirPrint: `dnssd://HP%20Envy%206400._ipp._tcp.local/`
