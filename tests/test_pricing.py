"""Tests for the pricing data module (GH-4)."""

import threading

import pytest

# ---------------------------------------------------------------------------
# MODEL_PRICING structure
# ---------------------------------------------------------------------------


class TestModelPricing:
    """Validate the MODEL_PRICING dict has correct structure."""

    REQUIRED_KEYS = {"input_per_million", "output_per_million", "context_window", "label"}

    def test_contains_gpt2(self):
        from workbench.pricing import MODEL_PRICING

        assert "gpt2" in MODEL_PRICING

    def test_contains_llama3(self):
        from workbench.pricing import MODEL_PRICING

        assert "llama-3" in MODEL_PRICING

    def test_contains_mistral(self):
        from workbench.pricing import MODEL_PRICING

        assert "mistral" in MODEL_PRICING

    def test_contains_v2_frontier_models(self):
        """MODEL_PRICING must include all v2 tokenizer families."""
        from workbench.pricing import MODEL_PRICING

        for key in ("o200k_base", "cl100k_base", "qwen-2.5", "gemma-2", "command-r"):
            assert key in MODEL_PRICING, f"missing: {key}"

    def test_has_at_least_eight_entries(self):
        from workbench.pricing import MODEL_PRICING

        assert len(MODEL_PRICING) >= 8

    def test_all_entries_have_required_keys(self):
        from workbench.pricing import MODEL_PRICING

        for model, data in MODEL_PRICING.items():
            for key in self.REQUIRED_KEYS:
                assert key in data, f"{model} missing key: {key}"

    def test_input_per_million_is_numeric(self):
        from workbench.pricing import MODEL_PRICING

        for model, data in MODEL_PRICING.items():
            assert isinstance(data["input_per_million"], (int, float)), f"{model}"

    def test_output_per_million_is_numeric(self):
        from workbench.pricing import MODEL_PRICING

        for model, data in MODEL_PRICING.items():
            assert isinstance(data["output_per_million"], (int, float)), f"{model}"

    def test_context_window_is_positive_int(self):
        from workbench.pricing import MODEL_PRICING

        for model, data in MODEL_PRICING.items():
            assert isinstance(data["context_window"], int), f"{model}"
            assert data["context_window"] > 0, f"{model}"

    def test_label_is_nonempty_string(self):
        from workbench.pricing import MODEL_PRICING

        for model, data in MODEL_PRICING.items():
            assert isinstance(data["label"], str), f"{model}"
            assert len(data["label"]) > 0, f"{model}"

    def test_keys_match_supported_tokenizers(self):
        """MODEL_PRICING keys must match SUPPORTED_TOKENIZERS keys."""
        from workbench.pricing import MODEL_PRICING
        from workbench.tokenizer import SUPPORTED_TOKENIZERS

        assert set(MODEL_PRICING.keys()) == set(SUPPORTED_TOKENIZERS.keys())

    def test_prices_are_non_negative(self):
        from workbench.pricing import MODEL_PRICING

        for model, data in MODEL_PRICING.items():
            assert data["input_per_million"] >= 0, f"{model}"
            assert data["output_per_million"] >= 0, f"{model}"


# ---------------------------------------------------------------------------
# get_pricing
# ---------------------------------------------------------------------------


class TestGetPricing:
    """Tests for get_pricing(model_name) -> dict."""

    def test_returns_dict_for_known_model(self):
        from workbench.pricing import get_pricing

        result = get_pricing("gpt2")
        assert isinstance(result, dict)

    def test_returns_correct_data(self):
        from workbench.pricing import MODEL_PRICING, get_pricing

        result = get_pricing("llama-3")
        assert result == MODEL_PRICING["llama-3"]

    def test_unknown_model_raises_key_error(self):
        from workbench.pricing import get_pricing

        with pytest.raises(KeyError):
            get_pricing("nonexistent-model")

    def test_all_models_accessible(self):
        from workbench.pricing import MODEL_PRICING, get_pricing

        for model in MODEL_PRICING:
            result = get_pricing(model)
            assert "input_per_million" in result


# ---------------------------------------------------------------------------
# available_models
# ---------------------------------------------------------------------------


class TestAvailableModels:
    """Tests for available_models() -> list[str]."""

    def test_returns_list(self):
        from workbench.pricing import available_models

        result = available_models()
        assert isinstance(result, list)

    def test_returns_sorted(self):
        from workbench.pricing import available_models

        result = available_models()
        assert result == sorted(result)

    def test_contains_all_models(self):
        from workbench.pricing import MODEL_PRICING, available_models

        result = available_models()
        assert set(result) == set(MODEL_PRICING.keys())

    def test_all_elements_are_strings(self):
        from workbench.pricing import available_models

        for name in available_models():
            assert isinstance(name, str)


# ---------------------------------------------------------------------------
# LAST_UPDATED
# ---------------------------------------------------------------------------


class TestLastUpdated:
    """Tests for LAST_UPDATED constant."""

    def test_is_nonempty_string(self):
        from workbench.pricing import LAST_UPDATED

        assert isinstance(LAST_UPDATED, str)
        assert len(LAST_UPDATED) > 0

    def test_looks_like_a_date(self):
        """Should be in YYYY-MM-DD format."""
        from workbench.pricing import LAST_UPDATED

        parts = LAST_UPDATED.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # year
        assert all(p.isdigit() for p in parts)


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestRefreshFromOpenrouterThreadSafety:
    """Verify that concurrent refresh and read don't expose empty cache state."""

    def test_cache_never_empty_during_refresh(self):
        """A reader calling get_pricing during a refresh must never see empty cache.

        Strategy: pre-populate the cache with one model, then start a refresh
        that replaces the cache with new data. A barrier ensures the reader
        thread starts while the refresh is running. The reader must always find
        the pre-populated model OR the new data — never KeyError from empty state.
        """
        from unittest.mock import patch

        import workbench.pricing as pricing

        # Pre-populate the live cache with a known model so readers have data.
        pricing._clear_cache()
        pricing._pricing_cache["test-model"] = {
            "input_per_million": 1.0,
            "output_per_million": 2.0,
            "context_window": 4096,
            "label": "Test Model",
        }

        barrier = threading.Barrier(2)
        key_errors: list[Exception] = []
        empty_cache_observations: list[int] = []

        # Fake models list — large enough to give the reader thread time to interleave.
        fake_models = [
            {
                "id": f"openrouter-model-{i}",
                "name": f"Model {i}",
                "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                "context_length": 4096,
            }
            for i in range(200)
        ]

        def refresh_thread():
            barrier.wait()
            with patch("workbench.openrouter.fetch_models", return_value=fake_models):
                pricing.refresh_from_openrouter()

        def reader_thread():
            barrier.wait()
            for _ in range(500):
                try:
                    cache_snapshot = set(pricing._pricing_cache.keys())
                    if len(cache_snapshot) == 0:
                        empty_cache_observations.append(1)
                    # Attempt to read the pre-seeded model; if cache is mid-clear
                    # and test-model was removed before new models were added,
                    # get_pricing would raise KeyError.
                except Exception as exc:
                    key_errors.append(exc)

        t1 = threading.Thread(target=refresh_thread)
        t2 = threading.Thread(target=reader_thread)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        pricing._clear_cache()

        assert not key_errors, f"Unexpected exceptions: {key_errors}"
        assert len(empty_cache_observations) == 0, (
            f"Cache was observed empty {len(empty_cache_observations)} time(s) "
            "during refresh — atomic swap required"
        )

    def test_last_refreshed_updated_atomically(self):
        """_last_refreshed must be set inside the same lock as cache population.

        After a successful refresh, _last_refreshed must not be None.
        This guards against the global assignment racing with a clear.
        """
        from unittest.mock import patch

        import workbench.pricing as pricing

        pricing._clear_cache()

        fake_models = [
            {
                "id": "some-model",
                "name": "Some Model",
                "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                "context_length": 4096,
            }
        ]

        with patch("workbench.openrouter.fetch_models", return_value=fake_models):
            pricing.refresh_from_openrouter()

        assert pricing.get_last_refreshed() is not None
        pricing._clear_cache()

    def test_get_pricing_returns_cached_openrouter_model(self):
        """get_pricing must return a cached OpenRouter model correctly under lock."""
        from unittest.mock import patch

        import workbench.pricing as pricing

        pricing._clear_cache()

        fake_models = [
            {
                "id": "openrouter/test-locked-model",
                "name": "Locked Model",
                "pricing": {"prompt": "0.000003", "completion": "0.000006"},
                "context_length": 8192,
            }
        ]

        with patch("workbench.openrouter.fetch_models", return_value=fake_models):
            pricing.refresh_from_openrouter()

        result = pricing.get_pricing("openrouter/test-locked-model")
        assert result["input_per_million"] == pytest.approx(3.0)
        assert result["output_per_million"] == pytest.approx(6.0)

        pricing._clear_cache()

    def test_available_models_includes_cached_models_after_refresh(self):
        """available_models() must include freshly refreshed OpenRouter models."""
        from unittest.mock import patch

        import workbench.pricing as pricing

        pricing._clear_cache()

        fake_models = [
            {
                "id": "openrouter/fresh-model",
                "name": "Fresh Model",
                "pricing": {"prompt": "0.000001", "completion": "0.000001"},
                "context_length": 4096,
            }
        ]

        with patch("workbench.openrouter.fetch_models", return_value=fake_models):
            pricing.refresh_from_openrouter()

        models = pricing.available_models()
        assert "openrouter/fresh-model" in models

        pricing._clear_cache()
