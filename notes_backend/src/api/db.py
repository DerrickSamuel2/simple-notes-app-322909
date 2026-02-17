"""SQLite database helpers for the notes backend.

This module centralizes DB connection logic and all note persistence operations.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import List, Optional


def _parse_sqlite_db_env(value: str) -> str:
    """Parse SQLITE_DB env var into a filesystem path.

    Accepts either:
    - a plain file path (e.g. /path/to/myapp.db)
    - a sqlite URI (e.g. sqlite:////path/to/myapp.db)
    """
    trimmed = value.strip()
    if trimmed.startswith("sqlite:///"):
        # sqlite:////abs/path => "/abs/path" after stripping "sqlite:///"
        return trimmed[len("sqlite:///") :]
    return trimmed


# PUBLIC_INTERFACE
def get_db_path() -> str:
    """Return the SQLite DB path from env.

    Uses SQLITE_DB (provided by the database container contract).

    Raises:
        RuntimeError: if SQLITE_DB is missing.
    """
    sqlite_db = os.getenv("SQLITE_DB")
    if not sqlite_db:
        # NOTE: orchestrator should set SQLITE_DB in the backend .env.
        raise RuntimeError(
            "Missing required environment variable SQLITE_DB (path or sqlite:/// URI)."
        )
    return _parse_sqlite_db_env(sqlite_db)


def _connect() -> sqlite3.Connection:
    """Create a SQLite connection with recommended pragmas enabled."""
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL improves concurrent-read behavior (safe for single-file SQLite DB usage).
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def _row_to_note_dict(row: sqlite3.Row) -> dict:
    """Convert a notes row to a JSON-serializable dict."""
    created_at = row["created_at"]
    updated_at = row["updated_at"]

    # sqlite may return str timestamps; keep them as ISO-ish strings.
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    if isinstance(updated_at, datetime):
        updated_at = updated_at.isoformat()

    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "created_at": created_at,
        "updated_at": updated_at,
    }


# PUBLIC_INTERFACE
def list_notes(limit: int = 100, offset: int = 0) -> List[dict]:
    """List notes ordered by updated time descending."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, title, content, created_at, updated_at
            FROM notes
            ORDER BY datetime(updated_at) DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        return [_row_to_note_dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# PUBLIC_INTERFACE
def get_note(note_id: int) -> Optional[dict]:
    """Fetch a single note by id, or None if not found."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, title, content, created_at, updated_at
            FROM notes
            WHERE id = ?
            """,
            (note_id,),
        )
        row = cur.fetchone()
        return _row_to_note_dict(row) if row else None
    finally:
        conn.close()


# PUBLIC_INTERFACE
def create_note(title: str, content: str) -> dict:
    """Create a note and return the created record."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO notes (title, content)
            VALUES (?, ?)
            """,
            (title, content),
        )
        conn.commit()
        note_id = int(cur.lastrowid)
        created = get_note(note_id)
        # get_note opens its own connection; safe and keeps mapping centralized.
        if not created:
            raise RuntimeError("Failed to load newly created note.")
        return created
    finally:
        conn.close()


# PUBLIC_INTERFACE
def update_note(note_id: int, title: str, content: str) -> Optional[dict]:
    """Update a note. Returns updated record, or None if not found."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE notes
            SET title = ?, content = ?
            WHERE id = ?
            """,
            (title, content, note_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
        updated = get_note(note_id)
        if not updated:
            raise RuntimeError("Failed to load updated note.")
        return updated
    finally:
        conn.close()


# PUBLIC_INTERFACE
def delete_note(note_id: int) -> bool:
    """Delete a note. Returns True if deleted, False if not found."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
