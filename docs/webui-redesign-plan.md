# WebUI Design-System (Redesign 2026)

Referenz für die Oberfläche in `app/web`. Das Dokument löst den alten
Redesign-Plan ab: die dort beschriebene monolithische `App.svelte` mit
`alert()`-Meldungen und separater `Mobile.svelte` existiert nicht mehr.

## 1. Scope

Visuelles/UX-Redesign auf der bestehenden Svelte-4-Basis. Architektur,
REST-API, WebSockets, i18n (de/en), PWA und Dark-Mode bleiben unangetastet —
kein Framework-Rebuild, keine neuen Runtime-Dependencies.

## 2. Verbindliche Design-Entscheidungen

| Achse | Entscheidung |
|---|---|
| Tiefe | Visuelles/UX-Redesign auf Svelte-4-Basis. Kein Rewrite. |
| Visuelle Sprache | **iOS-Soft** — große Radien, weiche Schatten, luftig, freundlich. |
| Referenz-Modus | **Light = Held**, Dark **gleichwertig** über *Elevation* (Flächen-Ebenen) statt Schatten. Default bleibt `theme: 'system'`. |
| Akzent/Marke | **iOS-Blau** `#007aff` (Dark `#0a84ff`). Logo, PWA `theme-color` und UI sind darauf vereinheitlicht. |
| Navigation | 5 Items: **Scan · Übersicht · Verlauf · Verwalten · Einstellungen**. `Verwalten` bleibt konsolidiert (Devices/Targets/Profiles als Tabs *innerhalb* der View). |
| Startseite | **Scan** (schnellster Weg zur Kernaktion). |
| Styling | **Vanilla CSS** mit Token-Layer. Kein Tailwind, keine Component-Lib. |
| Icons | Inline-SVG-Set in `components/ui/Icon.svelte`, bei Bedarf mit Lucide-Pfaden erweitern. Dep-frei bleiben. |
| Typo | **Inter** (via `@fontsource/inter` gebündelt). |
| Dichte | Komfortabel als Default, `compactTables` schaltet auf `[data-density="compact"]`. |
| Listen | iOS-„inset grouped" (eine gerundete Fläche mit Hairline-Trennern), nicht N schwebende Einzelkärtchen. |

**Anti-Muster (bewusst vermieden):** keine ALL-CAPS-Eyebrows, kein „→" an
Button-/Link-Text, kein Monospace für UI-Labels, nicht „ein Radius/ein
Schatten für alles". Radien sind gestaffelt (Hero 24 / Karte 20 / Control 12).

## 3. Tokens

Source of Truth ist `app/web/src/app.css`, Sektion 1. Neue Screens **nur** mit
diesen Variablen bauen, keine Hex-Werte hart reinschreiben.

**Light**
```
--bg:#eef1f6  --surface:#fff  --surface-2:#f5f7fb  --surface-3:#eef2f8
--text:#1c2530  --muted:#6b7688  --faint:#98a2b3  --line:#e4e9f1  --line-strong:#d5dce8
--accent:#007aff  --accent-strong:#0062cc  --accent-soft:#e8f1ff  --on-accent:#fff
--success:#1f9d55  --warn:#c77700  --danger:#d63a2f  --info:#2f6df0  (+ *-soft)
--r-lg:24  --r-card:20  --r-ctl:12  --r-sm:10  --r-pill:999
--sh-sm/-md/-lg (Light: echte Schatten)
```

**Dark** (`[data-theme="dark"]` + `@media(prefers-color-scheme:dark) [data-theme="system"]`)
```
--bg:#0f1420  --surface:#171d2b  --surface-2:#1f2637  --surface-3:#252d40
--accent:#0a84ff  …  --sh-sm/-md/-lg: none
```

**Dark-Shadows sind bewusst `none`.** Elevation in Dark kommt aus einer höheren
`--surface-*`-Stufe plus Border — keine Schatten faken.

## 4. Aufbau von `app.css`

20 kommentierte Sektionen: Tokens → Reset → Shell → Topbar → Buttons → Forms →
Cards → Badges → Inset-Listen → Overview (Hero/KPIs) → Scan-Flow → History →
Manage/Resource → Settings → Statistics → Dialogs → BottomNav → Motion →
Responsive → Density.

Klassennamen sind bewusst stabil gehalten; die Views erben den Look über die
gemeinsamen Klassen (`.btn.primary/.secondary/.ghost/.danger`, `.card`,
`.badge.<tone>`, `.clean-list/.list-row`, `.resource-card`, `.settings-card`).

## 5. Dichte / Compact-Modus

`settings.compactTables` (localStorage, Default `false`) setzt in `App.svelte`
`data-density="compact"` auf `.app-shell` — analog zu `data-theme`. Sektion 20
in `app.css` reduziert daraufhin Padding und Zeilenhöhe in Listen, History-,
Resource- und Settings-Karten. Der Schalter liegt in **Einstellungen →
Oberfläche**.

## 6. Leitplanken für Folgearbeit

- Tokens und bestehende Klassen wiederverwenden. Konsistenz vor Kreativität.
- Keine neuen Dependencies. Icons via `Icon.svelte` + Lucide-Pfade.
- API-, i18n- und WebSocket-Flows nicht anfassen; Feature-Parität wahren
  (Scan, Batch, Targets, History, Stats).
- Dark-Mode bei jeder neuen UI mitdenken (Elevation statt Schatten).

## 7. Verifikation

```bash
cd app/web
npm ci
npm run build      # muss durchlaufen
npm run check      # 0 errors / 0 warnings
npm run test:e2e   # Playwright-Durchlauf des Multipage-Scans
```

Regressions-Check nach Änderungen an `app.css` (jede genutzte Klasse muss
abgedeckt sein):

```bash
comm -23 \
  <(grep -rhoE 'class="[^"]*"' app/web/src --include=*.svelte | sed 's/class="//;s/"//' | tr ' ' '\n' | sed 's/{.*}//' | grep -vE '^\s*$' | sort -u) \
  <(grep -oE '\.[a-zA-Z][a-zA-Z0-9_-]+' app/web/src/app.css | sed 's/^\.//' | sort -u)
```

Erwartung: keine Treffer.

## 8. Offene Punkte

- `views/StatisticsView.svelte` ist derzeit in keiner Route eingebunden; die
  Chart-Styles (Sektion 15) sind vorhanden, die View aber nicht erreichbar.
- Für die Status `delivery_failed`, `scanning`, `processing`, `delivering` und
  `retry_scheduled` fehlen `status_*`-Keys in `lib/i18n.js`; Badges zeigen dort
  den Rohwert.
- Theme-/Sprach-Umschalter in der Topbar wäre möglich, ist aber nicht
  beschlossen — aktuell liegt beides in den Einstellungen.
