#!/usr/bin/env python3
"""
CLI for Secured String Matching using Searchable Encryption.

Commands:
  init          Generate and save a new secret key
  upload <dir>  Encrypt and upload all .txt files from a directory
  search <q>    Search for keyword; print matching document IDs
  retrieve <id> Retrieve and decrypt a document by ID
  demo          Run demo with built-in sample documents
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from client import SSEClient
from server import SSEServer
from crypto import generate_key

KEY_FILE = Path("key.bin")
SERVER_STORAGE = Path("server_storage")


def load_key() -> bytes:
    if not KEY_FILE.exists():
        print("No key found. Run: python cli.py init", file=sys.stderr)
        sys.exit(1)
    return KEY_FILE.read_bytes()


def save_key(key: bytes) -> None:
    KEY_FILE.write_bytes(key)
    print("Key saved to", KEY_FILE)


def cmd_init(_: argparse.Namespace) -> None:
    key = generate_key()
    save_key(key)
    print("New SSE key generated. Use 'upload' and 'search' next.")


def cmd_upload(args: argparse.Namespace) -> None:
    key = load_key()
    server = SSEServer(storage_dir=SERVER_STORAGE)
    client = SSEClient(master_key=key, server=server)
    dir_path = Path(args.directory)
    if not dir_path.is_dir():
        print("Not a directory:", dir_path, file=sys.stderr)
        sys.exit(1)
    documents = []
    for f in sorted(dir_path.glob("*.txt")):
        doc_id = f.stem
        plaintext = f.read_bytes()
        documents.append((doc_id, plaintext))
    if not documents:
        print("No .txt files in", dir_path, file=sys.stderr)
        sys.exit(1)
    client.upload_documents(documents)
    print("Uploaded", len(documents), "document(s):", [d[0] for d in documents])


def cmd_search(args: argparse.Namespace) -> None:
    key = load_key()
    server = SSEServer(storage_dir=SERVER_STORAGE)
    client = SSEClient(master_key=key, server=server)
    doc_ids = client.search(args.query)
    print("Query:", args.query)
    print("Matches:", len(doc_ids))
    for doc_id in doc_ids:
        print(" -", doc_id)


def cmd_retrieve(args: argparse.Namespace) -> None:
    key = load_key()
    server = SSEServer(storage_dir=SERVER_STORAGE)
    client = SSEClient(master_key=key, server=server)
    plaintext = client.retrieve_and_decrypt(args.doc_id)
    if plaintext is None:
        print("Document not found:", args.doc_id, file=sys.stderr)
        sys.exit(1)
    sys.stdout.buffer.write(plaintext)


def cmd_demo(_: argparse.Namespace) -> None:
    """Run a self-contained demo with sample documents (no key file required)."""
    sample_dir = Path(__file__).parent / "data" / "sample_docs"
    if not sample_dir.exists():
        print("Sample data not found at", sample_dir, file=sys.stderr)
        sys.exit(1)
    key = generate_key()
    server = SSEServer(storage_dir=SERVER_STORAGE)
    client = SSEClient(master_key=key, server=server)
    documents = []
    for f in sorted(sample_dir.glob("*.txt")):
        documents.append((f.stem, f.read_bytes()))
    client.upload_documents(documents)
    print("Demo: uploaded", len(documents), "sample documents.")
    print("\nSearching for 'invoice'...")
    ids = client.search("invoice")
    print("Matches:", ids)
    print("\nSearching for 'confidential'...")
    ids2 = client.search("confidential")
    print("Matches:", ids2)
    if ids:
        print("\nRetrieving first match and showing first 200 bytes:")
        pt = client.retrieve_and_decrypt(ids[0])
        if pt:
            print(pt[:200].decode("utf-8", errors="replace"), "...")
    print("\nDemo done.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Secured String Matching using Searchable Encryption"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Generate and save a new secret key")
    p_upload = sub.add_parser("upload", help="Upload .txt files from a directory")
    p_upload.add_argument("directory", help="Directory containing .txt files")
    p_search = sub.add_parser("search", help="Search for a keyword")
    p_search.add_argument("query", help="Search keyword")
    p_retrieve = sub.add_parser("retrieve", help="Retrieve and decrypt a document")
    p_retrieve.add_argument("doc_id", help="Document ID")
    sub.add_parser("demo", help="Run demo with sample documents")
    args = parser.parse_args()
    if args.command == "init":
        cmd_init(args)
    elif args.command == "upload":
        cmd_upload(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "retrieve":
        cmd_retrieve(args)
    elif args.command == "demo":
        cmd_demo(args)


if __name__ == "__main__":
    main()
