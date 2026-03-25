"""Tests for the Token Tax Dashboard UI (GH-5)."""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# build_token_tax_ui smoke test
# ---------------------------------------------------------------------------


class TestBuildTokenTaxUi:
    """Smoke tests for build_token_tax_ui() -> gr.Blocks."""

    def test_returns_gradio_blocks(self):
        import gradio as gr
        from token_tax_ui import build_token_tax_ui

        demo = build_token_tax_ui()
        assert isinstance(demo, gr.Blocks)


# ---------------------------------------------------------------------------
# handle_dashboard
# ---------------------------------------------------------------------------


class TestHandleDashboard:
    """Tests for the _handle_dashboard extracted handler."""

    def _mock_tokenizer(self, token_count: int):
        tok = MagicMock()
        tok.encode.return_value = list(range(token_count))
        tok.convert_ids_to_tokens.return_value = [f"t{i}" for i in range(token_count)]
        return tok

    def test_returns_expected_outputs(self):
        from token_tax_ui import _handle_dashboard

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = _handle_dashboard(
                text="hello world",
                english_text="hello world",
                selected_models=["gpt2"],
                monthly_requests=1000,
                avg_chars=100,
            )

        # Should return: (table_data, context_md, recommendations_md)
        assert len(result) == 3
        table_data, context_md, recs_md = result
        assert isinstance(table_data, dict)
        assert isinstance(context_md, str)
        assert isinstance(recs_md, str)

    def test_table_has_expected_columns(self):
        from token_tax_ui import _handle_dashboard

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            table_data, _, _ = _handle_dashboard(
                text="test",
                english_text="test",
                selected_models=["gpt2"],
                monthly_requests=1000,
                avg_chars=50,
            )

        assert "headers" in table_data
        assert "data" in table_data
        assert len(table_data["data"]) == 1  # one model

    def test_multiple_models(self):
        from token_tax_ui import _handle_dashboard

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            table_data, _, _ = _handle_dashboard(
                text="test",
                english_text="test",
                selected_models=["gpt2", "mistral"],
                monthly_requests=1000,
                avg_chars=50,
            )

        assert len(table_data["data"]) == 2

    def test_no_english_text_still_works(self):
        from token_tax_ui import _handle_dashboard

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = _handle_dashboard(
                text="hello",
                english_text="",
                selected_models=["gpt2"],
                monthly_requests=1000,
                avg_chars=50,
            )

        assert len(result) == 3

    def test_empty_text_returns_gracefully(self):
        from token_tax_ui import _handle_dashboard

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(0)):
            result = _handle_dashboard(
                text="",
                english_text="",
                selected_models=["gpt2"],
                monthly_requests=0,
                avg_chars=0,
            )

        assert len(result) == 3

    def test_no_models_selected_returns_empty(self):
        from token_tax_ui import _handle_dashboard

        result = _handle_dashboard(
            text="test",
            english_text="test",
            selected_models=[],
            monthly_requests=1000,
            avg_chars=50,
        )

        table_data, _, recs = result
        assert len(table_data["data"]) == 0

    def test_error_returns_error_message(self):
        from token_tax_ui import _handle_dashboard

        with patch("token_tax.get_tokenizer", side_effect=ValueError("bad model")):
            result = _handle_dashboard(
                text="test",
                english_text="test",
                selected_models=["bad"],
                monthly_requests=1000,
                avg_chars=50,
            )

        _, _, recs = result
        assert "error" in recs.lower() or "Error" in recs
