# Neue Features - Quick Start Guide

## 🎉 Was ist neu?

RaspScan hat jetzt **vollständige Persistence, Background Processing und Authentication**!

## 1️⃣ Persistence (SQLite)

### Was bedeutet das?
- **Jobs überleben Neustarts** - Scan/Print History bleibt erhalten
- **Targets werden gespeichert** - SMB/SFTP/Email Konfigurationen persistent
- **User Accounts** - Login-Daten sicher in Datenbank

### Verwendung
Nichts zu tun! Die Datenbank wird automatisch erstellt beim ersten Start:

```bash
python -m uvicorn app.main:app --reload
```

**Ergebnis:** `raspscan.db` wird im aktuellen Verzeichnis erstellt.

### Backup
```bash
# Einfach die Datei kopieren
cp raspscan.db raspscan_backup.db
```

---

## 2️⃣ Background Processing

### Was bedeutet das?
- **Scans blockieren die API nicht mehr** - Requests werden sofort zurückgegeben
- **Async Execution** - Scans laufen im Hintergrund
- **Job Status Tracking** - Status wird in DB aktualisiert

### Wie es funktioniert
```python
# Scan starten
POST /api/v1/scan/start
{
  "device_id": "escl:...",
  "profile_id": "color_300_pdf",
  "target_id": "my_nas"
}

# Sofortige Antwort mit job_id
{
  "job_id": "abc-123",
  "status": "queued"
}

# Status abfragen
GET /api/v1/scan/jobs/abc-123
{
  "id": "abc-123",
  "status": "running",  # oder "completed" / "failed"
  "file_path": "/tmp/scan_abc-123.pdf"
}
```

### Technical Details
- Nutzt `asyncio` für non-blocking execution
- Für Production mit vielen Users: Celery/RQ empfohlen
- Single-process, aber nicht blockierend

---

## 3️⃣ Authentication (JWT)

### Default Admin User
Beim ersten Start wird automatisch erstellt:
- **Username:** `admin`
- **Password:** `admin`

**⚠️ WICHTIG: Passwort sofort ändern!**

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "admin",
    "is_admin": true
  }
}
```

### Token verwenden
```bash
curl -H "Authorization: Bearer eyJhbGc..." \
  http://localhost:8000/api/v1/scan/start
```

### Neue User registrieren
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "scanner_user",
    "password": "secure_password",
    "email": "user@example.com"
  }'
```

### Logout (Token widerrufen)
```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🔐 Auth aktivieren (Optional)

Standardmäßig ist Auth **optional** - API funktioniert ohne Token.

### Auth für alle Routes erzwingen:

**Option 1: .env Datei**
```bash
# Erstelle .env im Projekt-Root
cat > .env << EOF
RASPSCAN_REQUIRE_AUTH=true
RASPSCAN_JWT_SECRET=your-super-secret-key-change-this
RASPSCAN_JWT_EXPIRATION=3600
EOF
```

**Option 2: Environment Variables**
```bash
export RASPSCAN_REQUIRE_AUTH=true
export RASPSCAN_JWT_SECRET=your-secret-key
python -m uvicorn app.main:app
```

---

## 🛡️ Routes schützen

### Beispiel: Scan nur für authentifizierte User

```python
# In app/api/scan.py
from app.core.auth.dependencies import get_current_user
from app.core.auth.models import User

@router.post("/start")
async def start_scan(
    payload: ScanRequest,
    current_user: User = Depends(get_current_user)  # Hinzufügen
):
    # Jetzt nur mit gültigem Token erreichbar
    ...
```

### Beispiel: Admin-only Route

```python
from app.core.auth.dependencies import get_current_admin_user

@router.post("/printers/add")
async def add_printer(
    printer: AddPrinterRequest,
    admin: User = Depends(get_current_admin_user)  # Nur Admins
):
    ...
```

---

## 📊 Job History & Status

### Alle Jobs anzeigen
```bash
curl http://localhost:8000/api/v1/history
```

**Response:**
```json
[
  {
    "id": "job-123",
    "job_type": "scan",
    "status": "completed",
    "device_id": "escl:HP_Envy",
    "target_id": "nas",
    "file_path": "/tmp/scan_123.pdf",
    "created_at": "2025-11-30T10:00:00",
    "updated_at": "2025-11-30T10:02:00"
  }
]
```

### Job Status abfragen
```bash
curl http://localhost:8000/api/v1/scan/jobs/job-123
```

---

## 🎯 Production Checklist

Bevor du RaspScan in Production verwendest:

- [ ] **Default Admin Passwort ändern!**
- [ ] **Auth aktivieren:** `RASPSCAN_REQUIRE_AUTH=true`
- [ ] **Eigenen JWT Secret setzen:** `RASPSCAN_JWT_SECRET=...`
- [ ] **HTTPS aktivieren** (via Caddy/nginx Reverse Proxy)
- [ ] **CORS anpassen** (nicht `*` in Production)
- [ ] **Backup-Strategy** für `raspscan.db`
- [ ] **Temp-File Cleanup** einrichten (cronjob)
- [ ] **Logging** konfigurieren
- [ ] **Rate Limiting** hinzufügen

---

## 🐛 Troubleshooting

### "Unable to open database file"
```bash
# Stelle sicher, dass Schreibrechte existieren
chmod 755 .
touch raspscan.db
chmod 644 raspscan.db
```

### "Token expired"
Tokens sind standardmäßig 1 Stunde gültig. Neu einloggen oder Expiration erhöhen:
```bash
export RASPSCAN_JWT_EXPIRATION=86400  # 24 Stunden
```

### "Admin password not working"
Password wurde geändert oder DB gelöscht:
```bash
# DB neu initialisieren
rm raspscan.db
python -m uvicorn app.main:app  # Erstellt neue DB mit admin/admin
```

### Background Jobs hängen
```bash
# Job Status prüfen
curl http://localhost:8000/api/v1/history

# Logs checken
uvicorn app.main:app --log-level debug
```

---

## 📚 API Dokumentation

**Swagger UI:** http://localhost:8000/docs

**ReDoc:** http://localhost:8000/redoc

Alle neuen Endpoints sind dort dokumentiert:
- `/api/v1/auth/login` - Login
- `/api/v1/auth/register` - Registrierung
- `/api/v1/auth/logout` - Logout
- `/api/v1/auth/me` - Aktuelle User Info

---

## 🚀 Next Steps

1. **Web UI Update:** Login-Formular hinzufügen
2. **WebSockets:** Real-time Job Updates
3. **Multi-page Scanning:** ADF Support
4. **OCR Integration:** Searchable PDFs
5. **Email Notifications:** Bei Job-Completion

Viel Erfolg! 🎉
