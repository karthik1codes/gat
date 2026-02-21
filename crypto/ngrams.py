"""
N-gram tokenization for substring search.

- Configurable n (default 3); character n-grams from text.
- Used to build encrypted n-gram index and to generate search tokens for substring queries.
"""

from typing import List, Set


def extract_ngrams(text: str, n: int = 3) -> List[str]:
    """
    Extract character n-grams from text. Normalized to lowercase.
    Returns list (with duplicates) for frequency if needed; for index use set.
    """
    text = text.lower().strip()
    if len(text) < n:
        return [text] if text else []
    return [text[i : i + n] for i in range(len(text) - n + 1)]


def extract_ngrams_unique(text: str, n: int = 3) -> Set[str]:
    """Unique n-grams from text. Use for index keys and search token set."""
    return set(extract_ngrams(text, n))
