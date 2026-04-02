from unittest.mock import patch

from benchmark_engine import clear_benchmark_cache, run_benchmark_request
from workbench_types import BenchmarkRequest


class TestBenchmarkEngine:
    def teardown_method(self):
        clear_benchmark_cache()

    def test_run_benchmark_request_reuses_cached_results(self):
        request = BenchmarkRequest.from_inputs(
            corpus_key="strict_parallel",
            languages=["en"],
            tokenizer_keys=["gpt2"],
            row_limit=5,
        )
        payload = {
            "rows": [{"language": "en", "tokenizer_key": "gpt2", "corpus_key": "strict_parallel"}],
            "raw_rows": [{"language": "en", "tokenizer_key": "gpt2"}],
            "matrix": {("en", "gpt2"): {"language": "en", "tokenizer_key": "gpt2"}},
            "languages": ["en"],
            "tokenizers": ["gpt2"],
        }

        with patch("benchmark_engine.benchmark_corpus", return_value=payload) as mock_benchmark:
            first = run_benchmark_request(request)
            second = run_benchmark_request(request)

        assert mock_benchmark.call_count == 1
        assert first.rows == second.rows
        assert first is not second

    def test_run_benchmark_request_reports_cached_progress(self):
        request = BenchmarkRequest.from_inputs(
            corpus_key="strict_parallel",
            languages=["en"],
            tokenizer_keys=["gpt2"],
            row_limit=5,
        )
        payload = {
            "rows": [{"language": "en", "tokenizer_key": "gpt2", "corpus_key": "strict_parallel"}],
            "raw_rows": [{"language": "en", "tokenizer_key": "gpt2"}],
            "matrix": {("en", "gpt2"): {"language": "en", "tokenizer_key": "gpt2"}},
            "languages": ["en"],
            "tokenizers": ["gpt2"],
        }
        calls: list[tuple[float, str]] = []

        with patch("benchmark_engine.benchmark_corpus", return_value=payload):
            run_benchmark_request(request)
            run_benchmark_request(request, progress_callback=lambda ratio, desc: calls.append((ratio, desc)))

        assert calls
        assert calls[-1][0] == 0.9
        assert "cached benchmark" in calls[-1][1].lower()
