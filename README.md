# Secured String Matching using Searchable Encryption

A secure system that enables **string matching on encrypted data** while preserving data confidentiality and privacy. The server stores only ciphertexts and an encrypted index; search is performed using **search tokens** (trapdoors) so the server never sees plaintext data or search queries.

## Features

- **Document encryption**: AES-256-GCM for document contents (random IV per document)
- **Key management**: HKDF-derived key separation (K_enc, K_search, K_index); keys never stored on server; per-user key isolation
- **Searchable index**: Inverted index mapping trapdoors to document IDs; constant-time comparison to prevent timing leaks
- **Exact keyword search**: Generate a search token for a query; server returns matching document IDs without seeing the query or document contents
- **Client/Server split**: Client holds the secret key; server stores only ciphertexts and the encrypted index

## Vault architecture (Cryptomator-grade)

Optional **vault** layer adds password-based key derivation and in-memory key lifecycle:

- **Vault states**: `LOCKED` (no decryption) / `UNLOCKED` (keys in memory only). Manual lock and configurable inactivity auto-lock.
- **Key derivation**: Scrypt (or PBKDF2-HMAC-SHA256, 200k+ iterations) from password + 32-byte salt → K_master; then HKDF to derive:
  - **K_file_enc** (AES-256-GCM file encryption), **K_filename_enc** (filename encryption), **K_search** / **K_index** (search/index), **K_index_mac** (index integrity).
- **File encryption**: `crypto/file_encryption.py` — 96-bit IV, authenticated encryption; optional metadata HMAC.
- **Filename encryption**: `crypto/filename_encryption.py` — server stores only base64-encoded ciphertext; no plaintext filenames.
- **Index integrity**: `crypto/index_protection.py` — HMAC(K_index_mac) per index block/entry; verify before using search results.
- **API**: `POST /api/vault/unlock`, `POST /api/vault/lock`, `GET /api/vault/status`, `GET /api/vault/stats` (total files, size, algorithm, KDF, last unlock).
- Keys are **never** stored in plaintext on the server; cleared from memory on lock. See `THREAT_MODEL.md` for leakage and assumptions.

Existing SSE flow (document encrypt/search/retrieve) is unchanged; vault is additive for password-unlock and future vault-key–based uploads.

## Project structure

```
gat/
├── crypto/           # SSE + vault: keys, kdf, vault, sse, file_encryption, filename_encryption, index_protection
├── client/           # Data owner: encrypt, build index, search token, decrypt
├── server/           # Untrusted server: store index + docs, match token → doc IDs
├── backend/          # Full-stack: FastAPI app, Google OAuth, REST API, vault API
│   ├── app/          # main, auth, routes, services (vault_service), sse_service, database
│   └── requirements.txt
├── frontend/         # React + Vite + Tailwind, Google sign-in, dashboard
├── tests/            # Security tests: vault, KDF, encryption, index integrity
├── data/sample_docs/
├── cli.py            # Command-line interface
├── requirements.txt
└── README.md
```

## Setup

```bash
pip install -r requirements.txt
```

## Usage

### 1. Generate a secret key (for persistent use)

```bash
python cli.py init
```

This creates `key.bin`. Keep it secret; without it you cannot decrypt or generate valid search tokens.

### 2. Upload documents

Encrypt and upload all `.txt` files from a directory (e.g. sample docs):

```bash
python cli.py upload data/sample_docs
```

Documents are encrypted and indexed by keyword; the server stores only ciphertext and the encrypted index.

### 3. Search

Search by keyword (exact match, case-insensitive):

```bash
python cli.py search invoice
python cli.py search confidential
```

Output is the list of document IDs that contain that keyword. The server never sees the keyword—only the search token.

### 4. Retrieve and decrypt

Fetch and decrypt a document by ID:

```bash
python cli.py retrieve doc1
```

### 5. One-shot demo (no key file)

Run a self-contained demo with built-in sample documents:

```bash
python cli.py demo
```

This generates a temporary key, uploads sample docs, runs a few searches, and retrieves one document. No `key.bin` required.

## How it works

1. **Client** derives an encryption key and an index key from a master key.
2. **Upload**: For each document, the client encrypts the body (AES-GCM) and extracts keywords. For each keyword, it computes a **trapdoor** (HMAC) and adds the document ID to the index under that trapdoor. Encrypted documents and the index are sent to the server.
3. **Search**: The client computes the trapdoor for the query keyword and sends only this token to the server. The server looks up the token in the index and returns the list of document IDs.
4. **Retrieve**: The client requests a document by ID; the server returns the ciphertext; the client decrypts with the master key.

The server never sees plaintext documents, plaintext keywords, or the search query—only trapdoors and ciphertexts.

## Full-stack web application


The project includes a **web app** with Google OAuth, upload, search, and document view.

### Backend (FastAPI)

```bash
cd gat
pip install -r backend/requirements.txt
```

Set environment (optional; defaults work for local dev):

- `GOOGLE_CLIENT_ID` — same as the Google Cloud OAuth client ID used by the frontend.
- `GAT_SERVER_SECRET` — secret to encrypt per-user SSE keys in the DB (min 32 chars).
- `GAT_JWT_SECRET` — secret for signing JWTs.

Run the API:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (React + Vite + Tailwind)

```bash
cd frontend
npm install
```

Create `.env` (see `frontend/.env.example`):

- `VITE_GOOGLE_CLIENT_ID` — Google OAuth client ID (from [Google Cloud Console](https://console.cloud.google.com/apis/credentials), OAuth 2.0 Client ID for a Web application, with authorized JavaScript origins including `http://localhost:5173`).

Run the dev server (proxies `/api` to the backend):

```bash
npm run dev
```

Open **http://localhost:5173**. Sign in with Google, upload documents, search by keyword, and open documents to view decrypted content.

### Deploy to Vercel (frontend + backend)

To deploy the full app (frontend and API) on [Vercel](https://vercel.com) without removing any functionality, see **[docs/VERCEL_DEPLOYMENT.md](docs/VERCEL_DEPLOYMENT.md)**. You’ll set environment variables (Google OAuth, secrets), connect the repo, and deploy; API and UI run in one project with `/api/*` handled by the backend.

### Google OAuth setup

1. In [Google Cloud Console](https://console.cloud.google.com/), create or select a project.
2. Enable the **Google+ API** (or **Google Identity**) if needed.
3. Go to **APIs & Services → Credentials** and create an **OAuth 2.0 Client ID** (Web application).
4. Add **Authorized JavaScript origins**: `http://localhost:5173`, `http://127.0.0.1:5173` (and your production URL when you deploy).
5. Copy the **Client ID** into:
   - Backend: `GOOGLE_CLIENT_ID` (or `GAT_GOOGLE_CLIENT_ID`).
   - Frontend: `VITE_GOOGLE_CLIENT_ID` in `.env`.

## Security

- **Key management**: A single master key is generated with `os.urandom`. HKDF derives three separate keys: K_enc (document encryption), K_search (trapdoor generation), K_index (index encoding). The server stores only data partitioned by key identifier (e.g. user id); no key material is ever stored on the server.
- **Confidentiality**: Document contents are encrypted with AES-256-GCM; keywords are represented by trapdoors (HMAC-SHA256). The server never sees plaintext.
- **Query privacy**: The server sees only the search token (trapdoor), not the query string.
- **Timing**: Server-side trapdoor comparison uses constant-time equality to avoid timing side channels.
- **Leakage**: Same keyword yields the same trapdoor (search-pattern leakage). Access pattern (which doc IDs are returned per query) is visible to the server. See [THREAT_MODEL.md](THREAT_MODEL.md) for the full adversary model, leakage profile, and mitigations.

### Leakage summary (formal)

- **What leaks**: Search pattern (same query → same token); access pattern (which doc IDs per query); response volume; ciphertext size.
- **What does not leak**: Document plaintext; keyword plaintext; key material.
- **Assumptions**: Key remains secret; server is honest-but-curious; no server-side plaintext processing.

---

## Advanced features (production upgrade)

- **Forward-private SSE**: `upload_documents_forward_secure(keyword_counter, docs)` and `search_forward_secure(keyword_counter, query)`. Per-keyword counter; server cannot link past searches to future insertions.
- **Padded response**: `search(query, pad_to=N)` returns padded, shuffled doc ID list; client filters to known doc IDs.
- **Scalable index**: `SSEServer(storage_dir=..., use_sqlite_index=True)` uses SQLite for the index (O(1) insert; full scan for constant-time search). Default remains JSON.
- **Substring search**: `upload_documents_substring_index(docs, n=3)` then `search_substring(query, n=3)`. Encrypted n-gram index; result = intersection of n-gram matches.
- **Fuzzy search**: `upload_documents_phonetic_index(docs)` then `search_phonetic_candidates(query)` or `search_fuzzy(query, max_edit_distance=2)`. Soundex + client-side Levenshtein verification.
- **Ranking**: `search_ranked(query, top_k=10)`. TF-IDF computed client-side after decryption; returns top-K doc IDs.
- **Concurrency**: Server uses a lock around index and document updates to prevent race conditions.

---

## Benchmarking

```bash
python benchmark.py
```

Measures upload time, search latency, and index size for 100, 1000, and 5000 documents (JSON and SQLite backends). Results are written to `benchmark_results.csv`.

---

## Testing the changes

### 1. Automated tests (unit + security)

From the project root:

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

This runs:

- **Judge Mode**: security-info endpoint, no secrets in responses, debug payload shape.
- **Vault security**: KDF, vault lock/unlock, file/filename encryption roundtrip, index sign/verify.

All tests should pass. No backend or frontend server is required.

### 2. Backend API (manual)

Start the backend:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Then (optional, no auth):

- **Health**: `curl http://localhost:8000/api/health` → `{"status":"ok"}`.
- **Security info**: `curl http://localhost:8000/api/security-info` → encryption/token algo, key size, leakage profile.

With auth (after signing in via the frontend, copy the JWT from DevTools → Application → Local Storage, or use the frontend):

- **Benchmark** (POST; requires auth): from the dashboard or  
  `curl -X POST http://localhost:8000/api/benchmark/run -H "Authorization: Bearer YOUR_JWT"`  
  → returns `benchmark_results` for 100, 1000, 5000 docs (upload time, token gen, search latency, index size).
- **Simulate server view** (GET; requires vault unlocked):  
  `curl "http://localhost:8000/api/simulate/server-view?q=invoice" -H "Authorization: Bearer YOUR_JWT"`  
  → returns only safe metadata: `search_token`, `matched_doc_ids`, `ciphertext_size`, `index_size` (no plaintext, no keys).

### 3. Full-stack (upload, search, list, filenames)

1. **Start backend** (port 8000) and **frontend** (`cd frontend && npm run dev`, port 5173).
2. **Sign in** with Google (ensure `VITE_GOOGLE_CLIENT_ID` and backend `GOOGLE_CLIENT_ID` are set).
3. **Create vault** (first time): set a password and confirm.
4. **Unlock vault** and stay on the dashboard.
5. **Upload**: choose one or more `.txt`/`.md`/`.csv` files. Confirm “Uploaded and encrypted” and that the list updates.
6. **Search**: type a word that appears in the uploaded files (e.g. “invoice”). Confirm results and that opening a document shows the correct decrypted content.
7. **List**: “Your documents” should show the same doc IDs; filenames are stored encrypted (new uploads) or as legacy plaintext; API returns either `encrypted_filename_payload` or `original_filename`.
8. **Judge Mode**: turn on “Judge Mode (Cryptographic Trace)”. Upload or search again; confirm the trace panels (client/server steps, security metrics, “What server sees”) and that no secret key or plaintext appears.

### 4. Filename encryption

- **New uploads**: With vault unlocked, filenames are encrypted before being stored; `doc_metadata.json` holds `encrypted_filename`, `filename_iv`, `filename_tag` (no plaintext).
- **List/encrypted-path**: API may return `encrypted_filename_payload`; the frontend can decrypt with the vault client-string key to display the original filename.
- **Legacy**: Old entries (plain string in metadata) still return `original_filename` for backward compatibility.

### 5. Index migration (JSON → SQLite)

- If a user already had `index.json`, the first request that creates their SSE client runs **migration**: data is copied into `index.db`, then `index.json` is renamed to `index.json.bak`.
- **Check**: Before migration, `backend/data/user_storage/<user_id>/index.json` exists. After one authenticated request (e.g. list or search), `index.db` exists and `index.json.bak` is present; search results stay the same.

### Quick checklist

| Check | How |
|-------|-----|
| Unit tests pass | `python -m pytest tests/ -v` |
| Upload works | Upload file in UI → see in “Your documents” |
| Search works | Search a keyword → see matching docs, open and read content |
| List works | “Your documents” and pagination load correctly |
| Judge Mode | Toggle on → upload/search show trace; no secrets in UI/network |
| Benchmark | Call `POST /api/benchmark/run` (auth) → JSON with timings and sizes |
| Simulate | Call `GET /api/simulate/server-view?q=...` (auth + vault) → only safe metadata |
| Filenames encrypted | New uploads → inspect `doc_metadata.json` (no plaintext filename) |
| Migration | Old user with `index.json` → after one request, `index.db` + `index.json.bak` |

---

## License

MIT (see LICENSE).
