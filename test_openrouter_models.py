"""Tests for OpenRouter model discovery (Issue 2)."""

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# fetch_models
# ---------------------------------------------------------------------------


SAMPLE_MODELS_RESPONSE = {
    "data": [
        {
            "id": "openai/gpt-4o",
            "name": "GPT-4o",
            "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
            "context_length": 128000,
        },
        {
            "id": "meta-llama/llama-3.1-8b-instruct",
            "name": "Llama 3.1 8B Instruct",
            "pricing": {"prompt": "0.00000005", "completion": "0.00000008"},
            "context_length": 131072,
        },
        {
            "id": "mistralai/mistral-7b-instruct",
            "name": "Mistral 7B Instruct",
            "pricing": {"prompt": "0.00000004", "completion": "0.00000004"},
            "context_length": 32768,
        },
    ]
}


class TestCallOpenrouterTimeout:
    """call_openrouter must pass a timeout to requests.post."""

    def test_post_called_with_timeout(self):
        from openrouter import call_openrouter

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"choices": [{"message": {"content": "hi"}}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("openrouter.requests.post", return_value=mock_resp) as mock_post:
            call_openrouter("fake-key", "test/model", "hello")

        _, kwargs = mock_post.call_args
        assert kwargs.get("timeout") == 30


class TestFetchModels:
    """Tests for fetch_models() -> list[dict]."""

    def test_returns_list(self):
        from openrouter import fetch_models

        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_MODELS_RESPONSE
        mock_resp.raise_for_status = MagicMock()

        with patch("openrouter.requests.get", return_value=mock_resp):
            result = fetch_models()
        assert isinstance(result, list)

    def test_returns_model_dicts(self):
        from openrouter import fetch_models

        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_MODELS_RESPONSE
        mock_resp.raise_for_status = MagicMock()

        with patch("openrouter.requests.get", return_value=mock_resp):
            result = fetch_models()
        assert len(result) == 3
        assert result[0]["id"] == "openai/gpt-4o"

    def test_each_model_has_required_fields(self):
        from openrouter import fetch_models

        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_MODELS_RESPONSE
        mock_resp.raise_for_status = MagicMock()

        with patch("openrouter.requests.get", return_value=mock_resp):
            result = fetch_models()
        for model in result:
            assert "id" in model
            assert "pricing" in model
            assert "context_length" in model

    def test_calls_correct_url(self):
        from openrouter import OPENROUTER_MODELS_URL, fetch_models

        mock_resp = MagicMock()
        mock_resp.json.return_value = SAMPLE_MODELS_RESPONSE
        mock_resp.raise_for_status = MagicMock()

        with patch("openrouter.requests.get", return_value=mock_resp) as mock_get:
            fetch_models()
        mock_get.assert_called_once_with(OPENROUTER_MODELS_URL, timeout=10)

    def test_raises_on_http_error(self):
        from openrouter import fetch_models

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("503 Service Unavailable")

        with patch("openrouter.requests.get", return_value=mock_resp):
            with pytest.raises(Exception, match="503"):
                fetch_models()

    def test_returns_empty_list_on_missing_data_key(self):
        from openrouter import fetch_models

        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()

        with patch("openrouter.requests.get", return_value=mock_resp):
            result = fetch_models()
        assert result == []


# ---------------------------------------------------------------------------
# Pricing cache: refresh_from_openrouter
# ---------------------------------------------------------------------------


class TestRefreshFromOpenrouter:
    """Tests for refresh_from_openrouter() in pricing.py."""

    def test_updates_cache_with_live_data(self):
        from pricing import _clear_cache, _pricing_cache, refresh_from_openrouter

        _clear_cache()
        mock_models = [
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
                "context_length": 128000,
            },
        ]
        with patch("openrouter.fetch_models", return_value=mock_models):
            refresh_from_openrouter()

        assert "openai/gpt-4o" in _pricing_cache

    def test_cached_entry_has_required_keys(self):
        from pricing import _clear_cache, _pricing_cache, refresh_from_openrouter

        _clear_cache()
        mock_models = [
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
                "context_length": 128000,
            },
        ]
        with patch("openrouter.fetch_models", return_value=mock_models):
            refresh_from_openrouter()

        entry = _pricing_cache["openai/gpt-4o"]
        assert "input_per_million" in entry
        assert "output_per_million" in entry
        assert "context_window" in entry
        assert "label" in entry

    def test_converts_per_token_to_per_million(self):
        from pricing import _clear_cache, _pricing_cache, refresh_from_openrouter

        _clear_cache()
        mock_models = [
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
                "context_length": 128000,
            },
        ]
        with patch("openrouter.fetch_models", return_value=mock_models):
            refresh_from_openrouter()

        entry = _pricing_cache["openai/gpt-4o"]
        assert entry["input_per_million"] == pytest.approx(2.50)
        assert entry["output_per_million"] == pytest.approx(10.00)

    def test_fallback_on_api_failure(self):
        from pricing import _clear_cache, get_pricing, refresh_from_openrouter

        _clear_cache()
        with patch("openrouter.fetch_models", side_effect=Exception("network error")):
            refresh_from_openrouter()

        # Static fallback should still work
        result = get_pricing("gpt2")
        assert result["input_per_million"] == 0.0

    def test_last_refreshed_updated(self):
        from pricing import _clear_cache, get_last_refreshed, refresh_from_openrouter

        _clear_cache()
        mock_models = [
            {
                "id": "openai/gpt-4o",
                "name": "GPT-4o",
                "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
                "context_length": 128000,
            },
        ]
        with patch("openrouter.fetch_models", return_value=mock_models):
            refresh_from_openrouter()

        ts = get_last_refreshed()
        assert ts is not None


class TestGetPricingWithCache:
    """Tests for get_pricing() with cache layer."""

    def test_static_still_works(self):
        from pricing import _clear_cache, get_pricing

        _clear_cache()
        result = get_pricing("gpt2")
        assert result["input_per_million"] == 0.0

    def test_cached_model_returned(self):
        from pricing import _clear_cache, _pricing_cache, get_pricing

        _clear_cache()
        _pricing_cache["test/model"] = {
            "input_per_million": 1.0,
            "output_per_million": 2.0,
            "context_window": 4096,
            "label": "Test Model",
        }
        result = get_pricing("test/model")
        assert result["input_per_million"] == 1.0

    def test_cache_preferred_over_static_for_tokenizer_keys(self):
        """Live cache takes precedence over static MODEL_PRICING entries."""
        from pricing import _clear_cache, _pricing_cache, get_pricing

        _clear_cache()
        _pricing_cache["gpt2"] = {
            "input_per_million": 999.0,
            "output_per_million": 999.0,
            "context_window": 999,
            "label": "Live override",
        }
        result = get_pricing("gpt2")
        # Live cache takes precedence
        assert result["input_per_million"] == 999.0


class TestAvailableModelsWithCache:
    """Tests for available_models() with cache layer."""

    def test_includes_static_models(self):
        from pricing import _clear_cache, available_models

        _clear_cache()
        result = available_models()
        assert "gpt2" in result

    def test_includes_cached_models(self):
        from pricing import _clear_cache, _pricing_cache, available_models

        _clear_cache()
        _pricing_cache["test/cached-model"] = {
            "input_per_million": 1.0,
            "output_per_million": 2.0,
            "context_window": 4096,
            "label": "Test",
        }
        result = available_models()
        assert "test/cached-model" in result

    def test_no_duplicates(self):
        from pricing import _clear_cache, available_models

        _clear_cache()
        result = available_models()
        assert len(result) == len(set(result))
