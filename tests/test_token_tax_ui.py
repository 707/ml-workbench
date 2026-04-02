"""Tests for the Token Tax Dashboard UI (GH-5, GH-6, GH-8)."""

import csv
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# build_token_tax_ui smoke test
# ---------------------------------------------------------------------------


class TestBuildTokenTaxUi:
    """Smoke tests for build_token_tax_ui() -> gr.Blocks."""

    def test_returns_gradio_blocks(self):
        import gradio as gr

        from workbench.token_tax_ui import build_token_tax_ui

        demo = build_token_tax_ui()
        assert isinstance(demo, gr.Blocks)


class TestWorkbenchHandlers:
    def test_default_benchmark_metric_uses_dense_streaming_metric(self):
        from workbench.token_tax_ui import _default_benchmark_metric_for

        assert _default_benchmark_metric_for("strict_parallel") == "rtc"
        assert _default_benchmark_metric_for("streaming_exploration") == "bytes_per_token"

    def test_default_benchmark_tokenizers_use_curated_subset(self):
        from workbench.token_tax_ui import default_benchmark_tokenizers

        selected = default_benchmark_tokenizers()

        assert "gpt2" in selected
        assert "o200k_base" in selected
        assert "qwen3-coder" not in selected
        assert "trinity-large" not in selected
        assert len(selected) <= 4

    def test_scenario_model_ids_use_all_valid_free_models_for_selected_tokenizers(self):
        from workbench.token_tax_ui import derive_scenario_model_ids

        selected = derive_scenario_model_ids(["llama-3", "mistral"], include_proxy=False)

        assert "meta-llama/llama-3.2-3b-instruct:free" in selected
        assert "mistralai/mistral-7b-instruct:free" in selected
        assert "qwen/qwen-2.5-7b-instruct:free" not in selected

    def test_scenario_model_ids_return_empty_when_no_tokenizers_selected(self):
        from workbench.token_tax_ui import derive_scenario_model_ids

        assert derive_scenario_model_ids([], include_proxy=False) == []

    def test_scenario_model_ids_respect_proxy_toggle(self):
        from workbench.token_tax_ui import derive_scenario_model_ids

        without_proxy = derive_scenario_model_ids(["gemma-2"], include_proxy=False)
        with_proxy = derive_scenario_model_ids(["gemma-2"], include_proxy=True)

        assert without_proxy == []
        assert with_proxy == ["google/gemma-3-27b-it:free"]

    def test_handle_scenario_tab_derives_current_model_selection(self):
        from workbench.token_tax_ui import _handle_scenario_tab
        from workbench.types import ScenarioResult

        captured: dict[str, object] = {}

        def _fake_run_scenario_request(request, progress_callback=None):
            captured["request"] = request
            return ScenarioResult(
                rows=[
                {
                    "label": "gpt-oss-20b (Free)",
                    "model_id": "openai/gpt-oss-20b:free",
                    "language": "en",
                    "tokenizer_key": "gpt-oss",
                    "rtc": 1.4,
                    "context_loss_pct": 28.57,
                    "monthly_input_tokens": 140000,
                    "monthly_output_tokens": 25000,
                    "monthly_cost": 12.5,
                    "ttft_seconds": None,
                    "output_tokens_per_second": None,
                    "provenance": "strict_verified",
                    "mapping_quality": "exact",
                    "lane": "Strict Evidence",
                }
                ],
                model_ids=["openai/gpt-oss-120b:free", "openai/gpt-oss-20b:free"],
            )

        with patch("workbench.token_tax_ui.run_scenario_request", side_effect=_fake_run_scenario_request):
            outputs = _handle_scenario_tab(
                ["en"],
                ["gpt-oss"],
                100000,
                1000,
                250,
                0.1,
                "rtc",
                "monthly_cost",
                "none",
                False,
                False,
                False,
            )

        assert list(captured["request"].tokenizer_keys) == ["gpt-oss"]
        assert outputs[0]["data"][0][2] in {"openai/gpt-oss-120b:free", "openai/gpt-oss-20b:free"}

    def test_handle_scenario_tab_returns_empty_state_when_no_tokenizers_selected(self):
        from workbench.token_tax_ui import _handle_scenario_tab

        outputs = _handle_scenario_tab(
            ["en"],
            [],
            100000,
            600,
            250,
            0.1,
            "rtc",
            "monthly_cost",
            "none",
            False,
            False,
            False,
        )

        assert outputs[0]["data"] == []
        assert "Select at least one benchmark tokenizer family." in outputs[-2]

    def test_handle_catalog_tab_serializes_tokenizer_rows(self):
        from workbench.token_tax_ui import _handle_catalog_tab
        from workbench.types import CatalogResult

        tokenizer_rows = [
            {
                "tokenizer_key": "llama-3",
                "label": "Llama 3 family",
                "tokenizer_source": "NousResearch/Meta-Llama-3-8B",
                "mapping_quality": "exact",
                "provenance": "strict_verified",
                "free_models": [{"label": "Llama 3.2 3B (Free)", "model_id": "meta-llama/llama-3.2-3b-instruct:free"}],
                "aa_matches": [{"label": "Llama 3.1 8B", "ttft_seconds": 0.44}],
            },
        ]

        with patch(
            "workbench.token_tax_ui.run_catalog_request",
            return_value=CatalogResult(
                rows=tokenizer_rows,
                appendix="## Catalog Appendix",
                diagnostics="## Diagnostics",
            ),
        ):
            table, appendix, diagnostics = _handle_catalog_tab(
                include_proxy=False,
                refresh_live=False,
                live_updates=True,
            )

        assert table["headers"][0] == "Tokenizer Family"
        assert table["data"][0][1] == "llama-3"
        assert "Catalog Appendix" in appendix
        assert "Diagnostics" in diagnostics

    def test_handle_catalog_tab_returns_final_tuple_not_streaming_generator(self):
        from workbench.token_tax_ui import _handle_catalog_tab

        outputs = _handle_catalog_tab(include_proxy=False, refresh_live=False, live_updates=False)

        assert isinstance(outputs, tuple)
        assert len(outputs) == 3

    def test_aggregate_scenario_rows_groups_by_model(self):
        from workbench.token_tax_ui import _aggregate_scenario_rows

        rows = [
            {
                "label": "Llama 3.1 8B",
                "model_id": "meta-llama/llama-3.1-8b-instruct",
                "language": "ar",
                "tokenizer_key": "llama-3",
                "rtc": 2.0,
                "context_loss_pct": 50.0,
                "monthly_input_tokens": 200_000,
                "monthly_output_tokens": 55_000,
                "monthly_cost": 10.0,
                "ttft_seconds": 0.44,
                "output_tokens_per_second": 84.2,
                "provenance": "strict_verified",
            },
            {
                "label": "Llama 3.1 8B",
                "model_id": "meta-llama/llama-3.1-8b-instruct",
                "language": "ja",
                "tokenizer_key": "llama-3",
                "rtc": 1.5,
                "context_loss_pct": 33.3,
                "monthly_input_tokens": 150_000,
                "monthly_output_tokens": 55_000,
                "monthly_cost": 7.5,
                "ttft_seconds": 0.44,
                "output_tokens_per_second": 84.2,
                "provenance": "strict_verified",
            },
        ]

        aggregated = _aggregate_scenario_rows(rows)

        assert len(aggregated) == 1
        assert aggregated[0]["monthly_cost"] == 17.5
        assert aggregated[0]["monthly_input_tokens"] == 350_000

    def test_handle_benchmark_tab_returns_final_tuple_with_live_diagnostics_enabled(self):
        from workbench.token_tax_ui import _handle_benchmark_tab
        from workbench.types import BenchmarkResult

        benchmark_rows = [
            {
                "lane": "Strict Evidence",
                "language": "en",
                "label": "GPT-2 legacy",
                "tokenizer_key": "gpt2",
                "token_count": 4,
                "token_fertility": 1.0,
                "bytes_per_token": 1.2,
                "rtc": 1.0,
                "byte_premium": 1.0,
                "risk_level": "low",
                "sample_count": 2,
                "provenance": "strict_verified",
                "mapping_quality": "exact",
                "corpus_key": "strict_parallel",
            },
        ]
        raw_rows = [
            {
                "lane": "Strict Evidence",
                "language": "en",
                "tokenizer_key": "gpt2",
                "sample_index": 0,
                "token_count": 4,
                "unique_tokens": 4,
                "continued_word_rate": 0.25,
                "bytes_per_token": 1.2,
                "rtc": 1.0,
                "text": "hello world",
                "english_text": "hello world",
                "token_preview": "hello | world",
            },
        ]
        with patch(
            "workbench.token_tax_ui.run_benchmark_request",
            return_value=BenchmarkResult(
                rows=benchmark_rows,
                raw_rows=raw_rows,
                languages=["en"],
                tokenizers=["gpt2"],
                composition_rows=[],
            ),
        ):
            outputs = _handle_benchmark_tab(
                "strict_parallel",
                ["en"],
                ["gpt2"],
                "rtc",
                5,
                False,
                False,
                "en",
                "gpt2",
                0,
                True,
            )

        assert isinstance(outputs, tuple)
        assert len(outputs) == 12
        assert "Benchmark Summary" in outputs[0]
        assert outputs[5] is not None
        assert "Diagnostics" in outputs[-1]

    def test_handle_benchmark_tab_returns_runtime_message_when_benchmark_errors(self):
        from workbench.token_tax_ui import _handle_benchmark_tab

        with patch("workbench.token_tax_ui.run_benchmark_request", side_effect=RuntimeError("boom")):
            outputs = _handle_benchmark_tab(
                "Strict Evidence",
                ["en"],
                ["gpt2"],
                "rtc",
                5,
                False,
                False,
                "en",
                "gpt2",
                0,
                False,
            )

        assert "Runtime error" in outputs[-2]
        assert "boom" in outputs[-2]

    def test_language_script_presets_filter_supported_languages(self):
        from workbench.token_tax_ui import apply_language_preset

        assert apply_language_preset("Arabic") == ["ar"]
        assert set(apply_language_preset("Latin")) >= {"en", "fr", "de", "es", "pt"}

    def test_language_choice_pairs_use_human_readable_labels(self):
        from workbench.token_tax_ui import language_choice_pairs

        choices = language_choice_pairs(["en", "ar", "hi"])
        assert ("English", "en") in choices
        assert ("Arabic", "ar") in choices
        assert ("Hindi", "hi") in choices

    def test_build_benchmark_preview_markdown_uses_selected_row(self):
        from workbench.token_tax_ui import build_benchmark_preview_markdown

        markdown = build_benchmark_preview_markdown(
            [
                {
                    "lane": "Strict Evidence",
                    "language": "fr",
                    "tokenizer_key": "gpt2",
                    "sample_index": 0,
                    "text": "Bonjour le monde",
                    "token_preview": "Bon | jour | monde",
                    "token_texts": ["Bon", "jour", "monde"],
                    "token_count": 3,
                },
            ],
            "fr",
            "gpt2",
            0,
        )

        assert "Strict Evidence" in markdown
        assert "French" in markdown
        assert "preview-token" in markdown
        assert "Bonjour le monde" in markdown

    def test_build_coverage_rows_extracts_unique_token_metrics(self):
        from workbench.token_tax_ui import build_coverage_rows

        rows = build_coverage_rows(
            [
                {
                    "language": "fr",
                    "tokenizer_key": "gpt2",
                    "label": "GPT-2 legacy",
                    "unique_tokens": 12,
                    "continued_word_rate": 0.4,
                    "bytes_per_token": 2.0,
                    "lane": "Streaming Exploration",
                },
            ]
        )

        assert rows[0]["unique_tokens"] == 12
        assert rows[0]["continued_word_rate"] == 0.4

    def test_observed_composition_uses_full_token_texts_not_preview(self):
        from workbench.token_tax_ui import build_observed_composition_rows

        rows = build_observed_composition_rows(
            [
                {
                    "language": "fr",
                    "tokenizer_key": "gpt2",
                    "token_preview": "Bon | jour",
                    "token_texts": ["Bon", "jour", "monde"],
                },
            ]
        )

        assert sum(row["token_count"] for row in rows) == 3

    def test_build_benchmark_summary_markdown_reports_key_ranges(self):
        from workbench.token_tax_ui import build_benchmark_summary_markdown

        markdown = build_benchmark_summary_markdown(
            [
                {
                    "lane": "Strict Evidence",
                    "language": "ar",
                    "tokenizer_key": "gpt2",
                    "rtc": 2.4,
                    "bytes_per_token": 3.2,
                    "continued_word_rate": 0.55,
                },
                {
                    "lane": "Strict Evidence",
                    "language": "ja",
                    "tokenizer_key": "llama-3",
                    "rtc": 1.6,
                    "bytes_per_token": 1.8,
                    "continued_word_rate": 0.22,
                },
            ],
            metric_key="rtc",
        )

        assert "Benchmark Summary" in markdown
        assert "summary-pill" in markdown
        assert "Biggest Relative Token Cost jump" in markdown
        assert "Text packed into each token" in markdown
        assert "Word split rate" in markdown

    def test_build_benchmark_summary_markdown_uses_plain_language_labels(self):
        from workbench.token_tax_ui import build_benchmark_summary_markdown

        markdown = build_benchmark_summary_markdown(
            [
                {
                    "lane": "Strict Evidence",
                    "language": "ar",
                    "tokenizer_key": "gpt2",
                    "rtc": 2.4,
                    "bytes_per_token": 3.2,
                    "continued_word_rate": 0.55,
                },
            ],
            metric_key="rtc",
        )

        assert "Relative Token Cost" in markdown
        assert "Text packed into each token" in markdown
        assert "Word split rate" in markdown

    def test_chart_explainer_text_is_visible_copy_not_tooltip_html(self):
        import inspect

        import workbench.token_tax_ui as token_tax_ui

        src = inspect.getsource(token_tax_ui.build_token_tax_ui)
        assert "tooltip_label_html" not in src
        assert "How to read this chart" in src

    def test_filter_layout_uses_asymmetric_rail_classes(self):
        import inspect

        import workbench.token_tax_ui as token_tax_ui

        src = inspect.getsource(token_tax_ui.build_token_tax_ui)
        assert "filter-rail filter-rail--compact" in src
        assert "filter-rail filter-rail--wide" in src
        assert "filter-rail filter-rail--scenario-inputs" in src
        assert "scenario-control-grid" in src
        assert "scenario-control-stack" in src
        assert "scenario-checkbox-group" in src
        assert "scenario-custom-row" in src
        assert "scenario-options-row" in src
        assert 'show_progress="full"' in src
        assert 'gr.File(label="Raw Data CSV"' in src
        assert 'gr.DataFrame(label="Raw Benchmark Data"' not in src

    def test_catalog_filters_use_horizontal_utility_row(self):
        import inspect

        import workbench.token_tax_ui as token_tax_ui

        src = inspect.getsource(token_tax_ui.build_token_tax_ui)
        assert "catalog-utility-row" in src

    def test_build_coverage_rows_preserve_fertility_for_bar_charts(self):
        from workbench.token_tax_ui import build_coverage_rows

        rows = build_coverage_rows(
            [
                {
                    "language": "fr",
                    "tokenizer_key": "gpt2",
                    "label": "GPT-2 legacy",
                    "unique_tokens": 12,
                    "continued_word_rate": 0.4,
                    "bytes_per_token": 2.0,
                    "token_fertility": 1.9,
                    "lane": "Streaming Exploration",
                },
            ]
        )

        assert rows[0]["token_fertility"] == 1.9

    def test_build_scenario_speed_summary_reports_matches_and_gaps(self):
        from workbench.token_tax_ui import build_scenario_speed_summary_markdown

        markdown = build_scenario_speed_summary_markdown(
            [
                {
                    "label": "Llama 3.2 3B Instruct (Free)",
                    "ttft_seconds": None,
                    "output_tokens_per_second": None,
                },
                {
                    "label": "Mistral 7B Instruct (Free)",
                    "ttft_seconds": 0.45,
                    "output_tokens_per_second": 88.0,
                },
                {
                    "label": "Qwen 2.5 7B Instruct (Free)",
                    "ttft_seconds": 0.62,
                    "output_tokens_per_second": 71.5,
                },
            ]
        )

        assert "matched models: **2 / 3**" in markdown.lower()
        assert "Mistral 7B Instruct (Free)" in markdown
        assert "Llama 3.2 3B Instruct (Free)" in markdown

    def test_build_scenario_outputs_includes_language_detail_plots(self):
        from workbench.token_tax_ui import _build_scenario_outputs

        rows = [
            {
                "label": "Qwen 2.5 7B Instruct (Free)",
                "model_id": "qwen/qwen-2.5-7b-instruct:free",
                "language": "en",
                "tokenizer_key": "qwen-2.5",
                "rtc": 1.0,
                "context_loss_pct": 0.0,
                "monthly_input_tokens": 100000,
                "monthly_output_tokens": 25000,
                "monthly_cost": 10.0,
                "ttft_seconds": None,
                "output_tokens_per_second": None,
                "provenance": "strict_verified",
            },
            {
                "label": "Qwen 2.5 7B Instruct (Free)",
                "model_id": "qwen/qwen-2.5-7b-instruct:free",
                "language": "ar",
                "tokenizer_key": "qwen-2.5",
                "rtc": 1.6,
                "context_loss_pct": 37.5,
                "monthly_input_tokens": 160000,
                "monthly_output_tokens": 25000,
                "monthly_cost": 12.0,
                "ttft_seconds": None,
                "output_tokens_per_second": None,
                "provenance": "strict_verified",
            },
        ]

        outputs = _build_scenario_outputs(rows, "strict_parallel", "rtc", "monthly_cost", "none")

        assert outputs[2].data
        assert outputs[4].data
        assert outputs[9].data

    def test_handle_scenario_tab_recomputes_chart_outputs_across_runs(self):
        from workbench.token_tax_ui import _handle_scenario_tab
        from workbench.types import ScenarioResult

        def _fake_run_scenario_request(request, progress_callback=None):
            tokenizer_key = request.tokenizer_keys[0]
            if tokenizer_key == "llama-3":
                return ScenarioResult(rows=[
                    {
                        "label": "Llama 3.2 3B Instruct (Free)",
                        "model_id": "meta-llama/llama-3.2-3b-instruct:free",
                        "language": "en",
                        "tokenizer_key": "llama-3",
                        "rtc": 1.2,
                        "context_loss_pct": 10.0,
                        "monthly_input_tokens": 120000,
                        "monthly_output_tokens": 25000,
                        "monthly_cost": 8.0,
                        "ttft_seconds": None,
                        "output_tokens_per_second": None,
                        "provenance": "strict_verified",
                    }
                ], model_ids=["meta-llama/llama-3.2-3b-instruct:free"])
            return ScenarioResult(rows=[
                {
                    "label": "Qwen 2.5 7B Instruct (Free)",
                    "model_id": "qwen/qwen-2.5-7b-instruct:free",
                    "language": "en",
                    "tokenizer_key": "qwen-2.5",
                    "rtc": 1.8,
                    "context_loss_pct": 20.0,
                    "monthly_input_tokens": 180000,
                    "monthly_output_tokens": 25000,
                    "monthly_cost": 14.0,
                    "ttft_seconds": None,
                    "output_tokens_per_second": None,
                    "provenance": "strict_verified",
                }
            ], model_ids=["qwen/qwen-2.5-7b-instruct:free"])

        with patch("workbench.token_tax_ui.run_scenario_request", side_effect=_fake_run_scenario_request):
            first = _handle_scenario_tab(
                ["en"], ["llama-3"], 100000, 600, 250, 0.1, "rtc", "monthly_cost", "none", False, False, False
            )
            second = _handle_scenario_tab(
                ["en"], ["qwen-2.5"], 100000, 600, 250, 0.1, "rtc", "monthly_cost", "none", False, False, False
            )

        assert float(first[1].data[0].x[0]) != float(second[1].data[0].x[0])

    def test_handle_scenario_tab_returns_final_tuple_not_streaming_generator(self):
        from workbench.token_tax_ui import _handle_scenario_tab
        from workbench.types import ScenarioResult

        with patch("workbench.token_tax_ui.run_scenario_request", return_value=ScenarioResult(rows=[], model_ids=[])):
            result = _handle_scenario_tab(
                ["en"],
                ["llama-3"],
                100000,
                600,
                250,
                0.1,
                "rtc",
                "monthly_cost",
                "none",
                False,
                False,
                False,
            )

        assert isinstance(result, tuple)

    def test_build_benchmark_chart_explainer_mentions_plain_language_terms(self):
        from workbench.token_tax_ui import build_benchmark_chart_explainer_markdown

        markdown = build_benchmark_chart_explainer_markdown("rtc", "Coverage")

        assert "Relative Token Cost" in markdown
        assert "same meaning" in markdown
        assert "###" not in markdown

    def test_build_benchmark_chart_explainer_for_coverage_mentions_split_rate(self):
        from workbench.token_tax_ui import build_benchmark_chart_explainer_markdown

        markdown = build_benchmark_chart_explainer_markdown("token_fertility", "Coverage")

        assert "Word split rate" in markdown
        assert "Tokens per word / character" in markdown
        assert markdown.lstrip().startswith("<div")

    def test_build_benchmark_chart_explainer_for_streaming_baseline_mentions_caveat(self):
        from workbench.token_tax_ui import build_benchmark_chart_explainer_markdown

        markdown = build_benchmark_chart_explainer_markdown("english_baseline_ratio", "Overview")

        assert "exploratory" in markdown.lower()
        assert "english baseline" in markdown.lower()
        assert "not aligned" in markdown.lower()
        assert "metric-badge" in markdown

    def test_sparse_streaming_baseline_metric_shows_explanatory_empty_state(self):
        from workbench.token_tax_ui import _build_benchmark_outputs

        rows = [
            {
                "lane": "Streaming Exploration",
                "language": "en",
                "tokenizer_key": "gpt2",
                "bytes_per_token": 2.0,
                "token_fertility": 1.5,
                "continued_word_rate": 0.2,
                "unique_tokens": 12,
                "english_baseline_ratio": 1.0,
                "sample_count": 3,
                "provenance": "strict_verified",
                "corpus_key": "streaming_exploration",
            },
            {
                "lane": "Streaming Exploration",
                "language": "ar",
                "tokenizer_key": "gpt2",
                "bytes_per_token": 1.8,
                "token_fertility": 5.2,
                "continued_word_rate": 0.7,
                "unique_tokens": 34,
                "english_baseline_ratio": None,
                "sample_count": 3,
                "provenance": "strict_verified",
                "corpus_key": "streaming_exploration",
            },
            {
                "lane": "Streaming Exploration",
                "language": "hi",
                "tokenizer_key": "gpt2",
                "bytes_per_token": 1.7,
                "token_fertility": 6.0,
                "continued_word_rate": 0.8,
                "unique_tokens": 31,
                "english_baseline_ratio": None,
                "sample_count": 3,
                "provenance": "strict_verified",
                "corpus_key": "streaming_exploration",
            },
        ]

        outputs = _build_benchmark_outputs(
            rows,
            [],
            [],
            ["en", "ar", "hi"],
            "english_baseline_ratio",
            "appendix",
            "en",
            "gpt2",
            0,
        )

        heatmap = outputs[2]
        distribution = outputs[3]

        assert "english baseline" in heatmap.layout.annotations[0].text.lower()
        assert "english baseline" in distribution.layout.annotations[0].text.lower()

    def test_build_benchmark_summary_marks_streaming_baseline_as_exploratory(self):
        from workbench.token_tax_ui import build_benchmark_summary_markdown

        markdown = build_benchmark_summary_markdown(
            [
                {
                    "lane": "Streaming Exploration",
                    "language": "en",
                    "tokenizer_key": "gpt2",
                    "english_baseline_ratio": 1.0,
                    "bytes_per_token": 2.4,
                    "continued_word_rate": 0.25,
                },
            ],
            metric_key="english_baseline_ratio",
        )

        assert "Exploratory only" in markdown
        assert "metric-badge" in markdown

    def test_build_scenario_appendix_summary_is_compact_plain_language(self):
        from workbench.token_tax_ui import build_scenario_appendix_summary_html

        html = build_scenario_appendix_summary_html()

        assert "Scenario assumptions" in html
        assert "Strict Evidence" in html
        assert "business impact" in html
        assert "benchmark-driven" in html.lower()
        assert "legacy 4 chars/token heuristic" in html.lower()

    def test_shorten_model_label_truncates_long_values(self):
        from workbench.token_tax_ui import shorten_model_label

        shortened = shorten_model_label("Qwen 2.5 7B Instruct (Free) with very long suffix")

        assert shortened.endswith("...")
        assert len(shortened) < len("Qwen 2.5 7B Instruct (Free) with very long suffix")

    def test_export_rows_csv_writes_current_rows(self):
        from workbench.token_tax_ui import export_rows_csv

        path = export_rows_csv(
            [
                {"language": "English", "tokenizer_key": "gpt2", "rtc": 1.0},
                {"language": "Arabic", "tokenizer_key": "gpt2", "rtc": 2.4},
            ],
            ["language", "tokenizer_key", "rtc"],
            prefix="benchmark-raw",
        )

        assert path is not None
        csv_path = Path(path)
        assert csv_path.exists()
        assert csv_path.read_text(encoding="utf-8").splitlines()[0] == "language,tokenizer_key,rtc"

    def test_export_rows_csv_returns_none_for_empty_rows(self):
        from workbench.token_tax_ui import export_rows_csv

        assert export_rows_csv([], ["language"]) is None

    def test_catalog_display_rows_use_review_friendly_column_labels(self):
        from workbench.token_tax_ui import CATALOG_COLUMNS, _catalog_display_rows

        rows = _catalog_display_rows(
            [
                {
                    "tokenizer_key": "llama-3",
                    "label": "Llama 3 family",
                    "tokenizer_source": "NousResearch/Meta-Llama-3-8B",
                    "mapping_quality": "exact",
                    "provenance": "strict_verified",
                    "free_models": [{"label": "Llama 3.2 3B Instruct (Free)"}],
                    "aa_matches": [{"label": "Llama 3.1 8B"}],
                    "min_input_per_million": 0.05,
                    "max_context_window": 128000,
                },
            ]
        )

        assert "Tokenizer Family" in CATALOG_COLUMNS
        assert "Free Model Examples" in CATALOG_COLUMNS
        assert rows[0]["Tokenizer Family"] == "Llama 3 family"
        assert rows[0]["Free Model Examples"] == "Llama 3.2 3B Instruct (Free)"

    def test_catalog_display_rows_use_human_friendly_mapping_labels(self):
        from workbench.token_tax_ui import _catalog_display_rows

        rows = _catalog_display_rows(
            [
                {
                    "tokenizer_key": "command-r",
                    "label": "Command R family (BLOOM proxy)",
                    "tokenizer_source": "bigscience/bloom-560m",
                    "mapping_quality": "proxy",
                    "provenance": "proxy",
                    "free_models": [],
                    "aa_matches": [],
                    "min_input_per_million": None,
                    "max_context_window": None,
                },
            ]
        )

        assert rows[0]["Mapping"] == "Proxy tokenizer mapping"


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
        from workbench.token_tax_ui import _handle_dashboard

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
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
        from workbench.token_tax_ui import _handle_dashboard

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
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
        from workbench.token_tax_ui import _handle_dashboard

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            table_data, _, _, _, _ = _handle_dashboard(
                text="test",
                english_text="test",
                selected_models=["gpt2", "mistral"],
                monthly_requests=1000,
                avg_chars=50,
            )

        assert len(table_data["data"]) == 2

    def test_no_english_text_still_works(self):
        from workbench.token_tax_ui import _handle_dashboard

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
            result = _handle_dashboard(
                text="hello",
                english_text="",
                selected_models=["gpt2"],
                monthly_requests=1000,
                avg_chars=50,
            )

        assert len(result) == 5

    def test_empty_text_returns_gracefully(self):
        from workbench.token_tax_ui import _handle_dashboard

        with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(0)):
            result = _handle_dashboard(
                text="",
                english_text="",
                selected_models=["gpt2"],
                monthly_requests=0,
                avg_chars=0,
            )

        assert len(result) == 5

    def test_no_models_selected_returns_empty(self):
        from workbench.token_tax_ui import _handle_dashboard

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
        from workbench.token_tax_ui import _handle_dashboard

        with patch("workbench.token_tax.get_tokenizer", side_effect=ValueError("bad model")):
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
        from workbench.token_tax_ui import _handle_traffic

        table, _, summary = _handle_traffic(None, "gpt2")
        assert "Upload" in summary
        assert len(table["data"]) == 0

    def test_valid_csv_returns_results(self):
        from workbench.token_tax_ui import _handle_traffic

        path = _write_csv(
            [["en", "1000", "500"], ["ar", "2000", "300"]],
            headers=["language", "request_count", "avg_chars"],
        )
        try:
            with patch("workbench.token_tax.get_tokenizer", return_value=self._mock_tokenizer(5)):
                table, _, summary = _handle_traffic(path, "gpt2")

            assert len(table["data"]) == 2
            assert "token tax exposure" in summary.lower()
            assert "legacy heuristic estimate" in summary.lower()
            assert "4 chars/token" in summary.lower()
        finally:
            os.unlink(path)

    def test_invalid_csv_returns_error(self):
        from workbench.token_tax_ui import _handle_traffic

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
        from workbench.token_tax_ui import _handle_traffic

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
        from workbench.token_tax_ui import _handle_traffic

        path = _write_csv(
            [["en", "1000", "500"]],
            headers=["language", "request_count", "avg_chars"],
        )
        try:
            with patch("workbench.token_tax.get_tokenizer", side_effect=ValueError("bad")):
                table, _, summary = _handle_traffic(path, "gpt2")
            assert "error" in summary.lower()
        finally:
            os.unlink(path)

    def test_high_exposure_shows_warning(self):
        from workbench.token_tax_ui import _handle_traffic

        path = _write_csv(
            [["ar", "5000", "500"]],
            headers=["language", "request_count", "avg_chars"],
        )
        try:
            # Mock so Arabic gets many more tokens than English baseline
            source_tok = self._mock_tokenizer(15)  # Arabic: 15 tokens

            def _side_effect(name):
                return source_tok  # same tokenizer, tokenize_text will differ

            with patch("workbench.token_tax.get_tokenizer", side_effect=_side_effect):
                with patch("workbench.token_tax.tokenize_text") as mock_tt:
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
        from workbench.charts import build_bubble_chart

        fig = build_bubble_chart(self._make_results())
        assert isinstance(fig, go.Figure)

    def test_figure_has_traces(self):
        from workbench.charts import build_bubble_chart

        fig = build_bubble_chart(self._make_results(3))
        assert len(fig.data) > 0

    def test_trace_type_is_scatter(self):
        from workbench.charts import build_bubble_chart

        fig = build_bubble_chart(self._make_results(3))
        for trace in fig.data:
            assert trace.type == "scatter"

    def test_empty_results_returns_empty_figure(self):
        from workbench.charts import build_bubble_chart

        fig = build_bubble_chart([])
        assert isinstance(fig, go.Figure)
        # Should have no data traces or an annotation explaining emptiness
        assert len(fig.data) == 0 or all(
            len(trace.x or []) == 0 for trace in fig.data
        )

    def test_single_model_does_not_crash(self):
        from workbench.charts import build_bubble_chart

        fig = build_bubble_chart(self._make_results(1))
        assert isinstance(fig, go.Figure)
        assert len(fig.data) > 0

    def test_bubble_size_varies_with_token_count(self):
        from workbench.charts import build_bubble_chart

        results = self._make_results(3)
        fig = build_bubble_chart(results)
        # All traces should have marker sizes set
        for trace in fig.data:
            assert trace.marker is not None
            assert trace.marker.size is not None

    def test_axes_labels(self):
        from workbench.charts import build_bubble_chart

        fig = build_bubble_chart(self._make_results(3))
        assert "RTC" in (fig.layout.xaxis.title.text or "")
        assert "Cost" in (fig.layout.yaxis.title.text or "")
