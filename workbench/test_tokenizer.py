"""
TDD tests for workbench/tokenizer.py — Tokenizer Inspector module.

Test order matches implementation phases:
  Phase 1: get_tokenizer, tokenize_text, fragmentation_ratio, flag_oov_words,
           detect_language, efficiency_score, translate_to_english
  Phase 2: render_tokens_html
  Phase 3: build_tokenizer_ui (smoke test)
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Phase 1 — get_tokenizer
# ---------------------------------------------------------------------------


class TestGetTokenizer:
    """Unit tests for get_tokenizer(name)."""

    def test_returns_tokenizer_for_gpt2(self):
        """get_tokenizer('gpt2') must return a tokenizer object."""
        from tokenizer import get_tokenizer

        mock_tok = MagicMock()
        with patch("tokenizer.AutoTokenizer.from_pretrained", return_value=mock_tok) as mock_fp:
            result = get_tokenizer("gpt2")

        assert result is mock_tok

    def test_returns_tokenizer_for_llama3(self):
        """get_tokenizer('llama-3') must return a tokenizer object."""
        from tokenizer import get_tokenizer

        mock_tok = MagicMock()
        with patch("tokenizer.AutoTokenizer.from_pretrained", return_value=mock_tok):
            result = get_tokenizer("llama-3")

        assert result is mock_tok

    def test_returns_tokenizer_for_mistral(self):
        """get_tokenizer('mistral') must return a tokenizer object."""
        from tokenizer import get_tokenizer

        mock_tok = MagicMock()
        with patch("tokenizer.AutoTokenizer.from_pretrained", return_value=mock_tok):
            result = get_tokenizer("mistral")

        assert result is mock_tok

    def test_raises_for_unknown_name(self):
        """get_tokenizer with unrecognised name must raise ValueError."""
        from tokenizer import get_tokenizer

        with pytest.raises(ValueError, match="unknown"):
            get_tokenizer("nonexistent-model-xyz")

    def test_calls_from_pretrained_with_correct_repo_id_for_gpt2(self):
        """get_tokenizer('gpt2') must call from_pretrained with 'gpt2'."""
        import tokenizer as tok_module
        from tokenizer import get_tokenizer

        with patch.dict(tok_module._tokenizer_cache, {}, clear=True):
            with patch("tokenizer.AutoTokenizer.from_pretrained", return_value=MagicMock()) as mock_fp:
                get_tokenizer("gpt2")

        mock_fp.assert_called_once_with("gpt2")

    def test_calls_from_pretrained_with_correct_repo_id_for_llama3(self):
        """get_tokenizer('llama-3') must use NousResearch/Meta-Llama-3-8B."""
        import tokenizer as tok_module
        from tokenizer import get_tokenizer

        with patch.dict(tok_module._tokenizer_cache, {}, clear=True):
            with patch("tokenizer.AutoTokenizer.from_pretrained", return_value=MagicMock()) as mock_fp:
                get_tokenizer("llama-3")

        mock_fp.assert_called_once_with("NousResearch/Meta-Llama-3-8B")

    def test_calls_from_pretrained_with_correct_repo_id_for_mistral(self):
        """get_tokenizer('mistral') must use mistralai/Mistral-7B-v0.1."""
        import tokenizer as tok_module
        from tokenizer import get_tokenizer

        with patch.dict(tok_module._tokenizer_cache, {}, clear=True):
            with patch("tokenizer.AutoTokenizer.from_pretrained", return_value=MagicMock()) as mock_fp:
                get_tokenizer("mistral")

        mock_fp.assert_called_once_with("mistralai/Mistral-7B-v0.1")

    def test_caches_tokenizer_on_second_call(self):
        """Second call with same name must not call from_pretrained again."""
        # Import fresh to reset module-level cache
        import importlib
        import tokenizer as tok_module
        importlib.reload(tok_module)

        mock_tok = MagicMock()
        with patch("tokenizer.AutoTokenizer.from_pretrained", return_value=mock_tok) as mock_fp:
            first = tok_module.get_tokenizer("gpt2")
            second = tok_module.get_tokenizer("gpt2")

        assert mock_fp.call_count == 1
        assert first is second

    def test_supported_tokenizers_registry_has_three_entries(self):
        """SUPPORTED_TOKENIZERS must have exactly 3 entries."""
        from tokenizer import SUPPORTED_TOKENIZERS

        assert len(SUPPORTED_TOKENIZERS) == 3

    def test_supported_tokenizers_keys(self):
        """SUPPORTED_TOKENIZERS must contain gpt2, llama-3, mistral keys."""
        from tokenizer import SUPPORTED_TOKENIZERS

        assert "gpt2" in SUPPORTED_TOKENIZERS
        assert "llama-3" in SUPPORTED_TOKENIZERS
        assert "mistral" in SUPPORTED_TOKENIZERS


# ---------------------------------------------------------------------------
# Phase 1 — tokenize_text
# ---------------------------------------------------------------------------


class TestTokenizeText:
    """Unit tests for tokenize_text(text, tokenizer) -> list[dict]."""

    def _mock_tokenizer(self, token_ids, tokens):
        """Build a minimal mock tokenizer."""
        tok = MagicMock()
        tok.encode.return_value = token_ids
        tok.convert_ids_to_tokens.return_value = tokens
        return tok

    def test_returns_list(self):
        """tokenize_text must return a list."""
        from tokenizer import tokenize_text

        tok = self._mock_tokenizer([123], ["hello"])
        result = tokenize_text("hello", tok)

        assert isinstance(result, list)

    def test_each_entry_has_token_and_id_keys(self):
        """Each dict in the result must have 'token' and 'id' keys."""
        from tokenizer import tokenize_text

        tok = self._mock_tokenizer([10, 20], ["Hello", " world"])
        result = tokenize_text("Hello world", tok)

        for entry in result:
            assert "token" in entry
            assert "id" in entry

    def test_token_values_are_strings(self):
        """'token' values must be strings."""
        from tokenizer import tokenize_text

        tok = self._mock_tokenizer([10, 20], ["Hello", " world"])
        result = tokenize_text("Hello world", tok)

        for entry in result:
            assert isinstance(entry["token"], str)

    def test_id_values_are_ints(self):
        """'id' values must be ints."""
        from tokenizer import tokenize_text

        tok = self._mock_tokenizer([10, 20], ["Hello", " world"])
        result = tokenize_text("Hello world", tok)

        for entry in result:
            assert isinstance(entry["id"], int)

    def test_token_and_id_values_correct(self):
        """Token and id values must match the mock tokenizer output."""
        from tokenizer import tokenize_text

        tok = self._mock_tokenizer([7, 42], ["Hi", "!"])
        result = tokenize_text("Hi!", tok)

        assert result[0] == {"token": "Hi", "id": 7}
        assert result[1] == {"token": "!", "id": 42}

    def test_empty_text_returns_empty_list(self):
        """Empty string → tokenizer returns [] → result is []."""
        from tokenizer import tokenize_text

        tok = self._mock_tokenizer([], [])
        result = tokenize_text("", tok)

        assert result == []

    def test_length_matches_number_of_tokens(self):
        """Result length must equal the number of token IDs returned."""
        from tokenizer import tokenize_text

        tok = self._mock_tokenizer([1, 2, 3, 4], ["a", "b", "c", "d"])
        result = tokenize_text("a b c d", tok)

        assert len(result) == 4


# ---------------------------------------------------------------------------
# Phase 1 — fragmentation_ratio
# ---------------------------------------------------------------------------


class TestFragmentationRatio:
    """Unit tests for fragmentation_ratio(text, tokenizer) -> dict[str, float]."""

    def _mock_tokenizer(self, token_ids, tokens):
        tok = MagicMock()
        tok.encode.return_value = token_ids
        tok.convert_ids_to_tokens.return_value = tokens
        return tok

    def test_returns_dict(self):
        """fragmentation_ratio must return a dict."""
        from tokenizer import fragmentation_ratio

        tok = self._mock_tokenizer([1, 2], ["Hello", " world"])
        result = fragmentation_ratio("Hello world", tok)

        assert isinstance(result, dict)

    def test_contains_ratio_key(self):
        """Result must contain a 'ratio' key."""
        from tokenizer import fragmentation_ratio

        tok = self._mock_tokenizer([1, 2], ["Hello", " world"])
        result = fragmentation_ratio("Hello world", tok)

        assert "ratio" in result

    def test_ratio_is_float(self):
        """ratio value must be a float."""
        from tokenizer import fragmentation_ratio

        tok = self._mock_tokenizer([1, 2], ["Hello", " world"])
        result = fragmentation_ratio("Hello world", tok)

        assert isinstance(result["ratio"], float)

    def test_ratio_is_tokens_per_word(self):
        """ratio = num_tokens / num_words for simple input."""
        from tokenizer import fragmentation_ratio

        # 4 tokens for 2 words → ratio 2.0
        tok = self._mock_tokenizer([1, 2, 3, 4], ["Hel", "lo", " wor", "ld"])
        result = fragmentation_ratio("Hello world", tok)

        assert result["ratio"] == pytest.approx(2.0)

    def test_empty_text_returns_ratio_zero(self):
        """Empty text → ratio 0.0 (no division by zero crash)."""
        from tokenizer import fragmentation_ratio

        tok = self._mock_tokenizer([], [])
        result = fragmentation_ratio("", tok)

        assert result["ratio"] == pytest.approx(0.0)

    def test_contains_token_count_key(self):
        """Result must contain 'token_count' key."""
        from tokenizer import fragmentation_ratio

        tok = self._mock_tokenizer([1, 2, 3], ["a", "b", "c"])
        result = fragmentation_ratio("a b c", tok)

        assert "token_count" in result

    def test_token_count_value_correct(self):
        """token_count must equal the number of tokens from the tokenizer."""
        from tokenizer import fragmentation_ratio

        tok = self._mock_tokenizer([1, 2, 3], ["a", "b", "c"])
        result = fragmentation_ratio("a b c", tok)

        assert result["token_count"] == 3


# ---------------------------------------------------------------------------
# Phase 1 — flag_oov_words
# ---------------------------------------------------------------------------


class TestFlagOovWords:
    """Unit tests for flag_oov_words(text, tokenizer, threshold) -> set[str]."""

    def _mock_tokenizer_with_word_encoding(self, word_token_counts: dict):
        """
        Build a mock tokenizer where encode(word) returns a list of token IDs
        whose length equals word_token_counts[word].
        """
        tok = MagicMock()

        def encode_side_effect(text, add_special_tokens=True):
            word = text.strip()
            count = word_token_counts.get(word, 1)
            return list(range(count))

        tok.encode.side_effect = encode_side_effect
        tok.convert_ids_to_tokens.return_value = []
        return tok

    def test_returns_set(self):
        """flag_oov_words must return a set."""
        from tokenizer import flag_oov_words

        tok = self._mock_tokenizer_with_word_encoding({"hello": 1})
        result = flag_oov_words("hello", tok)

        assert isinstance(result, set)

    def test_word_above_threshold_is_flagged(self):
        """A word that fragments into more tokens than threshold is in the result."""
        from tokenizer import flag_oov_words

        # "supercalifragilistic" splits into 5 tokens, threshold=3 → flagged
        tok = self._mock_tokenizer_with_word_encoding({"supercalifragilistic": 5})
        result = flag_oov_words("supercalifragilistic", tok, threshold=3)

        assert "supercalifragilistic" in result

    def test_word_at_threshold_is_flagged(self):
        """A word that fragments into exactly threshold tokens is flagged."""
        from tokenizer import flag_oov_words

        tok = self._mock_tokenizer_with_word_encoding({"hello": 3})
        result = flag_oov_words("hello", tok, threshold=3)

        assert "hello" in result

    def test_word_below_threshold_not_flagged(self):
        """A word that fragments into fewer tokens than threshold is not flagged."""
        from tokenizer import flag_oov_words

        tok = self._mock_tokenizer_with_word_encoding({"hello": 1})
        result = flag_oov_words("hello", tok, threshold=3)

        assert "hello" not in result

    def test_default_threshold_is_3(self):
        """Default threshold is 3."""
        from tokenizer import flag_oov_words

        tok = self._mock_tokenizer_with_word_encoding({"word": 3})
        result = flag_oov_words("word", tok)

        assert "word" in result

    def test_empty_text_returns_empty_set(self):
        """Empty text → no words to evaluate → empty set."""
        from tokenizer import flag_oov_words

        tok = self._mock_tokenizer_with_word_encoding({})
        result = flag_oov_words("", tok)

        assert result == set()

    def test_multiple_words_only_oov_flagged(self):
        """Only words meeting the threshold are flagged; others are not."""
        from tokenizer import flag_oov_words

        tok = self._mock_tokenizer_with_word_encoding({"cat": 1, "superlongword": 5})
        result = flag_oov_words("cat superlongword", tok, threshold=3)

        assert "superlongword" in result
        assert "cat" not in result


# ---------------------------------------------------------------------------
# Phase 1 — detect_language
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    """Unit tests for detect_language(text) -> str."""

    def test_returns_string(self):
        """detect_language must always return a string."""
        from tokenizer import detect_language

        with patch("tokenizer.detect", return_value="en"):
            result = detect_language("Hello world")

        assert isinstance(result, str)

    def test_returns_detected_language_code(self):
        """Returns the language code from langdetect.detect."""
        from tokenizer import detect_language

        with patch("tokenizer.detect", return_value="fr"):
            result = detect_language("Bonjour le monde")

        assert result == "fr"

    def test_returns_en_on_lang_detect_exception(self):
        """Returns 'en' when LangDetectException is raised."""
        from tokenizer import detect_language
        from langdetect import LangDetectException

        with patch("tokenizer.detect", side_effect=LangDetectException(0, "error")):
            result = detect_language("???")

        assert result == "en"

    def test_english_text_returns_en(self):
        """English text returns 'en' via the mock."""
        from tokenizer import detect_language

        with patch("tokenizer.detect", return_value="en"):
            result = detect_language("The quick brown fox")

        assert result == "en"

    def test_empty_text_returns_en(self):
        """Empty text triggers LangDetectException — falls back to 'en'."""
        from tokenizer import detect_language
        from langdetect import LangDetectException

        with patch("tokenizer.detect", side_effect=LangDetectException(0, "empty")):
            result = detect_language("")

        assert result == "en"


# ---------------------------------------------------------------------------
# Phase 1 — efficiency_score
# ---------------------------------------------------------------------------


class TestEfficiencyScore:
    """Unit tests for efficiency_score(input_tokens, english_tokens) -> float."""

    def test_returns_float(self):
        """efficiency_score must return a float."""
        from tokenizer import efficiency_score

        result = efficiency_score(10, 8)

        assert isinstance(result, float)

    def test_equal_tokens_returns_one(self):
        """When input_tokens == english_tokens, score is 1.0."""
        from tokenizer import efficiency_score

        assert efficiency_score(10, 10) == pytest.approx(1.0)

    def test_fewer_input_tokens_than_english_gives_score_above_one(self):
        """Compact non-English text (fewer tokens) → score > 1."""
        from tokenizer import efficiency_score

        # 5 tokens in source vs 10 in English → 10/5 = 2.0
        assert efficiency_score(5, 10) == pytest.approx(2.0)

    def test_more_input_tokens_than_english_gives_score_below_one(self):
        """Verbose non-English text (more tokens) → score < 1."""
        from tokenizer import efficiency_score

        # 20 tokens in source vs 10 in English → 10/20 = 0.5
        assert efficiency_score(20, 10) == pytest.approx(0.5)

    def test_zero_english_tokens_returns_one(self):
        """Zero english_tokens is the zero-guard case — must return 1.0."""
        from tokenizer import efficiency_score

        assert efficiency_score(10, 0) == pytest.approx(1.0)

    def test_zero_input_tokens_returns_one(self):
        """Zero input_tokens with zero division guard returns 1.0."""
        from tokenizer import efficiency_score

        assert efficiency_score(0, 0) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Token tax metrics (GH-3)
# ---------------------------------------------------------------------------


class TestRelativeTokenizationCost:
    """Unit tests for relative_tokenization_cost(source_tokens, english_tokens)."""

    def test_returns_float(self):
        from tokenizer import relative_tokenization_cost

        result = relative_tokenization_cost(10, 5)
        assert isinstance(result, float)

    def test_equal_tokens_returns_one(self):
        from tokenizer import relative_tokenization_cost

        assert relative_tokenization_cost(5, 5) == pytest.approx(1.0)

    def test_source_higher_than_english_returns_above_one(self):
        """10 source tokens vs 5 English → RTC = 2.0 (token tax)."""
        from tokenizer import relative_tokenization_cost

        assert relative_tokenization_cost(10, 5) == pytest.approx(2.0)

    def test_source_lower_than_english_returns_below_one(self):
        """3 source tokens vs 6 English → RTC = 0.5 (more efficient)."""
        from tokenizer import relative_tokenization_cost

        assert relative_tokenization_cost(3, 6) == pytest.approx(0.5)

    def test_zero_english_tokens_returns_one(self):
        """Zero guard: denominator 0 → 1.0."""
        from tokenizer import relative_tokenization_cost

        assert relative_tokenization_cost(10, 0) == pytest.approx(1.0)

    def test_zero_source_tokens_returns_zero(self):
        """Zero source tokens → 0.0 (no tokens = no cost)."""
        from tokenizer import relative_tokenization_cost

        assert relative_tokenization_cost(0, 5) == pytest.approx(0.0)

    def test_both_zero_returns_one(self):
        from tokenizer import relative_tokenization_cost

        assert relative_tokenization_cost(0, 0) == pytest.approx(1.0)


class TestBytePremium:
    """Unit tests for byte_premium(text, english_text)."""

    def test_returns_float(self):
        from tokenizer import byte_premium

        result = byte_premium("hello", "hello")
        assert isinstance(result, float)

    def test_identical_text_returns_one(self):
        from tokenizer import byte_premium

        assert byte_premium("hello", "hello") == pytest.approx(1.0)

    def test_arabic_vs_english_above_one(self):
        """Arabic uses more UTF-8 bytes than English for similar content."""
        from tokenizer import byte_premium

        arabic = "مرحبا بالعالم"
        english = "hello world"
        result = byte_premium(arabic, english)
        assert result > 1.0

    def test_empty_english_returns_one(self):
        """Zero guard: empty English text → 1.0."""
        from tokenizer import byte_premium

        assert byte_premium("hello", "") == pytest.approx(1.0)

    def test_empty_source_returns_zero(self):
        """Empty source text → 0.0."""
        from tokenizer import byte_premium

        assert byte_premium("", "hello") == pytest.approx(0.0)

    def test_both_empty_returns_one(self):
        from tokenizer import byte_premium

        assert byte_premium("", "") == pytest.approx(1.0)


class TestContextWindowUsage:
    """Unit tests for context_window_usage(token_count, window_size)."""

    def test_returns_float(self):
        from tokenizer import context_window_usage

        result = context_window_usage(1000, 128_000)
        assert isinstance(result, float)

    def test_known_fraction(self):
        from tokenizer import context_window_usage

        assert context_window_usage(1000, 128_000) == pytest.approx(1000 / 128_000)

    def test_full_window(self):
        from tokenizer import context_window_usage

        assert context_window_usage(128_000, 128_000) == pytest.approx(1.0)

    def test_zero_tokens(self):
        from tokenizer import context_window_usage

        assert context_window_usage(0, 128_000) == pytest.approx(0.0)

    def test_default_window_size(self):
        """Default window_size is 128_000."""
        from tokenizer import context_window_usage

        assert context_window_usage(128_000) == pytest.approx(1.0)

    def test_zero_window_returns_one(self):
        """Zero guard: window_size 0 → 1.0."""
        from tokenizer import context_window_usage

        assert context_window_usage(100, 0) == pytest.approx(1.0)


class TestQualityRiskLevel:
    """Unit tests for quality_risk_level(rtc)."""

    def test_returns_string(self):
        from tokenizer import quality_risk_level

        result = quality_risk_level(1.0)
        assert isinstance(result, str)

    def test_low_risk(self):
        from tokenizer import quality_risk_level

        assert quality_risk_level(1.0) == "low"
        assert quality_risk_level(1.4) == "low"

    def test_moderate_risk(self):
        from tokenizer import quality_risk_level

        assert quality_risk_level(1.5) == "moderate"
        assert quality_risk_level(2.0) == "moderate"
        assert quality_risk_level(2.4) == "moderate"

    def test_high_risk(self):
        from tokenizer import quality_risk_level

        assert quality_risk_level(2.5) == "high"
        assert quality_risk_level(3.0) == "high"
        assert quality_risk_level(3.9) == "high"

    def test_severe_risk(self):
        from tokenizer import quality_risk_level

        assert quality_risk_level(4.0) == "severe"
        assert quality_risk_level(5.0) == "severe"
        assert quality_risk_level(10.0) == "severe"

    def test_boundary_1_5(self):
        """Exactly 1.5 → moderate (inclusive lower bound)."""
        from tokenizer import quality_risk_level

        assert quality_risk_level(1.5) == "moderate"

    def test_boundary_2_5(self):
        """Exactly 2.5 → high."""
        from tokenizer import quality_risk_level

        assert quality_risk_level(2.5) == "high"

    def test_boundary_4_0(self):
        """Exactly 4.0 → severe."""
        from tokenizer import quality_risk_level

        assert quality_risk_level(4.0) == "severe"


# ---------------------------------------------------------------------------
# Phase 1 — translate_to_english
# ---------------------------------------------------------------------------


class TestTranslateToEnglish:
    """Unit tests for translate_to_english(text, api_key) -> str."""

    def _make_response(self, translated_text: str) -> dict:
        return {
            "choices": [{"message": {"content": translated_text}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20},
        }

    def test_returns_string(self):
        """translate_to_english must return a string."""
        from tokenizer import translate_to_english

        with patch("tokenizer.call_openrouter", return_value=self._make_response("Hello")):
            result = translate_to_english("Bonjour", "sk-key")

        assert isinstance(result, str)

    def test_calls_call_openrouter(self):
        """translate_to_english must call call_openrouter."""
        from tokenizer import translate_to_english

        with patch("tokenizer.call_openrouter", return_value=self._make_response("Hi")) as mock_call:
            translate_to_english("Hola", "sk-key")

        assert mock_call.called

    def test_passes_api_key_to_call_openrouter(self):
        """API key must be forwarded to call_openrouter."""
        from tokenizer import translate_to_english

        with patch("tokenizer.call_openrouter", return_value=self._make_response("Hi")) as mock_call:
            translate_to_english("Hola", "my-key")

        assert mock_call.call_args.args[0] == "my-key"

    def test_returns_translated_content(self):
        """Return value is the content from the model response."""
        from tokenizer import translate_to_english

        with patch("tokenizer.call_openrouter", return_value=self._make_response("Hello world")):
            result = translate_to_english("Bonjour monde", "key")

        assert result == "Hello world"

    def test_prompt_contains_source_text(self):
        """The prompt sent to the model must include the source text."""
        from tokenizer import translate_to_english

        with patch("tokenizer.call_openrouter", return_value=self._make_response("ok")) as mock_call:
            translate_to_english("Guten Tag", "key")

        prompt_arg = mock_call.call_args.args[2]
        assert "Guten Tag" in prompt_arg


# ---------------------------------------------------------------------------
# Phase 2 — render_tokens_html
# ---------------------------------------------------------------------------


class TestRenderTokensHtml:
    """Unit tests for render_tokens_html(tokens, oov_words) -> str."""

    def test_returns_string(self):
        """render_tokens_html must return a string."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "Hello", "id": 1}, {"token": " world", "id": 2}]
        result = render_tokens_html(tokens, set())

        assert isinstance(result, str)

    def test_each_token_appears_in_output(self):
        """Each token text must appear somewhere in the HTML output."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "Hello", "id": 1}, {"token": " world", "id": 2}]
        result = render_tokens_html(tokens, set())

        assert "Hello" in result
        assert "world" in result

    def test_span_style_preserves_whitespace(self):
        """Token span style should preserve visible spaces between decoded chunks."""
        from tokenizer import render_tokens_html

        tokens = [{"token": " hello", "id": 1}]
        result = render_tokens_html(tokens, set())

        assert "white-space:pre" in result
        assert "color:#000" in result

    def test_oov_tokens_have_highlight_colour(self):
        """OOV tokens must be rendered with #ffcccc background."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "superlongword", "id": 99}]
        result = render_tokens_html(tokens, {"superlongword"})

        assert "#ffcccc" in result

    def test_normal_tokens_do_not_have_oov_highlight(self):
        """Non-OOV tokens must NOT be rendered with #ffcccc background."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "Hello", "id": 1}]
        result = render_tokens_html(tokens, set())

        assert "#ffcccc" not in result

    def test_alternating_bg_colours_for_normal_tokens(self):
        """Normal tokens alternate between two distinct background colours."""
        from tokenizer import render_tokens_html

        tokens = [
            {"token": "a", "id": 1},
            {"token": "b", "id": 2},
            {"token": "c", "id": 3},
        ]
        result = render_tokens_html(tokens, set())

        # Must have at least two different background colour values
        import re
        colours = re.findall(r"background[^;\"]*?:([^;\"]+)", result)
        unique = set(c.strip() for c in colours)
        assert len(unique) >= 2

    def test_html_escapes_special_chars_in_token(self):
        """Token text with < > & must be HTML-escaped."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "<br>", "id": 5}]
        result = render_tokens_html(tokens, set())

        assert "<br>" not in result
        assert "&lt;" in result

    def test_empty_tokens_returns_string(self):
        """Empty token list returns an empty or valid HTML string (no crash)."""
        from tokenizer import render_tokens_html

        result = render_tokens_html([], set())

        assert isinstance(result, str)

    def test_oov_word_matching_is_case_insensitive_or_exact(self):
        """OOV matching uses the exact word from the oov_words set."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "Cat", "id": 10}]
        result = render_tokens_html(tokens, {"Cat"})

        assert "#ffcccc" in result

    def test_decoded_view_hides_special_tokens_by_default(self):
        """Decoded view should skip special tokens like BOS when configured."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "<|begin_of_text|>", "id": 1}, {"token": "hello", "id": 2}]
        mock_tok = MagicMock()
        mock_tok.all_special_ids = [1]
        mock_tok.decode.side_effect = lambda ids, **kwargs: "" if ids == [1] else "hello"

        result = render_tokens_html(
            tokens,
            set(),
            tokenizer=mock_tok,
            decoded_view=True,
            hide_special_tokens=True,
        )

        assert "begin_of_text" not in result
        assert "hello" in result

    def test_decoded_view_can_show_readable_decoded_text(self):
        """Decoded view should prefer tokenizer.decode output over raw token text."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "Ġhello", "id": 42}]
        mock_tok = MagicMock()
        mock_tok.all_special_ids = []
        mock_tok.decode.return_value = " hello"

        result = render_tokens_html(
            tokens,
            set(),
            tokenizer=mock_tok,
            decoded_view=True,
            hide_special_tokens=True,
        )

        assert "Ġhello" not in result
        assert "hello" in result

    def test_decoded_view_handles_multibyte_text_via_cumulative_decode(self):
        """Readable mode should use cumulative decode chunks for multibyte scripts."""
        from tokenizer import render_tokens_html

        # Simulate a tokenizer where individual token decode is not readable,
        # but cumulative decode forms proper text.
        tokens = [
            {"token": "à®µ", "id": 10},
            {"token": "à®£", "id": 11},
            {"token": "à®ķ", "id": 12},
        ]
        mock_tok = MagicMock()
        mock_tok.all_special_ids = []

        def _decode(ids, **kwargs):
            if ids == [10]:
                return ""
            if ids == [10, 11]:
                return "வ"
            if ids == [10, 11, 12]:
                return "வண"
            return ""

        mock_tok.decode.side_effect = _decode

        result = render_tokens_html(
            tokens,
            set(),
            tokenizer=mock_tok,
            decoded_view=True,
            hide_special_tokens=True,
        )

        assert "à®µ" not in result
        assert "வ" in result

    def test_decoded_view_uses_byte_decoder_path_when_available(self):
        """Readable mode should prefer byte-decoder accumulation for byte-level tokens."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "A", "id": 1}, {"token": "B", "id": 2}]
        mock_tok = MagicMock()
        mock_tok.all_special_ids = []
        mock_tok.byte_decoder = {"A": 65, "B": 66}
        # If decode() were used, we'd see replacement chars; byte path should avoid this.
        mock_tok.decode.return_value = "��"

        result = render_tokens_html(
            tokens,
            set(),
            tokenizer=mock_tok,
            decoded_view=True,
            hide_special_tokens=True,
        )

        assert "��" not in result
        assert ">A</span>" in result
        assert ">B</span>" in result

    def test_decoded_view_prefers_convert_tokens_to_string_for_readable_output(self):
        """Readable mode should use convert_tokens_to_string when available."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "à®µ", "id": 1}, {"token": "à®£", "id": 2}]
        mock_tok = MagicMock()
        mock_tok.all_special_ids = []
        mock_tok.convert_tokens_to_string.side_effect = ["", "வ"]
        # If this decode path were used directly, we'd likely see noise.
        mock_tok.decode.return_value = "��"

        result = render_tokens_html(
            tokens,
            set(),
            tokenizer=mock_tok,
            decoded_view=True,
            hide_special_tokens=True,
        )

        assert "��" not in result
        assert "வ" in result

    def test_decoded_view_handles_replacement_prefix_drift(self):
        """If previous decoded text contains replacement chars, we should still recover new readable chars."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "x", "id": 1}, {"token": "y", "id": 2}]
        mock_tok = MagicMock()
        mock_tok.all_special_ids = []
        # Step 1 has replacement char, step 2 resolves to a real Tamil letter.
        mock_tok.convert_tokens_to_string.side_effect = ["�", "வ"]

        result = render_tokens_html(
            tokens,
            set(),
            tokenizer=mock_tok,
            decoded_view=True,
            hide_special_tokens=True,
        )

        assert "வ" in result


# ---------------------------------------------------------------------------
# Phase 3 — build_tokenizer_ui (smoke test)
# ---------------------------------------------------------------------------


class TestDecodedViewGenericFallbackEdgeCases:
    """Cover edge cases in the generic fallback decode path of render_tokens_html."""

    def test_decode_exception_falls_back_to_prev(self):
        """When tokenizer.decode raises, use previous decoded text."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "a", "id": 1}, {"token": "b", "id": 2}]
        mock_tok = MagicMock()
        mock_tok.all_special_ids = []
        # First call ok, second raises
        mock_tok.decode.side_effect = ["a", Exception("decode error")]

        result = render_tokens_html(
            tokens, set(), tokenizer=mock_tok,
            decoded_view=True, hide_special_tokens=True,
        )
        assert isinstance(result, str)

    def test_non_prefix_stable_decode_single_token_fallback(self):
        """When cumulative decode is not prefix-stable, fall back to single-token decode."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "a", "id": 1}, {"token": "b", "id": 2}]
        mock_tok = MagicMock()
        mock_tok.all_special_ids = []
        # Non-prefix-stable: second call returns something that doesn't start with first
        mock_tok.decode.side_effect = lambda ids, **kw: "a" if len(ids) == 1 and ids[0] == 1 else ("XY" if len(ids) == 2 else "b")

        result = render_tokens_html(
            tokens, set(), tokenizer=mock_tok,
            decoded_view=True, hide_special_tokens=True,
        )
        assert "b" in result

    def test_non_prefix_stable_single_decode_exception(self):
        """When single-token decode also raises, chunk is empty string."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "a", "id": 1}, {"token": "b", "id": 2}]
        mock_tok = MagicMock()
        mock_tok.all_special_ids = []
        call_count = [0]

        def _decode(ids, **kw):
            call_count[0] += 1
            if len(ids) == 1 and ids[0] == 1:
                return "a"
            if len(ids) == 2:
                return "XY"  # non-prefix-stable
            # Single-token fallback for id=2
            raise Exception("single decode failed")

        mock_tok.decode.side_effect = _decode

        result = render_tokens_html(
            tokens, set(), tokenizer=mock_tok,
            decoded_view=True, hide_special_tokens=True,
        )
        assert isinstance(result, str)

    def test_replacement_char_stripped_in_generic_fallback(self):
        """Replacement characters should be stripped in the generic fallback path."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "x", "id": 1}]
        mock_tok = MagicMock()
        mock_tok.all_special_ids = []
        mock_tok.decode.return_value = "he\ufffdllo"

        result = render_tokens_html(
            tokens, set(), tokenizer=mock_tok,
            decoded_view=True, hide_special_tokens=True,
        )
        assert "\ufffd" not in result
        assert "hello" in result

    def test_byte_decoder_hides_special_tokens(self):
        """Byte decoder path should hide special tokens when configured."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "<s>", "id": 1}, {"token": "A", "id": 2}]
        mock_tok = MagicMock()
        mock_tok.all_special_ids = [1]
        mock_tok.byte_decoder = {"A": 65}

        result = render_tokens_html(
            tokens, set(), tokenizer=mock_tok,
            decoded_view=True, hide_special_tokens=True,
        )
        assert "<s>" not in result
        assert ">A</span>" in result

    def test_byte_decoder_non_mapped_char(self):
        """Chars not in byte_decoder should encode via UTF-8 fallback."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "\u00e9", "id": 1}]  # é
        mock_tok = MagicMock()
        mock_tok.all_special_ids = []
        mock_tok.byte_decoder = {}  # empty dict but truthy... no, empty dict is falsy

        # Need a non-empty byte_decoder that doesn't contain the char
        mock_tok.byte_decoder = {"A": 65}

        result = render_tokens_html(
            tokens, set(), tokenizer=mock_tok,
            decoded_view=True, hide_special_tokens=True,
        )
        assert isinstance(result, str)

    def test_convert_tokens_to_string_exception_falls_to_next_path(self):
        """When convert_tokens_to_string raises, should fall through to byte or generic path."""
        from tokenizer import render_tokens_html

        tokens = [{"token": "hi", "id": 1}]
        mock_tok = MagicMock()
        mock_tok.all_special_ids = []
        mock_tok.convert_tokens_to_string.side_effect = Exception("not supported")
        mock_tok.decode.return_value = "hi"

        result = render_tokens_html(
            tokens, set(), tokenizer=mock_tok,
            decoded_view=True, hide_special_tokens=True,
        )
        assert "hi" in result


class TestHandleSingle:
    """Tests for _handle_single extracted handler."""

    def test_returns_html_and_stats(self):
        from tokenizer import _handle_single
        from unittest.mock import patch, MagicMock

        mock_tok = MagicMock()
        mock_tok.encode.return_value = [1, 2, 3]
        mock_tok.convert_ids_to_tokens.return_value = ["hello", "world", "!"]
        mock_tok.all_special_ids = []

        with patch("tokenizer.get_tokenizer", return_value=mock_tok):
            html, stats = _handle_single("gpt2", "hello world!", 3, False)

        assert isinstance(html, str)
        assert "**Tokens:** 3" in stats
        assert "**Fragmentation ratio:**" in stats
        assert "**Detected language:**" in stats

    def test_error_returns_empty_html_and_error_message(self):
        from tokenizer import _handle_single
        from unittest.mock import patch

        with patch("tokenizer.get_tokenizer", side_effect=ValueError("unknown")):
            html, stats = _handle_single("bad_model", "text", 3, False)

        assert html == ""
        assert "Error:" in stats

    def test_decoded_view_passed_through(self):
        from tokenizer import _handle_single
        from unittest.mock import patch, MagicMock

        mock_tok = MagicMock()
        mock_tok.encode.return_value = [1]
        mock_tok.convert_ids_to_tokens.return_value = ["hi"]
        mock_tok.all_special_ids = []
        mock_tok.decode.return_value = "hi"

        with patch("tokenizer.get_tokenizer", return_value=mock_tok):
            html, stats = _handle_single("gpt2", "hi", 3, True)

        assert isinstance(html, str)
        assert "**Tokens:** 1" in stats


class TestHandleCompare:
    """Tests for _handle_compare extracted handler."""

    def test_returns_two_html_and_ratio_markdown(self):
        from tokenizer import _handle_compare
        from unittest.mock import patch, MagicMock

        mock_tok_a = MagicMock()
        mock_tok_a.encode.return_value = [1, 2]
        mock_tok_a.convert_ids_to_tokens.return_value = ["he", "llo"]
        mock_tok_a.all_special_ids = []

        mock_tok_b = MagicMock()
        mock_tok_b.encode.return_value = [1, 2, 3, 4]
        mock_tok_b.convert_ids_to_tokens.return_value = ["h", "e", "l", "lo"]
        mock_tok_b.all_special_ids = []

        with patch("tokenizer.get_tokenizer", side_effect=[mock_tok_a, mock_tok_b]):
            html_a, html_b, ratio_md = _handle_compare("hello", "gpt2", "mistral", False)

        assert isinstance(html_a, str)
        assert isinstance(html_b, str)
        assert "**gpt2:** 2 tokens" in ratio_md
        assert "**mistral:** 4 tokens" in ratio_md

    def test_error_returns_empty_and_error_message(self):
        from tokenizer import _handle_compare
        from unittest.mock import patch

        with patch("tokenizer.get_tokenizer", side_effect=ValueError("bad")):
            html_a, html_b, ratio_md = _handle_compare("text", "bad", "bad2", False)

        assert html_a == ""
        assert html_b == ""
        assert "Error:" in ratio_md


class TestBuildTokenizerUi:
    """Smoke test for build_tokenizer_ui() -> gr.Blocks."""

    def test_returns_gradio_blocks(self):
        """build_tokenizer_ui() must return a Gradio Blocks instance without raising."""
        import gradio as gr
        from tokenizer import build_tokenizer_ui

        demo = build_tokenizer_ui()

        assert isinstance(demo, gr.Blocks)
