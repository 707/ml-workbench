"""Tests for the Token Tax computation module (GH-5, GH-6)."""

import csv
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# analyze_text_across_models
# ---------------------------------------------------------------------------


class TestAnalyzeTextAcrossModels:
    """Tests for analyze_text_across_models(text, english_text, model_names)."""

    REQUIRED_KEYS = {
        "model", "token_count", "rtc", "byte_premium",
        "context_usage", "risk_level", "cost_per_million",
        "token_fertility",
    }

    def _mock_tokenizer(self, token_count: int):
        tok = MagicMock()
        tok.encode.return_value = list(range(token_count))
        tok.convert_ids_to_tokens.return_value = [f"t{i}" for i in range(token_count)]
        return tok

    def test_returns_list(self):
        from workbench.token_tax import analyze_text_across_models

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = analyze_text_across_models("hello world", "hello world", ["gpt2"])

        assert isinstance(result, list)

    def test_one_entry_per_model(self):
        from workbench.token_tax import analyze_text_across_models

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = analyze_text_across_models("hello", "hello", ["gpt2", "mistral"])

        assert len(result) == 2

    def test_each_entry_has_required_keys(self):
        from workbench.token_tax import analyze_text_across_models

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = analyze_text_across_models("hello", "hello", ["gpt2"])

        for entry in result:
            for key in self.REQUIRED_KEYS:
                assert key in entry, f"Missing key: {key}"

    def test_english_text_rtc_is_one(self):
        """When source == english, RTC should be 1.0."""
        from workbench.token_tax import analyze_text_across_models

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = analyze_text_across_models("hello world", "hello world", ["gpt2"])

        assert result[0]["rtc"] == pytest.approx(1.0)

    def test_non_english_rtc_above_one(self):
        """When source has more tokens than english, RTC > 1.0."""
        from workbench.token_tax import analyze_text_across_models

        source_tok = self._mock_tokenizer(10)
        with patch("workbench.token_tax.get_tokenizer", return_value=source_tok) as mock_get:
            # First call for source text returns 10 tokens, second for english returns 5
            mock_get.side_effect = [source_tok, source_tok]
            # We need to make tokenize_text return different counts for different texts
            with patch("workbench.token_tax.tokenize_text") as mock_tt:
                mock_tt.side_effect = [
                    [{"token": f"t{i}", "id": i} for i in range(10)],  # source
                    [{"token": f"t{i}", "id": i} for i in range(5)],   # english
                ]
                result = analyze_text_across_models("مرحبا", "hello", ["gpt2"])

        assert result[0]["rtc"] == pytest.approx(2.0)

    def test_no_english_text_rtc_is_one(self):
        """When english_text is None, RTC defaults to 1.0."""
        from workbench.token_tax import analyze_text_across_models

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = analyze_text_across_models("hello", None, ["gpt2"])

        assert result[0]["rtc"] == pytest.approx(1.0)

    def test_model_name_in_result(self):
        from workbench.token_tax import analyze_text_across_models

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(3)):
            result = analyze_text_across_models("hi", "hi", ["mistral"])

        assert result[0]["model"] == "mistral"

    def test_token_count_matches(self):
        from workbench.token_tax import analyze_text_across_models

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(7)):
            result = analyze_text_across_models("test text", "test text", ["gpt2"])

        assert result[0]["token_count"] == 7

    def test_cost_per_million_is_numeric(self):
        from workbench.token_tax import analyze_text_across_models

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = analyze_text_across_models("hi", "hi", ["gpt2"])

        assert isinstance(result[0]["cost_per_million"], (int, float))

    def test_empty_text_returns_zero_tokens(self):
        from workbench.token_tax import analyze_text_across_models

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(0)):
            result = analyze_text_across_models("", "", ["gpt2"])

        assert result[0]["token_count"] == 0


# ---------------------------------------------------------------------------
# benchmark_all (Issue 7)
# ---------------------------------------------------------------------------


class TestBenchmarkAll:
    """Tests for benchmark_all(languages, model_names)."""

    def _mock_tokenizer(self, token_count: int):
        tok = MagicMock()
        tok.encode.return_value = list(range(token_count))
        tok.convert_ids_to_tokens.return_value = [f"t{i}" for i in range(token_count)]
        return tok

    def test_returns_dict(self):
        from workbench.token_tax import benchmark_all

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = benchmark_all(["en"], ["gpt2"])
        assert isinstance(result, dict)

    def test_keys_are_tuples(self):
        from workbench.token_tax import benchmark_all

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = benchmark_all(["en", "ar"], ["gpt2"])
        for key in result:
            assert isinstance(key, tuple)
            assert len(key) == 2

    def test_correct_number_of_entries(self):
        from workbench.token_tax import benchmark_all

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = benchmark_all(["en", "ar"], ["gpt2", "mistral"])
        assert len(result) == 4  # 2 languages × 2 models

    def test_each_entry_has_rtc_and_token_count(self):
        from workbench.token_tax import benchmark_all

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = benchmark_all(["en"], ["gpt2"])
        entry = result[("en", "gpt2")]
        assert "rtc" in entry
        assert "token_count" in entry

    def test_english_rtc_is_one(self):
        from workbench.token_tax import benchmark_all

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = benchmark_all(["en"], ["gpt2"])
        assert result[("en", "gpt2")]["rtc"] == pytest.approx(1.0)

    def test_empty_languages_returns_empty(self):
        from workbench.token_tax import benchmark_all

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = benchmark_all([], ["gpt2"])
        assert result == {}

    def test_empty_models_returns_empty(self):
        from workbench.token_tax import benchmark_all

        result = benchmark_all(["en"], [])
        assert result == {}


# ---------------------------------------------------------------------------
# run_benchmark (Issue 9)
# ---------------------------------------------------------------------------


class TestRunBenchmark:
    """Tests for run_benchmark(languages, model_names)."""

    def _mock_tokenizer(self, token_count: int):
        tok = MagicMock()
        tok.encode.return_value = list(range(token_count))
        tok.convert_ids_to_tokens.return_value = [f"t{i}" for i in range(token_count)]
        return tok

    def test_returns_list(self):
        from workbench.token_tax import run_benchmark

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = run_benchmark(["en", "ar"], ["gpt2"])
        assert isinstance(result, list)

    def test_one_entry_per_language_model_pair(self):
        from workbench.token_tax import run_benchmark

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = run_benchmark(["en", "ar"], ["gpt2", "mistral"])
        # 2 languages × 2 models = 4, but results grouped by language
        assert len(result) == 2  # 2 languages
        assert len(result[0]["models"]) == 2

    def test_each_entry_has_language_and_models(self):
        from workbench.token_tax import run_benchmark

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = run_benchmark(["en"], ["gpt2"])
        entry = result[0]
        assert "language" in entry
        assert "models" in entry

    def test_model_entry_has_required_keys(self):
        from workbench.token_tax import run_benchmark

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = run_benchmark(["en"], ["gpt2"])
        model_entry = result[0]["models"][0]
        for key in ("model", "token_count", "rtc", "risk_level"):
            assert key in model_entry, f"Missing key: {key}"

    def test_none_languages_uses_all_sample_phrases(self):
        from workbench.token_tax import SAMPLE_PHRASES, run_benchmark

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = run_benchmark(None, ["gpt2"])
        assert len(result) == len(SAMPLE_PHRASES)

    def test_empty_models_returns_empty(self):
        from workbench.token_tax import run_benchmark

        result = run_benchmark(["en"], [])
        assert result == []

    def test_english_rtc_is_one(self):
        from workbench.token_tax import run_benchmark

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = run_benchmark(["en"], ["gpt2"])
        model_entry = result[0]["models"][0]
        assert model_entry["rtc"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# cost_projection
# ---------------------------------------------------------------------------


class TestCostProjection:
    """Tests for cost_projection(token_count, price_per_million, monthly_requests, avg_tokens_per_request)."""

    def test_returns_dict_with_required_keys(self):
        from workbench.token_tax import cost_projection

        result = cost_projection(100, 0.05, 10000, 100)
        assert "monthly_cost" in result
        assert "annual_cost" in result

    def test_known_values(self):
        """10k requests × 100 tokens × $0.05/1M = $0.05/month."""
        from workbench.token_tax import cost_projection

        result = cost_projection(100, 0.05, 10000, 100)
        expected_monthly = (10000 * 100 * 0.05) / 1_000_000
        assert result["monthly_cost"] == pytest.approx(expected_monthly)
        assert result["annual_cost"] == pytest.approx(expected_monthly * 12)

    def test_zero_requests_returns_zero(self):
        from workbench.token_tax import cost_projection

        result = cost_projection(100, 0.05, 0, 100)
        assert result["monthly_cost"] == pytest.approx(0.0)
        assert result["annual_cost"] == pytest.approx(0.0)

    def test_zero_price_returns_zero(self):
        from workbench.token_tax import cost_projection

        result = cost_projection(100, 0.0, 10000, 100)
        assert result["monthly_cost"] == pytest.approx(0.0)

    def test_values_are_floats(self):
        from workbench.token_tax import cost_projection

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

    def test_returns_dict(self):
        from workbench.token_tax import generate_recommendations

        results = [self._make_result("gpt2", 1.0, 0.0, "low")]
        rec = generate_recommendations(results, "en")
        assert isinstance(rec, dict)

    def test_has_required_keys(self):
        from workbench.token_tax import generate_recommendations

        results = [self._make_result("gpt2", 1.0, 0.0, "low")]
        rec = generate_recommendations(results, "en")
        for key in ("best_model", "risk_warnings", "mitigations", "executive_summary"):
            assert key in rec, f"Missing key: {key}"

    def test_best_model_is_dict(self):
        from workbench.token_tax import generate_recommendations

        results = [
            self._make_result("gpt2", 1.0, 0.0, "low"),
            self._make_result("mistral", 2.0, 0.04, "moderate"),
        ]
        rec = generate_recommendations(results, "ar")
        assert isinstance(rec["best_model"], dict)
        assert "name" in rec["best_model"]
        assert "reason" in rec["best_model"]

    def test_flags_high_risk_models(self):
        from workbench.token_tax import generate_recommendations

        results = [
            self._make_result("gpt2", 4.5, 0.0, "severe"),
            self._make_result("mistral", 1.5, 0.04, "moderate"),
        ]
        rec = generate_recommendations(results, "th")
        assert len(rec["risk_warnings"]) > 0

    def test_mitigations_for_high_rtc(self):
        from workbench.token_tax import generate_recommendations

        results = [self._make_result("gpt2", 3.0, 0.0, "high")]
        rec = generate_recommendations(results, "ar")
        assert len(rec["mitigations"]) > 0

    def test_no_mitigations_for_english(self):
        from workbench.token_tax import generate_recommendations

        results = [self._make_result("gpt2", 1.0, 0.0, "low")]
        rec = generate_recommendations(results, "en")
        assert len(rec["mitigations"]) == 0

    def test_executive_summary_is_string(self):
        from workbench.token_tax import generate_recommendations

        results = [self._make_result("gpt2", 1.0, 0.0, "low")]
        rec = generate_recommendations(results, "en")
        assert isinstance(rec["executive_summary"], str)
        assert len(rec["executive_summary"]) > 0

    def test_empty_results_returns_dict(self):
        from workbench.token_tax import generate_recommendations

        rec = generate_recommendations([], "en")
        assert isinstance(rec, dict)

    def test_single_model_no_crash(self):
        from workbench.token_tax import generate_recommendations

        results = [self._make_result("gpt2", 1.0, 0.0, "low")]
        rec = generate_recommendations(results, "en")
        assert isinstance(rec, dict)


# ---------------------------------------------------------------------------
# export_csv / export_json (Issue 12)
# ---------------------------------------------------------------------------


class TestExportCsv:
    """Tests for export_csv(results) -> str."""

    SAMPLE = [
        {"model": "gpt2", "token_count": 20, "token_fertility": 1.5, "rtc": 1.0,
         "byte_premium": 1.0, "context_usage": 0.02, "risk_level": "low",
         "cost_per_million": 0.0},
    ]

    def test_returns_string(self):
        from workbench.token_tax import export_csv

        result = export_csv(self.SAMPLE)
        assert isinstance(result, str)

    def test_contains_header_row(self):
        from workbench.token_tax import export_csv

        result = export_csv(self.SAMPLE)
        first_line = result.strip().split("\n")[0]
        assert "model" in first_line
        assert "token_count" in first_line

    def test_contains_data_row(self):
        from workbench.token_tax import export_csv

        result = export_csv(self.SAMPLE)
        lines = result.strip().split("\n")
        assert len(lines) >= 2
        assert "gpt2" in lines[1]

    def test_multiple_rows(self):
        from workbench.token_tax import export_csv

        data = self.SAMPLE + [
            {"model": "mistral", "token_count": 30, "token_fertility": 2.0, "rtc": 1.5,
             "byte_premium": 1.1, "context_usage": 0.001, "risk_level": "moderate",
             "cost_per_million": 0.04},
        ]
        result = export_csv(data)
        lines = result.strip().split("\n")
        assert len(lines) == 3  # header + 2 rows

    def test_empty_returns_header_only(self):
        from workbench.token_tax import export_csv

        result = export_csv([])
        lines = result.strip().split("\n")
        assert len(lines) == 1  # header only


class TestExportJson:
    """Tests for export_json(results) -> str."""

    SAMPLE = [
        {"model": "gpt2", "token_count": 20, "token_fertility": 1.5, "rtc": 1.0,
         "byte_premium": 1.0, "context_usage": 0.02, "risk_level": "low",
         "cost_per_million": 0.0},
    ]

    def test_returns_string(self):
        from workbench.token_tax import export_json

        result = export_json(self.SAMPLE)
        assert isinstance(result, str)

    def test_valid_json(self):
        import json

        from workbench.token_tax import export_json

        result = export_json(self.SAMPLE)
        parsed = json.loads(result)
        assert isinstance(parsed, list)

    def test_preserves_data(self):
        import json

        from workbench.token_tax import export_json

        result = export_json(self.SAMPLE)
        parsed = json.loads(result)
        assert parsed[0]["model"] == "gpt2"
        assert parsed[0]["token_count"] == 20

    def test_empty_returns_empty_list(self):
        import json

        from workbench.token_tax import export_json

        result = export_json([])
        parsed = json.loads(result)
        assert parsed == []


class TestBenchmarkDetails:
    def test_build_benchmark_detail_rows_returns_previewable_raw_rows(self):
        from workbench.corpora import CorpusSample
        from workbench.token_tax import build_benchmark_detail_rows

        samples = {
            "fr": [
                CorpusSample("fr", "Bonjour le monde", "Hello world", "strict_parallel", "https://example.com", "strict_verified"),
            ],
        }

        class _Tok:
            def encode(self, text, add_special_tokens=True):
                return [1, 2, 3]

            def convert_ids_to_tokens(self, token_ids):
                return ["Bon", "jour", "monde"]

        with patch("workbench.token_tax.fetch_corpus_samples", return_value=samples):
            with patch("workbench.token_tax.get_tokenizer", return_value=_Tok()):
                rows = build_benchmark_detail_rows("strict_parallel", ["fr"], ["gpt2"], row_limit=5)

        assert rows[0]["lane"] == "Strict Evidence"
        assert rows[0]["token_preview"]
        assert rows[0]["sample_index"] == 0
        assert rows[0]["token_texts"] == ["Bon", "jour", "monde"]

    def test_benchmark_corpus_returns_lightweight_raw_rows_without_token_texts(self):
        from workbench.corpora import CorpusSample
        from workbench.token_tax import benchmark_corpus

        samples = {
            "fr": [
                CorpusSample("fr", "Bonjour le monde", "Hello world", "strict_parallel", "https://example.com", "strict_verified"),
            ],
        }

        class _Tok:
            def encode(self, text, add_special_tokens=True):
                return [1, 2, 3]

            def convert_ids_to_tokens(self, token_ids):
                return ["Bon", "jour", "monde"]

        with patch("workbench.token_tax.fetch_corpus_samples", return_value=samples):
            with patch("workbench.token_tax.get_tokenizer", return_value=_Tok()):
                result = benchmark_corpus(
                    "strict_parallel",
                    ["fr"],
                    ["gpt2"],
                    row_limit=5,
                    include_raw_rows=True,
                )

        assert result["raw_rows"][0]["token_preview"] == "Bon | jour | monde"
        assert "token_texts" not in result["raw_rows"][0]
        assert result["composition_rows"][0]["token_count"] == 3

    def test_iter_benchmark_rows_dedupes_unique_tokens_across_selected_rows(self):
        from workbench.corpora import CorpusSample
        from workbench.token_tax import iter_benchmark_rows

        samples = {
            "fr": [
                CorpusSample("fr", "Bonjour", "Hello", "streaming_exploration", "https://example.com", "research_forward"),
                CorpusSample("fr", "Salut", "Hi", "streaming_exploration", "https://example.com", "research_forward"),
            ],
            "en": [
                CorpusSample("en", "Hello", "Hello", "streaming_exploration", "https://example.com", "research_forward"),
            ],
        }

        metrics = [
            {
                "token_count": 2,
                "token_fertility": 1.0,
                "bytes_per_token": 1.5,
                "unique_tokens": 2,
                "continued_word_rate": 0.0,
                "token_texts": ["Hello", "world"],
                "english_baseline_ratio": None,
                "byte_premium": None,
                "risk_level": "low",
            },
            {
                "token_count": 3,
                "token_fertility": 1.0,
                "bytes_per_token": 2.0,
                "unique_tokens": 2,
                "continued_word_rate": 0.25,
                "token_texts": ["Bon", "jour", "Bon"],
                "english_baseline_ratio": None,
                "byte_premium": None,
                "risk_level": "low",
            },
            {
                "token_count": 2,
                "token_fertility": 1.0,
                "bytes_per_token": 1.5,
                "unique_tokens": 2,
                "continued_word_rate": 0.1,
                "token_texts": ["jour", "Salut"],
                "english_baseline_ratio": None,
                "byte_premium": None,
                "risk_level": "low",
            },
        ]

        with patch("workbench.token_tax.fetch_corpus_samples", return_value=samples):
            with patch("workbench.token_tax._sample_metrics", side_effect=metrics):
                rows = list(iter_benchmark_rows("streaming_exploration", ["fr"], ["gpt2"], row_limit=5))

        assert rows[0]["unique_tokens"] == 3

    def test_iter_benchmark_rows_skips_tokenizers_that_fail_to_load(self):
        from workbench.corpora import CorpusSample
        from workbench.token_tax import iter_benchmark_rows

        samples = {
            "en": [
                CorpusSample("en", "Hello world", "Hello world", "strict_parallel", "https://example.com", "strict_verified"),
            ],
        }

        class _Tok:
            def encode(self, text, add_special_tokens=True):
                return [1, 2]

            def convert_ids_to_tokens(self, token_ids):
                return ["Hello", "world"]

        def _fake_get_tokenizer(name):
            if name == "llama-3":
                raise RuntimeError("download stalled")
            return _Tok()

        with patch("workbench.token_tax.fetch_corpus_samples", return_value=samples):
            with patch("workbench.token_tax.get_tokenizer", side_effect=_fake_get_tokenizer):
                rows = list(
                    iter_benchmark_rows(
                        "strict_parallel",
                        ["en"],
                        ["llama-3", "gpt2"],
                        row_limit=5,
                    )
                )

        assert len(rows) == 1
        assert rows[0]["tokenizer_key"] == "gpt2"


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
        from workbench.token_tax import SAMPLE_PHRASES

        assert len(SAMPLE_PHRASES) >= 15

    def test_all_values_are_nonempty_strings(self):
        from workbench.token_tax import SAMPLE_PHRASES

        for lang, phrase in SAMPLE_PHRASES.items():
            assert isinstance(phrase, str), f"{lang}"
            assert len(phrase.strip()) > 0, f"{lang} is empty"

    def test_includes_required_languages(self):
        from workbench.token_tax import SAMPLE_PHRASES

        for lang in self.REQUIRED_LANGUAGES:
            assert lang in SAMPLE_PHRASES, f"Missing language: {lang}"

    def test_keys_are_lowercase_bcp47(self):
        from workbench.token_tax import SAMPLE_PHRASES

        for lang in SAMPLE_PHRASES:
            assert lang == lang.lower(), f"{lang} not lowercase"
            assert len(lang) >= 2, f"{lang} too short"


class TestLegacyCharsPerToken:
    """The legacy estimator ratio must be a named constant, not a magic number."""

    def test_constant_exists_and_equals_four(self):
        from workbench.token_tax import LEGACY_CHARS_PER_TOKEN

        assert isinstance(LEGACY_CHARS_PER_TOKEN, float)
        assert LEGACY_CHARS_PER_TOKEN == 4.0

    def test_portfolio_analysis_uses_named_constant(self):
        """portfolio_analysis source must reference the constant, not a magic 4.0."""
        import inspect

        import workbench.token_tax as token_tax

        source = inspect.getsource(token_tax.portfolio_analysis)
        assert "LEGACY_CHARS_PER_TOKEN" in source
        assert "/ 4.0)" not in source

    def test_scenario_appendix_labels_strict_method_against_legacy_estimator(self):
        from workbench.token_tax import scenario_appendix

        markdown = scenario_appendix()

        assert "Strict benchmark-driven estimate" in markdown
        assert "Legacy heuristic estimate" in markdown


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
        from workbench.token_tax import parse_traffic_csv

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
        from workbench.token_tax import parse_traffic_csv

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
        from workbench.token_tax import parse_traffic_csv

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
        from workbench.token_tax import parse_traffic_csv

        path = _write_csv(
            [["en", "abc", "500"]],
            headers=["language", "request_count", "avg_chars"],
        )
        try:
            with pytest.raises(ValueError, match="Row 2"):
                parse_traffic_csv(path)
        finally:
            os.unlink(path)

    def test_non_numeric_avg_chars_raises(self):
        from workbench.token_tax import parse_traffic_csv

        path = _write_csv(
            [["en", "1000", "xyz"]],
            headers=["language", "request_count", "avg_chars"],
        )
        try:
            with pytest.raises(ValueError, match="Row 2"):
                parse_traffic_csv(path)
        finally:
            os.unlink(path)

    def test_extra_columns_ignored(self):
        from workbench.token_tax import parse_traffic_csv

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
        from workbench.token_tax import portfolio_analysis

        data = [{"language": "en", "request_count": 1000, "avg_chars": 500}]
        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = portfolio_analysis(data, "gpt2")

        assert "total_monthly_cost" in result
        assert "languages" in result
        assert "token_tax_exposure" in result

    def test_languages_list_has_entries(self):
        from workbench.token_tax import portfolio_analysis

        data = [
            {"language": "en", "request_count": 1000, "avg_chars": 500},
            {"language": "ar", "request_count": 2000, "avg_chars": 300},
        ]
        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = portfolio_analysis(data, "gpt2")

        assert len(result["languages"]) == 2

    def test_each_language_entry_has_required_keys(self):
        from workbench.token_tax import portfolio_analysis

        data = [{"language": "en", "request_count": 1000, "avg_chars": 500}]
        required = {"language", "traffic_share", "token_count", "rtc", "cost_share", "tax_ratio"}

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = portfolio_analysis(data, "gpt2")

        for entry in result["languages"]:
            for key in required:
                assert key in entry, f"Missing key: {key}"

    def test_traffic_shares_sum_to_one(self):
        from workbench.token_tax import portfolio_analysis

        data = [
            {"language": "en", "request_count": 500, "avg_chars": 500},
            {"language": "ar", "request_count": 500, "avg_chars": 300},
        ]
        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = portfolio_analysis(data, "gpt2")

        total_share = sum(e["traffic_share"] for e in result["languages"])
        assert total_share == pytest.approx(1.0)

    def test_cost_shares_sum_to_one(self):
        from workbench.token_tax import portfolio_analysis

        data = [
            {"language": "en", "request_count": 500, "avg_chars": 500},
            {"language": "ar", "request_count": 500, "avg_chars": 300},
        ]
        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = portfolio_analysis(data, "gpt2")

        total_share = sum(e["cost_share"] for e in result["languages"])
        assert total_share == pytest.approx(1.0)

    def test_unknown_language_falls_back_to_english(self):
        """Language not in SAMPLE_PHRASES should use English phrase → RTC 1.0."""
        from workbench.token_tax import portfolio_analysis

        data = [{"language": "xx", "request_count": 1000, "avg_chars": 500}]
        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = portfolio_analysis(data, "gpt2")

        assert len(result["languages"]) == 1
        assert result["languages"][0]["language"] == "xx"
        assert result["languages"][0]["rtc"] == pytest.approx(1.0)

    def test_token_tax_exposure_is_weighted_average(self):
        """token_tax_exposure == sum(rtc_i * traffic_share_i)."""
        from workbench.token_tax import portfolio_analysis

        data = [
            {"language": "en", "request_count": 600, "avg_chars": 500},
            {"language": "ar", "request_count": 400, "avg_chars": 300},
        ]
        en_tokens = [{"token": f"t{i}", "id": i} for i in range(5)]
        ar_tokens = [{"token": f"t{i}", "id": i} for i in range(10)]

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            with patch("workbench.token_tax.tokenize_text") as mock_tt:
                # Call order: English baseline, then en phrase, then ar phrase
                mock_tt.side_effect = [
                    en_tokens,   # English baseline
                    en_tokens,   # "en" language row
                    ar_tokens,   # "ar" language row
                ]
                result = portfolio_analysis(data, "gpt2")

        # en: RTC = 5/5 = 1.0, traffic_share = 0.6
        # ar: RTC = 10/5 = 2.0, traffic_share = 0.4
        # weighted = 1.0 * 0.6 + 2.0 * 0.4 = 1.4
        assert result["token_tax_exposure"] == pytest.approx(1.4)

    def test_empty_data_returns_zero_exposure(self):
        from workbench.token_tax import portfolio_analysis

        result = portfolio_analysis([], "gpt2")
        assert result["total_monthly_cost"] == pytest.approx(0.0)
        assert result["token_tax_exposure"] == pytest.approx(1.0)
        assert result["languages"] == []


# ---------------------------------------------------------------------------
# _is_continued_token — tokenizer-family-aware heuristic
# ---------------------------------------------------------------------------


class TestIsContinuedToken:
    """Tests for _is_continued_token(token_text, tokenizer_key)."""

    # ------------------------------------------------------------------
    # Universal pre-checks (apply before family logic)
    # ------------------------------------------------------------------

    def test_empty_string_not_continued_for_any_family(self):
        from workbench.token_tax import _is_continued_token

        for key in ("o200k_base", "cl100k_base", "gpt2", "llama-3", "mistral",
                    "qwen-2.5", "gemma-2", "unknown_family"):
            assert _is_continued_token("", key) is False, f"Failed for {key}"

    def test_whitespace_only_not_continued(self):
        from workbench.token_tax import _is_continued_token

        assert _is_continued_token("   ", "o200k_base") is False

    def test_punctuation_not_continued_regardless_of_family(self):
        from workbench.token_tax import _is_continued_token

        for punct in (".", ",", ";", ":", "!", "?", "(", ")", "[", "]",
                      "{", "}", '"', "'"):
            for key in ("o200k_base", "gpt2", "llama-3", "unknown_family"):
                assert _is_continued_token(punct, key) is False, (
                    f"Punctuation '{punct}' should not be continued for {key}"
                )

    # ------------------------------------------------------------------
    # tiktoken family: o200k_base, cl100k_base
    # ------------------------------------------------------------------

    def test_tiktoken_space_prefix_is_word_start(self):
        from workbench.token_tax import _is_continued_token

        # Leading space = word-start token in tiktoken
        assert _is_continued_token(" Hello", "o200k_base") is False
        assert _is_continued_token(" world", "cl100k_base") is False

    def test_tiktoken_no_space_prefix_is_continuation(self):
        from workbench.token_tax import _is_continued_token

        assert _is_continued_token("ello", "o200k_base") is True
        assert _is_continued_token("ing", "cl100k_base") is True

    def test_tiktoken_bare_word_is_continuation(self):
        from workbench.token_tax import _is_continued_token

        # A token with no leading space that starts a subword is a continuation
        assert _is_continued_token("oken", "o200k_base") is True

    # ------------------------------------------------------------------
    # GPT-2 family
    # ------------------------------------------------------------------

    def test_gpt2_g_prefix_is_word_start(self):
        from workbench.token_tax import _is_continued_token

        assert _is_continued_token("Ġhello", "gpt2") is False
        assert _is_continued_token("Ġworld", "gpt2") is False

    def test_gpt2_no_g_prefix_is_continuation(self):
        from workbench.token_tax import _is_continued_token

        assert _is_continued_token("ello", "gpt2") is True
        assert _is_continued_token("ing", "gpt2") is True

    # ------------------------------------------------------------------
    # SentencePiece families: llama-3, mistral, qwen-2.5, gemma-2
    # ------------------------------------------------------------------

    def test_sentencepiece_underscore_prefix_is_word_start(self):
        from workbench.token_tax import _is_continued_token

        for key in ("llama-3", "mistral", "qwen-2.5", "gemma-2"):
            assert _is_continued_token("▁hello", key) is False, (
                f"▁-prefixed token should be word-start for {key}"
            )

    def test_sentencepiece_no_underscore_is_continuation(self):
        from workbench.token_tax import _is_continued_token

        for key in ("llama-3", "mistral", "qwen-2.5", "gemma-2"):
            assert _is_continued_token("ello", key) is True, (
                f"No-prefix token should be continuation for {key}"
            )

    def test_new_exact_family_continuation_rules_come_from_registry_metadata(self):
        from workbench.token_tax import _is_continued_token

        assert _is_continued_token("▁hello", "qwen3-next") is False
        assert _is_continued_token("ello", "qwen3-next") is True
        assert _is_continued_token(" Hello", "gpt-oss") is False
        assert _is_continued_token("ello", "gpt-oss") is True

    def test_command_r_uses_gpt2_style_word_starts(self):
        from workbench.token_tax import _is_continued_token

        assert _is_continued_token("Ġhello", "command-r") is False
        assert _is_continued_token("ello", "command-r") is True
        assert _is_continued_token("▁hello", "command-r") is True

    # ------------------------------------------------------------------
    # BERT-style (not one of the 8 families but the logic must exist)
    # ------------------------------------------------------------------

    def test_bert_double_hash_is_continuation(self):
        from workbench.token_tax import _is_continued_token

        assert _is_continued_token("##ing", "bert-base-uncased") is True
        assert _is_continued_token("##tion", "bert-base-uncased") is True

    def test_bert_no_double_hash_is_word_start(self):
        from workbench.token_tax import _is_continued_token

        assert _is_continued_token("hello", "bert-base-uncased") is False

    # ------------------------------------------------------------------
    # Unknown / unrecognized family — safe default is word-start (False)
    # ------------------------------------------------------------------

    def test_unknown_family_defaults_to_not_continued(self):
        from workbench.token_tax import _is_continued_token

        # Safe default: assume word-start rather than continuation
        assert _is_continued_token("hello", "unknown_family") is False
        assert _is_continued_token("ing", "some_future_tokenizer") is False


# ---------------------------------------------------------------------------
# _safe_iqr
# ---------------------------------------------------------------------------


class TestSafeIqr:
    """Tests for _safe_iqr()."""

    def test_returns_none_for_empty(self):
        from workbench.token_tax import _safe_iqr
        assert _safe_iqr([]) is None

    def test_returns_none_for_too_few_values(self):
        from workbench.token_tax import _safe_iqr
        assert _safe_iqr([1.0, 2.0, 3.0]) is None

    def test_returns_none_for_all_none(self):
        from workbench.token_tax import _safe_iqr
        assert _safe_iqr([None, None, None, None]) is None

    def test_returns_float_for_sufficient_values(self):
        from workbench.token_tax import _safe_iqr
        result = _safe_iqr([1.0, 2.0, 3.0, 4.0])
        assert isinstance(result, float)

    def test_iqr_is_nonnegative(self):
        from workbench.token_tax import _safe_iqr
        result = _safe_iqr([1.0, 1.5, 2.0, 2.5, 3.0])
        assert result is not None
        assert result >= 0.0

    def test_skips_none_values(self):
        from workbench.token_tax import _safe_iqr
        result = _safe_iqr([1.0, None, 2.0, None, 3.0, 4.0])
        assert result is not None


# ---------------------------------------------------------------------------
# portfolio_analysis — estimation_method
# ---------------------------------------------------------------------------


class TestPortfolioAnalysisEstimationMethod:
    """estimation_method field should be present on all return paths."""

    def test_empty_traffic_has_estimation_method(self):
        from workbench.token_tax import portfolio_analysis
        result = portfolio_analysis([], "o200k_base")
        assert result["estimation_method"] == "heuristic"

    def test_nonempty_traffic_has_estimation_method(self):
        from workbench.token_tax import portfolio_analysis
        traffic = [{"language": "en", "request_count": 100, "avg_chars": 200}]
        result = portfolio_analysis(traffic, "o200k_base")
        assert result["estimation_method"] == "heuristic"
