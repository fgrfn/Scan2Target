# RaspScan Web UI (Svelte)

This directory will host the SvelteKit frontend for RaspScan.

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
