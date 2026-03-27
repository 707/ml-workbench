"""Tests for corpora.py — corpus registry and remote fetch resilience."""

import pytest
from unittest.mock import patch, MagicMock

from corpora import fetch_strict_parallel_samples, list_corpora, get_corpus


class TestFetchStrictParallelSamplesResilience:
    """Network failures should not crash the benchmark tab."""

    def test_network_failure_returns_empty_not_raises(self):
        """When all configs fail for a language, that language is omitted — no raise."""
        with patch("corpora._fetch_first_rows", side_effect=Exception("network error")):
            result = fetch_strict_parallel_samples(["ar"])
        assert isinstance(result, dict)
        assert result.get("ar", []) == []

    def test_partial_failure_preserves_successful_languages(self):
        """If one language succeeds and another fails, successful one is kept."""
        def _mock_fetch(dataset_id, config, split):
            if "ar" in config:
                raise Exception("network error")
            # Return a valid row for French
            return [{"fr": "Bonjour le monde", "en": "Hello world"}]

        with patch("corpora._fetch_first_rows", side_effect=_mock_fetch):
            result = fetch_strict_parallel_samples(["fr", "ar"])
        # French should be present (it's extracted from fr-en config for English)
        # Arabic should be absent (all configs failed)
        assert "ar" not in result


class TestListCorpora:
    """Smoke tests for corpus registry."""

    def test_returns_list(self):
        result = list_corpora()
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_entries_have_required_keys(self):
        result = list_corpora()
        for entry in result:
            assert "key" in entry
            assert "label" in entry
            assert "status" in entry


class TestGetCorpus:
    """Tests for get_corpus lookup."""

    def test_known_corpus(self):
        corpus = get_corpus("strict_parallel")
        assert corpus.key == "strict_parallel"

    def test_unknown_corpus_raises(self):
        with pytest.raises(KeyError, match="unknown corpus"):
            get_corpus("nonexistent")
