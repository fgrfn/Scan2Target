"""Regression tests for statistics status classification."""
from __future__ import annotations

import asyncio
import sqlite3
from contextlib import contextmanager

from api import stats


class _TestDatabase:
    def __init__(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE devices (id TEXT PRIMARY KEY, name TEXT);
            CREATE TABLE targets (id TEXT PRIMARY KEY, name TEXT);
            CREATE TABLE jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT,
                device_id TEXT,
                target_id TEXT,
                status TEXT,
                message TEXT,
                created_at TEXT
            );
            INSERT INTO devices VALUES ('scanner-1', 'Office scanner');
            INSERT INTO targets VALUES ('archive', 'Archive');
            INSERT INTO jobs VALUES
                ('ok', 'scan', 'scanner-1', 'archive', 'completed', NULL, datetime('now')),
                ('delivery', 'scan', 'scanner-1', 'archive', 'delivery_failed', 'unreachable', datetime('now')),
                ('scan', 'scan', 'scanner-1', 'archive', 'failed', 'jammed', datetime('now'));
            """
        )

    @contextmanager
    def get_connection(self):
        yield self.connection


def test_delivery_failures_are_included_in_statistics(monkeypatch):
    database = _TestDatabase()
    monkeypatch.setattr(stats, "get_db", lambda: database)

    timeline = asyncio.run(stats.get_scan_timeline())
    scanners = asyncio.run(stats.get_scanner_statistics())
    targets = asyncio.run(stats.get_target_statistics())

    assert timeline[0]["failed"] == 2
    assert scanners[0]["failed"] == 2
    assert scanners[0]["success_rate"] == 33.3
    assert targets[0]["successful"] == 1
    assert targets[0]["delivery_failed"] == 1
    assert targets[0]["failed"] == 1
    assert targets[0]["success_rate"] == 33.3
