"""Tests for the pricing data module (GH-4)."""

import pytest


# ---------------------------------------------------------------------------
# MODEL_PRICING structure
# ---------------------------------------------------------------------------


class TestModelPricing:
    """Validate the MODEL_PRICING dict has correct structure."""

    REQUIRED_KEYS = {"input_per_million", "output_per_million", "context_window", "label"}

    def test_contains_gpt2(self):
        from pricing import MODEL_PRICING

        assert "gpt2" in MODEL_PRICING

    def test_contains_llama3(self):
        from pricing import MODEL_PRICING

        assert "llama-3" in MODEL_PRICING

    def test_contains_mistral(self):
        from pricing import MODEL_PRICING

        assert "mistral" in MODEL_PRICING

    def test_contains_v2_frontier_models(self):
        """MODEL_PRICING must include all v2 tokenizer families."""
        from pricing import MODEL_PRICING

        for key in ("o200k_base", "cl100k_base", "qwen-2.5", "gemma-2", "command-r"):
            assert key in MODEL_PRICING, f"missing: {key}"

    def test_has_at_least_eight_entries(self):
        from pricing import MODEL_PRICING

        assert len(MODEL_PRICING) >= 8

    def test_all_entries_have_required_keys(self):
        from pricing import MODEL_PRICING

        for model, data in MODEL_PRICING.items():
            for key in self.REQUIRED_KEYS:
                assert key in data, f"{model} missing key: {key}"

    def test_input_per_million_is_numeric(self):
        from pricing import MODEL_PRICING

        for model, data in MODEL_PRICING.items():
            assert isinstance(data["input_per_million"], (int, float)), f"{model}"

    def test_output_per_million_is_numeric(self):
        from pricing import MODEL_PRICING

        for model, data in MODEL_PRICING.items():
            assert isinstance(data["output_per_million"], (int, float)), f"{model}"

    def test_context_window_is_positive_int(self):
        from pricing import MODEL_PRICING

        for model, data in MODEL_PRICING.items():
            assert isinstance(data["context_window"], int), f"{model}"
            assert data["context_window"] > 0, f"{model}"

    def test_label_is_nonempty_string(self):
        from pricing import MODEL_PRICING

        for model, data in MODEL_PRICING.items():
            assert isinstance(data["label"], str), f"{model}"
            assert len(data["label"]) > 0, f"{model}"

    def test_keys_match_supported_tokenizers(self):
        """MODEL_PRICING keys must match SUPPORTED_TOKENIZERS keys."""
        from pricing import MODEL_PRICING
        from tokenizer import SUPPORTED_TOKENIZERS

        assert set(MODEL_PRICING.keys()) == set(SUPPORTED_TOKENIZERS.keys())

    def test_prices_are_non_negative(self):
        from pricing import MODEL_PRICING

        for model, data in MODEL_PRICING.items():
            assert data["input_per_million"] >= 0, f"{model}"
            assert data["output_per_million"] >= 0, f"{model}"


# ---------------------------------------------------------------------------
# get_pricing
# ---------------------------------------------------------------------------


class TestGetPricing:
    """Tests for get_pricing(model_name) -> dict."""

    def test_returns_dict_for_known_model(self):
        from pricing import get_pricing

        result = get_pricing("gpt2")
        assert isinstance(result, dict)

    def test_returns_correct_data(self):
        from pricing import get_pricing, MODEL_PRICING

        result = get_pricing("llama-3")
        assert result == MODEL_PRICING["llama-3"]

    def test_unknown_model_raises_key_error(self):
        from pricing import get_pricing

        with pytest.raises(KeyError):
            get_pricing("nonexistent-model")

    def test_all_models_accessible(self):
        from pricing import get_pricing, MODEL_PRICING

        for model in MODEL_PRICING:
            result = get_pricing(model)
            assert "input_per_million" in result


# ---------------------------------------------------------------------------
# available_models
# ---------------------------------------------------------------------------


class TestAvailableModels:
    """Tests for available_models() -> list[str]."""

    def test_returns_list(self):
        from pricing import available_models

        result = available_models()
        assert isinstance(result, list)

    def test_returns_sorted(self):
        from pricing import available_models

        result = available_models()
        assert result == sorted(result)

    def test_contains_all_models(self):
        from pricing import available_models, MODEL_PRICING

        result = available_models()
        assert set(result) == set(MODEL_PRICING.keys())

    def test_all_elements_are_strings(self):
        from pricing import available_models

        for name in available_models():
            assert isinstance(name, str)


# ---------------------------------------------------------------------------
# LAST_UPDATED
# ---------------------------------------------------------------------------


class TestLastUpdated:
    """Tests for LAST_UPDATED constant."""

    def test_is_nonempty_string(self):
        from pricing import LAST_UPDATED

        assert isinstance(LAST_UPDATED, str)
        assert len(LAST_UPDATED) > 0

    def test_looks_like_a_date(self):
        """Should be in YYYY-MM-DD format."""
        from pricing import LAST_UPDATED

        parts = LAST_UPDATED.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # year
        assert all(p.isdigit() for p in parts)
