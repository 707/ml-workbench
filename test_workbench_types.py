from workbench_types import BenchmarkRequest, ScenarioRequest


class TestBenchmarkRequest:
    def test_cache_key_normalizes_inputs(self):
        request = BenchmarkRequest.from_inputs(
            corpus_key="strict_parallel",
            languages=["en", "ja"],
            tokenizer_keys=["gpt2", "llama-3"],
            row_limit=5,
            include_estimates=False,
            include_proxy=False,
        )

        assert request.languages == ("en", "ja")
        assert request.tokenizer_keys == ("gpt2", "llama-3")
        assert request.cache_key() == (
            "strict_parallel",
            ("en", "ja"),
            ("gpt2", "llama-3"),
            5,
            False,
            False,
        )


class TestScenarioRequest:
    def test_from_inputs_normalizes_numeric_and_sequence_fields(self):
        request = ScenarioRequest.from_inputs(
            corpus_key="strict_parallel",
            languages=["en"],
            tokenizer_keys=["mistral"],
            row_limit=25,
            monthly_requests=100000,
            avg_input_tokens=600,
            avg_output_tokens=250,
            reasoning_share=0.1,
        )

        assert request.languages == ("en",)
        assert request.tokenizer_keys == ("mistral",)
        assert request.monthly_requests == 100000
        assert request.reasoning_share == 0.1
