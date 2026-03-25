"""Tests for the Token Tax computation module (GH-5, GH-6)."""

import csv
import os
import tempfile

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# analyze_text_across_models
# ---------------------------------------------------------------------------


class TestAnalyzeTextAcrossModels:
    """Tests for analyze_text_across_models(text, english_text, model_names)."""

    REQUIRED_KEYS = {
        "model", "token_count", "rtc", "byte_premium",
        "context_usage", "risk_level", "cost_per_million",
    }

    def _mock_tokenizer(self, token_count: int):
        tok = MagicMock()
        tok.encode.return_value = list(range(token_count))
        tok.convert_ids_to_tokens.return_value = [f"t{i}" for i in range(token_count)]
        return tok

    def test_returns_list(self):
        from token_tax import analyze_text_across_models

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = analyze_text_across_models("hello world", "hello world", ["gpt2"])

        assert isinstance(result, list)

    def test_one_entry_per_model(self):
        from token_tax import analyze_text_across_models

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = analyze_text_across_models("hello", "hello", ["gpt2", "mistral"])

        assert len(result) == 2

    def test_each_entry_has_required_keys(self):
        from token_tax import analyze_text_across_models

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = analyze_text_across_models("hello", "hello", ["gpt2"])

        for entry in result:
            for key in self.REQUIRED_KEYS:
                assert key in entry, f"Missing key: {key}"

    def test_english_text_rtc_is_one(self):
        """When source == english, RTC should be 1.0."""
        from token_tax import analyze_text_across_models

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = analyze_text_across_models("hello world", "hello world", ["gpt2"])

        assert result[0]["rtc"] == pytest.approx(1.0)

    def test_non_english_rtc_above_one(self):
        """When source has more tokens than english, RTC > 1.0."""
        from token_tax import analyze_text_across_models

        source_tok = self._mock_tokenizer(10)
        english_tok = self._mock_tokenizer(5)

        with patch("token_tax.get_tokenizer", return_value=source_tok) as mock_get:
            # First call for source text returns 10 tokens, second for english returns 5
            mock_get.side_effect = [source_tok, source_tok]
            # We need to make tokenize_text return different counts for different texts
            with patch("token_tax.tokenize_text") as mock_tt:
                mock_tt.side_effect = [
                    [{"token": f"t{i}", "id": i} for i in range(10)],  # source
                    [{"token": f"t{i}", "id": i} for i in range(5)],   # english
                ]
                result = analyze_text_across_models("مرحبا", "hello", ["gpt2"])

        assert result[0]["rtc"] == pytest.approx(2.0)

    def test_no_english_text_rtc_is_one(self):
        """When english_text is None, RTC defaults to 1.0."""
        from token_tax import analyze_text_across_models

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = analyze_text_across_models("hello", None, ["gpt2"])

        assert result[0]["rtc"] == pytest.approx(1.0)

    def test_model_name_in_result(self):
        from token_tax import analyze_text_across_models

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(3)):
            result = analyze_text_across_models("hi", "hi", ["mistral"])

        assert result[0]["model"] == "mistral"

    def test_token_count_matches(self):
        from token_tax import analyze_text_across_models

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(7)):
            result = analyze_text_across_models("test text", "test text", ["gpt2"])

        assert result[0]["token_count"] == 7

    def test_cost_per_million_is_numeric(self):
        from token_tax import analyze_text_across_models

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = analyze_text_across_models("hi", "hi", ["gpt2"])

        assert isinstance(result[0]["cost_per_million"], (int, float))

    def test_empty_text_returns_zero_tokens(self):
        from token_tax import analyze_text_across_models

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(0)):
            result = analyze_text_across_models("", "", ["gpt2"])

        assert result[0]["token_count"] == 0


# ---------------------------------------------------------------------------
# cost_projection
# ---------------------------------------------------------------------------


class TestCostProjection:
    """Tests for cost_projection(token_count, price_per_million, monthly_requests, avg_tokens_per_request)."""

    def test_returns_dict_with_required_keys(self):
        from token_tax import cost_projection

        result = cost_projection(100, 0.05, 10000, 100)
        assert "monthly_cost" in result
        assert "annual_cost" in result

    def test_known_values(self):
        """10k requests × 100 tokens × $0.05/1M = $0.05/month."""
        from token_tax import cost_projection

        result = cost_projection(100, 0.05, 10000, 100)
        expected_monthly = (10000 * 100 * 0.05) / 1_000_000
        assert result["monthly_cost"] == pytest.approx(expected_monthly)
        assert result["annual_cost"] == pytest.approx(expected_monthly * 12)

    def test_zero_requests_returns_zero(self):
        from token_tax import cost_projection

        result = cost_projection(100, 0.05, 0, 100)
        assert result["monthly_cost"] == pytest.approx(0.0)
        assert result["annual_cost"] == pytest.approx(0.0)

    def test_zero_price_returns_zero(self):
        from token_tax import cost_projection

        result = cost_projection(100, 0.0, 10000, 100)
        assert result["monthly_cost"] == pytest.approx(0.0)

    def test_values_are_floats(self):
        from token_tax import cost_projection

        result = cost_projection(100, 0.05, 10000, 100)
        assert isinstance(result["monthly_cost"], float)
        assert isinstance(result["annual_cost"], float)


# ---------------------------------------------------------------------------
# generate_recommendations
# ---------------------------------------------------------------------------


class TestGenerateRecommendations:
    """Tests for generate_recommendations(analysis_results, language)."""

    def _make_result(self, model: str, rtc: float, cost: float, risk: str):
        return {
            "model": model, "token_count": 100, "rtc": rtc,
            "byte_premium": 1.0, "context_usage": 0.01,
            "risk_level": risk, "cost_per_million": cost,
        }

    def test_returns_nonempty_string(self):
        from token_tax import generate_recommendations

        results = [self._make_result("gpt2", 1.0, 0.0, "low")]
        rec = generate_recommendations(results, "en")
        assert isinstance(rec, str)
        assert len(rec) > 0

    def test_mentions_cheapest_model(self):
        from token_tax import generate_recommendations

        results = [
            self._make_result("gpt2", 1.0, 0.0, "low"),
            self._make_result("mistral", 2.0, 0.04, "moderate"),
        ]
        rec = generate_recommendations(results, "ar")
        assert "gpt2" in rec.lower()

    def test_flags_high_risk_models(self):
        from token_tax import generate_recommendations

        results = [
            self._make_result("gpt2", 4.5, 0.0, "severe"),
            self._make_result("mistral", 1.5, 0.04, "moderate"),
        ]
        rec = generate_recommendations(results, "th")
        assert "severe" in rec.lower() or "risk" in rec.lower()

    def test_single_model_no_crash(self):
        from token_tax import generate_recommendations

        results = [self._make_result("gpt2", 1.0, 0.0, "low")]
        rec = generate_recommendations(results, "en")
        assert isinstance(rec, str)

    def test_empty_results_returns_string(self):
        from token_tax import generate_recommendations

        rec = generate_recommendations([], "en")
        assert isinstance(rec, str)


# ---------------------------------------------------------------------------
# SAMPLE_PHRASES (GH-6)
# ---------------------------------------------------------------------------


class TestSamplePhrases:
    """Tests for SAMPLE_PHRASES dict."""

    REQUIRED_LANGUAGES = {
        "en", "zh", "ar", "hi", "ja", "ko", "fr", "de", "es", "pt",
        "ru", "th", "vi", "bn", "ta",
    }

    def test_has_at_least_15_languages(self):
        from token_tax import SAMPLE_PHRASES

        assert len(SAMPLE_PHRASES) >= 15

    def test_all_values_are_nonempty_strings(self):
        from token_tax import SAMPLE_PHRASES

        for lang, phrase in SAMPLE_PHRASES.items():
            assert isinstance(phrase, str), f"{lang}"
            assert len(phrase.strip()) > 0, f"{lang} is empty"

    def test_includes_required_languages(self):
        from token_tax import SAMPLE_PHRASES

        for lang in self.REQUIRED_LANGUAGES:
            assert lang in SAMPLE_PHRASES, f"Missing language: {lang}"

    def test_keys_are_lowercase_bcp47(self):
        from token_tax import SAMPLE_PHRASES

        for lang in SAMPLE_PHRASES:
            assert lang == lang.lower(), f"{lang} not lowercase"
            assert len(lang) >= 2, f"{lang} too short"


# ---------------------------------------------------------------------------
# parse_traffic_csv (GH-6)
# ---------------------------------------------------------------------------


def _write_csv(rows: list[list[str]], headers: list[str] | None = None) -> str:
    """Write rows to a temp CSV and return the file path."""
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", newline="") as f:
        writer = csv.writer(f)
        if headers:
            writer.writerow(headers)
        writer.writerows(rows)
    return path


class TestParseTrafficCsv:
    """Tests for parse_traffic_csv(file_path) -> list[dict]."""

    def test_valid_csv_returns_list_of_dicts(self):
        from token_tax import parse_traffic_csv

        path = _write_csv(
            [["en", "1000", "500"], ["ar", "2000", "300"]],
            headers=["language", "request_count", "avg_chars"],
        )
        try:
            result = parse_traffic_csv(path)
            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["language"] == "en"
            assert result[0]["request_count"] == 1000
            assert result[0]["avg_chars"] == 500
        finally:
            os.unlink(path)

    def test_missing_column_raises_value_error(self):
        from token_tax import parse_traffic_csv

        path = _write_csv(
            [["en", "1000"]],
            headers=["language", "request_count"],  # missing avg_chars
        )
        try:
            with pytest.raises(ValueError, match="avg_chars"):
                parse_traffic_csv(path)
        finally:
            os.unlink(path)

    def test_empty_csv_returns_empty_list(self):
        from token_tax import parse_traffic_csv

        path = _write_csv(
            [],
            headers=["language", "request_count", "avg_chars"],
        )
        try:
            result = parse_traffic_csv(path)
            assert result == []
        finally:
            os.unlink(path)

    def test_non_numeric_request_count_raises(self):
        from token_tax import parse_traffic_csv

        path = _write_csv(
            [["en", "abc", "500"]],
            headers=["language", "request_count", "avg_chars"],
        )
        try:
            with pytest.raises(ValueError):
                parse_traffic_csv(path)
        finally:
            os.unlink(path)

    def test_extra_columns_ignored(self):
        from token_tax import parse_traffic_csv

        path = _write_csv(
            [["en", "1000", "500", "extra_data"]],
            headers=["language", "request_count", "avg_chars", "notes"],
        )
        try:
            result = parse_traffic_csv(path)
            assert len(result) == 1
            assert "notes" not in result[0]
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# portfolio_analysis (GH-6)
# ---------------------------------------------------------------------------


class TestPortfolioAnalysis:
    """Tests for portfolio_analysis(traffic_data, model_name)."""

    def _mock_tokenizer(self, token_count: int):
        tok = MagicMock()
        tok.encode.return_value = list(range(token_count))
        tok.convert_ids_to_tokens.return_value = [f"t{i}" for i in range(token_count)]
        return tok

    def test_returns_dict_with_required_keys(self):
        from token_tax import portfolio_analysis

        data = [{"language": "en", "request_count": 1000, "avg_chars": 500}]
        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = portfolio_analysis(data, "gpt2")

        assert "total_monthly_cost" in result
        assert "languages" in result
        assert "token_tax_exposure" in result

    def test_languages_list_has_entries(self):
        from token_tax import portfolio_analysis

        data = [
            {"language": "en", "request_count": 1000, "avg_chars": 500},
            {"language": "ar", "request_count": 2000, "avg_chars": 300},
        ]
        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = portfolio_analysis(data, "gpt2")

        assert len(result["languages"]) == 2

    def test_each_language_entry_has_required_keys(self):
        from token_tax import portfolio_analysis

        data = [{"language": "en", "request_count": 1000, "avg_chars": 500}]
        required = {"language", "traffic_share", "token_count", "rtc", "cost_share", "tax_ratio"}

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = portfolio_analysis(data, "gpt2")

        for entry in result["languages"]:
            for key in required:
                assert key in entry, f"Missing key: {key}"

    def test_traffic_shares_sum_to_one(self):
        from token_tax import portfolio_analysis

        data = [
            {"language": "en", "request_count": 500, "avg_chars": 500},
            {"language": "ar", "request_count": 500, "avg_chars": 300},
        ]
        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = portfolio_analysis(data, "gpt2")

        total_share = sum(e["traffic_share"] for e in result["languages"])
        assert total_share == pytest.approx(1.0)

    def test_cost_shares_sum_to_one(self):
        from token_tax import portfolio_analysis

        data = [
            {"language": "en", "request_count": 500, "avg_chars": 500},
            {"language": "ar", "request_count": 500, "avg_chars": 300},
        ]
        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = portfolio_analysis(data, "gpt2")

        total_share = sum(e["cost_share"] for e in result["languages"])
        assert total_share == pytest.approx(1.0)

    def test_unknown_language_falls_back_to_english(self):
        """Language not in SAMPLE_PHRASES should not crash."""
        from token_tax import portfolio_analysis

        data = [{"language": "xx", "request_count": 1000, "avg_chars": 500}]
        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = portfolio_analysis(data, "gpt2")

        assert len(result["languages"]) == 1

    def test_empty_data_returns_zero_exposure(self):
        from token_tax import portfolio_analysis

        result = portfolio_analysis([], "gpt2")
        assert result["total_monthly_cost"] == pytest.approx(0.0)
        assert result["token_tax_exposure"] == pytest.approx(1.0)
        assert result["languages"] == []
