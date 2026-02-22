"""
Index storage backends: in-memory dict (JSON-backed) and SQLite.
Supports O(1) insert and full scan with constant-time comparison for search.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple


class IndexBackend:
    """Abstract backend for (trapdoor_hex, doc_id) entries."""

    def add(self, key_hex: str, doc_ids: List[str]) -> None:
        """Add or merge doc_ids for key_hex."""
        raise NotImplementedError

    def add_batch(self, index: Dict[str, List[str]]) -> None:
        """Add multiple key -> doc_ids."""
        for k, doc_ids in index.items():
            self.add(k, doc_ids)

    def iter_entries(self) -> Iterator[Tuple[str, List[str]]]:
        """Yield (key_hex, doc_ids) for all entries. Used for constant-time search."""
        raise NotImplementedError

    def remove_doc_id(self, doc_id: str) -> None:
        """Remove a document from the index (all keys that reference it)."""
        raise NotImplementedError

    def get_index_bytes_per_doc(self) -> Dict[str, int]:
        """Return approximate index bytes per doc_id (for per-document metrics)."""
        raise NotImplementedError

    def close(self) -> None:
        """Release resources."""
        pass


class JsonIndexBackend(IndexBackend):
    """In-memory dict persisted as JSON. Backward compatible."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._index: Dict[str, List[str]] = {}
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self._index = json.load(f)

    def add(self, key_hex: str, doc_ids: List[str]) -> None:
        self._index.setdefault(key_hex, []).extend(doc_ids)
        self._index[key_hex] = list(dict.fromkeys(self._index[key_hex]))
        self._save()

    def add_batch(self, index: Dict[str, List[str]]) -> None:
        for k, doc_ids in index.items():
            self._index.setdefault(k, []).extend(doc_ids)
            self._index[k] = list(dict.fromkeys(self._index[k]))
        self._save()

    def iter_entries(self) -> Iterator[Tuple[str, List[str]]]:
        yield from self._index.items()

    def remove_doc_id(self, doc_id: str) -> None:
        to_del = []
        for key_hex, doc_ids in list(self._index.items()):
            new_list = [d for d in doc_ids if d != doc_id]
            if not new_list:
                to_del.append(key_hex)
            else:
                self._index[key_hex] = new_list
        for k in to_del:
            del self._index[k]
        self._save()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._index, f, indent=2)

    def get_index_bytes_per_doc(self) -> Dict[str, int]:
        """Approximate bytes per doc: each (key, doc_ids) entry size split by doc."""
        out: Dict[str, int] = {}
        for key_hex, doc_ids in self._index.items():
            if not doc_ids:
                continue
            # Entry size: key + doc ids; split equally among docs in this entry
            entry_size = len(key_hex.encode("utf-8")) + sum(len(d.encode("utf-8")) for d in doc_ids) + 2 * len(doc_ids)
            per_doc = entry_size // len(doc_ids)
            for doc_id in doc_ids:
                out[doc_id] = out.get(doc_id, 0) + per_doc
        return out


class SqliteIndexBackend(IndexBackend):
    """
    SQLite-backed index: one row per (key_hex, doc_id).
    Scalable to large document sets; full scan for constant-time search.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS index_entries (key_hex TEXT NOT NULL, doc_id TEXT NOT NULL, UNIQUE(key_hex, doc_id))"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_key ON index_entries(key_hex)"
        )
        self._conn.commit()

    def add(self, key_hex: str, doc_ids: List[str]) -> None:
        seen = set()
        for doc_id in doc_ids:
            if doc_id in seen:
                continue
            seen.add(doc_id)
            self._conn.execute(
                "INSERT OR IGNORE INTO index_entries (key_hex, doc_id) VALUES (?, ?)",
                (key_hex, doc_id),
            )
        self._conn.commit()

    def add_batch(self, index: Dict[str, List[str]]) -> None:
        for key_hex, doc_ids in index.items():
            self.add(key_hex, doc_ids)

    def iter_entries(self) -> Iterator[Tuple[str, List[str]]]:
        cur = self._conn.execute("SELECT key_hex, doc_id FROM index_entries ORDER BY key_hex")
        # Group by key_hex
        current_key: Optional[str] = None
        current_list: List[str] = []
        for key_hex, doc_id in cur:
            if key_hex != current_key:
                if current_key is not None:
                    yield current_key, list(dict.fromkeys(current_list))
                current_key = key_hex
                current_list = [doc_id]
            else:
                current_list.append(doc_id)
        if current_key is not None:
            yield current_key, list(dict.fromkeys(current_list))

    def remove_doc_id(self, doc_id: str) -> None:
        self._conn.execute("DELETE FROM index_entries WHERE doc_id = ?", (doc_id,))
        self._conn.commit()

    def get_index_bytes_per_doc(self) -> Dict[str, int]:
        """Bytes per doc: sum of (key_hex + doc_id) length for each row (proxy for index share)."""
        cur = self._conn.execute(
            "SELECT doc_id, SUM(LENGTH(key_hex) + LENGTH(doc_id)) AS bytes FROM index_entries GROUP BY doc_id"
        )
        return dict(cur.fetchall())

    def close(self) -> None:
        self._conn.close()
