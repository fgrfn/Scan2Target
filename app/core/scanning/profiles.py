"""Scan profile storage and resolution.

Single source of truth for scan profiles. Profiles live in the
``scan_profiles`` SQLite table and are seeded with sensible defaults.
All API surfaces (Web UI, /scan/profiles, Home Assistant) read from here,
so profile IDs are guaranteed to be consistent everywhere.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from core.database import get_db

logger = logging.getLogger(__name__)


# Built-in profiles, seeded into the DB on startup. Users may edit or
# add profiles via /api/v1/profiles; built-ins are restored only if missing.
DEFAULT_PROFILES = [
    {
        'id': 'document_200_pdf',
        'name': 'Document @200 DPI (Small)',
        'dpi': 200,
        'color_mode': 'Gray',
        'paper_size': 'A4',
        'format': 'pdf',
        'quality': 80,
        'source': 'Flatbed',
        'batch_scan': False,
        'auto_detect': True,
        'description': 'Best for text documents - smallest size',
    },
    {
        'id': 'document_adf_200_pdf',
        'name': 'Multi-Page Document (ADF)',
        'dpi': 200,
        'color_mode': 'Gray',
        'paper_size': 'A4',
        'format': 'pdf',
        'quality': 80,
        'source': 'ADF',
        'batch_scan': True,
        'auto_detect': True,
        'description': 'Scan multiple pages from document feeder',
    },
    {
        'id': 'color_300_pdf',
        'name': 'Color @300 DPI (Medium)',
        'dpi': 300,
        'color_mode': 'Color',
        'paper_size': 'A4',
        'format': 'pdf',
        'quality': 85,
        'source': 'Flatbed',
        'batch_scan': False,
        'auto_detect': True,
        'description': 'Good quality for mixed content',
    },
    {
        'id': 'gray_150_pdf',
        'name': 'Grayscale @150 DPI (Fast)',
        'dpi': 150,
        'color_mode': 'Gray',
        'paper_size': 'A4',
        'format': 'pdf',
        'quality': 75,
        'source': 'Flatbed',
        'batch_scan': False,
        'auto_detect': True,
        'description': 'Quick scans, very small size',
    },
    {
        'id': 'photo_600_jpeg',
        'name': 'Photo @600 DPI (High Quality)',
        'dpi': 600,
        'color_mode': 'Color',
        'paper_size': 'A4',
        'format': 'jpeg',
        'quality': 95,
        'source': 'Flatbed',
        'batch_scan': False,
        'auto_detect': False,
        'description': 'Best quality for photos',
    },
]

DEFAULT_PROFILE_ID = 'document_200_pdf'

# Short names and legacy IDs accepted from Home Assistant configs (pre-4.0
# the HA endpoint advertised flatbed_*/adf_* IDs that no profile ever had).
PROFILE_ALIASES = {
    'document': 'document_200_pdf',
    'adf': 'document_adf_200_pdf',
    'multipage': 'document_adf_200_pdf',
    'color': 'color_300_pdf',
    'photo': 'photo_600_jpeg',
    'gray': 'gray_150_pdf',
    'fast': 'gray_150_pdf',
    'flatbed_document_200_gray_pdf': 'document_200_pdf',
    'flatbed_document_300_gray_pdf': 'document_200_pdf',
    'flatbed_color_300_pdf': 'color_300_pdf',
    'flatbed_photo_600_jpeg': 'photo_600_jpeg',
    'adf_document_200_gray_pdf': 'document_adf_200_pdf',
    'adf_document_300_gray_pdf': 'document_adf_200_pdf',
    'adf_color_300_pdf': 'document_adf_200_pdf',
}

_VALID_ID = re.compile(r'^[a-z0-9][a-z0-9_-]{1,63}$')


def _row_to_profile(row) -> dict:
    return {
        'id': row['id'],
        'name': row['name'],
        'dpi': row['dpi'],
        'color_mode': row['color_mode'],
        'paper_size': row['paper_size'],
        'format': row['format'],
        'quality': row['quality'] if row['quality'] is not None else 85,
        'source': row['source'] or 'Flatbed',
        'batch_scan': bool(row['batch_scan']),
        'auto_detect': bool(row['auto_detect']) if row['auto_detect'] is not None else True,
        'description': row['description'] or '',
        'is_builtin': bool(row['is_builtin']),
    }


class ProfileRepository:
    """CRUD access to scan profiles."""

    def list(self) -> List[dict]:
        try:
            with get_db().get_connection() as conn:
                rows = conn.execute(
                    "SELECT * FROM scan_profiles ORDER BY is_builtin DESC, name"
                ).fetchall()
            profiles = [_row_to_profile(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to load profiles from DB, using defaults: {e}")
            profiles = []
        if not profiles:
            return [dict(p, is_builtin=True) for p in DEFAULT_PROFILES]
        return profiles

    def get(self, profile_id: str) -> Optional[dict]:
        with get_db().get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM scan_profiles WHERE id = ?", (profile_id,)
            ).fetchone()
        return _row_to_profile(row) if row else None

    def resolve(self, profile_id: Optional[str]) -> dict:
        """Resolve a profile ID (including aliases) to a full profile dict.

        Falls back to the default profile with a warning so automations
        (e.g. Home Assistant) keep working even with stale IDs.
        """
        requested = (profile_id or '').strip()
        canonical = PROFILE_ALIASES.get(requested.lower(), requested)
        if canonical:
            profile = self.get(canonical)
            if profile:
                return profile
            # DB might be empty/unavailable - check built-in defaults
            for p in DEFAULT_PROFILES:
                if p['id'] == canonical:
                    return dict(p, is_builtin=True)
        fallback = self.get(DEFAULT_PROFILE_ID) or dict(DEFAULT_PROFILES[0], is_builtin=True)
        if requested:
            logger.warning(
                f"Unknown scan profile '{requested}', falling back to '{fallback['id']}'"
            )
        return fallback

    def create(self, profile: dict) -> dict:
        profile_id = (profile.get('id') or '').strip()
        if not _VALID_ID.match(profile_id):
            raise ValueError(
                "Profile ID must be 2-64 chars: lowercase letters, digits, '-' or '_'"
            )
        if self.get(profile_id):
            raise ValueError(f"Profile '{profile_id}' already exists")
        with get_db().get_connection() as conn:
            conn.execute(
                """
                INSERT INTO scan_profiles
                    (id, name, dpi, color_mode, paper_size, format, quality,
                     source, batch_scan, auto_detect, description, is_builtin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    profile_id,
                    profile['name'],
                    int(profile['dpi']),
                    profile['color_mode'],
                    profile.get('paper_size', 'A4'),
                    profile['format'],
                    int(profile.get('quality', 85)),
                    profile.get('source', 'Flatbed'),
                    1 if profile.get('batch_scan') else 0,
                    1 if profile.get('auto_detect', True) else 0,
                    profile.get('description', ''),
                ),
            )
        return self.get(profile_id)

    def update(self, profile_id: str, profile: dict) -> dict:
        existing = self.get(profile_id)
        if not existing:
            raise KeyError(f"Profile '{profile_id}' not found")
        with get_db().get_connection() as conn:
            conn.execute(
                """
                UPDATE scan_profiles SET
                    name = ?, dpi = ?, color_mode = ?, paper_size = ?,
                    format = ?, quality = ?, source = ?, batch_scan = ?,
                    auto_detect = ?, description = ?
                WHERE id = ?
                """,
                (
                    profile.get('name', existing['name']),
                    int(profile.get('dpi', existing['dpi'])),
                    profile.get('color_mode', existing['color_mode']),
                    profile.get('paper_size', existing['paper_size']),
                    profile.get('format', existing['format']),
                    int(profile.get('quality', existing['quality'])),
                    profile.get('source', existing['source']),
                    1 if profile.get('batch_scan', existing['batch_scan']) else 0,
                    1 if profile.get('auto_detect', existing['auto_detect']) else 0,
                    profile.get('description', existing['description']),
                    profile_id,
                ),
            )
        return self.get(profile_id)

    def delete(self, profile_id: str) -> bool:
        existing = self.get(profile_id)
        if not existing:
            return False
        if existing['is_builtin']:
            raise ValueError("Built-in profiles cannot be deleted")
        with get_db().get_connection() as conn:
            conn.execute("DELETE FROM scan_profiles WHERE id = ?", (profile_id,))
        return True

    def seed_defaults(self) -> None:
        """Insert any missing built-in profiles (idempotent)."""
        with get_db().get_connection() as conn:
            for p in DEFAULT_PROFILES:
                row = conn.execute(
                    "SELECT id FROM scan_profiles WHERE id = ?", (p['id'],)
                ).fetchone()
                if row:
                    # Make sure pre-4.0 seeded rows are marked as built-in and
                    # have the extended columns populated.
                    conn.execute(
                        """
                        UPDATE scan_profiles SET
                            is_builtin = 1,
                            quality = COALESCE(quality, ?),
                            source = COALESCE(source, ?),
                            batch_scan = COALESCE(batch_scan, ?),
                            auto_detect = COALESCE(auto_detect, ?),
                            description = COALESCE(description, ?)
                        WHERE id = ?
                        """,
                        (
                            p['quality'], p['source'],
                            1 if p['batch_scan'] else 0,
                            1 if p['auto_detect'] else 0,
                            p['description'], p['id'],
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO scan_profiles
                            (id, name, dpi, color_mode, paper_size, format, quality,
                             source, batch_scan, auto_detect, description, is_builtin)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                        """,
                        (
                            p['id'], p['name'], p['dpi'], p['color_mode'],
                            p['paper_size'], p['format'], p['quality'], p['source'],
                            1 if p['batch_scan'] else 0,
                            1 if p['auto_detect'] else 0,
                            p['description'],
                        ),
                    )


def get_profile_repository() -> ProfileRepository:
    return ProfileRepository()
