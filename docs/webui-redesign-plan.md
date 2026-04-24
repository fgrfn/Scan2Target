# WebUI Redesign Plan (2026)

## 1) Ist-Analyse

### Technologie-Stack
- Frontend: Svelte 4 + Vite 5 (`app/web`).
- Styling: globales CSS + viele Inline-Styles in `App.svelte`.
- Backend: FastAPI mit Routern unter `/api/v1/*`.
- Realtime: WebSocket über `/api/v1/ws`, zusätzlich Polling als Fallback.

### Aktueller Frontend-Aufbau
- Haupt-UI: `app/web/src/App.svelte` (monolithische Komponente).
- Mobile Quick-UI: `app/web/src/Mobile.svelte` (separate Entry-Page `/mobile`).
- Basiskomponenten: `NavBar.svelte`, `SectionCard.svelte`, `StatGrid.svelte`.

### Relevante API-Endpunkte (Frontend-Nutzung)
- Version: `GET /api/v1/version`
- Scanner/Geräte: `GET /api/v1/devices`, `GET /api/v1/devices/discover`, `POST /api/v1/devices/add`, `DELETE /api/v1/devices/{id}`
- Scans: `GET /api/v1/scan/profiles`, `POST /api/v1/scan/start`, `POST /api/v1/scan/preview`, `POST /api/v1/scan/batch`, `POST /api/v1/scan/jobs/{id}/cancel`
- Targets: `GET /api/v1/targets`, `POST /api/v1/targets`, `PUT /api/v1/targets/{id}`, `DELETE /api/v1/targets/{id}`, `POST /api/v1/targets/{id}/test`
- Historie/Status: `GET /api/v1/history`, `DELETE /api/v1/history`, `DELETE /api/v1/history/{id}`, `POST /api/v1/history/{id}/retry-upload`
- Statistik: `/api/v1/stats/*`
- Realtime: `ws://.../api/v1/ws`

### Hauptprobleme
1. **Wartbarkeit:** `App.svelte` enthält State, API-Aufrufe, Business-Logik und große Template-Blöcke.
2. **UX-Konsistenz:** viele Block-`alert()`-Meldungen statt einheitlicher UI-Feedback-Muster.
3. **Layout-Konsistenz:** viele Inline-Styles erschweren Reuse und visuelle Einheitlichkeit.
4. **Responsive Tiefe:** einige große Tabellen/Formen sind auf kleinen Breakpoints nur begrenzt optimiert.

## 2) Zielbild

- Modernes, klares Dashboard-Design (Dark-first).
- Einheitliche Karten, Typografie, Formulare, Buttons, Badges und Zustandsfarben.
- Verbesserte visuelle Hierarchie und Lesbarkeit.
- Bestehende API-Anbindung bleibt unverändert.
- Keine Feature-Regression (Scan, Batch, Targets, History, Stats, WebSocket).

## 3) Umsetzungsplan

### Phase A – Design-Fundament
- Überarbeitung globaler Tokens (Farben, Abstände, Radius, Schatten, Fokus-Ringe).
- Vereinheitlichung der Top-Navigation und Card-Komponenten.
- Bessere responsive Regeln für <= 1100px, <= 760px.

### Phase B – UI-Konsolidierung
- Reduktion von Inline-Styling zugunsten zentraler Klassen.
- Bessere Darstellungsregeln für Listen, Panels, Tabellen und Formularfelder.
- Einheitliches visuelles Verhalten für Hover/Focus/Disabled.

### Phase C – Feature-Sicherheit
- Bestehende API- und WebSocket-Flows unverändert beibehalten.
- Build prüfen (`npm run build`) und visuelle Regression minimal halten.

## 4) Geplante Dateianpassungen
- `app/web/src/app.css` (komplettes visuelles Redesign-Fundament)
- `app/web/src/components/NavBar.svelte` (modernisierte Header-Navigation)
- `app/web/src/components/SectionCard.svelte` (saubere Card-Header-Struktur)
- `app/web/src/components/StatGrid.svelte` (verbesserte KPI-Karten)

## 5) Nicht-Ziele in diesem Schritt
- Keine API-Änderungen im Backend.
- Keine Entfernung bestehender Features.
- Kein schweres neues UI-Framework.
