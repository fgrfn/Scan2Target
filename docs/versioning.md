# Versionierung und Releases

## Übersicht

Scan2Target verwendet [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking Changes (Inkompatible API-Änderungen)
- **MINOR**: Neue Features (rückwärtskompatibel)
- **PATCH**: Bugfixes (rückwärtskompatibel)

Die aktuelle Version wird in der Datei `VERSION` im Root-Verzeichnis gespeichert.

## Automatische Releases

Bei jedem Push auf den `main`-Branch wird automatisch:

1. Die Versionsnummer erhöht (basierend auf Commit-Messages)
2. Ein Git-Tag erstellt
3. Ein GitHub Release veröffentlicht
4. Docker Images mit der neuen Version gebaut

### Version Bump Logik

Die Version wird automatisch basierend auf Commit-Messages erhöht:

- **MAJOR**: Commits mit `break:`, `breaking:` oder `major:` Prefix
- **MINOR**: Commits mit `feat:` oder `feature:` Prefix  
- **PATCH**: Alle anderen Commits

**Beispiele:**
```bash
git commit -m "feat: neue Scanner-Unterstützung"  # → Minor bump (z.B. 1.0.0 → 1.1.0)
git commit -m "fix: PDF-Konvertierung korrigiert"  # → Patch bump (z.B. 1.1.0 → 1.1.1)
git commit -m "break: API-Endpoints umbenannt"     # → Major bump (z.B. 1.1.1 → 2.0.0)
```

### Manuelles Release

Du kannst auch manuell ein Release mit spezifischem Bump-Type erstellen:

1. Gehe zu [Actions](https://github.com/fgrfn/Scan2Target/actions/workflows/release.yml)
2. Klicke auf "Run workflow"
3. Wähle den Bump-Type: `patch`, `minor` oder `major`
4. Klicke auf "Run workflow"

## Docker Images

Docker Images werden automatisch mit folgenden Tags veröffentlicht:

- `ghcr.io/fgrfn/scan2target:latest` - Neueste stabile Version
- `ghcr.io/fgrfn/scan2target:1.0.0` - Spezifische Version
- `ghcr.io/fgrfn/scan2target:1.0` - Major.Minor Version
- `ghcr.io/fgrfn/scan2target:1` - Major Version
- `ghcr.io/fgrfn/scan2target:main` - Main Branch (Dev)

## Version in der Anwendung

Die Version ist in der FastAPI-Anwendung verfügbar:

- API-Dokumentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health-Endpoint: `GET /health` (enthält Version in Zukunft)
- OpenAPI-Schema: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

## Workflow-Details

### Release Workflow (`.github/workflows/release.yml`)

- **Trigger**: Push auf `main` (außer VERSION-Datei und Workflow-Änderungen)
- **Aktionen**:
  1. Liest aktuelle Version
  2. Bestimmt Bump-Type aus Commits
  3. Erhöht Version
  4. Committed neue VERSION-Datei
  5. Erstellt Git-Tag
  6. Generiert Changelog
  7. Erstellt GitHub Release

### Docker Build Workflow (`.github/workflows/docker-build.yml`)

- **Trigger**: Push auf Branches, Tags (`v*.*.*`)
- **Aktionen**:
  1. Baut Docker Image
  2. Taggt mit Version und Branch
  3. Pushed zu GitHub Container Registry

## Skip CI

Um ein Commit ohne Release zu machen:

```bash
git commit -m "docs: README aktualisiert [skip ci]"
```

Die Release-Workflow ignoriert automatisch:
- Änderungen an `VERSION`
- Änderungen an `.github/workflows/**`
- Commits mit `[skip ci]` im Message
