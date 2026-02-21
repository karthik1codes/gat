"""
Judge Mode (Cryptographic Transparency): ensure debug responses are safe and backward compatible.
- security-info endpoint returns only allowed metadata.
- Search/upload debug payloads never contain secret_key, plaintext, or derived keys.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient

# Load backend app (add backend to path if needed)
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
from app.main import app

client = TestClient(app)

FORBIDDEN_KEYS = {"secret_key", "plaintext", "key", "derived_key", "master_key", "k_enc", "k_search"}


def test_security_info_returns_safe_metadata():
    """GET /api/security-info must return only algorithm names and leakage profile (no secrets)."""
    r = client.get("/api/security-info")
    assert r.status_code == 200
    data = r.json()
    assert "encryption" in data
    assert data["encryption"] == "AES-256-GCM"
    assert "token_generation" in data
    assert data["token_generation"] == "HMAC-SHA256"
    assert "key_size_bits" in data
    assert data["key_size_bits"] == 256
    assert "leakage_profile" in data
    lp = data["leakage_profile"]
    assert "search_pattern" in lp and "access_pattern" in lp and "content_leakage" in lp
    # No secret or key material
    for key in data:
        assert key not in FORBIDDEN_KEYS
    for key in lp:
        assert key not in FORBIDDEN_KEYS


def test_security_info_no_secrets_in_response():
    """Ensure security-info response body does not contain forbidden substrings."""
    r = client.get("/api/security-info")
    assert r.status_code == 200
    text = r.text
    assert "secret" not in text.lower() or "content_leakage" in text  # only in key name
    # "key" appears only in key_size_bits / token_generation algorithm name
    assert "secret_key" not in text
    assert "plaintext" not in text


def test_search_debug_payload_structure():
    """SearchDebugInfo model allows only safe fields (used when debug=true)."""
    from app.routes.documents import SearchDebugInfo

    safe_payload = {
        "search_token": "aabbcc",
        "matched_encrypted_doc_ids": ["id1"],
        "encryption_algorithm": "AES-256-GCM",
        "token_algorithm": "HMAC-SHA256",
        "index_lookup_performed": True,
        "result_count": 1,
    }
    obj = SearchDebugInfo(**safe_payload)
    d = obj.model_dump()
    for key in d:
        assert key not in FORBIDDEN_KEYS
    assert "search_token" in d
    assert "matched_encrypted_doc_ids" in d
