"""
SSE Server: stores encrypted documents and encrypted search index.
Performs string matching by comparing search token (trapdoor) with index entries.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

# Index format: { trapdoor_hex: [doc_id1, doc_id2, ...] }
# Documents: { doc_id: ciphertext_bytes (base64 or raw) }


class SSEServer:
    """Untrusted server: holds encrypted index and documents; answers search with token."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else Path("server_storage")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._index: Dict[str, List[str]] = {}  # trapdoor_hex -> [doc_id]
        self._documents: Dict[str, bytes] = {}  # doc_id -> ciphertext
        self._load_state()

    def _index_path(self) -> Path:
        return self.storage_dir / "index.json"

    def _docs_path(self) -> Path:
        return self.storage_dir / "documents"

    def _load_state(self) -> None:
        """Load persisted index and document list from disk."""
        ip = self._index_path()
        if ip.exists():
            with open(ip, "r", encoding="utf-8") as f:
                self._index = json.load(f)
        dp = self._docs_path()
        if dp.exists():
            for f in dp.iterdir():
                if f.is_file():
                    self._documents[f.name] = f.read_bytes()

    def _save_state(self) -> None:
        """Persist index and documents."""
        self._index_path().parent.mkdir(parents=True, exist_ok=True)
        with open(self._index_path(), "w", encoding="utf-8") as f:
            json.dump(self._index, f, indent=2)
        doc_dir = self._docs_path()
        doc_dir.mkdir(parents=True, exist_ok=True)
        for doc_id, ct in self._documents.items():
            (doc_dir / doc_id).write_bytes(ct)

    def upload_index(self, index: Dict[str, List[str]]) -> None:
        """
        Accept encrypted index from client.
        index: map of trapdoor_hex -> list of document IDs.
        """
        for k, doc_ids in index.items():
            self._index.setdefault(k, []).extend(doc_ids)
            self._index[k] = list(dict.fromkeys(self._index[k]))  # dedupe
        self._save_state()

    def upload_document(self, doc_id: str, ciphertext: bytes) -> None:
        """Store one encrypted document."""
        self._documents[doc_id] = ciphertext
        self._docs_path().mkdir(parents=True, exist_ok=True)
        (self._docs_path() / doc_id).write_bytes(ciphertext)

    def search(self, token: bytes) -> List[str]:
        """
        String matching: find document IDs whose index entry matches the token.
        token: trapdoor (raw bytes) from client.
        Returns list of document IDs.
        """
        key = token.hex()
        return self._index.get(key, []).copy()

    def get_document(self, doc_id: str) -> Optional[bytes]:
        """Return encrypted document by ID, or None if not found."""
        return self._documents.get(doc_id)

    def list_document_ids(self) -> List[str]:
        """Return all stored document IDs (for debugging)."""
        return list(self._documents.keys())
