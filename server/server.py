"""
SSE Server: stores encrypted documents and encrypted search index.
Performs string matching by comparing search token (trapdoor) with index entries.
Supports padded responses and SQLite index backend for scalability.
"""

import os
import random
import threading
from pathlib import Path
from typing import Dict, List, Optional

from .index_backend import IndexBackend, JsonIndexBackend, SqliteIndexBackend


class SSEServer:
    """Untrusted server: holds encrypted index and documents; answers search with token."""

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        use_sqlite_index: bool = False,
    ):
        self.storage_dir = Path(storage_dir) if storage_dir else Path("server_storage")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        if use_sqlite_index:
            self._backend: IndexBackend = SqliteIndexBackend(self.storage_dir / "index.db")
        else:
            self._backend = JsonIndexBackend(self.storage_dir / "index.json")
        self._documents: Dict[str, bytes] = {}
        self._lock = threading.RLock()  # Concurrency-safe updates
        self._load_documents()

    def _docs_path(self) -> Path:
        return self.storage_dir / "documents"

    def _load_documents(self) -> None:
        """Load document store from disk."""
        dp = self._docs_path()
        if dp.exists():
            for f in dp.iterdir():
                if f.is_file():
                    self._documents[f.name] = f.read_bytes()

    def _save_documents(self) -> None:
        self._docs_path().mkdir(parents=True, exist_ok=True)
        for doc_id, ct in self._documents.items():
            (self._docs_path() / doc_id).write_bytes(ct)

    def upload_index(self, index: Dict[str, List[str]]) -> None:
        """
        Accept encrypted index from client.
        index: map of trapdoor_hex -> list of document IDs.
        """
        with self._lock:
            self._backend.add_batch(index)

    def upload_document(self, doc_id: str, ciphertext: bytes) -> None:
        """Store one encrypted document."""
        with self._lock:
            self._documents[doc_id] = ciphertext
            self._docs_path().mkdir(parents=True, exist_ok=True)
            (self._docs_path() / doc_id).write_bytes(ciphertext)

    def search_multi(self, tokens: List[bytes], pad_to: int = 0) -> List[str]:
        """
        Return union of document IDs for any index entry matching any token.
        Uses backend iter_entries and constant-time comparison.
        If pad_to > 0, pad with dummy document IDs and shuffle.
        """
        from crypto import constant_time_equals
        result = []
        for stored_hex, doc_ids in self._backend.iter_entries():
            try:
                stored = bytes.fromhex(stored_hex)
            except ValueError:
                continue
            for token in tokens:
                if len(token) == len(stored) and constant_time_equals(token, stored):
                    result.extend(doc_ids)
                    break
        result = list(dict.fromkeys(result))  # dedupe, preserve order
        if pad_to > 0 and len(result) < pad_to:
            # Add dummy IDs not in stored documents so client can filter
            real = set(self._documents)
            needed = pad_to - len(result)
            added = 0
            while added < needed:
                dummy = os.urandom(16).hex()
                if dummy not in real and dummy not in result:
                    result.append(dummy)
                    added += 1
            random.shuffle(result)
        return result

    def search(self, token: bytes, pad_to: int = 0) -> List[str]:
        """
        String matching: find document IDs whose index entry matches the token.
        Uses constant-time comparison. If pad_to > 0, response is padded and shuffled.
        """
        return self.search_multi([token], pad_to=pad_to)

    def search_multi_breakdown(self, tokens: List[bytes]) -> List[List[str]]:
        """
        Return doc_id list per token: result[i] = doc_ids matching tokens[i].
        Used for substring search (n-gram intersection) and other multi-token queries.
        """
        from crypto import constant_time_equals
        result: List[List[str]] = [[] for _ in tokens]
        for stored_hex, doc_ids in self._backend.iter_entries():
            try:
                stored = bytes.fromhex(stored_hex)
            except ValueError:
                continue
            for i, token in enumerate(tokens):
                if len(token) == len(stored) and constant_time_equals(token, stored):
                    result[i] = list(dict.fromkeys(result[i] + doc_ids))
                    break
        return result

    def get_document(self, doc_id: str) -> Optional[bytes]:
        """Return encrypted document by ID, or None if not found."""
        return self._documents.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        """Remove document and its index entries. Returns True if doc existed."""
        with self._lock:
            if doc_id not in self._documents:
                return False
            del self._documents[doc_id]
            doc_path = self._docs_path() / doc_id
            if doc_path.exists():
                doc_path.unlink()
            self._backend.remove_doc_id(doc_id)
        return True

    def list_document_ids(self) -> List[str]:
        """Return all stored document IDs (for debugging)."""
        return list(self._documents.keys())

    def get_index_bytes_per_doc(self) -> Dict[str, int]:
        """Return approximate index bytes per doc_id (for per-document metrics)."""
        with self._lock:
            return self._backend.get_index_bytes_per_doc()

    def close(self) -> None:
        """Release resources (e.g. SQLite connection)."""
        self._backend.close()
