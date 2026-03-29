"""Focused tests for the Token Tax Workbench v2 paths."""

import pytest
from unittest.mock import patch, MagicMock


class TestBenchmarkCorpus:
    def _mock_tokenizer(self, token_count: int):
        tok = MagicMock()
        tok.encode.return_value = list(range(token_count))
        tok.convert_ids_to_tokens.return_value = [f"t{i}" for i in range(token_count)]
        return tok

    def test_benchmark_corpus_returns_rows(self):
        from corpora import CorpusSample
        from token_tax import benchmark_corpus

        samples = {
            "en": [
                CorpusSample("en", "hello world", "hello world", "strict_parallel", "https://example.com", "strict_verified"),
            ],
            "ar": [
                CorpusSample("ar", "مرحبا بالعالم", "hello world", "strict_parallel", "https://example.com", "strict_verified"),
            ],
        }

        with patch("token_tax.fetch_corpus_samples", return_value=samples):
            with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
                result = benchmark_corpus("strict_parallel", ["en", "ar"], ["gpt2"])

        assert len(result["rows"]) == 2
        assert ("ar", "gpt2") in result["matrix"]

    def test_benchmark_corpus_raises_when_no_rows_are_available(self):
        from token_tax import benchmark_corpus

        with patch("token_tax.fetch_corpus_samples", return_value={}):
            with pytest.raises(RuntimeError, match="No benchmark rows were produced"):
                benchmark_corpus("strict_parallel", ["en"], ["gpt2"])

    def test_benchmark_corpus_tags_rows_with_lane(self):
        from corpora import CorpusSample
        from token_tax import benchmark_corpus

        samples = {
            "en": [
                CorpusSample("en", "hello there", None, "streaming_exploration", "https://example.com", "research_forward"),
            ],
            "fr": [
                CorpusSample("fr", "bonjour", "hello", "streaming_exploration", "https://example.com", "research_forward"),
            ],
        }

        with patch("token_tax.fetch_corpus_samples", return_value=samples):
            with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
                result = benchmark_corpus("streaming_exploration", ["fr"], ["gpt2"])

        assert result["rows"][0]["lane"] == "Streaming Exploration"
        assert result["rows"][0]["english_baseline_ratio"] is not None
        assert result["rows"][0]["rtc"] is None

    def test_benchmark_appendix_mentions_streaming_lane(self):
        from token_tax import benchmark_appendix

        appendix = benchmark_appendix("streaming_exploration")
        assert "exploratory only" in appendix.lower()
        assert "english_baseline_ratio" in appendix


class TestScenarioAnalysis:
    def test_scenario_analysis_returns_cost_rows(self):
        from token_tax import scenario_analysis

        benchmark_rows = [
            {
                "language": "ar",
                "tokenizer_key": "gpt2",
                "rtc": 2.0,
                "lane": "Strict Evidence",
                "provenance": "strict_verified",
                "mapping_quality": "exact",
            },
        ]
        catalog_rows = [
            {
                "model_id": "openai/gpt-4o",
                "label": "GPT-4o",
                "tokenizer_key": "gpt2",
                "mapping_quality": "exact",
                "provenance": "strict_verified",
                "input_per_million": 1.0,
                "output_per_million": 2.0,
                "context_window": 128000,
                "latency_ms": None,
                "throughput_tps": None,
                "source": "test",
            },
        ]

        with patch("token_tax.benchmark_corpus", return_value={"rows": benchmark_rows, "languages": ["ar"]}):
            with patch("token_tax.build_catalog_entries", return_value=catalog_rows):
                rows = scenario_analysis(
                    corpus_key="strict_parallel",
                    languages=["ar"],
                    tokenizer_keys=["gpt2"],
                    model_ids=["openai/gpt-4o"],
                    row_limit=25,
                    monthly_requests=1000,
                    avg_input_tokens=100,
                    avg_output_tokens=50,
                    reasoning_share=0.1,
                )

        assert len(rows) == 1
        assert rows[0]["monthly_cost"] > 0

    def test_scenario_analysis_raises_when_benchmark_is_empty(self):
        from token_tax import scenario_analysis

        with patch("token_tax.benchmark_corpus", return_value={"rows": [], "languages": ["ar"]}):
            with patch("token_tax.build_catalog_entries", return_value=[]):
                with pytest.raises(RuntimeError, match="No scenario rows were produced"):
                    scenario_analysis(
                        corpus_key="strict_parallel",
                        languages=["ar"],
                        tokenizer_keys=["gpt2"],
                        model_ids=["openai/gpt-4o"],
                        row_limit=25,
                        monthly_requests=1000,
                        avg_input_tokens=100,
                        avg_output_tokens=50,
                        reasoning_share=0.1,
                    )

    def test_scenario_analysis_preserves_speed_metadata(self):
        from token_tax import scenario_analysis

        benchmark_rows = [
            {
                "language": "ar",
                "tokenizer_key": "llama-3",
                "rtc": 2.0,
                "lane": "Strict Evidence",
                "provenance": "strict_verified",
                "mapping_quality": "exact",
            },
        ]
        catalog_rows = [
            {
                "model_id": "meta-llama/llama-3.1-8b-instruct",
                "label": "Llama 3.1 8B Instruct",
                "tokenizer_key": "llama-3",
                "mapping_quality": "exact",
                "provenance": "strict_verified",
                "input_per_million": 0.05,
                "output_per_million": 0.08,
                "context_window": 128000,
                "latency_ms": 0.44,
                "throughput_tps": 84.2,
                "ttft_seconds": 0.44,
                "output_tokens_per_second": 84.2,
                "telemetry_provider": "Artificial Analysis",
                "source": "test",
            },
        ]

        with patch("token_tax.benchmark_corpus", return_value={"rows": benchmark_rows, "languages": ["ar"]}):
            with patch("token_tax.build_catalog_entries", return_value=catalog_rows):
                rows = scenario_analysis(
                    corpus_key="strict_parallel",
                    languages=["ar"],
                    tokenizer_keys=["llama-3"],
                    model_ids=["meta-llama/llama-3.1-8b-instruct"],
                    row_limit=25,
                    monthly_requests=1000,
                    avg_input_tokens=100,
                    avg_output_tokens=50,
                    reasoning_share=0.1,
                )

        assert rows[0]["ttft_seconds"] == 0.44
        assert rows[0]["output_tokens_per_second"] == 84.2

    def test_scenario_analysis_compares_multiple_models_on_one_tokenizer(self):
        from token_tax import scenario_analysis

        benchmark_rows = [
            {
                "language": "ja",
                "tokenizer_key": "llama-3",
                "rtc": 1.7,
                "lane": "Strict Evidence",
                "provenance": "strict_verified",
                "mapping_quality": "exact",
            },
        ]
        catalog_rows = [
            {
                "model_id": "meta-llama/llama-3.1-8b-instruct",
                "label": "Llama 3.1 8B Instruct",
                "tokenizer_key": "llama-3",
                "mapping_quality": "exact",
                "provenance": "strict_verified",
                "input_per_million": 0.05,
                "output_per_million": 0.08,
                "context_window": 128000,
                "latency_ms": None,
                "throughput_tps": None,
                "source": "test",
            },
            {
                "model_id": "meta-llama/llama-3.2-3b-instruct:free",
                "label": "Llama 3.2 3B Instruct (Free)",
                "tokenizer_key": "llama-3",
                "mapping_quality": "exact",
                "provenance": "strict_verified",
                "input_per_million": 0.03,
                "output_per_million": 0.05,
                "context_window": 128000,
                "latency_ms": None,
                "throughput_tps": None,
                "source": "test",
            },
        ]

        with patch("token_tax.benchmark_corpus", return_value={"rows": benchmark_rows, "languages": ["ja"]}):
            with patch("token_tax.build_catalog_entries", return_value=catalog_rows):
                rows = scenario_analysis(
                    corpus_key="strict_parallel",
                    languages=["ja"],
                    tokenizer_keys=["llama-3"],
                    model_ids=[
                        "meta-llama/llama-3.1-8b-instruct",
                        "meta-llama/llama-3.2-3b-instruct:free",
                    ],
                    row_limit=25,
                    monthly_requests=1000,
                    avg_input_tokens=100,
                    avg_output_tokens=50,
                    reasoning_share=0.1,
                )

        assert len(rows) == 2

    def test_scenario_analysis_rejects_streaming_exploration_as_cost_basis(self):
        from token_tax import scenario_analysis

        with pytest.raises(ValueError, match="Strict Evidence"):
            scenario_analysis(
                corpus_key="streaming_exploration",
                languages=["fr"],
                tokenizer_keys=["gpt2"],
                model_ids=["mistralai/mistral-7b-instruct:free"],
                row_limit=25,
                monthly_requests=1000,
                avg_input_tokens=100,
                avg_output_tokens=50,
                reasoning_share=0.1,
            )


class TestScenarioCharts:
    def test_latency_chart_explains_missing_metadata(self):
        from charts import build_metric_scatter

        fig = build_metric_scatter(
            [{"label": "GPT-4o", "monthly_cost": 10.0, "latency_ms": None}],
            x_key="latency_ms",
            y_key="monthly_cost",
        )

        assert "latency metadata" in fig.layout.annotations[0].text.lower()


class TestAuditMarkdown:
    def test_audit_markdown_mentions_sources(self):
        from token_tax import audit_markdown

        markdown = audit_markdown()
        assert "FLORES-200" in markdown
        assert "OpenRouter Models API" in markdown


class TestSpaceConfig:
    def test_readme_declares_docker_sdk_entrypoint(self):
        from pathlib import Path

        readme = Path(__file__).with_name("README.md").read_text(encoding="utf-8")
        assert 'sdk: docker' in readme
        assert 'app_port: 7860' in readme


class TestDockerfile:
    def test_dockerfile_is_minimal_and_bootstraps_app(self):
        from pathlib import Path

        dockerfile = Path(__file__).with_name("Dockerfile").read_text(encoding="utf-8")
        assert "FROM python:3.10-slim" in dockerfile
        assert "apt-get" not in dockerfile
        assert 'CMD ["python", "-u", "bootstrap.py"]' in dockerfile


class TestDockerIgnore:
    def test_dockerignore_includes_benchmark_and_telemetry_snapshots(self):
        from pathlib import Path

        dockerignore = Path(__file__).with_name(".dockerignore").read_text(encoding="utf-8")
        assert "!data/strict_parallel/flores_v1.jsonl" in dockerignore
        assert "!data/telemetry/" in dockerignore
        assert "!data/telemetry/artificial_analysis_snapshot.json" in dockerignore


class TestBootstrap:
    def test_bootstrap_declares_required_runtime_modules(self):
        from bootstrap import REQUIRED_MODULES

        for module_name in (
            "app",
            "charts",
            "corpora",
            "diagnostics",
            "model_registry",
            "pricing",
            "provenance",
            "token_tax",
            "token_tax_ui",
            "tokenizer",
        ):
            assert module_name in REQUIRED_MODULES


class TestRequirements:
    def test_requirements_align_with_hf_gradio_sdk(self):
        from pathlib import Path

        requirements = Path(__file__).with_name("requirements.txt").read_text(encoding="utf-8")
        assert "gradio[oauth,mcp]==6.8.0" in requirements

    def test_pyproject_aligns_with_hf_gradio_sdk(self):
        from pathlib import Path

        pyproject = Path(__file__).with_name("pyproject.toml").read_text(encoding="utf-8")
        assert 'gradio[oauth,mcp]==6.8.0' in pyproject


class TestDeployVerification:
    def test_makefile_exposes_render_and_hf_deploy_paths(self):
        from pathlib import Path

        makefile = Path(__file__).with_name("Makefile").read_text(encoding="utf-8")
        assert "deploy-render" in makefile
        assert "git push $(GITHUB_REMOTE) main" in makefile
        assert "deploy-hf" in makefile
        assert "verify_hf_space.py" in makefile
        assert "Verifying Hugging Face runtime" in makefile
