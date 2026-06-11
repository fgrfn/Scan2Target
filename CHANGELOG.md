# Changelog

## 4.0.0 (2026-06-11)

Complete redesign release: unified responsive Web UI, repaired Home Assistant
integration, DB-backed scan profiles, live job updates over WebSocket, and a
set of long-standing bug fixes. All existing features are preserved.

### Fixed

- **Home Assistant integration works again.**
  `GET /api/v1/homeassistant/profiles` previously advertised profile IDs
  (`flatbed_*` / `adf_*`) that the scan engine never knew, so every Home
  Assistant scan silently fell back to the default profile. The endpoint now
  returns the real profile IDs, and the `/scan` endpoint accepts short
  aliases (`document`, `adf`, `color`, `photo`, `fast`) as well as all legacy
  pre-4.0 IDs — existing Home Assistant configurations keep working.
- `/api/v1/homeassistant/status` now reports real `active_scans` and
  `last_scan` values (previously hardcoded placeholders).
- The `source` parameter documented for Home Assistant scans is now actually
  accepted and forwarded to the scanner.
- **Live job updates over WebSocket actually arrive.** Broadcasts from the
  scan worker thread were silently dropped (no event loop in the executor
  thread); they are now scheduled thread-safely onto the main loop. The Web
  UI uses the WebSocket for live progress and falls back to polling only
  when disconnected.
- **Temp file leak fixed:** intermediate per-page TIFF files are now always
  cleaned up after a scan, instead of accumulating in `/tmp/scan2target`.
- Scan jobs are no longer marked `completed` before delivery to the target
  has been attempted.
- The mobile UI entry point (`mobile.html`) was never included in production
  builds due to a Vite misconfiguration; the separate mobile app has been
  replaced by a single responsive UI (see below).

### Changed

- **New unified, responsive Web UI** (desktop sidebar / mobile bottom nav)
  replacing the separate desktop and mobile apps. The mobile-only features
  (quick scan, manual multi-page batch scan with per-page preview, favorite
  auto-select) are now available everywhere.
- "Active Scans" is no longer a separate page: running and queued jobs are
  shown live on the dashboard (with cancel) and indicated in the top bar.
- Complete English/German localization from a single dictionary; language
  choice is persisted.
- `SCAN2TARGET_REQUIRE_AUTH=true` is now actually enforced: all `/api/*`
  routes (except login, health, version and the separately guarded Home
  Assistant routes) require a Bearer token. Default remains `false`.
- CORS origins are configurable via `SCAN2TARGET_CORS_ORIGINS`.

### Added

- **Custom scan profiles:** profiles are stored in the database and editable
  in Settings (`/api/v1/profiles` CRUD). Built-in profiles cannot be deleted.
- **Optional Home Assistant API key:** set `SCAN2TARGET_HA_API_KEY` to require
  an `X-API-Key` header on all `/api/v1/homeassistant/*` endpoints.
- Settings page includes a Home Assistant helper that generates ready-to-copy
  `rest_command` YAML for this server.
- Login screen in the Web UI (shown automatically when the API requires
  authentication).

### Removed

- Separate mobile UI (`mobile.html`, `Mobile.svelte`) — replaced by the
  responsive app; the `/mobile` URL still serves the unified UI.
- Non-functional "Glass effects" setting and dead UI elements (unused NavBar
  component, fake ⌘K hint).

### Upgrade notes

- No action required for existing Home Assistant configurations; legacy
  profile IDs are accepted as aliases.
- Existing databases are migrated automatically (extended `scan_profiles`
  table).
