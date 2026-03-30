"""
TDD tests for app.py — Reasoning Model Comparison Gradio App.

Test order matches implementation phases:
  Phase 1: parse_think_block, call_openrouter, extract_usage
  Phase 2: run_comparison (mocked HTTP)
"""

import json
import inspect
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


class TestComparisonUiLabels:
    """UI text checks for the comparison tab prompt inputs."""

    def test_input_prompt_label_present_and_preset_label_removed(self):
        """Prompt area should use 'Input Prompt' wording instead of 'Preset Questions'."""
        import app

        src = inspect.getsource(app._build_comparison_blocks)
        assert "Input Prompt" in src
        assert "Preset Questions" not in src

    def test_server_key_is_never_serialized_into_component_value(self):
        """Server-side keys must stay in backend state, not frontend textbox config."""
        import app

        src = inspect.getsource(app._build_comparison_blocks)
        assert 'api_key = gr.State("")' in src
        assert "value=SERVER_KEY" not in src

    def test_comparison_status_wrapper_reports_progress_and_completion(self):
        from app import render_comparison_with_status

        with patch("app.run_comparison", return_value=(
            {"reasoning": "step", "answer": "A", "usage": {"prompt_tokens": 1, "completion_tokens": 2, "reasoning_tokens": 1}},
            {"answer": "B", "usage": {"prompt_tokens": 1, "completion_tokens": 1, "reasoning_tokens": 0}},
        )):
            outputs = render_comparison_with_status(
                "sk-or-test",
                "Qwen 2.5 7B Instruct (Free)",
                "Llama 3.2 3B Instruct (Free)",
                1.0,
                1.0,
                None,
                None,
                "How many r's are in strawberry?",
                "",
                [],
                {
                    "Qwen 2.5 7B Instruct (Free)": "qwen/qwen-2.5-7b-instruct:free",
                    "Llama 3.2 3B Instruct (Free)": "meta-llama/llama-3.2-3b-instruct:free",
                },
            )

        assert "completed" in outputs[2].lower()
        assert "Prompt length" in outputs[2]

    def test_build_ui_wraps_tabs_in_custom_app_shell(self):
        import app

        src = inspect.getsource(app.build_ui)
        assert "with gr.Blocks(" in src
        assert ".render()" in src
        assert "demo.load(" in src

    def test_build_ui_removes_theme_toggle_markup(self):
        import app

        src = inspect.getsource(app.build_ui)
        assert "theme-toggle" not in src
        assert "theme-choice-light" not in src
        assert "theme-choice-dark" not in src

    def test_build_ui_includes_explainer_tab(self):
        import app

        src = inspect.getsource(app.build_ui)
        assert 'with gr.Tab("Why Tokenizers Matter")' in src


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

        with patch("openrouter.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"choices": []}
            mock_post.return_value.raise_for_status = MagicMock()

            call_openrouter("sk-test", "some/model", "question?")

        args, kwargs = mock_post.call_args
        assert args[0] == "https://openrouter.ai/api/v1/chat/completions"

    def test_sends_authorization_header(self):
        """Authorization header must include the API key."""
        from app import call_openrouter

        with patch("openrouter.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {}
            mock_post.return_value.raise_for_status = MagicMock()

            call_openrouter("my-api-key", "some/model", "hi")

        _, kwargs = mock_post.call_args
        assert "Authorization" in kwargs["headers"]
        assert "my-api-key" in kwargs["headers"]["Authorization"]

    def test_sends_model_in_payload(self):
        """The model ID must appear in the POST body."""
        from app import call_openrouter

        with patch("openrouter.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {}
            mock_post.return_value.raise_for_status = MagicMock()

            call_openrouter("key", "deepseek/deepseek-r1", "question")

        _, kwargs = mock_post.call_args
        assert kwargs["json"]["model"] == "deepseek/deepseek-r1"

    def test_sends_user_message_in_payload(self):
        """The prompt must appear as a user message in the messages list."""
        from app import call_openrouter

        with patch("openrouter.requests.post") as mock_post:
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

        with patch("openrouter.requests.post") as mock_post:
            mock_post.return_value.json.return_value = expected
            mock_post.return_value.raise_for_status = MagicMock()

            result = call_openrouter("key", "model", "2+2?")

        assert result == expected

    def test_raises_on_http_error(self):
        """Non-2xx response should propagate as an exception."""
        import requests as req_lib
        from app import call_openrouter

        with patch("openrouter.requests.post") as mock_post:
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
        from app import MODEL_R1, run_comparison

        llama_resp = self._make_response("Llama is fine.")

        def side_effect(api_key, model, prompt):
            if model == MODEL_R1:
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
        from app import MODEL_LLAMA, MODEL_R1, run_comparison

        r1_resp = self._make_response("<think>t</think>a")
        llama_resp = self._make_response("b")

        with patch("app.call_openrouter") as mock_call:
            mock_call.side_effect = [r1_resp, llama_resp]

            run_comparison("key", "q?")

        called_models = [call.args[1] for call in mock_call.call_args_list]
        assert MODEL_R1 in called_models
        assert MODEL_LLAMA in called_models


# ---------------------------------------------------------------------------
# Phase 3 — _format_usage
# ---------------------------------------------------------------------------


class TestFormatUsage:
    """Unit tests for _format_usage(usage) — Markdown formatter."""

    def test_basic_output_contains_prompt_and_completion(self):
        """Must include prompt_tokens and completion_tokens in output."""
        from app import _format_usage

        out = _format_usage({"prompt_tokens": 10, "completion_tokens": 50, "reasoning_tokens": 0})

        assert "10" in out
        assert "50" in out

    def test_no_reasoning_tokens_omits_reasoning_line(self):
        """If reasoning_tokens is 0, no 'Reasoning tokens' line appears."""
        from app import _format_usage

        out = _format_usage({"prompt_tokens": 5, "completion_tokens": 30, "reasoning_tokens": 0})

        assert "Reasoning" not in out

    def test_with_reasoning_tokens_includes_reasoning_and_answer_lines(self):
        """If reasoning_tokens > 0, both reasoning and answer-token lines appear."""
        from app import _format_usage

        out = _format_usage({"prompt_tokens": 10, "completion_tokens": 400, "reasoning_tokens": 350})

        assert "Reasoning" in out
        assert "Answer" in out
        assert "350" in out

    def test_answer_tokens_computed_as_completion_minus_reasoning(self):
        """Answer tokens = completion - reasoning when reasoning > 0."""
        from app import _format_usage

        out = _format_usage({"prompt_tokens": 10, "completion_tokens": 400, "reasoning_tokens": 350})

        # answer tokens = 400 - 350 = 50
        assert "50" in out

    def test_returns_string(self):
        """Return type is always str."""
        from app import _format_usage

        result = _format_usage({})

        assert isinstance(result, str)

    def test_empty_dict_returns_string_with_zeros(self):
        """Empty dict — all counts default to 0, no crash."""
        from app import _format_usage

        out = _format_usage({})

        assert "0" in out


# ---------------------------------------------------------------------------
# Phase 3 — compare (Gradio handler)
# ---------------------------------------------------------------------------


class TestCompare:
    """Unit tests for compare(api_key, preset, custom) — mocked run_comparison."""

    def _r1_result(self, reasoning="step", answer="R1 answer"):
        return {
            "reasoning": reasoning,
            "answer": answer,
            "usage": {"prompt_tokens": 10, "completion_tokens": 100, "reasoning_tokens": 80},
        }

    def _llama_result(self, answer="Llama answer"):
        return {
            "answer": answer,
            "usage": {"prompt_tokens": 10, "completion_tokens": 40, "reasoning_tokens": 0},
        }

    def test_missing_api_key_returns_error_message(self):
        """Empty api_key should return error strings without calling run_comparison."""
        from app import compare

        r1_reasoning, r1_answer, r1_stats, llama_answer, llama_stats = compare(
            "", "preset question", ""
        )

        assert "No API key" in r1_answer
        assert "No API key" in llama_answer

    def test_custom_question_overrides_preset(self):
        """Non-empty custom question is used instead of preset."""
        from app import compare

        with patch("app.run_comparison") as mock_run:
            mock_run.return_value = (self._r1_result(), self._llama_result())

            compare("key", "preset", "custom question")

        _, called_question = mock_run.call_args.args
        assert called_question == "custom question"

    def test_preset_used_when_custom_is_empty(self):
        """Empty custom uses preset question."""
        from app import compare

        with patch("app.run_comparison") as mock_run:
            mock_run.return_value = (self._r1_result(), self._llama_result())

            compare("key", "preset question", "")

        _, called_question = mock_run.call_args.args
        assert called_question == "preset question"

    def test_returns_five_values(self):
        """compare() must return exactly 5 values."""
        from app import compare

        with patch("app.run_comparison") as mock_run:
            mock_run.return_value = (self._r1_result(), self._llama_result())

            result = compare("key", "preset", "")

        assert len(result) == 5

    def test_r1_error_result_surfaces_error_text(self):
        """If R1 returns an error dict, the answer field shows the error."""
        from app import compare

        with patch("app.run_comparison") as mock_run:
            mock_run.return_value = ({"error": "timeout"}, self._llama_result())

            _, r1_answer, _, _, _ = compare("key", "preset", "")

        assert "Error" in r1_answer
        assert "timeout" in r1_answer

    def test_llama_error_result_surfaces_error_text(self):
        """If Llama returns an error dict, the answer field shows the error."""
        from app import compare

        with patch("app.run_comparison") as mock_run:
            mock_run.return_value = (self._r1_result(), {"error": "503"})

            _, _, _, llama_answer, _ = compare("key", "preset", "")

        assert "Error" in llama_answer
        assert "503" in llama_answer

    def test_custom_whitespace_only_falls_back_to_preset(self):
        """Whitespace-only custom input should be treated as empty."""
        from app import compare

        with patch("app.run_comparison") as mock_run:
            mock_run.return_value = (self._r1_result(), self._llama_result())

            compare("key", "preset q", "   ")

        _, called_question = mock_run.call_args.args
        assert called_question == "preset q"

    def test_no_question_returns_error_message(self):
        """Empty preset and empty custom should return 'No question' error."""
        from app import compare

        r1_reasoning, r1_answer, r1_stats, llama_answer, llama_stats = compare(
            "valid-key", "", ""
        )

        assert "No question" in r1_answer
        assert "No question" in llama_answer


# ---------------------------------------------------------------------------
# Phase 3 — build_ui (smoke test)
# ---------------------------------------------------------------------------


class TestBuildUi:
    """Smoke tests for build_ui() — verifies Gradio Blocks is constructed."""

    def test_build_ui_returns_gradio_blocks(self):
        """build_ui() must return a Gradio Blocks or TabbedInterface without raising."""
        import gradio as gr
        from app import build_ui

        demo = build_ui()

        assert isinstance(demo, (gr.Blocks, gr.TabbedInterface))


# ---------------------------------------------------------------------------
# Phase 3 — _stats_to_html
# ---------------------------------------------------------------------------


class TestStatsToHtml:
    """Unit tests for _stats_to_html(stats_md)."""

    def test_bold_markdown_becomes_strong_tag(self):
        """**Key:** should become <strong>Key:</strong>."""
        from app import _stats_to_html

        result = _stats_to_html("**Prompt tokens:** 10")

        assert "<strong>Prompt tokens:</strong>" in result

    def test_double_newline_becomes_br(self):
        """Two-space + newline (markdown line break) becomes <br>."""
        from app import _stats_to_html

        result = _stats_to_html("line1  \nline2")

        assert "<br>" in result

    def test_returns_string(self):
        """Return type is always str."""
        from app import _stats_to_html

        assert isinstance(_stats_to_html(""), str)


# ---------------------------------------------------------------------------
# Phase 3 — _build_card
# ---------------------------------------------------------------------------


class TestBuildCard:
    """Unit tests for _build_card(...)."""

    def test_returns_string(self):
        """_build_card must return a string."""
        from app import _build_card

        result = _build_card("Q?", "reasoning", "answer A", "stats A", "answer B", "stats B")

        assert isinstance(result, str)

    def test_question_appears_in_output(self):
        """The question text must appear in the card HTML."""
        from app import _build_card

        result = _build_card("What is 2+2?", "", "4", "", "4", "")

        assert "What is 2+2?" in result

    def test_model_labels_appear_in_output(self):
        """model_a_label and model_b_label must appear in the card HTML."""
        from app import _build_card

        result = _build_card("Q?", "", "a", "", "b", "",
                             model_a_label="MyModelA", model_b_label="MyModelB")

        assert "MyModelA" in result
        assert "MyModelB" in result

    def test_html_escapes_question(self):
        """HTML special characters in the question must be escaped."""
        from app import _build_card

        result = _build_card("<script>", "", "a", "", "b", "")

        assert "<script>" not in result
        assert "&lt;script&gt;" in result


# ---------------------------------------------------------------------------
# Phase 5 — FREE_MODELS registry
# ---------------------------------------------------------------------------


class TestFreeModels:
    """Unit tests for the FREE_MODELS registry."""

    def test_free_models_is_non_empty(self):
        """FREE_MODELS must contain at least one entry."""
        from app import FREE_MODELS

        assert len(FREE_MODELS) > 0

    def test_free_models_contains_2_tuples_of_strings(self):
        """Every entry must be a 2-tuple of (str, str)."""
        from app import FREE_MODELS

        for entry in FREE_MODELS:
            assert isinstance(entry, tuple)
            assert len(entry) == 2
            assert isinstance(entry[0], str)
            assert isinstance(entry[1], str)

    def test_free_models_labels_are_non_empty(self):
        """Display labels (first element) must not be empty strings."""
        from app import FREE_MODELS

        for label, _ in FREE_MODELS:
            assert label.strip() != ""

    def test_free_models_ids_are_non_empty(self):
        """Model IDs (second element) must not be empty strings."""
        from app import FREE_MODELS

        for _, model_id in FREE_MODELS:
            assert model_id.strip() != ""

    def test_free_models_ids_are_strictly_free(self):
        """Every live comparison model must be an explicit OpenRouter free-tier ID."""
        from app import FREE_MODELS

        for _, model_id in FREE_MODELS:
            assert model_id.endswith(":free")

    def test_model_r1_default_present_in_free_models(self):
        """MODEL_R1 default must be one of the model IDs in FREE_MODELS."""
        from app import FREE_MODELS, MODEL_R1

        model_ids = [m_id for _, m_id in FREE_MODELS]
        assert MODEL_R1 in model_ids

    def test_model_llama_default_present_in_free_models(self):
        """MODEL_LLAMA default must be one of the model IDs in FREE_MODELS."""
        from app import FREE_MODELS, MODEL_LLAMA

        model_ids = [m_id for _, m_id in FREE_MODELS]
        assert MODEL_LLAMA in model_ids

    def test_free_models_are_derived_from_shared_runtime_registry(self):
        from app import FREE_MODELS
        from model_registry import list_free_runtime_choices

        expected = sorted(
            (row["label"], row["model_id"])
            for row in list_free_runtime_choices(include_proxy=False)
        )
        assert sorted(FREE_MODELS) == expected


class TestHostedKeyDisclosure:
    def test_comparison_ui_discloses_hosted_key_usage_when_server_key_is_present(self):
        import inspect
        import app

        src = inspect.getsource(app._build_comparison_blocks)
        assert "hosted server-side OpenRouter key" in src


# ---------------------------------------------------------------------------
# Phase 5 — extended call_openrouter (temperature / max_tokens)
# ---------------------------------------------------------------------------


class TestCallOpenrouterInferenceParams:
    """Tests for optional temperature and max_tokens kwargs on call_openrouter."""

    def test_temperature_included_in_payload_when_set(self):
        """temperature kwarg must appear in the POST body when provided."""
        from app import call_openrouter

        with patch("openrouter.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {}
            mock_post.return_value.raise_for_status = MagicMock()

            call_openrouter("key", "model", "q", temperature=0.7)

        _, kwargs = mock_post.call_args
        assert kwargs["json"]["temperature"] == 0.7

    def test_max_tokens_included_in_payload_when_set(self):
        """max_tokens kwarg must appear in the POST body when provided."""
        from app import call_openrouter

        with patch("openrouter.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {}
            mock_post.return_value.raise_for_status = MagicMock()

            call_openrouter("key", "model", "q", max_tokens=512)

        _, kwargs = mock_post.call_args
        assert kwargs["json"]["max_tokens"] == 512

    def test_temperature_absent_when_none(self):
        """temperature must NOT appear in payload when not provided (None)."""
        from app import call_openrouter

        with patch("openrouter.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {}
            mock_post.return_value.raise_for_status = MagicMock()

            call_openrouter("key", "model", "q")

        _, kwargs = mock_post.call_args
        assert "temperature" not in kwargs["json"]

    def test_max_tokens_absent_when_none(self):
        """max_tokens must NOT appear in payload when not provided (None)."""
        from app import call_openrouter

        with patch("openrouter.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {}
            mock_post.return_value.raise_for_status = MagicMock()

            call_openrouter("key", "model", "q")

        _, kwargs = mock_post.call_args
        assert "max_tokens" not in kwargs["json"]

    def test_both_params_sent_when_both_set(self):
        """Both temperature and max_tokens appear together when both provided."""
        from app import call_openrouter

        with patch("openrouter.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {}
            mock_post.return_value.raise_for_status = MagicMock()

            call_openrouter("key", "model", "q", temperature=1.0, max_tokens=256)

        _, kwargs = mock_post.call_args
        assert kwargs["json"]["temperature"] == 1.0
        assert kwargs["json"]["max_tokens"] == 256


# ---------------------------------------------------------------------------
# Phase 5 — _call_model
# ---------------------------------------------------------------------------


class TestCallModel:
    """Unit tests for _call_model(api_key, model_id, prompt, temperature, max_tokens)."""

    def _make_response(self, content, reasoning=None, reasoning_tokens=0):
        resp = {
            "choices": [{"message": {"content": content}}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 50,
            },
        }
        if reasoning is not None:
            resp["choices"][0]["message"]["reasoning"] = reasoning
        if reasoning_tokens > 0:
            resp["usage"]["completion_tokens_details"] = {"reasoning_tokens": reasoning_tokens}
        return resp

    def test_returns_dict_with_answer_and_usage(self):
        """_call_model must return a dict with 'answer' and 'usage' keys."""
        from app import _call_model

        resp = self._make_response("plain answer")
        with patch("app.call_openrouter", return_value=resp):
            result = _call_model("key", "some/model", "q?")

        assert "answer" in result
        assert "usage" in result

    def test_reasoning_from_dedicated_field(self):
        """If message.reasoning is present, use it as reasoning."""
        from app import _call_model

        resp = self._make_response("The answer.", reasoning="deep thought")
        with patch("app.call_openrouter", return_value=resp):
            result = _call_model("key", "some/model", "q?")

        assert result["reasoning"] == "deep thought"
        assert result["answer"] == "The answer."

    def test_reasoning_falls_back_to_think_block(self):
        """If no message.reasoning field, parse <think> block from content."""
        from app import _call_model

        resp = self._make_response("<think>my reasoning</think>My answer.")
        with patch("app.call_openrouter", return_value=resp):
            result = _call_model("key", "some/model", "q?")

        assert "my reasoning" in result["reasoning"]
        assert result["answer"] == "My answer."

    def test_no_reasoning_gives_empty_reasoning(self):
        """Plain content with no reasoning field or think tags → reasoning is ''."""
        from app import _call_model

        resp = self._make_response("Just the answer.")
        with patch("app.call_openrouter", return_value=resp):
            result = _call_model("key", "some/model", "q?")

        assert result["reasoning"] == ""
        assert result["answer"] == "Just the answer."

    def test_forwards_temperature_to_call_openrouter(self):
        """temperature kwarg must be passed through to call_openrouter."""
        from app import _call_model

        resp = self._make_response("answer")
        with patch("app.call_openrouter", return_value=resp) as mock_call:
            _call_model("key", "some/model", "q?", temperature=0.5)

        _, kwargs = mock_call.call_args
        assert kwargs.get("temperature") == 0.5

    def test_forwards_max_tokens_to_call_openrouter(self):
        """max_tokens kwarg must be passed through to call_openrouter."""
        from app import _call_model

        resp = self._make_response("answer")
        with patch("app.call_openrouter", return_value=resp) as mock_call:
            _call_model("key", "some/model", "q?", max_tokens=128)

        _, kwargs = mock_call.call_args
        assert kwargs.get("max_tokens") == 128

    def test_calls_openrouter_with_correct_model_id(self):
        """The model_id argument must be passed to call_openrouter."""
        from app import _call_model

        resp = self._make_response("answer")
        with patch("app.call_openrouter", return_value=resp) as mock_call:
            _call_model("key", "my/custom-model", "q?")

        assert mock_call.call_args.args[1] == "my/custom-model"


# ---------------------------------------------------------------------------
# Phase 5 — updated run_comparison (explicit model IDs + params)
# ---------------------------------------------------------------------------


class TestRunComparisonWithModels:
    """Tests for run_comparison with explicit model_a, model_b, params."""

    def _make_response(self, content):
        return {
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 20},
        }

    def test_uses_provided_model_a_id(self):
        """run_comparison must call _call_model with the model_a ID."""
        from app import run_comparison

        resp = self._make_response("answer")
        with patch("app.call_openrouter", return_value=resp) as mock_call:
            run_comparison("key", "q?", model_a="custom/model-a", model_b="custom/model-b")

        called_models = [call.args[1] for call in mock_call.call_args_list]
        assert "custom/model-a" in called_models

    def test_uses_provided_model_b_id(self):
        """run_comparison must call _call_model with the model_b ID."""
        from app import run_comparison

        resp = self._make_response("answer")
        with patch("app.call_openrouter", return_value=resp) as mock_call:
            run_comparison("key", "q?", model_a="custom/model-a", model_b="custom/model-b")

        called_models = [call.args[1] for call in mock_call.call_args_list]
        assert "custom/model-b" in called_models

    def test_params_a_forwarded_to_model_a(self):
        """params_a temperature/max_tokens must reach call_openrouter for model_a."""
        from app import run_comparison

        resp = self._make_response("answer")
        calls_seen = []

        def capture(*args, **kwargs):
            calls_seen.append((args[1], kwargs))
            return resp

        with patch("app.call_openrouter", side_effect=capture):
            run_comparison(
                "key", "q?",
                model_a="model-a", model_b="model-b",
                params_a={"temperature": 0.3, "max_tokens": 64},
            )

        model_a_call = next(kw for m, kw in calls_seen if m == "model-a")
        assert model_a_call.get("temperature") == 0.3
        assert model_a_call.get("max_tokens") == 64

    def test_params_b_forwarded_to_model_b(self):
        """params_b temperature/max_tokens must reach call_openrouter for model_b."""
        from app import run_comparison

        resp = self._make_response("answer")
        calls_seen = []

        def capture(*args, **kwargs):
            calls_seen.append((args[1], kwargs))
            return resp

        with patch("app.call_openrouter", side_effect=capture):
            run_comparison(
                "key", "q?",
                model_a="model-a", model_b="model-b",
                params_b={"temperature": 1.5, "max_tokens": 256},
            )

        model_b_call = next(kw for m, kw in calls_seen if m == "model-b")
        assert model_b_call.get("temperature") == 1.5
        assert model_b_call.get("max_tokens") == 256

    def test_defaults_use_model_r1_and_model_llama(self):
        """When model_a/model_b omitted, defaults to MODEL_R1 and MODEL_LLAMA."""
        from app import run_comparison, MODEL_R1, MODEL_LLAMA

        resp = self._make_response("answer")
        with patch("app.call_openrouter", return_value=resp) as mock_call:
            run_comparison("key", "q?")

        called_models = [call.args[1] for call in mock_call.call_args_list]
        assert MODEL_R1 in called_models
        assert MODEL_LLAMA in called_models
