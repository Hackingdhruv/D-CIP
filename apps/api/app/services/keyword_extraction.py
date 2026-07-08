"""Keyword extraction — frequency-based relevance scoring, no external models.

Uses a modified TF weighting with positional bias: terms in the first quarter
of the document are scored higher than terms that appear only at the end.
"""

from __future__ import annotations

import re
import math
from dataclasses import dataclass
from collections import Counter

_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "up", "about", "into", "through", "during",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "shall", "can", "need", "dare", "ought", "used", "that", "which", "who",
    "this", "these", "those", "it", "its", "we", "our", "they", "their",
    "he", "she", "him", "her", "his", "my", "your", "your", "i", "me",
    "not", "no", "nor", "so", "yet", "if", "then", "than", "as", "well",
    "also", "just", "more", "most", "other", "some", "such", "only", "own",
    "same", "too", "very", "any", "each", "all", "both", "few", "more",
    "most", "other", "into", "over", "after", "before", "between", "under",
    "again", "further", "once", "here", "there", "when", "where", "why",
    "how", "what", "which", "who", "whom", "re", "s", "t", "don", "ve",
    "ll", "m", "d", "wasn", "isn", "didn", "doesn", "couldn", "wouldn",
    "haven", "hasn", "hadn", "won", "mustn", "shan",
})


@dataclass
class ExtractedKeyword:
    keyword: str
    score: float


def extract_keywords(text: str, max_keywords: int = 30) -> list[ExtractedKeyword]:
    """Return the top *max_keywords* keywords ranked by relevance score."""
    if not text or not text.strip():
        return []

    tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_\-]{2,}\b", text)
    tokens_lower = [t.lower() for t in tokens]
    total = len(tokens_lower)
    if total == 0:
        return []

    # Term frequency
    tf = Counter(t for t in tokens_lower if t not in _STOP_WORDS)

    # Positional boost: terms appearing in first 25% score higher
    first_quarter_end = total // 4
    first_quarter_tokens = set(tokens_lower[:first_quarter_end])

    scored: dict[str, float] = {}
    for term, count in tf.items():
        if len(term) < 3:
            continue
        freq_score = count / total
        # Log-scale to prevent very common words dominating
        tf_score = math.log1p(count) / math.log1p(total)
        pos_boost = 1.3 if term in first_quarter_tokens else 1.0
        scored[term] = tf_score * pos_boost * freq_score * 1000

    sorted_terms = sorted(scored.items(), key=lambda x: x[1], reverse=True)

    # Prefer multi-word phrases: scan bigrams
    bigram_tf = Counter(
        f"{tokens_lower[i]} {tokens_lower[i+1]}"
        for i in range(len(tokens_lower) - 1)
        if tokens_lower[i] not in _STOP_WORDS and tokens_lower[i+1] not in _STOP_WORDS
    )
    for phrase, count in bigram_tf.most_common(10):
        if count >= 2:
            phrase_score = math.log1p(count) / math.log1p(total) * 1500
            sorted_terms.append((phrase, phrase_score))

    # Final deduplicated top-N
    seen: set[str] = set()
    results: list[ExtractedKeyword] = []
    for term, score in sorted(sorted_terms, key=lambda x: x[1], reverse=True):
        if term not in seen:
            seen.add(term)
            results.append(ExtractedKeyword(keyword=term, score=round(score, 4)))
        if len(results) >= max_keywords:
            break

    return results
