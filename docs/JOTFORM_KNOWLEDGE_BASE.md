# CIPHER Agent – Knowledge Base

Use this document in Jotform TRAIN → **KNOWLEDGE** (paste the text) or **FILE** (upload this file).

---

## What This Website Is

This is a **searchable encryption** web app. Users upload documents that are encrypted in the browser. They can search by keyword without the server ever seeing document contents or search queries. The server stores only ciphertexts and an encrypted index; search uses opaque tokens (trapdoors), so the server cannot read plaintext.

## How It Works (Simple)

1. **Upload**: The client (your browser) encrypts each document with AES-256-GCM and extracts keywords. For each keyword it computes a search token (trapdoor) and adds the document ID to the index under that token. Only encrypted documents and the index are sent to the server.
2. **Search**: You type a keyword. The client turns it into a search token and sends only that token. The server looks up the token in the index and returns matching document IDs. The server never sees the keyword.
3. **View**: You request a document by ID. The server sends the ciphertext; the client decrypts it with your key. Only you can read the content.

## Cryptography

- **Document encryption**: AES-256-GCM, random IV per document.
- **Keys**: Derived on the client with HKDF into K_enc (encryption), K_search (trapdoors), K_index (index). The server never stores or sees key material.
- **Search tokens**: HMAC-SHA256; same keyword always gives the same token (deterministic). Server uses constant-time comparison to avoid timing leaks.
- **Optional vault**: Password-based unlock; keys only in memory when unlocked; lock clears keys. Protects files, filenames, and index integrity.

## What the Server Sees vs. Does Not See

**Server sees:** Encrypted documents (ciphertexts), index (trapdoor → list of doc IDs), search tokens (opaque), which document IDs are returned for each search, result set sizes, ciphertext lengths.

**Server does NOT see:** Plaintext documents, plaintext keywords, your search query text, or any key material. Without your key, the server cannot decrypt or infer what you searched for.

## Leakage (What Can Be Inferred)

- **Search pattern**: Same keyword → same token, so the server can tell when two searches are for the same keyword.
- **Access pattern**: The server sees which document IDs are returned for each search.
- **Volume**: Number of documents, index size, result sizes (unless padding is used).
- **Ciphertext size**: Length of each encrypted file (padding to hide this is planned).

Mitigations: Padded responses (fixed-size results with dummy IDs), forward-private SSE (planned), document padding (planned).

## Attacks We Discuss

- **Frequency attack**: Server may use result sizes and language statistics to guess which tokens correspond to which keywords. Mitigation: padding, forward privacy.
- **Dictionary attack**: If someone learns one keyword–token pair, they can recognize all searches for that keyword. Mitigation: forward privacy, constant-time comparison, keeping the key secret.
- **File injection attack**: A malicious server could inject documents and infer keywords. **Our assumption**: Only the client uploads data; the server does not inject. Access control limits who can write.
- **Access pattern inference**: Server sees which docs match each search; over time it can infer keyword–document links. Mitigation: padded responses, dummy IDs, forward privacy (partial or planned).

## Web App Features

- **Sign-in**: Google OAuth. Your data is tied to your account; keys are isolated per user.
- **Dashboard**: Upload files (.txt, .md, .csv), search (keyword, substring, fuzzy, or ranked), view and delete documents, open decrypted content.
- **Privacy & threat model**: Link on the dashboard to the full threat model document.
- **Attack discussion**: Collapsible section on the dashboard summarizing frequency, dictionary, file injection, and access pattern inference.
- **Judge Mode**: When on, upload and search show safe trace metadata (algorithm names, token hashes, no secrets) so you can see how the system works. Security info shows encryption algorithm, token generation, key size, and leakage profile (search pattern, access pattern, content leakage).
- **Performance & scaling**: "Run benchmark" runs tests on 100, 1000, and 5000 documents and shows encryption time, search time, index size, and a scaling summary (e.g. encryption ms per doc, search latency at 5000 docs, index bytes per doc) so you see the system scales.

## Trust and Assumptions

- The server is **honest-but-curious**: it runs the protocol correctly but may try to learn from ciphertexts and query patterns.
- Security depends on **your key** staying secret. The client never sends the key to the server.
- We do not claim formal security proofs; the design is documented for transparency and evaluation.
