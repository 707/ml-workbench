"""
TDD tests for app.py — Reasoning Model Comparison Gradio App.

Test order matches implementation phases:
  Phase 1: parse_think_block, call_openrouter, extract_usage
  Phase 2: run_comparison (mocked HTTP)
"""

import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Phase 1 — parse_think_block
# ---------------------------------------------------------------------------

class TestParseThinkBlock:
    """Unit tests for parse_think_block(text)."""

    def test_normal_case_returns_reasoning_and_answer(self):
        """Full <think>...</think> block followed by an answer."""
        from app import parse_think_block

        text = "<think>step 1\nstep 2</think>The answer is 42."
        reasoning, answer = parse_think_block(text)

        assert reasoning == "step 1\nstep 2"
        assert answer == "The answer is 42."

    def test_no_think_tags_returns_empty_reasoning(self):
        """Text with no <think> tag at all — reasoning should be empty string."""
        from app import parse_think_block

        text = "Plain response with no thinking."
        reasoning, answer = parse_think_block(text)

        assert reasoning == ""
        assert answer == "Plain response with no thinking."

    def test_empty_think_block(self):
        """<think></think> with nothing inside — reasoning is empty string."""
        from app import parse_think_block

        text = "<think></think>Short answer."
        reasoning, answer = parse_think_block(text)

        assert reasoning == ""
        assert answer == "Short answer."

    def test_strips_opening_think_tag_from_reasoning(self):
        """Reasoning part must not contain the leading <think> tag."""
        from app import parse_think_block

        text = "<think>Some reasoning here</think>Final answer."
        reasoning, answer = parse_think_block(text)

        assert "<think>" not in reasoning
        assert "Some reasoning here" in reasoning

    def test_answer_has_no_closing_think_tag(self):
        """Answer part must not start with </think>."""
        from app import parse_think_block

        text = "<think>reasoning</think>answer text"
        reasoning, answer = parse_think_block(text)

        assert "</think>" not in answer
        assert answer == "answer text"

    def test_answer_leading_whitespace_stripped(self):
        """Common pattern: </think>\\nThe answer — leading whitespace removed."""
        from app import parse_think_block

        text = "<think>reasoning</think>\n\nThe answer."
        reasoning, answer = parse_think_block(text)

        assert answer == "The answer."

    def test_empty_string_returns_empty_reasoning_and_empty_answer(self):
        """Edge case: completely empty input."""
        from app import parse_think_block

        reasoning, answer = parse_think_block("")

        assert reasoning == ""
        assert answer == ""

    def test_only_think_opening_tag_no_closing(self):
        """Malformed: <think> present but no </think> — treat as no tags found."""
        from app import parse_think_block

        text = "<think>incomplete reasoning"
        reasoning, answer = parse_think_block(text)

        assert reasoning == ""
        assert answer == "<think>incomplete reasoning"

    def test_returns_tuple_of_two_strings(self):
        """Return type is always a 2-tuple of strings."""
        from app import parse_think_block

        result = parse_think_block("anything")

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], str)

    def test_multiline_reasoning_preserved(self):
        """Multi-line reasoning block is preserved in full."""
        from app import parse_think_block

        reasoning_text = "line 1\nline 2\nline 3"
        text = f"<think>{reasoning_text}</think>Done."
        reasoning, answer = parse_think_block(text)

        assert reasoning == reasoning_text

    def test_multiple_closing_tags_splits_on_first(self):
        """If </think> appears multiple times, split on first occurrence."""
        from app import parse_think_block

        text = "<think>reasoning</think>answer with </think> inside"
        reasoning, answer = parse_think_block(text)

        assert reasoning == "reasoning"
        assert "answer with </think> inside" in answer


# ---------------------------------------------------------------------------
# Phase 1 — extract_usage
# ---------------------------------------------------------------------------

class TestExtractUsage:
    """Unit tests for extract_usage(response)."""

    def _r1_response(self, prompt_tokens=10, completion_tokens=500, reasoning_tokens=300):
        """Fixture: R1-style response with reasoning_tokens field."""
        return {
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "completion_tokens_details": {
                    "reasoning_tokens": reasoning_tokens,
                },
            }
        }

    def _llama_response(self, prompt_tokens=10, completion_tokens=80):
        """Fixture: Llama-style response — no completion_tokens_details."""
        return {
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }
        }

    def test_r1_response_extracts_all_fields(self):
        """Full R1 response returns all three token counts."""
        from app import extract_usage

        usage = extract_usage(self._r1_response())

        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 500
        assert usage["reasoning_tokens"] == 300

    def test_llama_response_reasoning_tokens_defaults_to_zero(self):
        """Llama response has no reasoning_tokens — should default to 0."""
        from app import extract_usage

        usage = extract_usage(self._llama_response())

        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 80
        assert usage["reasoning_tokens"] == 0

    def test_missing_usage_key_returns_all_zeros(self):
        """If 'usage' key absent entirely, return zeros not a KeyError."""
        from app import extract_usage

        usage = extract_usage({})

        assert usage["prompt_tokens"] == 0
        assert usage["completion_tokens"] == 0
        assert usage["reasoning_tokens"] == 0

    def test_missing_completion_tokens_details_returns_zero_reasoning(self):
        """completion_tokens_details absent — reasoning_tokens defaults to 0."""
        from app import extract_usage

        response = {
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 50,
            }
        }
        usage = extract_usage(response)

        assert usage["reasoning_tokens"] == 0

    def test_returns_dict_with_required_keys(self):
        """Return value always has the three expected keys."""
        from app import extract_usage

        usage = extract_usage({})

        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "reasoning_tokens" in usage

    def test_reasoning_tokens_present_but_none_defaults_to_zero(self):
        """reasoning_tokens field present but value is None — treat as 0."""
        from app import extract_usage

        response = {
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 100,
                "completion_tokens_details": {
                    "reasoning_tokens": None,
                },
            }
        }
        usage = extract_usage(response)

        assert usage["reasoning_tokens"] == 0


# ---------------------------------------------------------------------------
# Phase 1 — call_openrouter
# ---------------------------------------------------------------------------

class TestCallOpenrouter:
    """Unit tests for call_openrouter(api_key, model, prompt) — HTTP mocked."""

    def test_posts_to_correct_url(self):
        """Must POST to the OpenRouter chat completions endpoint."""
        from app import call_openrouter

        with patch("app.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"choices": []}
            mock_post.return_value.raise_for_status = MagicMock()

            call_openrouter("sk-test", "some/model", "question?")

        args, kwargs = mock_post.call_args
        assert args[0] == "https://openrouter.ai/api/v1/chat/completions"

    def test_sends_authorization_header(self):
        """Authorization header must include the API key."""
        from app import call_openrouter

        with patch("app.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {}
            mock_post.return_value.raise_for_status = MagicMock()

            call_openrouter("my-api-key", "some/model", "hi")

        _, kwargs = mock_post.call_args
        assert "Authorization" in kwargs["headers"]
        assert "my-api-key" in kwargs["headers"]["Authorization"]

    def test_sends_model_in_payload(self):
        """The model ID must appear in the POST body."""
        from app import call_openrouter

        with patch("app.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {}
            mock_post.return_value.raise_for_status = MagicMock()

            call_openrouter("key", "deepseek/deepseek-r1", "question")

        _, kwargs = mock_post.call_args
        assert kwargs["json"]["model"] == "deepseek/deepseek-r1"

    def test_sends_user_message_in_payload(self):
        """The prompt must appear as a user message in the messages list."""
        from app import call_openrouter

        with patch("app.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {}
            mock_post.return_value.raise_for_status = MagicMock()

            call_openrouter("key", "model", "What is 2+2?")

        _, kwargs = mock_post.call_args
        messages = kwargs["json"]["messages"]
        assert any(m["role"] == "user" and "What is 2+2?" in m["content"] for m in messages)

    def test_returns_json_response(self):
        """Return value should be the parsed JSON dict from the response."""
        from app import call_openrouter

        expected = {"choices": [{"message": {"content": "4"}}]}

        with patch("app.requests.post") as mock_post:
            mock_post.return_value.json.return_value = expected
            mock_post.return_value.raise_for_status = MagicMock()

            result = call_openrouter("key", "model", "2+2?")

        assert result == expected

    def test_raises_on_http_error(self):
        """Non-2xx response should propagate as an exception."""
        import requests as req_lib
        from app import call_openrouter

        with patch("app.requests.post") as mock_post:
            mock_post.return_value.raise_for_status.side_effect = req_lib.HTTPError("401")

            with pytest.raises(req_lib.HTTPError):
                call_openrouter("bad-key", "model", "question")


# ---------------------------------------------------------------------------
# Phase 2 — run_comparison
# ---------------------------------------------------------------------------

class TestRunComparison:
    """Unit tests for run_comparison(api_key, question) — mocked call_openrouter."""

    def _make_response(self, content, reasoning_tokens=0, completion_tokens=50, prompt_tokens=10):
        """Helper: build a minimal OpenRouter-style response dict."""
        resp = {
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        }
        if reasoning_tokens > 0:
            resp["usage"]["completion_tokens_details"] = {
                "reasoning_tokens": reasoning_tokens
            }
        return resp

    def test_returns_two_results(self):
        """run_comparison must return exactly two result objects."""
        from app import run_comparison

        r1_resp = self._make_response("<think>thinking</think>Answer A", reasoning_tokens=200)
        llama_resp = self._make_response("Answer B")

        with patch("app.call_openrouter") as mock_call:
            mock_call.side_effect = [r1_resp, llama_resp]

            r1_result, llama_result = run_comparison("key", "question?")

        assert r1_result is not None
        assert llama_result is not None

    def test_r1_result_has_reasoning_field(self):
        """R1 result dict must include 'reasoning' key with parsed think content."""
        from app import run_comparison

        r1_resp = self._make_response("<think>step by step</think>Final.", reasoning_tokens=100)
        llama_resp = self._make_response("Direct answer.")

        with patch("app.call_openrouter") as mock_call:
            mock_call.side_effect = [r1_resp, llama_resp]

            r1_result, _ = run_comparison("key", "question?")

        assert "reasoning" in r1_result
        assert "step by step" in r1_result["reasoning"]

    def test_r1_result_has_answer_field(self):
        """R1 result dict must include 'answer' key with post-think content."""
        from app import run_comparison

        r1_resp = self._make_response("<think>thinking</think>The answer is 5.", reasoning_tokens=50)
        llama_resp = self._make_response("5")

        with patch("app.call_openrouter") as mock_call:
            mock_call.side_effect = [r1_resp, llama_resp]

            r1_result, _ = run_comparison("key", "question?")

        assert "answer" in r1_result
        assert "The answer is 5." in r1_result["answer"]

    def test_llama_result_has_answer_field(self):
        """Llama result dict must include 'answer' key."""
        from app import run_comparison

        r1_resp = self._make_response("<think>x</think>R1 answer", reasoning_tokens=10)
        llama_resp = self._make_response("Llama answer here.")

        with patch("app.call_openrouter") as mock_call:
            mock_call.side_effect = [r1_resp, llama_resp]

            _, llama_result = run_comparison("key", "q?")

        assert "answer" in llama_result
        assert "Llama answer here." in llama_result["answer"]

    def test_results_include_usage(self):
        """Both result dicts must include 'usage' with token counts."""
        from app import run_comparison

        r1_resp = self._make_response("<think>t</think>a", reasoning_tokens=300, completion_tokens=320)
        llama_resp = self._make_response("b", completion_tokens=40)

        with patch("app.call_openrouter") as mock_call:
            mock_call.side_effect = [r1_resp, llama_resp]

            r1_result, llama_result = run_comparison("key", "q")

        assert "usage" in r1_result
        assert "usage" in llama_result
        assert r1_result["usage"]["reasoning_tokens"] == 300
        assert llama_result["usage"]["completion_tokens"] == 40

    def test_r1_failure_does_not_crash_llama_result(self):
        """If R1 call raises, llama result must still be returned (not exception)."""
        from app import run_comparison

        llama_resp = self._make_response("Llama is fine.")

        def side_effect(api_key, model, prompt):
            if "deepseek" in model:
                raise Exception("R1 network error")
            return llama_resp

        with patch("app.call_openrouter", side_effect=side_effect):
            r1_result, llama_result = run_comparison("key", "question?")

        assert "error" in r1_result
        assert "answer" in llama_result

    def test_llama_failure_does_not_crash_r1_result(self):
        """If Llama call raises, R1 result must still be returned (not exception)."""
        from app import run_comparison

        r1_resp = self._make_response("<think>ok</think>R1 answer", reasoning_tokens=50)

        def side_effect(api_key, model, prompt):
            if "llama" in model:
                raise Exception("Llama timeout")
            return r1_resp

        with patch("app.call_openrouter", side_effect=side_effect):
            r1_result, llama_result = run_comparison("key", "question?")

        assert "answer" in r1_result
        assert "error" in llama_result

    def test_calls_both_models(self):
        """Both model IDs must be passed to call_openrouter."""
        from app import run_comparison

        r1_resp = self._make_response("<think>t</think>a")
        llama_resp = self._make_response("b")

        with patch("app.call_openrouter") as mock_call:
            mock_call.side_effect = [r1_resp, llama_resp]

            run_comparison("key", "q?")

        called_models = [call.args[1] for call in mock_call.call_args_list]
        assert any("deepseek" in m for m in called_models)
        assert any("llama" in m for m in called_models)
