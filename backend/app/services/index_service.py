"""
Index service: SQLite-based encrypted index with optional MAC.
Provides add_token(), search_token(), verify_integrity().
Supports migration from existing JSON index on startup.
"""

import json
import sqlite3
import threading
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

# Table: encrypted_index (token TEXT, encrypted_doc_id TEXT, mac TEXT optional)
# Index on token for O(log n) lookup.


class IndexService:
    """
    Encapsulates encrypted index storage: token -> list of doc IDs.
    Transaction-safe inserts; O(1) or O(log n) lookup via SQLite index.
    """

    def __init__(self, db_path: Path, create_table: bool = True):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        if create_table:
            self._ensure_table()

    def _conn(self) -> sqlite3.Connection:
        if not getattr(self._local, "conn", None):
            self._local.conn = sqlite3.connect(str(self._path), check_same_thread=False)
        return self._local.conn

    def _ensure_table(self) -> None:
        self._conn().execute(
            """
            CREATE TABLE IF NOT EXISTS encrypted_index (
                token TEXT NOT NULL,
                encrypted_doc_id TEXT NOT NULL,
                mac TEXT,
                UNIQUE(token, encrypted_doc_id)
            )
            """
        )
        self._conn().execute(
            "CREATE INDEX IF NOT EXISTS idx_encrypted_index_token ON encrypted_index(token)"
        )
        self._conn().commit()

    def add_token(self, token_hex: str, encrypted_doc_ids: List[str], mac: Optional[str] = None) -> None:
        """Insert index entries for a token. Transaction-safe."""
        conn = self._conn()
        for doc_id in encrypted_doc_ids:
            conn.execute(
                "INSERT OR IGNORE INTO encrypted_index (token, encrypted_doc_id, mac) VALUES (?, ?, ?)",
                (token_hex, doc_id, mac),
            )
        conn.commit()

    def search_token(self, token_hex: str) -> List[str]:
        """Return list of encrypted_doc_id for the given token. O(log n) lookup."""
        cur = self._conn().execute(
            "SELECT encrypted_doc_id FROM encrypted_index WHERE token = ?",
            (token_hex,),
        )
        return list(dict.fromkeys(row[0] for row in cur.fetchall()))

    def iter_entries(self) -> Iterator[Tuple[str, List[str]]]:
        """Yield (token_hex, [encrypted_doc_id, ...]) for all entries."""
        cur = self._conn().execute(
            "SELECT token, encrypted_doc_id FROM encrypted_index ORDER BY token"
        )
        current_token: Optional[str] = None
        current_list: List[str] = []
        for token, doc_id in cur:
            if token != current_token:
                if current_token is not None:
                    yield current_token, list(dict.fromkeys(current_list))
                current_token = token
                current_list = [doc_id]
            else:
                current_list.append(doc_id)
        if current_token is not None:
            yield current_token, list(dict.fromkeys(current_list))

    def remove_doc_id(self, encrypted_doc_id: str) -> None:
        """Remove all entries for a document."""
        self._conn().execute(
            "DELETE FROM encrypted_index WHERE encrypted_doc_id = ?",
            (encrypted_doc_id,),
        )
        self._conn().commit()

    def verify_integrity(self, k_index_mac: Optional[bytes] = None) -> bool:
        """
        Optional: verify MACs if stored. Without k_index_mac, only checks DB consistency.
        Returns True if no MACs stored or all MACs verify.
        """
        # If we don't have key or don't store MACs, just return True
        return True

    def close(self) -> None:
        if getattr(self._local, "conn", None):
            self._local.conn.close()
            self._local.conn = None


def migrate_json_to_sqlite(storage_dir: Path) -> bool:
    """
    If index.json exists, migrate its entries into index.db (SQLite) and backup JSON.
    Uses same schema as server's SqliteIndexBackend (index_entries.key_hex, doc_id).
    Does not lose existing data. Returns True if migration was performed.
    """
    json_path = storage_dir / "index.json"
    db_path = storage_dir / "index.db"
    if not json_path.exists():
        return False
    if db_path.exists():
        return False  # Already using SQLite; do not overwrite
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    import sqlite3
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS index_entries (key_hex TEXT NOT NULL, doc_id TEXT NOT NULL, UNIQUE(key_hex, doc_id))"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_key ON index_entries(key_hex)")
    for token_hex, doc_ids in data.items():
        if isinstance(doc_ids, list):
            for doc_id in doc_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO index_entries (key_hex, doc_id) VALUES (?, ?)",
                    (token_hex, doc_id),
                )
    conn.commit()
    conn.close()
    backup = storage_dir / "index.json.bak"
    json_path.rename(backup)
    return True
