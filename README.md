# RaspScan

RaspScan is a Raspberry Pi-based scan and print server that centralizes scanning for devices without physical scan buttons (e.g., HP Envy 6400) and exposes AirPrint/IPP printing via CUPS.

## Contents
- `docs/architecture.md` — system architecture, API overview, security model.
- `docs/implementation_plan.md` — roadmap from MVP to v1.0.
- `app/` — backend (FastAPI), core modules, and web UI skeleton.

## Quick Start (planned)
1. Install dependencies: `sudo apt install cups avahi-daemon sane-airscan python3-venv`.
2. Create Python virtualenv and install API requirements (to be added).
3. Run backend: `uvicorn app.main:app --reload`.
4. Access API at `http://localhost:8000/api/v1` and health check at `/health`.

For HTTPS, place RaspScan behind Caddy or nginx with TLS termination and enable IP allowlists via configuration.
