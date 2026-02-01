"""SQLite database setup and session management."""
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator


class Database:
    """SQLite database connection manager."""
    
    def __init__(self, db_path: str = "scan2target.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with automatic commit/rollback."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_schema(self):
        """Initialize database schema if not exists."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    device_id TEXT,
                    target_id TEXT,
                    printer_id TEXT,
                    status TEXT NOT NULL,
                    file_path TEXT,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Targets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS targets (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    config TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    description TEXT,
                    is_favorite INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    is_active INTEGER DEFAULT 1,
                    is_admin INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            
            # Sessions table (for token blacklist/revocation)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    revoked INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Scan profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_profiles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    dpi INTEGER NOT NULL,
                    color_mode TEXT NOT NULL,
                    paper_size TEXT NOT NULL,
                    format TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Devices table (unified printers and scanners)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    device_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    uri TEXT NOT NULL UNIQUE,
                    make TEXT,
                    model TEXT,
                    connection_type TEXT,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    is_favorite INTEGER DEFAULT 0,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_type_created ON jobs(job_type, created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_type ON devices(device_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_active ON devices(is_active)")
            
            conn.commit()


# Global database instance
_db_instance = None


def get_db() -> Database:
    """Get or create the global database instance."""
    global _db_instance
    if _db_instance is None:
        # Use environment variable or default path
        db_path = os.getenv("SCAN2TARGET_DATABASE_PATH") or os.getenv("SCAN2TARGET_DB_PATH", "scan2target.db")
        _db_instance = Database(db_path)
    return _db_instance
