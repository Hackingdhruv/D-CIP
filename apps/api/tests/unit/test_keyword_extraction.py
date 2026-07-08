"""Unit tests for keyword extraction service."""

from __future__ import annotations

import pytest

from app.services.keyword_extraction import extract_keywords


class TestKeywordExtraction:
    def test_returns_keywords_from_text(self) -> None:
        text = "The investigation revealed financial fraud involving multiple transactions."
        keywords = extract_keywords(text, max_keywords=10)
        assert len(keywords) > 0
        terms = [k.keyword for k in keywords]
        # Common meaningful words should appear
        assert any("investigation" in t or "financial" in t or "fraud" in t for t in terms)

    def test_excludes_stopwords(self) -> None:
        text = "The and or but in on at to for of with by"
        keywords = extract_keywords(text, max_keywords=20)
        stop_words = {"the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        for kw in keywords:
            assert kw.keyword not in stop_words

    def test_max_keywords_respected(self) -> None:
        text = " ".join(f"term{i}" for i in range(100))
        keywords = extract_keywords(text, max_keywords=10)
        assert len(keywords) <= 10

    def test_scores_are_positive(self) -> None:
        text = "evidence financial transaction criminal investigation suspect"
        keywords = extract_keywords(text)
        for kw in keywords:
            assert kw.score >= 0

    def test_empty_text_returns_empty(self) -> None:
        assert extract_keywords("") == []
        assert extract_keywords("   ") == []

    def test_repeated_terms_score_higher(self) -> None:
        text = "fraud fraud fraud fraud other term"
        keywords = extract_keywords(text, max_keywords=10)
        terms = [k.keyword for k in keywords]
        # "fraud" (or its bigram "fraud fraud") must appear in top results
        assert any("fraud" in t for t in terms[:3])
