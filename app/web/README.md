# Scan2Target Web UI (Svelte + Vite)

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

# Scan2Target Web UI (Svelte)

This directory hosts the Svelte + Vite frontend for Scan2Target.

## Pages to Implement
- **Dashboard:** overall status of scanners/printers and recent scan jobs.
- **Scan:** scanner selection, profile parameters, target choice, progress/result link.
- **Print:** file upload, printer selection, job status.
- **Targets/Settings:** manage SMB/SFTP/Email/Paperless/Webhook destinations, credential tests.
- **History:** unified scan/print history with download links for scans.

## Suggested Structure
```
src/
  routes/
    +page.svelte        # Dashboard
    scan/+page.svelte
    print/+page.svelte
    targets/+page.svelte
    history/+page.svelte
  lib/components/
    Navbar.svelte
    StatusCards.svelte
    JobTable.svelte
  lib/api/client.ts     # typed API client for FastAPI
```

Use a lightweight UI kit (e.g., Skeleton/Tailwind) to keep bundles small for Raspberry Pi clients.
