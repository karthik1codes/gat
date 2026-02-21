"""
SSE Client: key management, document encryption, index building,
search token generation, and document retrieval/decryption.
Supports deterministic SSE (default) and forward-private SSE (optional).
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
from crypto.forward_secure import (
    build_forward_secure_index_key,
    build_forward_secure_search_tokens,
)
from crypto.ngrams import extract_ngrams_unique
from crypto.phonetic import soundex_words, soundex, levenshtein_distance
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
        self._known_doc_ids: set[str] = set()  # for filtering padded search results

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
            self._known_doc_ids.add(doc_id)
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

    def search(self, query: str, pad_to: int = 0) -> List[str]:
        """
        Generate search token and return matching document IDs.
        If pad_to > 0, server returns padded list; client filters to known doc IDs.
        """
        token = build_trapdoor(query.strip().lower(), self._key)
        raw = self._server.search(token, pad_to=pad_to)
        if pad_to > 0 and self._known_doc_ids:
            return [x for x in raw if x in self._known_doc_ids]
        return raw

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

    # -------------------------------------------------------------------------
    # Forward-private SSE: per-keyword counter; server cannot link searches to
    # future insertions. Caller must persist keyword_counter (e.g. to disk).
    # -------------------------------------------------------------------------

    def upload_documents_forward_secure(
        self,
        keyword_counter: Dict[str, int],
        documents: List[Tuple[str, bytes]],
    ) -> None:
        """
        Encrypt and upload documents using forward-private index entries.
        keyword_counter is updated in place; persist it for future searches.
        Each (keyword, counter) gets a unique index key; counter increments per add.
        """
        index: Dict[str, List[str]] = {}
        for doc_id, plaintext in documents:
            payload, _ = encrypt_document(plaintext, self._key)
            self._server.upload_document(doc_id, payload)
            keywords = _extract_keywords(plaintext.decode("utf-8", errors="replace"))
            for w in keywords:
                c = keyword_counter.get(w, 0)
                key = build_forward_secure_index_key(w, c, self._key)
                key_hex = key.hex()
                index.setdefault(key_hex, []).append(doc_id)
                keyword_counter[w] = c + 1
        for k in index:
            index[k] = list(dict.fromkeys(index[k]))
        self._server.upload_index(index)

    def search_forward_secure(
        self, keyword_counter: Dict[str, int], query: str, pad_to: int = 0
    ) -> List[str]:
        """
        Search using forward-private tokens: send tokens for counter 0..max-1.
        Returns union of doc_ids for the keyword (all counter versions).
        If pad_to > 0, server returns padded list; client filters to known doc IDs.
        """
        w = query.strip().lower()
        max_c = keyword_counter.get(w, 0)
        if max_c == 0:
            return []
        tokens = build_forward_secure_search_tokens(w, max_c, self._key)
        raw = self._server.search_multi(tokens, pad_to=pad_to)
        if pad_to > 0 and self._known_doc_ids:
            return [x for x in raw if x in self._known_doc_ids]
        return raw

    # -------------------------------------------------------------------------
    # Substring search: encrypted n-gram index; search = intersection of sets.
    # -------------------------------------------------------------------------

    def upload_documents_substring_index(
        self,
        documents: List[Tuple[str, bytes]],
        n: int = 3,
    ) -> None:
        """
        Build and upload n-gram index for substring search.
        Each n-gram (e.g. trigram) is indexed; same index backend as keyword search.
        """
        index: Dict[str, List[str]] = {}
        for doc_id, plaintext in documents:
            self._known_doc_ids.add(doc_id)
            text = plaintext.decode("utf-8", errors="replace")
            for ng in extract_ngrams_unique(text, n):
                key_hex = encrypt_keyword_for_index(ng, self._key).hex()
                index.setdefault(key_hex, []).append(doc_id)
        for k in index:
            index[k] = list(dict.fromkeys(index[k]))
        self._server.upload_index(index)

    def search_substring(self, query: str, n: int = 3, pad_to: int = 0) -> List[str]:
        """
        Substring search: query is tokenized into n-grams; return doc_ids that
        contain all n-grams (intersection). Empty query returns [].
        """
        ngs = extract_ngrams_unique(query.strip().lower(), n)
        if not ngs:
            return []
        tokens = [build_trapdoor(ng, self._key) for ng in ngs]
        per_token = self._server.search_multi_breakdown(tokens)
        if not per_token:
            return []
        # Intersection of doc_id sets
        sets = [set(doc_ids) for doc_ids in per_token]
        result = list(sets[0].intersection(*sets[1:]))
        if pad_to > 0 and self._known_doc_ids:
            result = [x for x in result if x in self._known_doc_ids]
        return result

    # -------------------------------------------------------------------------
    # Fuzzy search: phonetic index (Soundex) + client-side edit-distance filter.
    # -------------------------------------------------------------------------

    def upload_documents_phonetic_index(self, documents: List[Tuple[str, bytes]]) -> None:
        """
        Build encrypted phonetic (Soundex) index. Same index backend as keywords.
        Call after upload_documents; used for search_phonetic_candidates / search_fuzzy.
        """
        index: Dict[str, List[str]] = {}
        for doc_id, plaintext in documents:
            self._known_doc_ids.add(doc_id)
            text = plaintext.decode("utf-8", errors="replace")
            for code in soundex_words(text):
                key_hex = encrypt_keyword_for_index(code, self._key).hex()
                index.setdefault(key_hex, []).append(doc_id)
        for k in index:
            index[k] = list(dict.fromkeys(index[k]))
        self._server.upload_index(index)

    def search_phonetic_candidates(self, query: str) -> List[str]:
        """
        Return doc_ids that contain words with same Soundex as query.
        Does not verify edit distance; use search_fuzzy for that.
        """
        codes = soundex_words(query.strip().lower())
        if not codes:
            return []
        tokens = [build_trapdoor(c, self._key) for c in codes]
        return list(dict.fromkeys(self._server.search_multi(tokens)))

    def search_fuzzy(
        self,
        query: str,
        max_edit_distance: int = 2,
    ) -> List[str]:
        """
        Phonetic search then client-side edit-distance verification.
        Fetches candidate docs, decrypts, keeps only docs with a word within
        max_edit_distance of query. Edit distance is never sent to server.
        """
        candidates = self.search_phonetic_candidates(query)
        if not candidates:
            return []
        query_lower = query.strip().lower()
        result = []
        for doc_id in candidates:
            plain = self.retrieve_and_decrypt(doc_id)
            if plain is None:
                continue
            words = set(plain.decode("utf-8", errors="replace").lower().split())
            for w in words:
                if len(w) < 2:
                    continue
                if levenshtein_distance(query_lower, w) <= max_edit_distance:
                    result.append(doc_id)
                    break
        return result

    # -------------------------------------------------------------------------
    # Ranking: TF-IDF computed client-side after decryption; return top-K.
    # -------------------------------------------------------------------------

    def search_ranked(self, query: str, top_k: int = 10, pad_to: int = 0) -> List[str]:
        """
        Keyword search then rank by TF-IDF. TF/IDF computed client-side from
        decrypted documents; server never sees scores or term frequencies.
        Returns top_k doc_ids ordered by score (desc).
        """
        import math
        w = query.strip().lower()
        if not w:
            return []
        doc_ids = self.search(w, pad_to=pad_to)
        if not doc_ids:
            return []
        N = len(self._server.list_document_ids()) or 1
        df = len(doc_ids)
        idf = math.log((N + 1) / (df + 1)) + 1.0
        scores: List[Tuple[str, float]] = []
        for doc_id in doc_ids:
            plain = self.retrieve_and_decrypt(doc_id)
            if plain is None:
                continue
            text = plain.decode("utf-8", errors="replace").lower()
            terms = text.split()
            if not terms:
                scores.append((doc_id, 0.0))
                continue
            tf = sum(1 for t in terms if t == w) / len(terms)
            scores.append((doc_id, tf * idf))
        scores.sort(key=lambda x: -x[1])
        return [doc_id for doc_id, _ in scores[:top_k]]
