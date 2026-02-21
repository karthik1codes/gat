"""
Phonetic encoding for fuzzy search.

- Soundex: 4-character code for words that sound similar.
- Used to build encrypted phonetic index; search returns candidates, then
  client-side edit-distance verification.
"""

from typing import List, Set

# Soundex digit mapping: A=0, B=1, C=2, ... (index by ord(c)-ord('A'))
_SOUNDEX_DIGITS = "01230120022455012623010202"


def soundex(word: str, length: int = 4) -> str:
    """
    Soundex encoding: first letter + 3 digits from consonants.
    Similar-sounding words get the same code.
    """
    if not word or not word.isalpha():
        return ""
    word = word.upper()
    first = word[0]
    code = first
    for c in word[1:]:
        idx = ord(c) - ord("A")
        if idx < 0 or idx >= 26:
            continue
        d = _SOUNDEX_DIGITS[idx]
        if d == "0":
            continue
        if code and code[-1] == d:
            continue
        code += d
    code = code.replace("0", "")
    code = (code + "0" * length)[:length]
    return code


def soundex_words(text: str) -> Set[str]:
    """Soundex codes for all words in text (lowercased words)."""
    words = text.lower().split()
    return {soundex(w) for w in words if soundex(w)}


def levenshtein_distance(a: str, b: str) -> int:
    """
    Edit distance (Levenshtein) between two strings.
    Used client-side only to verify fuzzy matches; never sent to server.
    """
    if len(a) < len(b):
        a, b = b, a
    n, m = len(a), len(b)
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        curr = [i]
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[m]
