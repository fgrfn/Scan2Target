# RaspScan Web UI (Svelte + Vite)

A lightweight, modern single-page UI built with Svelte and Vite. The design uses a dark, glassy shell that highlights scan/print status, targets, and job history. All interactive controls are stubbed and should be wired to the FastAPI backend endpoints.

## Getting Started

```bash
cd app/web
npm install
npm run dev   # defaults to http://localhost:5173
npm run build # emits production assets to dist/
```

## Key Features in the Prototype
- Dashboard hero with live status tiles and quick calls to action
- Scan panel: list discovered scanners, quick profiles, and a launch form for server-side scans
- Print panel: printer list and an upload + options form
- Targets: curated SMB/SFTP/Email/Paperless/Webhook destinations with an add form
- History: unified scan/print table with status badges

## Hooking Up to the Backend
- Replace the stubbed alerts and forms with calls to `/api/scan/start`, `/api/printers`, `/api/print`, and `/api/targets`.
- Inject real data by fetching `/api/scan/devices`, `/api/printers`, and `/api/history` on load.
- When containerizing, serve the built `dist/` directory with Caddy/nginx or behind the FastAPI static files middleware.

## Styling Notes
- Uses the Inter variable font (`@fontsource/inter`) and custom gradients; no heavyweight UI kits are required.
- The layout is responsive down to tablet widths; cards collapse into a single column for narrow viewports.

## Suggested Next Steps
- Add authentication-aware layouts once the auth API is available.
- Swap stubbed selects with data-bound dropdowns and add progress indicators for active jobs.
- Extract reusable widgets (tables, chips, cards) into `src/components` as the UI grows.
