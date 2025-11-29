# RaspScan Implementation Plan

## Milestones

### v0.1 (MVP)
- FastAPI scaffold with authentication stubs and in-memory session tokens.
- Basic config storage: SQLite migrations, YAML bootstrap loader.
- Scanner discovery via SANE/eSCL enumeration (list only).
- Start scan for a single backend; save to local folder target; filename templates.
- Printer enumeration via CUPS; submit print job for uploaded PDF/JPEG/PNG; test page endpoint.
- Targets: Local folder + SMB (basic upload) + Webhook; Paperless consume folder drop.
- Web UI (Svelte) skeleton: Dashboard, Scan form (single target), Print upload, Targets list, History list.
- Systemd service files for API and frontend; README for reverse proxy with Caddy.

### v0.3
- Full scan profiles (150/300/600 DPI; color/gray; A4/Letter; PDF/JPEG).
- Target connectivity tests; SFTP optional; SMTP email sending.
- Jobs/history persistence with status transitions; WebSocket job updates.
- IP allowlist enforcement; password hashing; encrypted credential fields.
- Paperless HTTP uploader; retry queue for failed target uploads.

### v0.5
- Robust discovery (Avahi/mDNS for AirScan/eSCL); device capability caching.
- UI improvements: profile selection, per-target config forms, progress indicators.
- Configurable default printer/options; CUPS queue monitoring; cancel job API.
- Installer scripts: Docker Compose stack (API, frontend, CUPS, Avahi); data volume layout.
- Metrics/health endpoints; structured JSON logging; log rotation guidance.

### v1.0
- Hardened security: session/JWT rotation, CSRF protection, rate limiting on auth.
- Full target matrix (Local, SMB, SFTP, Email, Paperless folder + HTTP, Webhook) with retries and exponential backoff.
- UI polish and accessibility; downloadable scan links; history filters.
- Backup/restore tooling for SQLite + YAML; migration helpers.
- Optional OCR sidecar integration and API exposure (if available).

## Technology Justification
- **FastAPI (Python 3):** async-friendly, strong typing via Pydantic, lightweight for Pi hardware.
- **Svelte Frontend:** minimal bundle size, fast load on low-power devices, easy component model.
- **SQLite + YAML:** SQLite for atomic writes and queries; YAML for bootstrap and human-editable defaults. Encryption for secrets.
- **CUPS Integration:** Native on Raspberry Pi OS, provides IPP/AirPrint exposure.
- **Avahi/mDNS:** Needed for AirPrint/AirScan discovery.

## Phased Development Steps
1. **Bootstrap repo**: scaffold backend folders, create Svelte starter, add pre-commit configs, Dockerfile/compose skeleton.
2. **Config + Auth foundation**: setup SQLite models, migration tool (Alembic), auth endpoints, secure password hashing, secret key loader.
3. **Printing module**: CUPS client wrapper, printer listing, print submission, test page, queues API.
4. **Scanning module**: device discovery abstraction (SANE/eSCL), scan execution worker, file conversion, filename templates.
5. **Targets module**: local + SMB + webhook first; add email, Paperless, SFTP with connectivity checks.
6. **Jobs/history**: persistent job tracking, WebSocket notifications, retry logic service.
7. **Frontend**: dashboard widgets, scan/print flows, target management forms, history views, auth UI.
8. **Security & deployment**: IP allowlist middleware, TLS proxy guidance, systemd units, Docker Compose, Avahi/CUPS integration docs.
9. **Hardening & tests**: unit/integration tests with mock devices, linting, observability hooks, backup/restore scripts.
