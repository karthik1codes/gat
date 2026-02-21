"""
Forward-private SSE: reduce search pattern leakage.

- Per-keyword update counter: each time a document containing a keyword is added,
  the keyword's counter increments. Index key = F_k(keyword || counter).
- Search: client sends tokens for all counter values 0..max; server cannot link
  a search to a specific future insertion (old tokens remain valid for old data).
- Ephemeral per-search behaviour: client sends a set of tokens; server sees only
  opaque tokens. Same keyword at different times can send same token set (counter
  range) but server does not learn keyword.
- Inspired by Bost's forward-secure SSE: after an update, new data is bound to new
  counter; past search tokens do not reveal which keyword was updated.
"""

from .keys import derive_key_bundle

try:
    from Cryptodome.Hash import HMAC, SHA256
except ImportError:
    from Crypto.Hash import HMAC, SHA256

# Label to separate forward-secure domain from deterministic trapdoors
LABEL_FWD = b"sse.v1.forward"


def _fwd_key(master_key: bytes) -> bytes:
    """Derive key for forward-secure token/index. Separate from deterministic trapdoors."""
    bundle = derive_key_bundle(master_key)
    h = HMAC.new(bundle.k_search, digestmod=SHA256)
    h.update(LABEL_FWD)
    return h.digest()


def build_forward_secure_index_key(keyword: str, counter: int, master_key: bytes) -> bytes:
    """
    Index key for (keyword, counter). Stored on server.
    Same (keyword, counter) always yields same key; different counter => different key.
    """
    k = _fwd_key(master_key)
    w = keyword.strip().lower().encode("utf-8")
    h = HMAC.new(k, digestmod=SHA256)
    h.update(w)
    h.update(counter.to_bytes(8, "big"))
    return h.digest()


def build_forward_secure_search_tokens(keyword: str, counter_max: int, master_key: bytes) -> list[bytes]:
    """
    Tokens for search: one per counter value in [0, counter_max).
    Server matches any of these to return all doc_ids for this keyword.
    counter_max is the current counter (exclusive), so tokens for 0..counter_max-1.
    """
    return [build_forward_secure_index_key(keyword, c, master_key) for c in range(counter_max)]
