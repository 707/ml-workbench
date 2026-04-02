from unittest.mock import patch

from workbench.engines.scenario import derive_scenario_model_ids, run_scenario_request
from workbench.types import ScenarioRequest


class TestScenarioEngine:
    def test_derive_scenario_model_ids_filters_by_tokenizer_and_proxy(self):
        rows = [
            {"model_id": "a", "tokenizer_key": "llama-3"},
            {"model_id": "b", "tokenizer_key": "mistral"},
        ]
        with patch("workbench.engines.scenario.list_free_runtime_choices", return_value=rows):
            result = derive_scenario_model_ids(("mistral",), include_proxy=False)

        assert result == ["b"]

    def test_run_scenario_request_uses_derived_model_ids(self):
        from workbench.types import BenchmarkResult

        request = ScenarioRequest.from_inputs(
            corpus_key="strict_parallel",
            languages=["en"],
            tokenizer_keys=["llama-3"],
            row_limit=25,
            monthly_requests=100000,
            avg_input_tokens=600,
            avg_output_tokens=250,
            reasoning_share=0.1,
        )
        with (
            patch("workbench.engines.scenario.derive_scenario_model_ids", return_value=["model-a"]) as mock_ids,
            patch(
                "workbench.engines.scenario.run_benchmark_request",
                return_value=BenchmarkResult(
                    rows=[
                        {
                            "language": "en",
                            "tokenizer_key": "llama-3",
                            "rtc": 1.5,
                            "lane": "Strict Evidence",
                        }
                    ],
                    raw_rows=[],
                    languages=["en"],
                    tokenizers=["llama-3"],
                    composition_rows=[],
                ),
            ) as mock_benchmark,
            patch(
                "workbench.engines.scenario.build_catalog_entries",
                return_value=[
                    {
                        "model_id": "model-a",
                        "label": "Model A",
                        "tokenizer_key": "llama-3",
                        "input_per_million": 1.0,
                        "output_per_million": 2.0,
                        "latency_ms": None,
                        "throughput_tps": None,
                        "ttft_seconds": None,
                        "output_tokens_per_second": None,
                        "telemetry_provider": None,
                        "provenance": "strict_verified",
                        "mapping_quality": "exact",
                    }
                ],
            ),
        ):
            result = run_scenario_request(request)

        mock_ids.assert_called_once()
        assert mock_benchmark.call_args.args[0] == request.to_benchmark_request()
        assert result.model_ids == ["model-a"]
        assert result.rows[0]["model_id"] == "model-a"

    def test_run_scenario_request_raises_when_selected_tokenizer_missing_from_benchmark(self):
        from workbench.types import BenchmarkResult

        request = ScenarioRequest.from_inputs(
            corpus_key="strict_parallel",
            languages=["en"],
            tokenizer_keys=["qwen-2.5"],
            row_limit=25,
            monthly_requests=100000,
            avg_input_tokens=600,
            avg_output_tokens=250,
            reasoning_share=0.1,
        )

        with patch("workbench.engines.scenario.derive_scenario_model_ids", return_value=["model-a"]):
            with patch(
                "workbench.engines.scenario.run_benchmark_request",
                return_value=BenchmarkResult(
                    rows=[],
                    raw_rows=[],
                    languages=["en"],
                    tokenizers=[],
                    composition_rows=[],
                ),
            ):
                with patch("workbench.engines.scenario.resolve_selection", return_value={"label": "Qwen 2.5 family"}):
                    with patch("workbench.engines.scenario.build_catalog_entries", return_value=[]):
                        try:
                            run_scenario_request(request)
                        except RuntimeError as exc:
                            assert "Qwen 2.5 family" in str(exc)
                        else:
                            raise AssertionError("Expected RuntimeError for missing benchmark tokenizer")
