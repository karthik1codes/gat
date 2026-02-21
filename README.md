# Secured String Matching using Searchable Encryption

A secure system that enables **string matching on encrypted data** while preserving data confidentiality and privacy. The server stores only ciphertexts and an encrypted index; search is performed using **search tokens** (trapdoors) so the server never sees plaintext data or search queries.

## Features

- **Document encryption**: AES-256-GCM for document contents
- **Searchable index**: Inverted index mapping (encrypted) keywords to document IDs; trapdoors via HMAC-SHA256
- **Exact keyword search**: Generate a search token for a query; server returns matching document IDs without seeing the query or document contents
- **Client/Server split**: Client holds the secret key; server stores encrypted data and index and performs matching

## Project structure

```
gat/
├── crypto/           # SSE primitives: key gen, encrypt/decrypt, trapdoor
│   ├── __init__.py
│   └── sse.py
├── client/           # Data owner: encrypt, build index, search token, decrypt
│   ├── __init__.py
│   └── client.py
├── server/           # Untrusted server: store index + docs, match token → doc IDs
│   ├── __init__.py
│   └── server.py
├── data/
│   └── sample_docs/  # Sample .txt documents for demo
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

## Security notes

- **Confidentiality**: Document contents and keywords are encrypted or replaced by trapdoors.
- **Query privacy**: The server sees only the search token, not the actual query string.
- This implementation does **not** hide the **access pattern** (which documents matched a query); hiding access patterns requires additional techniques (e.g. ORAM) and is out of scope for this project.

## License

MIT (see LICENSE).
