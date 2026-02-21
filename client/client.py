"""
SSE Client: key management, document encryption, index building,
search token generation, and document retrieval/decryption.
"""

import re
from typing import Dict, List, Optional, Tuple

from crypto import (
    generate_key,
    encrypt_document,
    decrypt_document,
    build_trapdoor,
    encrypt_keyword_for_index,
)
from server import SSEServer


def _extract_keywords(text: str) -> List[str]:
    """Extract normalized keywords (words) from text for indexing."""
    text = text.lower()
    words = re.findall(r"\b[a-z0-9]+\b", text)
    return list(dict.fromkeys(words))  # unique, preserve order


class SSEClient:
    """Data owner / searcher: holds secret key; encrypts, indexes, searches, decrypts."""

    def __init__(self, master_key: Optional[bytes] = None, server: Optional[SSEServer] = None):
        self._key = master_key if master_key is not None else generate_key()
        self._server = server or SSEServer()

    @property
    def master_key(self) -> bytes:
        return self._key

    def set_server(self, server: SSEServer) -> None:
        self._server = server

    def upload_documents(self, documents: List[Tuple[str, bytes]]) -> Dict[str, List[str]]:
        """
        Encrypt documents and build encrypted index (keyword -> doc IDs).
        documents: list of (doc_id, plaintext_bytes).
        Returns the index to be sent to server: { trapdoor_hex: [doc_id, ...] }.
        Also uploads each encrypted doc to server.
        """
        index: Dict[str, List[str]] = {}
        for doc_id, plaintext in documents:
            payload, _ = encrypt_document(plaintext, self._key)
            self._server.upload_document(doc_id, payload)
            keywords = _extract_keywords(plaintext.decode("utf-8", errors="replace"))
            for w in keywords:
                trap = encrypt_keyword_for_index(w, self._key)
                key_hex = trap.hex()
                index.setdefault(key_hex, []).append(doc_id)
        # Dedupe doc IDs per keyword
        for k in index:
            index[k] = list(dict.fromkeys(index[k]))
        self._server.upload_index(index)
        return index

    def upload_document(self, doc_id: str, plaintext: bytes) -> None:
        """Upload a single document: encrypt, index, and send to server."""
        self.upload_documents([(doc_id, plaintext)])

    def search(self, query: str) -> List[str]:
        """
        Generate search token for query string and return matching document IDs.
        Uses exact keyword match: query is treated as one keyword (or we could split).
        """
        token = build_trapdoor(query.strip().lower(), self._key)
        return self._server.search(token)

    def search_multi_keyword(self, keywords: List[str]) -> Dict[str, List[str]]:
        """Return for each keyword the list of matching doc IDs (for demo)."""
        result = {}
        for w in keywords:
            result[w] = self.search(w)
        return result

    def retrieve_and_decrypt(self, doc_id: str) -> Optional[bytes]:
        """Fetch encrypted document from server and decrypt."""
        ct = self._server.get_document(doc_id)
        if ct is None:
            return None
        return decrypt_document(ct, self._key)
