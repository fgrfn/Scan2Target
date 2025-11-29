# RaspScan Architecture & Design

## Overview
RaspScan is a Raspberry Pi-hosted scan and print server that centralizes scanner control and print spooling for mixed USB and network devices. The system drives scanners that lack physical scan buttons (e.g., HP Envy 6400) by initiating scans from a web UI or REST API, then routes output to local or network destinations.

## Goals and Constraints
- **Platform:** Raspberry Pi 4/5 on Raspberry Pi OS; efficient idle footprint.
- **Backends:** eSCL/AirScan and SANE for scanning; CUPS/IPP for printing.
- **Targets:** Local filesystem, SMB/CIFS, optional SFTP, Paperless-ngx (consume folder or HTTP), SMTP email, webhook callbacks. (No Nextcloud/WebDAV targets.)
- **Security:** Authenticated access, optional IP allowlist, reverse-proxy friendly HTTPS.
- **Extensibility:** Pluggable targets, profiles, and scanners; optional OCR as a future module.

## High-Level Architecture
```
+--------------------------------------------------------------+
|                          Web UI (Svelte)                    |
+--------------------------------------------------------------+
         | REST/HTTPS (FastAPI)            | WebSocket events
+----------------------+        +---------------------------------+
|     API Routers      |        |          Auth layer             |
+----------------------+        +---------------------------------+
         |                            |
         |                            v
         |                 +-------------------+
         |                 | Config & Secrets  |
         |                 |  (SQLite + YAML)  |
         |                 +-------------------+
         v                            |
+--------------------------------------------------------------+
|                      Application Core                        |
|  Scanning  | Printing | Targets | Jobs/History | Services     |
|  (SANE/    | (CUPS)   | (SMB,   | (SQLite)     | Schedulers   |
|  eSCL)     |          | SFTP,   |              | Event bus)   |
|            |          | Email,  |              |              |
|            |          | Paperless, Webhook)                |
+--------------------------------------------------------------+
         |
         v
   Device/Backend layer (SANE/eSCL/AirScan, CUPS/IPP)
```

### Module Responsibilities
- **API**: Versioned REST endpoints, authentication middleware, request validation, event streaming for job updates.
- **Core/Scanning**: Discover scanners (mDNS/Avahi and SANE backends), normalize capabilities, start scans, manage temporary files, and hand off to Targets.
- **Core/Printing**: Enumerate printers via CUPS, submit jobs, query queues, print test pages.
- **Core/Targets**: Upload/route scan outputs to configured destinations; provide connectivity tests.
- **Core/Config**: Manage settings, credentials, profiles; encryption-at-rest for secrets; pluggable storage backends (SQLite primary, YAML for bootstrapping and offline edits).
- **Core/Jobs**: Track scan and print jobs, persist status, and expose history.
- **Services**: Background schedulers (e.g., retry failed targets), watcher for Paperless consume folder handoff, IP allowlist enforcement helper.
- **Web UI**: Dashboard, scan/print pages, targets management, history, and configuration.

## Data & Control Flows
### Scan Workflow
1. **User Action**: User selects scanner, profile (DPI, color, size, format), and target; optional filename prefix.
2. **API**: `POST /api/v1/scan/start` validates payload and enqueues a scan job.
3. **Scanner Selection**: Core/Scanning resolves the device via eSCL/AirScan or SANE backend based on discovered inventory.
4. **Execution**: Start scan with requested parameters; stream to temporary file.
5. **Post-processing**: Convert to PDF/JPEG as needed; apply filename template `{prefix}{profile}_{date}_{time}.{ext}`.
6. **Target Delivery**: Core/Targets writes or uploads the file to the selected destination; optional webhook notification.
7. **Job Tracking**: Core/Jobs records status transitions (queued → running → delivered/failed) and stores metadata (scanner, profile, target, file path/URL).
8. **UI Feedback**: Clients poll `GET /api/v1/scan/jobs/{id}` or receive WebSocket events for progress.

### Print Workflow
1. **User Action**: Upload PDF/JPEG/PNG, choose printer and options.
2. **API**: `POST /api/v1/print` stores the file (temp) and submits to CUPS via Core/Printing.
3. **CUPS Handling**: Job ID returned; status polled via `GET /api/v1/printers/{id}/jobs`.
4. **Job Tracking**: Core/Jobs records print job metadata and status.

### Target Handling
- **Local folder**: Ensure directory path exists (`/data/scans/YYYY/MM/DD`), write file, set permissions.
- **SMB/CIFS**: Mount-on-demand using `smbclient` or `pysmb`; unmount/cleanup after upload.
- **SFTP (optional)**: Use `paramiko` for uploads.
- **Email**: Send via SMTP with TLS; attach file and include metadata.
- **Paperless-ngx**: Write to consume folder OR POST to HTTP API with token.
- **Webhook**: POST JSON metadata plus signed URL/location of the file.

## API Overview (v1)
- `GET /api/v1/scan/devices` — list discovered scanners and capabilities.
- `GET /api/v1/scan/profiles` — list predefined scan profiles.
- `POST /api/v1/scan/start` — start a scan with device/profile/target selection.
- `GET /api/v1/scan/jobs` — list scan jobs.
- `GET /api/v1/scan/jobs/{id}` — job status & result link.
- `GET /api/v1/printers` — list printers & status.
- `GET /api/v1/printers/{id}/jobs` — list jobs for a printer.
- `POST /api/v1/print` — upload + submit print job.
- `POST /api/v1/printers/{id}/test` — print a test page.
- `GET /api/v1/targets` — list targets.
- `POST /api/v1/targets` — create target (SMB/SFTP/Email/Paperless/Webhook/Local folder).
- `PUT /api/v1/targets/{id}` — update target settings.
- `DELETE /api/v1/targets/{id}` — delete target.
- `POST /api/v1/targets/{id}/test` — connectivity test.
- `GET /api/v1/history` — unified scan/print history.
- `POST /api/v1/auth/login` — obtain session/token.
- `POST /api/v1/auth/logout` — revoke session.

Example payloads:
```json
POST /api/v1/scan/start
{
  "device_id": "escl:HP_Envy_6400",
  "profile_id": "scan_a4_color_300",
  "target_id": "smb:nas_scans",
  "filename_prefix": "invoices_"
}
```
```json
POST /api/v1/print
{
  "printer_id": "ipp://printer.local/ipp/print",
  "options": {"sides": "two-sided-long-edge"},
  "file_id": "upload-temp-uuid"
}
```

## Configuration Model
- **Storage Choice:** SQLite for structured configuration, users, jobs, and targets; YAML for bootstrap defaults and easy manual edits. SQLite chosen for atomic updates, concurrent access, and simple backups on Pi. Secrets stored encrypted (e.g., Fernet key in `/etc/raspscan/secret.key`).
- **Entities:**
  - `User`: username, password hash, roles, allowed IP subnets.
  - `Scanner`: id, type (eSCL/SANE), capabilities, last_seen.
  - `Printer`: id, uri, name, status, defaults.
  - `ScanProfile`: id, dpi, color_mode, paper_size, format.
  - `Target`: id, type (local, smb, sftp, email, paperless_folder, paperless_api, webhook), config blob (encrypted fields for credentials), enabled flag.
  - `Job`: id, type (scan/print), device_id, target_id (scan), printer_id (print), file_path/url, status, timestamps, logs.

## Security Model
- **Auth:** Session or JWT tokens; password hashing via `argon2` or `bcrypt`; HTTPS recommended behind Caddy/nginx; optional IP allowlist enforced per request.
- **Secrets:** Encrypted credential fields; filesystem isolation (`/etc/raspscan/` for secrets, `/data/raspscan` for runtime data).
- **Network Exposure:** Run FastAPI on localhost:8000 with reverse proxy terminating TLS; disable anonymous access; CSRF protection for web UI.

## Deployment
- **Native:** Systemd units to start FastAPI (uvicorn) and optional workers; Avahi for mDNS/AirPrint; CUPS installed with IPP Everywhere.
- **Container:** Docker Compose defining API, frontend, CUPS, Avahi reflector, and a data volume for `/data/raspscan`.

## Non-Functional Considerations
- **Performance:** Use asynchronous I/O for network transfers; scanning/printing operations offloaded to worker threads to avoid blocking event loop.
- **Logging:** Structured logging (JSON) with per-module loggers; include job_id correlation; log target upload failures clearly.
- **Observability:** Health endpoint, metrics hook (e.g., Prometheus exporter) optional.

## Future Extensions
- OCR sidecar service; cloud storage targets; hardware button support via GPIO; multi-tenant user roles.
