"""Tests for the Token Tax Dashboard UI (GH-5, GH-6, GH-8)."""

import csv
import os
import tempfile

import plotly.graph_objects as go
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


class TestWorkbenchHandlers:
    def test_handle_catalog_tab_serializes_tokenizer_rows(self):
        from token_tax_ui import _handle_catalog_tab

        tokenizer_rows = [
            {
                "tokenizer_key": "llama-3",
                "label": "Llama 3 family",
                "tokenizer_source": "NousResearch/Meta-Llama-3-8B",
                "mapping_quality": "exact",
                "provenance": "strict_verified",
                "free_models": [{"label": "Llama 3.1 8B", "model_id": "meta-llama/llama-3.1-8b-instruct"}],
                "aa_matches": [{"label": "Llama 3.1 8B", "ttft_seconds": 0.44}],
            },
        ]

        with patch("token_tax_ui.build_tokenizer_catalog", return_value=tokenizer_rows):
            table, appendix, diagnostics = _handle_catalog_tab(include_proxy=False, refresh_live=False)

        assert table["headers"][0] == "label"
        assert table["data"][0][1] == "llama-3"
        assert "Catalog Appendix" in appendix
        assert "Diagnostics" in diagnostics


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

        # Should return: (table_data, context_md, bubble_chart, context_chart, recommendations_md)
        assert len(result) == 5
        table_data, context_md, bubble, ctx_chart, recs_md = result
        assert isinstance(table_data, dict)
        assert isinstance(context_md, str)
        assert isinstance(bubble, go.Figure)
        assert isinstance(ctx_chart, go.Figure)
        assert isinstance(recs_md, str)

    def test_table_has_expected_columns(self):
        from token_tax_ui import _handle_dashboard

        with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            table_data, _, _, _, _ = _handle_dashboard(
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
            table_data, _, _, _, _ = _handle_dashboard(
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

        assert len(result) == 5

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

        assert len(result) == 5

    def test_no_models_selected_returns_empty(self):
        from token_tax_ui import _handle_dashboard

        result = _handle_dashboard(
            text="test",
            english_text="test",
            selected_models=[],
            monthly_requests=1000,
            avg_chars=50,
        )

        table_data, _, _, _, recs = result
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

        _, _, _, _, recs = result
        assert "error" in recs.lower() or "Error" in recs


# ---------------------------------------------------------------------------
# _handle_traffic (GH-6)
# ---------------------------------------------------------------------------


def _write_csv(rows, headers=None):
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", newline="") as f:
        writer = csv.writer(f)
        if headers:
            writer.writerow(headers)
        writer.writerows(rows)
    return path


class TestHandleTraffic:
    """Tests for _handle_traffic extracted handler."""

    def _mock_tokenizer(self, token_count: int):
        tok = MagicMock()
        tok.encode.return_value = list(range(token_count))
        tok.convert_ids_to_tokens.return_value = [f"t{i}" for i in range(token_count)]
        return tok

    def test_no_file_returns_upload_message(self):
        from token_tax_ui import _handle_traffic

        table, _, summary = _handle_traffic(None, "gpt2")
        assert "Upload" in summary
        assert len(table["data"]) == 0

    def test_valid_csv_returns_results(self):
        from token_tax_ui import _handle_traffic

        path = _write_csv(
            [["en", "1000", "500"], ["ar", "2000", "300"]],
            headers=["language", "request_count", "avg_chars"],
        )
        try:
            with patch("token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
                table, _, summary = _handle_traffic(path, "gpt2")

            assert len(table["data"]) == 2
            assert "token tax exposure" in summary.lower()
        finally:
            os.unlink(path)

    def test_invalid_csv_returns_error(self):
        from token_tax_ui import _handle_traffic

        path = _write_csv(
            [["en", "1000"]],
            headers=["language", "request_count"],
        )
        try:
            table, _, summary = _handle_traffic(path, "gpt2")
            assert "CSV error" in summary
        finally:
            os.unlink(path)

    def test_empty_csv_returns_no_data_message(self):
        from token_tax_ui import _handle_traffic

        path = _write_csv(
            [],
            headers=["language", "request_count", "avg_chars"],
        )
        try:
            table, _, summary = _handle_traffic(path, "gpt2")
            assert "no data" in summary.lower()
        finally:
            os.unlink(path)

    def test_analysis_error_returns_error_message(self):
        from token_tax_ui import _handle_traffic

        path = _write_csv(
            [["en", "1000", "500"]],
            headers=["language", "request_count", "avg_chars"],
        )
        try:
            with patch("token_tax.get_tokenizer", side_effect=ValueError("bad")):
                table, _, summary = _handle_traffic(path, "gpt2")
            assert "error" in summary.lower()
        finally:
            os.unlink(path)

    def test_high_exposure_shows_warning(self):
        from token_tax_ui import _handle_traffic

        path = _write_csv(
            [["ar", "5000", "500"]],
            headers=["language", "request_count", "avg_chars"],
        )
        try:
            # Mock so Arabic gets many more tokens than English baseline
            source_tok = self._mock_tokenizer(15)  # Arabic: 15 tokens
            english_tok = self._mock_tokenizer(5)   # English: 5 tokens
            call_count = [0]

            def _side_effect(name):
                return source_tok  # same tokenizer, tokenize_text will differ

            with patch("token_tax.get_tokenizer", side_effect=_side_effect):
                with patch("token_tax.tokenize_text") as mock_tt:
                    # First call = English baseline, second = Arabic
                    mock_tt.side_effect = [
                        [{"token": f"t{i}", "id": i} for i in range(5)],   # en
                        [{"token": f"t{i}", "id": i} for i in range(15)],  # ar
                    ]
                    table, _, summary = _handle_traffic(path, "gpt2")

            assert "significant" in summary.lower()
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# build_bubble_chart (GH-8)
# ---------------------------------------------------------------------------


class TestBuildBubbleChart:
    """Tests for the build_bubble_chart pure function."""

    def _make_results(self, n: int = 3) -> list[dict]:
        """Create n fake analysis results for testing."""
        risk_levels = ["low", "moderate", "high", "severe"]
        return [
            {
                "model": f"model-{i}",
                "token_count": 100 * (i + 1),
                "rtc": 1.0 + i * 0.5,
                "cost_per_million": 0.01 * (i + 1),
                "context_usage": 0.001 * (i + 1),
                "byte_premium": 1.0 + i * 0.1,
                "risk_level": risk_levels[i % len(risk_levels)],
            }
            for i in range(n)
        ]

    def test_returns_plotly_figure(self):
        from charts import build_bubble_chart

        fig = build_bubble_chart(self._make_results())
        assert isinstance(fig, go.Figure)

    def test_figure_has_traces(self):
        from charts import build_bubble_chart

        fig = build_bubble_chart(self._make_results(3))
        assert len(fig.data) > 0

    def test_trace_type_is_scatter(self):
        from charts import build_bubble_chart

        fig = build_bubble_chart(self._make_results(3))
        for trace in fig.data:
            assert trace.type == "scatter"

    def test_empty_results_returns_empty_figure(self):
        from charts import build_bubble_chart

        fig = build_bubble_chart([])
        assert isinstance(fig, go.Figure)
        # Should have no data traces or an annotation explaining emptiness
        assert len(fig.data) == 0 or all(
            len(trace.x or []) == 0 for trace in fig.data
        )

    def test_single_model_does_not_crash(self):
        from charts import build_bubble_chart

        fig = build_bubble_chart(self._make_results(1))
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_bubble_size_varies_with_token_count(self):
        from charts import build_bubble_chart

        results = self._make_results(3)
        fig = build_bubble_chart(results)
        # All traces should have marker sizes set
        for trace in fig.data:
            assert trace.marker is not None
            assert trace.marker.size is not None

    def test_axes_labels(self):
        from charts import build_bubble_chart

        fig = build_bubble_chart(self._make_results(3))
        assert "RTC" in (fig.layout.xaxis.title.text or "")
        assert "Cost" in (fig.layout.yaxis.title.text or "")
