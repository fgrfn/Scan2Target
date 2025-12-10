# SMB-Integration - Verbesserte Robustheit

## Änderungen

### 1. **Robustes Connection-String-Parsing**

Die neue `_parse_smb_connection()` Funktion unterstützt jetzt **alle gängigen SMB-Formate**:

#### Unterstützte Formate:
```
✅ //server/share              → Standard Unix-Format
✅ \\server\share              → Windows-Format  
✅ server/share                → Vereinfachtes Format
✅ 192.168.1.100/documents     → IP + Share
✅ nas.local/backup            → Hostname + Share
✅ //server/share/folder/path  → Mit Unterordnern
✅ \\server\share\path         → Windows mit Pfad
```

#### Beispiele:
```python
"192.168.1.100/documents"       → Server: 192.168.1.100, Share: documents, Path: (root)
"//nas.local/scans/inbox"       → Server: nas.local, Share: scans, Path: inbox
"\\\\nas\\backup\\old\\scans"   → Server: nas, Share: backup, Path: old/scans
```

### 2. **Verbesserte Fehlerbehandlung**

#### Spezifische Fehlermeldungen:
- ❌ **NT_STATUS_LOGON_FAILURE** → "Login failed - check username and password"
- ❌ **NT_STATUS_BAD_NETWORK_NAME** → "Share 'XXX' not found on server"
- ❌ **NT_STATUS_ACCESS_DENIED** → "Access denied - check permissions"
- ❌ **NT_STATUS_HOST_UNREACHABLE** → "Server not reachable - check network"
- ❌ **NT_STATUS_OBJECT_NAME_NOT_FOUND** → "Path not found in share"

### 3. **Automatische Verzeichniserstellung**

Die Upload-Funktion versucht jetzt automatisch, Unterverzeichnisse zu erstellen:

```python
# Wenn upload_path = "scans/inbox" und Base-Path = "documents"
# Wird versucht: mkdir "documents/scans/inbox"
# Dann: put file.pdf "documents/scans/inbox/file.pdf"
```

### 4. **Erweiterte Validierung**

Die Verbindungstests sind jetzt umfassender:
- ✅ Testet tatsächlichen Share-Zugriff (nicht nur Server-Ping)
- ✅ Prüft Schreibrechte durch Upload + Delete eines Test-Files
- ✅ Validiert verschachtelte Pfade

### 5. **Debugging-Output**

Alle SMB-Operationen haben jetzt ausführliche Logs:
```
[SMB] Delivering file: scan_001.pdf
[SMB] Connection: 192.168.1.100/documents/inbox
[SMB] Parsed - Server: 192.168.1.100, Share: documents, Path: inbox
[SMB] Share path: //192.168.1.100/documents
[SMB] Target file path: inbox/scan_001.pdf
[SMB] ✓ Upload successful
```

## Konfiguration im Frontend

### Einfache Eingabe:

**Connection-Feld** akzeptiert jetzt flexibel:
```
192.168.1.100/documents
//nas.local/scans
\\server\share\folder
```

**Upload Path** (optional):
- Unterverzeichnis innerhalb des Shares
- Wird mit Base-Path aus Connection kombiniert
- Beispiel: Connection `//nas/backup`, Upload Path `scans/inbox` → Final: `//nas/backup/scans/inbox`

## Testing

### Test-Skript verwenden:

```bash
# Parsing-Tests (ohne echte Verbindung)
python3 test_smb.py

# Mit echtem SMB-Server testen
python3 test_smb.py
# Dann "y" eingeben für Connection-Test
```

### Manuelle Tests:

```python
from app.core.targets.manager import TargetManager

# Parse-Test
manager = TargetManager()
server, share, path = manager._parse_smb_connection("192.168.1.100/docs/scans")
print(f"Server: {server}, Share: {share}, Path: {path}")
# Output: Server: 192.168.1.100, Share: docs, Path: scans
```

## Häufige Probleme

### "Share not found"
→ Prüfen: Ist der Share-Name korrekt? Mit `smbclient -L //server -U user` alle Shares auflisten

### "Access denied"
→ Prüfen: Hat der Benutzer Schreibrechte auf dem Share?

### "Server not reachable"
→ Prüfen: 
  - Ist die IP/Hostname korrekt?
  - Firewall blockiert Port 445?
  - SMB-Service läuft auf dem Server?

### "Path not found"
→ Prüfen: Existiert der Unterordner auf dem Share? Ggf. manuell anlegen.

## Kompatibilität

- ✅ Samba (Linux/Unix)
- ✅ Windows File Sharing
- ✅ NAS-Geräte (Synology, QNAP, etc.)
- ✅ SMB v1, v2, v3

## Dependencies

Benötigt `smbclient`:
```bash
sudo apt install smbclient
```
