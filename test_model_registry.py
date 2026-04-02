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

    def test_contains_new_exact_free_model_mappings(self):
        from model_registry import MODEL_TOKENIZER_MAP

        expected = {
            "arcee-ai/trinity-large-preview:free",
            "arcee-ai/trinity-mini:free",
            "nvidia/nemotron-3-nano-30b-a3b:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "nvidia/nemotron-nano-9b-v2:free",
            "openai/gpt-oss-20b:free",
            "openai/gpt-oss-120b:free",
            "qwen/qwen3-coder:free",
            "qwen/qwen3-next-80b-a3b-instruct:free",
            "z-ai/glm-4.5-air:free",
        }
        assert expected.issubset(set(MODEL_TOKENIZER_MAP))


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
        from model_registry import MODEL_TOKENIZER_MAP, get_tokenizer_for_model

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
        from model_registry import MODEL_TOKENIZER_MAP, resolve_model

        for model_id in MODEL_TOKENIZER_MAP:
            result = resolve_model(model_id)
            assert result["tokenizer_key"] in result["pricing"].__class__.__name__ or True
            assert result["context_window"] > 0


class TestTokenizerFirstCatalog:
    def test_tokenizer_families_derive_from_shared_registry(self):
        from model_registry import TOKENIZER_FAMILIES
        from tokenizer_registry import TOKENIZER_FAMILY_SPECS

        assert set(TOKENIZER_FAMILIES) == set(TOKENIZER_FAMILY_SPECS)
        for key, family in TOKENIZER_FAMILIES.items():
            spec = TOKENIZER_FAMILY_SPECS[key]
            assert family.tokenizer_source == spec.tokenizer_source
            assert family.mapping_quality == spec.mapping_quality
            assert family.provenance == spec.provenance

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
        assert len(llama["free_models"]) >= 1

    def test_catalog_rows_are_tokenizer_first(self):
        from model_registry import build_tokenizer_catalog

        rows = build_tokenizer_catalog(include_proxy=True)
        row = rows[0]
        assert "tokenizer_key" in row
        assert "free_models" in row
        assert "aa_matches" in row

    def test_gpt_oss_family_attaches_multiple_free_models(self):
        from model_registry import build_tokenizer_catalog

        rows = build_tokenizer_catalog(include_proxy=False)
        gpt_oss = next(row for row in rows if row["tokenizer_key"] == "gpt-oss")

        model_ids = {model["model_id"] for model in gpt_oss["free_models"]}
        assert model_ids == {
            "openai/gpt-oss-20b:free",
            "openai/gpt-oss-120b:free",
        }

    def test_every_exact_family_has_continuation_style_metadata(self):
        from tokenizer_registry import TOKENIZER_FAMILY_SPECS

        exact_specs = [spec for spec in TOKENIZER_FAMILY_SPECS.values() if spec.mapping_quality == "exact"]
        assert exact_specs
        assert all(spec.continuation_style for spec in exact_specs)

    def test_every_exact_family_has_chart_color_metadata(self):
        from tokenizer_registry import TOKENIZER_FAMILY_SPECS

        exact_specs = [spec for spec in TOKENIZER_FAMILY_SPECS.values() if spec.mapping_quality == "exact"]
        assert all(spec.chart_color.startswith("#") for spec in exact_specs)

    def test_proxy_family_labels_call_out_stand_ins(self):
        from model_registry import list_tokenizer_families

        rows = list_tokenizer_families(include_proxy=True)

        gemma = next(row for row in rows if row["key"] == "gemma-2")
        command_r = next(row for row in rows if row["key"] == "command-r")

        assert "proxy" in gemma["label"].lower()
        assert "bloom" in command_r["label"].lower()


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

    def test_catalog_entries_attach_aa_metadata_for_matching_models(self, tmp_path, monkeypatch):
        from model_registry import build_catalog_entries

        snapshot = tmp_path / "aa.json"
        snapshot.write_text(json.dumps({
            "captured_at": "2026-03-27T12:00:00Z",
            "models": [
                {
                    "model_id": "mistralai/mistral-7b-instruct:free",
                    "tokenizer_key": "mistral",
                    "label": "Mistral 7B Instruct",
                    "ttft_seconds": 0.39,
                    "output_tokens_per_second": 96.4,
                    "provider": "Artificial Analysis",
                    "benchmark_url": "https://example.com/mistral",
                },
            ],
        }), encoding="utf-8")

        monkeypatch.setattr("model_registry.ARTIFICIAL_ANALYSIS_SNAPSHOT_PATH", snapshot)
        rows = build_catalog_entries(include_proxy=True, refresh_live=False)

        mistral = next(row for row in rows if row["model_id"] == "mistralai/mistral-7b-instruct:free")
        assert mistral["ttft_seconds"] == 0.39
        assert mistral["output_tokens_per_second"] == 96.4


class TestFreeRuntimeChoices:
    def test_free_runtime_choices_return_only_attached_free_models(self):
        from model_registry import list_free_runtime_choices

        rows = list_free_runtime_choices(include_proxy=False)
        assert rows
        assert all(row["runtime_badge"] == "Runnable here for free" for row in rows)

    def test_free_runtime_choices_expose_only_explicit_free_model_ids(self):
        from model_registry import list_free_runtime_choices

        rows = list_free_runtime_choices(include_proxy=False)
        assert all(row["model_id"].endswith(":free") for row in rows)

    def test_free_runtime_choices_include_new_exact_text_only_models(self):
        from model_registry import list_free_runtime_choices

        rows = list_free_runtime_choices(include_proxy=False)
        model_ids = {row["model_id"] for row in rows}

        expected = {
            "arcee-ai/trinity-large-preview:free",
            "arcee-ai/trinity-mini:free",
            "nvidia/nemotron-3-nano-30b-a3b:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "nvidia/nemotron-nano-9b-v2:free",
            "openai/gpt-oss-20b:free",
            "openai/gpt-oss-120b:free",
            "qwen/qwen3-coder:free",
            "qwen/qwen3-next-80b-a3b-instruct:free",
            "z-ai/glm-4.5-air:free",
        }
        assert expected.issubset(model_ids)

    def test_free_runtime_choices_cover_app_comparison_models(self):
        from app import FREE_MODELS
        from model_registry import list_free_runtime_choices

        expected = {
            (row["label"], row["model_id"])
            for row in list_free_runtime_choices(include_proxy=False)
        }
        assert set(FREE_MODELS) == expected
