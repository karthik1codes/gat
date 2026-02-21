# Threat Model: Secure Searchable Encryption System

## 1. System Assumptions

- **Client (data owner / user)** is trusted and has secure storage for the master key. The client never exposes the key to the server or the network.
- **Server** provides storage and search over encrypted data. The server is *honest-but-curious*: it follows the protocol but may try to learn information from stored data and query patterns.
- **Network** between client and server may be observed by a *passive attacker* (e.g. eavesdropping). We do not assume an active man-in-the-middle; TLS is recommended in production.
- **Cryptographic primitives** (AES-256-GCM, HMAC-SHA256, HKDF) are assumed secure. Randomness is from the OS CSPRNG (`os.urandom` / equivalent).

---

## 2. Adversary Model

### 2.1 Honest-but-Curious Server

The server correctly executes:

- Storing ciphertexts and the encrypted index.
- Answering search queries by matching trapdoors to index entries and returning document identifiers.
- Returning encrypted documents by ID.

The server may:

- Observe all stored ciphertexts and index entries (trapdoor → document ID list).
- Observe all search tokens (trapdoors) and the document IDs returned for each search.
- Correlate queries over time and with updates.

The server does **not**:

- Tamper with or drop data (beyond what we consider under "Availability").
- Inject forged documents or index entries (we assume the client is the only writer for its data).

### 2.2 Passive Network Attacker

An attacker can observe all traffic between client and server (e.g. before TLS or on a compromised link). They see:

- Encrypted document uploads.
- Index updates (opaque trapdoor keys and document ID lists).
- Search tokens (opaque) and returned document ID lists.

They cannot decrypt data or tokens without the client’s key.

---

## 3. Leakage Profile

### 3.1 What Leaks (to the server)

| Leakage | Description | Mitigation / note |
|--------|-------------|--------------------|
| **Search pattern** | Same keyword → same trapdoor → server learns that two searches are for the same keyword. | Mitigated by **forward-private SSE**: per-keyword counter; tokens include counter so server cannot link past searches to future insertions. Optional client methods `upload_documents_forward_secure` / `search_forward_secure`. |
| **Access pattern** | For each search, the server sees which document IDs were returned. | **Padded response**: server returns fixed-size list (pad_to) with dummy doc IDs and shuffle; client filters to known doc IDs. |
| **Volume** | Number of documents, number of index entries, size of result sets. | Padding and fixed-size responses (future work). |
| **Ciphertext size** | Length of each stored ciphertext. | Padding to fixed block sizes (future work). |

### 3.2 What Does Not Leak (under our assumptions)

- **Document plaintext**: Recovered only with the client’s key.
- **Keyword plaintext**: Queries and index keys are trapdoors; recovery without the key is assumed infeasible.
- **Key material**: Keys are derived client-side; only a key identifier (e.g. hash) may be used server-side for partitioning. The server never stores keys.

### 3.3 Assumptions

- **Key secrecy**: Security depends on the master key (and any derived keys) remaining secret. Compromise of the key allows decryption and generation of valid trapdoors.
- **Deterministic trapdoors**: Current design uses deterministic trapdoors (same keyword → same token). This is intentional for correctness but causes search-pattern leakage; forward privacy is a separate upgrade.
- **No server-side plaintext**: The server never sees plaintext documents or plaintext keywords; matching is on trapdoors only.

---

## 4. Attack Discussion

### 4.1 Frequency / Statistical Attacks

- **Keyword frequency**: If the server knows the underlying language or corpus statistics, it may try to map trapdoors to likely keywords by comparing result-set sizes or co-occurrence patterns.
- **Mitigation**: Forward-private schemes and padding (dummy results, fixed response sizes) reduce the utility of such analysis. Document and query padding are planned.

### 4.2 Known-Keyword Attacks

- If an attacker learns that a specific trapdoor corresponds to a known keyword (e.g. by client compromise or side channel), they can identify all searches for that keyword.
- **Mitigation**: Forward privacy ensures new insertions cannot be linked to past trapdoors; constant-time comparison prevents timing side channels on token matching.

### 4.3 File Injection Attacks

- A malicious server could try to inject chosen documents and observe whether future searches match them, to infer keywords.
- **Assumption**: We assume the server does not inject data; only the client uploads documents and index entries. In a multi-tenant setting, access control and authentication limit who can write to which partition.

### 4.4 Access Pattern Attacks

- Repeated searches and updates reveal which documents contain which (trapdoor) keywords. Over time, this can support inference.
- **Mitigation**: Padded responses and dummy document IDs, plus forward privacy, reduce linkability and are part of the planned upgrades.

---

## 5. Mitigation Summary

| Threat | Current mitigation | Planned |
|--------|--------------------|--------|
| Key compromise | Keys only on client; HKDF separation (K_enc, K_search, K_index) limits blast radius. | — |
| Timing on token match | Constant-time comparison in server search. | — |
| Search pattern leakage | — | Forward-private SSE. |
| Access pattern leakage | — | Padded responses, dummies. |
| Statistical/frequency | — | Padding, forward privacy. |

---

## 6. Scope and Limitations

- This document applies to the core SSE construction (key derivation, encryption, trapdoor generation, and server-side matching).
- Authentication, authorization, and transport security (TLS) are out of scope here but required in production.
- Formal security proofs are not claimed; the description is intended for design and evaluation (e.g. internship-level review).
