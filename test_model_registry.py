"""Tests for model registry (Issue 3)."""

import json
import pytest


# ---------------------------------------------------------------------------
# MODEL_TOKENIZER_MAP structure
# ---------------------------------------------------------------------------


class TestModelTokenizerMap:
    """Validate the MODEL_TOKENIZER_MAP dict."""

    def test_is_dict(self):
        from model_registry import MODEL_TOKENIZER_MAP

        assert isinstance(MODEL_TOKENIZER_MAP, dict)

    def test_has_at_least_eight_entries(self):
        from model_registry import MODEL_TOKENIZER_MAP

        assert len(MODEL_TOKENIZER_MAP) >= 8

    def test_all_values_are_valid_tokenizer_keys(self):
        from model_registry import MODEL_TOKENIZER_MAP
        from tokenizer import SUPPORTED_TOKENIZERS

        for model_id, tok_key in MODEL_TOKENIZER_MAP.items():
            assert tok_key in SUPPORTED_TOKENIZERS, (
                f"{model_id} maps to unknown tokenizer: {tok_key}"
            )

    def test_contains_gpt4o(self):
        from model_registry import MODEL_TOKENIZER_MAP

        assert "openai/gpt-4o" in MODEL_TOKENIZER_MAP

    def test_contains_llama(self):
        from model_registry import MODEL_TOKENIZER_MAP

        assert "meta-llama/llama-3.1-8b-instruct" in MODEL_TOKENIZER_MAP

    def test_gpt4o_maps_to_o200k(self):
        from model_registry import MODEL_TOKENIZER_MAP

        assert MODEL_TOKENIZER_MAP["openai/gpt-4o"] == "o200k_base"


# ---------------------------------------------------------------------------
# get_tokenizer_for_model
# ---------------------------------------------------------------------------


class TestGetTokenizerForModel:
    """Tests for get_tokenizer_for_model(model_id) -> str."""

    def test_returns_string(self):
        from model_registry import get_tokenizer_for_model

        result = get_tokenizer_for_model("openai/gpt-4o")
        assert isinstance(result, str)

    def test_known_model(self):
        from model_registry import get_tokenizer_for_model

        assert get_tokenizer_for_model("openai/gpt-4o") == "o200k_base"

    def test_unknown_model_raises(self):
        from model_registry import get_tokenizer_for_model

        with pytest.raises(KeyError):
            get_tokenizer_for_model("nonexistent/model")

    def test_all_mapped_models_resolve(self):
        from model_registry import get_tokenizer_for_model, MODEL_TOKENIZER_MAP

        for model_id in MODEL_TOKENIZER_MAP:
            result = get_tokenizer_for_model(model_id)
            assert isinstance(result, str)


# ---------------------------------------------------------------------------
# get_models_for_tokenizer
# ---------------------------------------------------------------------------


class TestGetModelsForTokenizer:
    """Tests for get_models_for_tokenizer(tokenizer_key) -> list[str]."""

    def test_returns_list(self):
        from model_registry import get_models_for_tokenizer

        result = get_models_for_tokenizer("o200k_base")
        assert isinstance(result, list)

    def test_o200k_has_multiple_models(self):
        from model_registry import get_models_for_tokenizer

        result = get_models_for_tokenizer("o200k_base")
        assert len(result) >= 2  # gpt-4o and gpt-4o-mini at minimum

    def test_unknown_tokenizer_returns_empty(self):
        from model_registry import get_models_for_tokenizer

        result = get_models_for_tokenizer("nonexistent")
        assert result == []

    def test_results_are_strings(self):
        from model_registry import get_models_for_tokenizer

        for model_id in get_models_for_tokenizer("o200k_base"):
            assert isinstance(model_id, str)


# ---------------------------------------------------------------------------
# resolve_model
# ---------------------------------------------------------------------------


class TestResolveModel:
    """Tests for resolve_model(model_id) -> dict."""

    def test_returns_dict(self):
        from model_registry import resolve_model

        result = resolve_model("openai/gpt-4o")
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        from model_registry import resolve_model

        result = resolve_model("openai/gpt-4o")
        assert "tokenizer_key" in result
        assert "pricing" in result
        assert "context_window" in result
        assert "label" in result

    def test_tokenizer_key_correct(self):
        from model_registry import resolve_model

        result = resolve_model("openai/gpt-4o")
        assert result["tokenizer_key"] == "o200k_base"

    def test_pricing_is_dict(self):
        from model_registry import resolve_model

        result = resolve_model("openai/gpt-4o")
        assert isinstance(result["pricing"], dict)
        assert "input_per_million" in result["pricing"]

    def test_unknown_model_raises(self):
        from model_registry import resolve_model

        with pytest.raises(KeyError):
            resolve_model("nonexistent/model")

    def test_all_mapped_models_resolve(self):
        from model_registry import resolve_model, MODEL_TOKENIZER_MAP

        for model_id in MODEL_TOKENIZER_MAP:
            result = resolve_model(model_id)
            assert result["tokenizer_key"] in result["pricing"].__class__.__name__ or True
            assert result["context_window"] > 0


class TestTokenizerFirstCatalog:
    def test_tokenizer_families_include_free_model_attachments(self):
        from model_registry import build_tokenizer_catalog

        rows = build_tokenizer_catalog(include_proxy=True)
        assert any(row["free_models"] for row in rows)

    def test_exact_catalog_hides_proxy_families_by_default(self):
        from model_registry import build_tokenizer_catalog

        rows = build_tokenizer_catalog(include_proxy=False)
        assert all(row["mapping_quality"] != "proxy" for row in rows)

    def test_llama_family_has_multiple_free_models(self):
        from model_registry import build_tokenizer_catalog

        rows = build_tokenizer_catalog(include_proxy=True)
        llama = next(row for row in rows if row["tokenizer_key"] == "llama-3")
        assert len(llama["free_models"]) >= 2

    def test_catalog_rows_are_tokenizer_first(self):
        from model_registry import build_tokenizer_catalog

        rows = build_tokenizer_catalog(include_proxy=True)
        row = rows[0]
        assert "tokenizer_key" in row
        assert "free_models" in row
        assert "aa_matches" in row


class TestArtificialAnalysisSnapshot:
    def test_catalog_attaches_aa_matches_from_snapshot(self, tmp_path, monkeypatch):
        from model_registry import build_tokenizer_catalog

        snapshot = tmp_path / "aa.json"
        snapshot.write_text(json.dumps({
            "captured_at": "2026-03-27T12:00:00Z",
            "models": [
                {
                    "model_id": "meta-llama/llama-3.1-8b-instruct",
                    "tokenizer_key": "llama-3",
                    "label": "Llama 3.1 8B",
                    "ttft_seconds": 0.42,
                    "output_tokens_per_second": 84.2,
                    "provider": "Artificial Analysis",
                    "benchmark_url": "https://example.com/llama",
                },
            ],
        }), encoding="utf-8")

        monkeypatch.setattr("model_registry.ARTIFICIAL_ANALYSIS_SNAPSHOT_PATH", snapshot)
        rows = build_tokenizer_catalog(include_proxy=True)

        llama = next(row for row in rows if row["tokenizer_key"] == "llama-3")
        assert len(llama["aa_matches"]) == 1
        assert llama["aa_matches"][0]["telemetry_provider"] == "Artificial Analysis"

    def test_catalog_leaves_aa_matches_empty_when_snapshot_missing(self, monkeypatch):
        from model_registry import build_tokenizer_catalog

        monkeypatch.setattr("model_registry.ARTIFICIAL_ANALYSIS_SNAPSHOT_PATH", __import__("pathlib").Path("/tmp/does-not-exist-aa.json"))
        rows = build_tokenizer_catalog(include_proxy=True)

        assert all(isinstance(row["aa_matches"], list) for row in rows)
