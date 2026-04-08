"""Initial schema.

Revision ID: 0001
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email         TEXT,
            is_active     INTEGER NOT NULL DEFAULT 1,
            is_admin      INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
            last_login    TEXT
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token      TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at TEXT NOT NULL,
            revoked    INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id              TEXT PRIMARY KEY,
            device_type     TEXT NOT NULL DEFAULT 'scanner',
            name            TEXT NOT NULL,
            uri             TEXT NOT NULL UNIQUE,
            make            TEXT,
            model           TEXT,
            connection_type TEXT,
            description     TEXT,
            is_active       INTEGER NOT NULL DEFAULT 1,
            is_favorite     INTEGER NOT NULL DEFAULT 0,
            last_seen       TEXT,
            created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
            updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS targets (
            id          TEXT PRIMARY KEY,
            type        TEXT NOT NULL,
            name        TEXT NOT NULL,
            config      TEXT NOT NULL DEFAULT '{}',
            enabled     INTEGER NOT NULL DEFAULT 1,
            description TEXT,
            is_favorite INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
            updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS scan_profiles (
            id         TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            dpi        INTEGER NOT NULL,
            color_mode TEXT NOT NULL,
            paper_size TEXT NOT NULL DEFAULT 'A4',
            format     TEXT NOT NULL,
            source     TEXT NOT NULL DEFAULT 'Flatbed',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id         TEXT PRIMARY KEY,
            job_type   TEXT NOT NULL DEFAULT 'scan',
            device_id  TEXT,
            target_id  TEXT,
            status     TEXT NOT NULL DEFAULT 'queued',
            file_path  TEXT,
            message    TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now'))
        )
    """)

    # Indexes
    for stmt in [
        "CREATE INDEX IF NOT EXISTS idx_jobs_status    ON jobs(status)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_created   ON jobs(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_user  ON sessions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_exp   ON sessions(expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_devices_type   ON devices(device_type)",
        "CREATE INDEX IF NOT EXISTS idx_devices_active ON devices(is_active)",
    ]:
        op.execute(stmt)

    # Default scan profiles
    op.execute("""
        INSERT OR IGNORE INTO scan_profiles (id, name, dpi, color_mode, format, source) VALUES
        ('doc_200_gray_pdf',  'Document 200 DPI (Gray)',  200, 'Gray',  'pdf',  'Flatbed'),
        ('doc_200_gray_adf',  'Document 200 DPI (ADF)',   200, 'Gray',  'pdf',  'ADF'),
        ('color_300_pdf',     'Color 300 DPI',            300, 'Color', 'pdf',  'Flatbed'),
        ('gray_150_pdf',      'Grayscale 150 DPI',        150, 'Gray',  'pdf',  'Flatbed'),
        ('photo_600_jpeg',    'Photo 600 DPI',            600, 'Color', 'jpeg', 'Flatbed')
    """)

    # Default app settings
    op.execute("""
        INSERT OR IGNORE INTO app_settings (key, value) VALUES
        ('require_auth',            'false'),
        ('log_level',               '"INFO"'),
        ('health_check_interval',   '60'),
        ('scanner_check_interval',  '30'),
        ('command_timeout',         '15'),
        ('cors_origins',            '["*"]')
    """)


def downgrade() -> None:
    for tbl in ["app_settings", "jobs", "scan_profiles", "targets", "devices", "sessions", "users"]:
        op.execute(f"DROP TABLE IF EXISTS {tbl}")
