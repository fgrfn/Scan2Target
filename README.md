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
1. Install dependencies: `sudo apt install cups cups-browsed avahi-daemon sane-utils sane-airscan python3-venv`.
2. Create Python virtualenv and install API requirements: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
3. Run backend: `uvicorn app.main:app --reload`.
4. Access API at `http://localhost:8000/api/v1` and health check at `/health`.

For HTTPS, place RaspScan behind Caddy or nginx with TLS termination and enable IP allowlists via configuration.

## Web UI (modern Svelte preview)
The `app/web` directory now includes a modern Svelte + Vite single-page interface with glassmorphism styling. To run locally:

```bash
cd app/web
npm install
npm run dev
```

Build assets with `npm run build`; serve the resulting `dist/` directory via Caddy/nginx or mount it as static files in the FastAPI app. Wire the stubbed controls to the existing API endpoints (e.g., `/api/scan/start`, `/api/printers`, `/api/print`).
