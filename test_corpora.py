"""Tests for corpora.py — corpus registry and local snapshot loading."""

import json
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from corpora import fetch_strict_parallel_samples, list_corpora, get_corpus


class TestFetchStrictParallelSamplesResilience:
    """Strict benchmark samples should load locally and degrade clearly."""

    def test_reads_local_snapshot_without_network(self, tmp_path):
        from corpora import fetch_strict_parallel_samples

        snapshot = tmp_path / "flores_v1.jsonl"
        rows = [
            {
                "language": "en",
                "text": "Hello world",
                "english_text": "Hello world",
                "corpus_key": "strict_parallel",
                "source_id": "flores:test:en:1",
                "provenance": "strict_verified",
            },
            {
                "language": "ar",
                "text": "مرحبا بالعالم",
                "english_text": "Hello world",
                "corpus_key": "strict_parallel",
                "source_id": "flores:test:ar:1",
                "provenance": "strict_verified",
            },
        ]
        snapshot.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")

        with patch("corpora.STRICT_PARALLEL_SNAPSHOT_PATH", snapshot):
            with patch("corpora._fetch_first_rows", side_effect=AssertionError("network should not be used")):
                result = fetch_strict_parallel_samples(["en", "ar"])

        assert len(result["en"]) == 1
        assert result["ar"][0].text == "مرحبا بالعالم"

    def test_network_failure_returns_empty_not_raises(self):
        """When snapshot is unavailable and network fails, language is omitted — no raise."""
        with patch("corpora.STRICT_PARALLEL_SNAPSHOT_PATH", Path("/tmp/does-not-exist.jsonl")):
            with patch("corpora._fetch_first_rows", side_effect=Exception("network error")):
                result = fetch_strict_parallel_samples(["ar"])
        assert isinstance(result, dict)
        assert result.get("ar", []) == []

    def test_missing_snapshot_and_network_failure_can_still_signal_upstream_empty(self):
        from token_tax import benchmark_corpus

        with patch("corpora.STRICT_PARALLEL_SNAPSHOT_PATH", Path("/tmp/does-not-exist.jsonl")):
            with patch("corpora._fetch_first_rows", side_effect=Exception("network error")):
                with pytest.raises(RuntimeError, match="No benchmark rows were produced"):
                    benchmark_corpus("strict_parallel", ["ar"], ["gpt2"])

    def test_partial_failure_preserves_successful_languages(self):
        """If one language succeeds and another fails, successful one is kept."""
        def _mock_fetch(dataset_id, config, split):
            if "ar" in config:
                raise Exception("network error")
            # Return a valid row for French
            return [{"fr": "Bonjour le monde", "en": "Hello world"}]

        with patch("corpora.STRICT_PARALLEL_SNAPSHOT_PATH", Path("/tmp/does-not-exist.jsonl")):
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

    def test_streaming_exploration_corpus_is_registered(self):
        result = list_corpora()
        keys = {entry["key"] for entry in result}
        assert "streaming_exploration" in keys


class TestGetCorpus:
    """Tests for get_corpus lookup."""

    def test_known_corpus(self):
        corpus = get_corpus("strict_parallel")
        assert corpus.key == "strict_parallel"

    def test_unknown_corpus_raises(self):
        with pytest.raises(KeyError, match="unknown corpus"):
            get_corpus("nonexistent")


class TestStreamingExplorationSamples:
    def test_streaming_fetch_uses_remote_rows(self):
        from corpora import fetch_corpus_samples

        with patch("corpora._fetch_streaming_rows", return_value={
            "fr": [
                {"text": "Bonjour le monde", "english_text": "Hello world"},
            ],
        }):
            result = fetch_corpus_samples("streaming_exploration", ["fr"], row_limit=5)

        assert "fr" in result
        assert result["fr"][0].text == "Bonjour le monde"

    def test_streaming_fetch_raises_clear_error_when_remote_fails(self):
        from corpora import fetch_corpus_samples

        with patch("corpora._fetch_streaming_rows", side_effect=RuntimeError("stream unavailable")):
            with pytest.raises(RuntimeError, match="Streaming exploration fetch failed"):
                fetch_corpus_samples("streaming_exploration", ["fr"], row_limit=5)
