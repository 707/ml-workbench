"""
TDD tests for translation.py — translation module with LRU caching.

Tests cover:
  - Correct return value (translated string)
  - call_openrouter is invoked
  - API key is forwarded
  - Correct content extracted from response
  - Prompt contains source text
  - Hardcoded model is meta-llama/llama-3.1-8b-instruct
  - LRU cache: same (text, api_key) hits API only once
  - LRU cache miss: different text hits API again
"""

import pytest
from unittest.mock import patch, MagicMock


def _make_response(translated_text: str) -> dict:
    return {
        "choices": [{"message": {"content": translated_text}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
    }


@pytest.fixture(autouse=True)
def clear_translation_cache():
    """Clear LRU cache before every test to prevent cross-test pollution."""
    from translation import translate_to_english
    translate_to_english.cache_clear()
    yield
    translate_to_english.cache_clear()


# ---------------------------------------------------------------------------
# Core behaviour
# ---------------------------------------------------------------------------


class TestTranslateToEnglishBehaviour:
    """Tests for translate_to_english(text, api_key) -> str in translation module."""

    def test_returns_string(self):
        """translate_to_english must return a string."""
        from translation import translate_to_english

        with patch("translation.call_openrouter", return_value=_make_response("Hello")):
            result = translate_to_english("Bonjour", "sk-key")

        assert isinstance(result, str)

    def test_calls_call_openrouter(self):
        """translate_to_english must call call_openrouter."""
        from translation import translate_to_english

        with patch("translation.call_openrouter", return_value=_make_response("Hi")) as mock_call:
            translate_to_english("Hola", "sk-key")

        assert mock_call.called

    def test_passes_api_key_to_call_openrouter(self):
        """API key must be forwarded as the first argument to call_openrouter."""
        from translation import translate_to_english

        with patch("translation.call_openrouter", return_value=_make_response("Hi")) as mock_call:
            translate_to_english("Hola", "my-key")

        assert mock_call.call_args.args[0] == "my-key"

    def test_returns_translated_content(self):
        """Return value is the content string from the model response."""
        from translation import translate_to_english

        with patch("translation.call_openrouter", return_value=_make_response("Hello world")):
            result = translate_to_english("Bonjour monde", "key")

        assert result == "Hello world"

    def test_prompt_contains_source_text(self):
        """The prompt sent to the model must include the source text."""
        from translation import translate_to_english

        with patch("translation.call_openrouter", return_value=_make_response("ok")) as mock_call:
            translate_to_english("Guten Tag", "key")

        prompt_arg = mock_call.call_args.args[2]
        assert "Guten Tag" in prompt_arg

    def test_uses_hardcoded_model(self):
        """The model ID must be meta-llama/llama-3.1-8b-instruct."""
        from translation import translate_to_english

        with patch("translation.call_openrouter", return_value=_make_response("ok")) as mock_call:
            translate_to_english("Test", "key")

        model_arg = mock_call.call_args.args[1]
        assert model_arg == "meta-llama/llama-3.1-8b-instruct"


# ---------------------------------------------------------------------------
# LRU cache behaviour
# ---------------------------------------------------------------------------


class TestTranslateToEnglishCache:
    """Tests for LRU caching behaviour in translate_to_english."""

    def test_cache_hit_same_args_calls_api_once(self):
        """Calling with identical (text, api_key) twice must hit the API only once."""
        from translation import translate_to_english

        with patch("translation.call_openrouter", return_value=_make_response("Hello")) as mock_call:
            translate_to_english("Bonjour", "sk-key")
            translate_to_english("Bonjour", "sk-key")

        assert mock_call.call_count == 1

    def test_cache_miss_different_text_calls_api_twice(self):
        """Calling with different text arguments must hit the API each time."""
        from translation import translate_to_english

        with patch("translation.call_openrouter", return_value=_make_response("Hello")) as mock_call:
            translate_to_english("Bonjour", "sk-key")
            translate_to_english("Hola", "sk-key")

        assert mock_call.call_count == 2

    def test_cache_miss_different_api_key_calls_api_twice(self):
        """Different api_key with same text is a cache miss and must call the API again."""
        from translation import translate_to_english

        with patch("translation.call_openrouter", return_value=_make_response("Hello")) as mock_call:
            translate_to_english("Bonjour", "key-1")
            translate_to_english("Bonjour", "key-2")

        assert mock_call.call_count == 2

    def test_cached_result_is_correct_value(self):
        """Second (cached) call must return the same translated string as the first."""
        from translation import translate_to_english

        with patch("translation.call_openrouter", return_value=_make_response("Hello")):
            first = translate_to_english("Bonjour", "sk-key")
            second = translate_to_english("Bonjour", "sk-key")

        assert first == second == "Hello"

    def test_cache_clear_resets_cache(self):
        """After cache_clear(), same args must hit the API again."""
        from translation import translate_to_english

        with patch("translation.call_openrouter", return_value=_make_response("Hello")) as mock_call:
            translate_to_english("Bonjour", "sk-key")
            translate_to_english.cache_clear()
            translate_to_english("Bonjour", "sk-key")

        assert mock_call.call_count == 2
