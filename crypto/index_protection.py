"""
Index integrity protection.

- Sign each index block (trapdoor_hex -> doc_ids) with HMAC-SHA256(K_index_mac).
- Verify before search result return; reject tampered or corrupted index.
- Protects against tampering, file injection, index corruption.
"""

import hmac
import hashlib
import json
from typing import Dict, List, Tuple

from .keys import constant_time_equals

MAC_SIZE = 32


def _serialize_index_block(entries: Dict[str, List[str]]) -> bytes:
    """Deterministic serialization for signing (sorted keys)."""
    items = sorted(entries.items())
    return json.dumps(items, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_index_block(entries: Dict[str, List[str]], k_index_mac: bytes) -> bytes:
    """
    Compute HMAC-SHA256 of serialized index block.
    k_index_mac must be 32 bytes.
    """
    if len(k_index_mac) != 32:
        raise ValueError("K_index_mac must be 32 bytes")
    data = _serialize_index_block(entries)
    return hmac.new(k_index_mac, data, hashlib.sha256).digest()


def verify_index_block(entries: Dict[str, List[str]], expected_mac: bytes, k_index_mac: bytes) -> bool:
    """Constant-time verification of index block MAC."""
    if len(expected_mac) != MAC_SIZE or len(k_index_mac) != 32:
        return False
    computed = sign_index_block(entries, k_index_mac)
    return constant_time_equals(computed, expected_mac)


def sign_index_entries(entries: Dict[str, List[str]], k_index_mac: bytes) -> Tuple[Dict[str, List[str]], bytes]:
    """
    Return (entries, mac). Store both; server stores entries and MAC.
    On read, verify with verify_index_block before use.
    """
    mac = sign_index_block(entries, k_index_mac)
    return entries, mac


def verify_index_entries(entries: Dict[str, List[str]], mac: bytes, k_index_mac: bytes) -> None:
    """Verify and raise ValueError if tampered."""
    if not verify_index_block(entries, mac, k_index_mac):
        raise ValueError("Index integrity check failed")


def sign_index_entry(trapdoor_hex: str, doc_ids: List[str], k_index_mac: bytes) -> bytes:
    """Per-entry MAC for search result verification. Server stores and returns with doc_ids."""
    if len(k_index_mac) != 32:
        raise ValueError("K_index_mac must be 32 bytes")
    data = (trapdoor_hex + "|" + ",".join(sorted(doc_ids))).encode("utf-8")
    return hmac.new(k_index_mac, data, hashlib.sha256).digest()


def verify_index_entry(trapdoor_hex: str, doc_ids: List[str], mac: bytes, k_index_mac: bytes) -> bool:
    """Constant-time verify per-entry MAC before using search results."""
    if len(mac) != MAC_SIZE or len(k_index_mac) != 32:
        return False
    expected = sign_index_entry(trapdoor_hex, doc_ids, k_index_mac)
    return constant_time_equals(mac, expected)
