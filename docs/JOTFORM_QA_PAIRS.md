# CIPHER Agent – Questions & Answers

Use these in Jotform TRAIN → **QUESTIONS & ANSWER**. Add each pair as one Q and one A in the builder.

---

## Q: Can the server read my documents?
**A:** No. Documents are encrypted on your device with AES-256-GCM. The server only stores ciphertext. Without your key, the server cannot decrypt or read your documents.

## Q: Can the server see what I search for?
**A:** No. Your search query is turned into an opaque search token (trapdoor) on your device. The server only sees that token and returns matching document IDs. It never sees the keyword or query text.

## Q: How does encryption work on this site?
**A:** When you upload a file, your browser encrypts it with AES-256-GCM using a key that never leaves your device. Keywords are extracted and turned into search tokens (HMAC). The server stores only the encrypted file and an index that maps tokens to document IDs. Your key is derived client-side and is not sent to the server.

## Q: Where are my keys stored?
**A:** Keys are derived on the client (your browser) and are not stored on the server. If the app has a vault, keys exist only in memory when the vault is unlocked and are cleared when you lock. The server never receives or stores key material.

## Q: What does the server see when I search?
**A:** The server sees an opaque search token (the same token every time for the same keyword) and the list of document IDs that match. It does not see your search keyword, document contents, or your key.

## Q: What is search pattern leakage?
**A:** Because the same keyword always produces the same token, the server can tell when two searches are for the same keyword. It cannot see the keyword itself. Mitigations like forward-private SSE and padding are planned or in progress.

## Q: What is access pattern leakage?
**A:** The server sees which document IDs are returned for each search. Over many searches it could infer which documents contain which (unknown) keywords. We use or plan padded responses and dummy IDs to reduce this.

## Q: What is a frequency attack?
**A:** The server could use the size of result sets and language statistics to guess which tokens correspond to which keywords (e.g. common words vs rare ones). We address this with response padding and forward privacy where possible.

## Q: What is a dictionary attack?
**A:** If an attacker learns that a specific token corresponds to a known keyword, they can recognize all searches for that keyword (trapdoors are deterministic). We mitigate with forward privacy, constant-time comparison, and keeping the key secure.

## Q: What is a file injection attack?
**A:** A malicious server could inject its own documents and see which searches return them, to infer keywords. We assume only the client uploads data; the server does not inject. Access control limits who can write.

## Q: What is access pattern inference?
**A:** By observing which document IDs are returned for each search over time, the server could infer which documents contain which keywords. Padded responses and forward privacy help reduce this.

## Q: How can I see that the system scales?
**A:** On the Dashboard, open the "Performance & scaling" section and click "Run benchmark." It runs tests on 100, 1000, and 5000 documents and shows encryption time, search time, index size, and a scaling summary (e.g. ms per doc, search latency at 5000 docs). This shows the system scales, not just that it works.

## Q: What is Judge Mode?
**A:** Judge Mode is a transparency feature. When you turn it on, upload and search responses include safe trace metadata (e.g. algorithm names, token hashes)—no secrets. You can see how encryption and search work. Security info shows encryption algorithm, token generation, key size, and leakage profile.

## Q: What file types can I upload?
**A:** The web app typically accepts .txt, .md, and .csv. Files are encrypted and indexed by keyword on your device before being sent to the server.

## Q: How do I know my data is safe?
**A:** Your documents are encrypted with AES-256-GCM before they leave your device. The server stores only ciphertext and an index of opaque tokens. It never sees plaintext or your key. We document what does leak (e.g. search pattern, access pattern) and our mitigations in the Privacy & threat model page.

## Q: What is the vault?
**A:** The vault is an optional layer that protects your keys with a password. Keys are derived from your password and exist only in memory when the vault is unlocked. When you lock, keys are cleared. The server never stores keys in plaintext.

## Q: Who can access my documents?
**A:** Only you. You sign in (e.g. with Google); your keys and data are isolated per account. The server cannot decrypt your documents without your key, which it never has.

## Q: Does the server store my password or key?
**A:** No. Keys are derived on the client and never sent to the server. If you use a vault, the password is used only on your device to unlock the key; the server does not receive or store the password or key.

## Q: What encryption is used?
**A:** Document contents use AES-256-GCM with a random IV per document. Search tokens use HMAC-SHA256. Keys are derived with HKDF. Key size is 256 bits.

## Q: Can I search by partial word or fuzzy spelling?
**A:** Yes. The dashboard supports keyword (exact), substring, fuzzy, and ranked search. The server still only sees opaque tokens; matching is done on the server using the encrypted index.

## Q: Where can I read the full threat model?
**A:** On the dashboard there is a link to "Privacy & threat model" that opens the full threat model document. It covers assumptions, leakage, attack discussion (frequency, dictionary, file injection, access pattern), and mitigations.
