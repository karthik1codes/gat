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
| **Volume** | Number of documents, number of index entries, size of result sets. | Padded search (`pad_to` parameter) returns fixed-size response; client filters to real doc IDs. |
| **Ciphertext size** | Length of each stored ciphertext. | **Document padding**: pad plaintext to fixed block sizes before encryption to hide exact length (future work). |

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

The following attacks are relevant to SSE. We discuss how they apply to this system and what mitigations exist or are planned.

### 4.1 Frequency attack

- **Idea**: The server observes result-set sizes and co-occurrence of trapdoors across documents. If it knows corpus or language statistics (e.g. word frequency), it can try to map trapdoors to likely keywords by matching observed result sizes to expected keyword frequencies.
- **In this system**: Same keyword always yields the same trapdoor, so the server sees a stable “result size” per trapdoor. That can be compared to known statistics to guess keywords.
- **Mitigation**: Forward-private schemes and response padding (dummy results, fixed response sizes) reduce the utility of frequency analysis. Document and query padding are planned.

### 4.2 Dictionary attack

- **Idea**: The attacker has a list of candidate keywords (a dictionary). If they learn that a specific trapdoor corresponds to one of these keywords (e.g. via client compromise, side channel, or frequency matching), they can identify all past and future searches for that keyword.
- **In this system**: Trapdoors are deterministic (same keyword → same token), so one revealed keyword-trapdoor pair exposes every search for that keyword.
- **Mitigation**: Forward privacy prevents linking new insertions to past trapdoors. Constant-time comparison on the server avoids timing side channels on token matching. Keeping the key and client environment secure limits how often keyword–trapdoor pairs can be learned.

### 4.3 File injection attack

- **Idea**: A malicious server (or an attacker who can cause documents to be indexed) injects chosen documents, then observes which future search tokens return those documents. By choosing documents with known keywords, the attacker infers which trapdoors correspond to which keywords.
- **In this system**: We assume **the server does not inject data**; only the client uploads documents and index entries. The server is honest-but-curious, not active in writing data. In multi-tenant deployments, access control and authentication restrict who can write to which partition, limiting injection to the data owner’s own uploads.
- **If injection were possible**: Mitigations would require forward privacy and/or client-side checks that only the data owner’s intended documents are indexed.

### 4.4 Access pattern inference

- **Idea**: For each search, the server sees which document IDs are returned (the access pattern). Over many queries and updates, it can infer which documents contain which (trapdoor) keywords and build a partial or full recovery of the index layout.
- **In this system**: The server sees every (trapdoor, set of document IDs) pair. Repeated searches and correlation over time allow inference of keyword–document relationships.
- **Mitigation**: Padded responses and dummy document IDs (e.g. `pad_to` in search) hide the true result size and add noise. Forward privacy reduces linkability between updates and queries. These are planned or partial; full mitigation of access-pattern inference is an active research topic.

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
