<div align="center">

<img src="logo.png" alt="Scan2Target Logo" width="300"/>

[![Version](https://img.shields.io/github/v/release/fgrfn/Scan2Target?label=version)](https://github.com/fgrfn/Scan2Target/releases)
[![CI](https://github.com/fgrfn/Scan2Target/actions/workflows/ci.yml/badge.svg)](https://github.com/fgrfn/Scan2Target/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://github.com/fgrfn/Scan2Target/pkgs/container/scan2target)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)

**Web-based scan server for USB and network scanners**

Control SANE/eSCL scanners remotely and route documents to network shares,
email, document-management systems, cloud storage or webhooks.

</div>

---

> **Learning project:** Scan2Target was created with AI/Copilot assistance as a
> practical project for modern web development, REST APIs and system integration.

## Features

### Scanner management

- Automatic discovery of USB and network scanners through SANE and eSCL/AirScan
- Flatbed, ADF and duplex workflows
- Health monitoring and scanner reconnection
- Low-resolution previews
- Manual and automatic multi-page scanning
- Restart-safe server-side scan sessions with resume and cancellation
- Page reordering, rotation, blank-page removal and margin/contrast optimization
- Optional searchable OCR and PDF/A-2 output (German and English)
- Real-time job updates through authenticated WebSockets
- Actual process termination when a running scan is cancelled

### Delivery targets

- SMB/CIFS
- SFTP
- Email/SMTP
- Paperless-ngx
- Webhooks
- Google Drive
- Dropbox
- OneDrive
- Nextcloud/WebDAV

### Web interface and integrations

- Responsive Svelte interface
- Progressive Web App
- English and German UI
- Configurable scan profiles
- Scan history and statistics
- REST API and Home Assistant endpoints
- Favorite scanner and target support

### Security and reliability

- Authentication enabled by default
- One-time first-run administrator setup; **no default password**
- Persistent signed sessions and encrypted target credentials
- Login throttling and password requirements
- Request, page-count and upload-size limits
- Filename/path validation
- Private-address protection for per-scan webhook callbacks
- Automated backend, frontend and live-container CI checks
- Manual, test-gated releases

## Quick start with Docker Compose

### 1. Clone the repository

```bash
git clone https://github.com/fgrfn/Scan2Target.git
cd Scan2Target
```

### 2. Create a secure environment file

```bash
printf 'SCAN2TARGET_SECRET_KEY=%s\nSCAN2TARGET_REQUIRE_AUTH=true\n' \
  "$(openssl rand -base64 48)" > .env
```

Keep this key together with your data backup. Changing or losing it prevents
stored target credentials from being decrypted.

### 3. Start Scan2Target

```bash
docker compose up -d
docker compose logs -f
```

Open:

```text
http://YOUR_SERVER_IP:8000
```

The Web UI asks you to create the first administrator. There is no
`admin/admin` account.

### USB scanner access

Enable the USB mappings in `docker-compose.yml` when the scanner is connected
directly to the Docker host:

```yaml
volumes:
  - /dev/bus/usb:/dev/bus/usb
devices:
  - /dev/bus/usb
```

Some hosts may additionally require privileged mode or an explicit device/group
mapping. Network scanner discovery uses host networking for mDNS/AirScan.

## Pre-built container image

Stable releases are tagged from versioned Git tags. The `latest` tag is not
replaced by ordinary development commits; ongoing main-branch builds use
`edge`.

```bash
# Stable release
docker pull ghcr.io/fgrfn/scan2target:latest

# Current main branch
docker pull ghcr.io/fgrfn/scan2target:edge
```

Example:

```bash
docker run -d \
  --name scan2target \
  --network host \
  --restart unless-stopped \
  -v scan2target-data:/data \
  -e SCAN2TARGET_SECRET_KEY="$(openssl rand -base64 48)" \
  -e SCAN2TARGET_REQUIRE_AUTH=true \
  ghcr.io/fgrfn/scan2target:latest
```

For persistent installations, store the key in an environment file or Docker
secret rather than generating a new value on every start.

## Important configuration

| Variable | Default | Description |
|---|---:|---|
| `SCAN2TARGET_SECRET_KEY` | none | Credential encryption key; required by Docker Compose |
| `SCAN2TARGET_JWT_SECRET` | generated/persisted | Optional separate session-signing secret |
| `SCAN2TARGET_REQUIRE_AUTH` | `true` | Require authentication for application API routes |
| `SCAN2TARGET_HA_API_KEY` | none | Dedicated key for Home Assistant endpoints |
| `SCAN2TARGET_CORS_ORIGINS` | empty | Comma-separated external browser origins |
| `SCAN2TARGET_ALLOW_PRIVATE_WEBHOOKS` | `false` | Permit per-scan callbacks to private/local addresses |
| `SCAN2TARGET_MAX_REQUEST_SIZE_MB` | `100` | Maximum HTTP request body size |
| `SCAN2TARGET_MAX_BATCH_PAGE_MB` | `20` | Maximum decoded size of one manual page |
| `SCAN2TARGET_MAX_BATCH_PAGES` | `100` | Maximum number of manual batch pages |
| `SCAN2TARGET_SCAN_SESSION_TTL_HOURS` | `24` | Retention time for unfinished server-side scan sessions |
| `SCAN2TARGET_DATA_DIR` | `/data` | Persistent application data directory |
| `SCAN2TARGET_DATABASE_PATH` | `/data/db/scan2target.db` | SQLite database path |
| `SCAN2TARGET_SCANNER_CHECK_INTERVAL` | `30` | Scanner reachability interval in seconds |
| `SCAN2TARGET_HEALTH_CHECK_INTERVAL` | `60` | Health-monitor interval in seconds |

See [`.env.example`](.env.example) for the complete documented template.

## Home Assistant

Home Assistant can trigger scans using the dedicated REST endpoints. Configure
`SCAN2TARGET_HA_API_KEY` and send it through `X-API-Key` instead of storing a
normal user session token in Home Assistant.

```yaml
rest_command:
  scan_document:
    url: "http://YOUR_SERVER_IP:8000/api/v1/homeassistant/scan"
    method: POST
    headers:
      X-API-Key: !secret scan2target_api_key
    content_type: "application/json"
    payload: >-
      {"scanner_id":"favorite","target_id":"favorite","profile":"document"}
```

Additional examples are available in [docs/homeassistant.md](docs/homeassistant.md)
and [examples/homeassistant_config.yaml](examples/homeassistant_config.yaml).

## Native installation

A native systemd installer is included for supported Debian/Ubuntu-style hosts:

```bash
git clone https://github.com/fgrfn/Scan2Target.git
cd Scan2Target
sudo ./installer/install.sh
```

After installation, open the Web UI and complete the first-run administrator
setup. Review the generated service configuration and make sure the data and
secret paths are included in your backup.

## Development

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pytest -q
ruff check app tests --select E9,F63,F7,F82
```

### Frontend

```bash
cd app/web
npm ci
npm run check
npm run build
```

### Container smoke test

```bash
docker build -t scan2target:dev .
docker run --privileged --rm -p 8000:8000 \
  -e SCAN2TARGET_SECRET_KEY=development-only-secret \
  -e SCAN2TARGET_REQUIRE_AUTH=false \
  scan2target:dev
```

Check `http://127.0.0.1:8000/health` after startup.

## Release process

Releases are created manually from the GitHub Actions **Create Release**
workflow. Before a version is tagged, the workflow runs backend tests, frontend
checks and a container build. Version tags publish stable container tags,
including `latest`.

## Documentation

- [Architecture](docs/architecture.md)
- [Docker deployment](docs/docker.md)
- [Unraid setup](docs/unraid-setup.md)
- [Home Assistant](docs/homeassistant.md)
- [Scan profiles](docs/profiles.md)
- [Scanner monitoring](docs/scanner-health-monitoring.md)
- [Logging](docs/logging.md)
- [Versioning](docs/versioning.md)
- [Deployment notes](DEPLOY.md)

## Security notes

- Run Scan2Target behind HTTPS when it is reachable outside a trusted LAN.
- Do not publish port 8000 directly to the Internet.
- Keep `/data`, the database and encryption/session secrets in the same backup
  plan.
- Leave private webhook callbacks disabled unless they are intentionally needed
  on a trusted network.
- Use a dedicated Home Assistant API key.
- Report sensitive vulnerabilities privately rather than opening a public issue.

## License

Scan2Target is released under the [MIT License](LICENSE).
