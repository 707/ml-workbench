"""Tests for the charts module (Issue 5–8)."""

import pytest

# ---------------------------------------------------------------------------
# RISK_COLORS
# ---------------------------------------------------------------------------


class TestRiskColors:
    """Validate RISK_COLORS dict exported from charts."""

    def test_is_dict(self):
        from charts import RISK_COLORS

        assert isinstance(RISK_COLORS, dict)

    def test_has_all_risk_levels(self):
        from charts import RISK_COLORS

        for level in ("low", "moderate", "high", "severe"):
            assert level in RISK_COLORS

    def test_values_are_hex_colors(self):
        from charts import RISK_COLORS

        for color in RISK_COLORS.values():
            assert color.startswith("#")
            assert len(color) == 7


# ---------------------------------------------------------------------------
# build_bubble_chart
# ---------------------------------------------------------------------------


SAMPLE_RESULTS = [
    {
        "model": "gpt2",
        "token_count": 20,
        "rtc": 1.0,
        "cost_per_million": 0.0,
        "risk_level": "low",
        "byte_premium": 1.0,
        "context_usage": 0.02,
        "token_fertility": 1.5,
    },
    {
        "model": "llama-3",
        "token_count": 35,
        "rtc": 1.75,
        "cost_per_million": 0.05,
        "risk_level": "moderate",
        "byte_premium": 1.2,
        "context_usage": 0.0003,
        "token_fertility": 2.1,
    },
]


class TestBuildBubbleChart:
    """Tests for build_bubble_chart() -> plotly Figure."""

    def test_returns_figure(self):
        from charts import build_bubble_chart

        fig = build_bubble_chart(SAMPLE_RESULTS)
        assert fig.__class__.__name__ == "Figure"

    def test_empty_results_returns_figure(self):
        from charts import build_bubble_chart

        fig = build_bubble_chart([])
        assert fig.__class__.__name__ == "Figure"

    def test_empty_results_has_annotation(self):
        from charts import build_bubble_chart

        fig = build_bubble_chart([])
        annotations = fig.layout.annotations
        assert len(annotations) > 0

    def test_one_trace_per_model(self):
        from charts import build_bubble_chart

        fig = build_bubble_chart(SAMPLE_RESULTS)
        assert len(fig.data) == 2

    def test_trace_names_match_models(self):
        from charts import build_bubble_chart

        fig = build_bubble_chart(SAMPLE_RESULTS)
        names = {t.name for t in fig.data}
        assert names == {"gpt2", "llama-3"}

    def test_has_model_labels_on_bubbles(self):
        """Bubbles should show model name as text label (not just hover)."""
        from charts import build_bubble_chart

        fig = build_bubble_chart(SAMPLE_RESULTS)
        for trace in fig.data:
            assert "text" in trace.mode

    def test_uses_theme_aware_layout_colors(self):
        from charts import build_bubble_chart

        fig = build_bubble_chart(SAMPLE_RESULTS)
        assert fig.layout.paper_bgcolor == "#ffffff"
        assert fig.layout.plot_bgcolor == "#ffffff"
        assert fig.layout.font.color == "#111111"


# ---------------------------------------------------------------------------
# build_context_chart (Issue 6)
# ---------------------------------------------------------------------------


class TestBuildContextChart:
    """Tests for build_context_chart() -> plotly Figure."""

    def test_returns_figure(self):
        from charts import build_context_chart

        fig = build_context_chart(SAMPLE_RESULTS)
        assert fig.__class__.__name__ == "Figure"

    def test_empty_returns_figure(self):
        from charts import build_context_chart

        fig = build_context_chart([])
        assert fig.__class__.__name__ == "Figure"

    def test_has_bar_traces(self):
        from charts import build_context_chart

        fig = build_context_chart(SAMPLE_RESULTS)
        assert len(fig.data) >= 1
        assert fig.data[0].type == "bar"

    def test_bar_count_matches_models(self):
        from charts import build_context_chart

        fig = build_context_chart(SAMPLE_RESULTS)
        assert len(fig.data[0].y) == 2


# ---------------------------------------------------------------------------
# build_heatmap (Issue 7)
# ---------------------------------------------------------------------------


SAMPLE_BENCHMARK = {
    ("en", "gpt2"): {"rtc": 1.0, "token_count": 15},
    ("ar", "gpt2"): {"rtc": 2.5, "token_count": 38},
    ("en", "llama-3"): {"rtc": 1.0, "token_count": 12},
    ("ar", "llama-3"): {"rtc": 2.1, "token_count": 25},
}


class TestBuildHeatmap:
    """Tests for build_heatmap() -> plotly Figure."""

    def test_returns_figure(self):
        from charts import build_heatmap

        fig = build_heatmap(SAMPLE_BENCHMARK, ["en", "ar"], ["gpt2", "llama-3"])
        assert fig.__class__.__name__ == "Figure"

    def test_empty_returns_figure(self):
        from charts import build_heatmap

        fig = build_heatmap({}, [], [])
        assert fig.__class__.__name__ == "Figure"

    def test_has_heatmap_trace(self):
        from charts import build_heatmap

        fig = build_heatmap(SAMPLE_BENCHMARK, ["en", "ar"], ["gpt2", "llama-3"])
        assert len(fig.data) >= 1
        assert fig.data[0].type == "heatmap"

    def test_z_values_shape(self):
        from charts import build_heatmap

        fig = build_heatmap(SAMPLE_BENCHMARK, ["en", "ar"], ["gpt2", "llama-3"])
        z = fig.data[0].z
        assert len(z) == 2  # 2 languages
        assert len(z[0]) == 2  # 2 models

    def test_heatmap_uses_theme_aware_layout_colors(self):
        from charts import build_heatmap

        fig = build_heatmap(SAMPLE_BENCHMARK, ["en", "ar"], ["gpt2", "llama-3"])
        assert fig.layout.paper_bgcolor == "#ffffff"
        assert fig.layout.plot_bgcolor == "#ffffff"
        assert fig.layout.font.color == "#111111"

    def test_heatmap_uses_intuitive_green_to_red_scale(self):
        from charts import build_heatmap

        fig = build_heatmap(SAMPLE_BENCHMARK, ["en", "ar"], ["gpt2", "llama-3"])
        colorscale = list(fig.data[0].colorscale)

        assert colorscale[0][1] == "#22c55e"
        assert colorscale[-1][1] == "#ef4444"

    def test_heatmap_preserves_missing_cells_as_none(self):
        from charts import build_heatmap

        fig = build_heatmap(
            {("en", "gpt2"): {"rtc": 1.0}},
            ["en", "ar"],
            ["gpt2", "llama-3"],
        )

        z = fig.data[0].z
        assert z[0][0] == 1.0
        assert z[0][1] is None
        assert z[1][0] is None


class TestBuildMetricScatter:
    def test_metric_scatter_truncates_visible_labels_but_keeps_full_hover_name(self):
        from charts import build_metric_scatter

        fig = build_metric_scatter(
            [
                {
                    "label": "Qwen 2.5 7B Instruct (Free) with a much longer display label",
                    "display_label": "Qwen 2.5 7B Instruct...",
                    "rtc": 3.0,
                    "monthly_cost": 92.0,
                    "tokenizer_key": "qwen-2.5",
                },
            ],
            x_key="rtc",
            y_key="monthly_cost",
        )

        assert fig.data[0].text[0] == "Qwen 2.5 7B Instruct..."
        assert fig.data[0].name == "Qwen 2.5 7B Instruct (Free) with a much longer display label"

    def test_speed_metadata_empty_state_mentions_benchmark_match(self):
        from charts import build_metric_scatter

        fig = build_metric_scatter(
            [{"label": "Llama 3.1 8B", "ttft_seconds": None, "output_tokens_per_second": None}],
            x_key="ttft_seconds",
            y_key="output_tokens_per_second",
        )

        assert "benchmark-only speed metadata" in fig.layout.annotations[0].text.lower()

    def test_bubble_sizes_are_bounded_for_large_size_values(self):
        from charts import build_metric_scatter

        fig = build_metric_scatter(
            [
                {"label": "A", "rtc": 1.9, "monthly_cost": 29.55, "monthly_input_tokens": 415_000_000, "tokenizer_key": "llama-3"},
                {"label": "B", "rtc": 3.05, "monthly_cost": 29.20, "monthly_input_tokens": 620_100_000, "tokenizer_key": "mistral"},
                {"label": "C", "rtc": 3.06, "monthly_cost": 94.12, "monthly_input_tokens": 517_500_000, "tokenizer_key": "qwen-2.5"},
            ],
            x_key="rtc",
            y_key="monthly_cost",
            size_key="monthly_input_tokens",
        )

        sizes = [trace.marker.size for trace in fig.data]
        assert all(size <= 34 for size in sizes)
        assert all(size >= 14 for size in sizes)

    def test_equal_size_values_use_stable_midpoint_bubbles(self):
        from charts import build_metric_scatter

        fig = build_metric_scatter(
            [
                {"label": "A", "rtc": 1.0, "monthly_cost": 10.0, "monthly_input_tokens": 1000, "tokenizer_key": "gpt2"},
                {"label": "B", "rtc": 2.0, "monthly_cost": 20.0, "monthly_input_tokens": 1000, "tokenizer_key": "llama-3"},
            ],
            x_key="rtc",
            y_key="monthly_cost",
            size_key="monthly_input_tokens",
        )

        sizes = [trace.marker.size for trace in fig.data]
        assert sizes[0] == pytest.approx(sizes[1])


class TestBenchmarkBarCharts:
    def test_build_category_bar_returns_grouped_bar_chart(self):
        from charts import build_category_bar

        fig = build_category_bar(
            [
                {"language": "English", "tokenizer_key": "gpt2", "unique_tokens": 12},
                {"language": "English", "tokenizer_key": "llama-3", "unique_tokens": 10},
                {"language": "Arabic", "tokenizer_key": "gpt2", "unique_tokens": 16},
                {"language": "Arabic", "tokenizer_key": "llama-3", "unique_tokens": 14},
            ],
            category_key="language",
            value_key="unique_tokens",
            title="Vocabulary Coverage",
            x_title="Language",
            y_title="Unique Tokens Used",
        )

        assert fig.__class__.__name__ == "Figure"
        assert fig.layout.barmode == "group"
        assert all(trace.type == "bar" for trace in fig.data)

    def test_build_stacked_category_bar_returns_stacked_bars(self):
        from charts import build_stacked_category_bar

        fig = build_stacked_category_bar(
            [
                {"tokenizer_key": "gpt2", "script": "Latin", "token_count": 20},
                {"tokenizer_key": "gpt2", "script": "Arabic", "token_count": 5},
                {"tokenizer_key": "llama-3", "script": "Latin", "token_count": 15},
                {"tokenizer_key": "llama-3", "script": "Arabic", "token_count": 8},
            ],
            category_key="tokenizer_key",
            value_key="token_count",
            stack_key="script",
            title="Observed Script Distribution",
            x_title="Tokenizer Family",
            y_title="Observed Tokens",
        )

        assert fig.__class__.__name__ == "Figure"
        assert fig.layout.barmode == "stack"
        assert all(trace.type == "bar" for trace in fig.data)


# ---------------------------------------------------------------------------
# build_cost_waterfall (Issue 8)
# ---------------------------------------------------------------------------


SAMPLE_PORTFOLIO = {
    "total_monthly_cost": 5.0,
    "token_tax_exposure": 1.8,
    "languages": [
        {"language": "en", "rtc": 1.0, "monthly_cost": 2.0, "traffic_share": 0.6, "cost_share": 0.4, "token_count": 15, "tax_ratio": 1.0},
        {"language": "ar", "rtc": 2.5, "monthly_cost": 3.0, "traffic_share": 0.4, "cost_share": 0.6, "token_count": 38, "tax_ratio": 2.5},
    ],
}


class TestBuildCostWaterfall:
    """Tests for build_cost_waterfall() -> plotly Figure."""

    def test_returns_figure(self):
        from charts import build_cost_waterfall

        fig = build_cost_waterfall(SAMPLE_PORTFOLIO)
        assert fig.__class__.__name__ == "Figure"

    def test_empty_returns_figure(self):
        from charts import build_cost_waterfall

        fig = build_cost_waterfall({"total_monthly_cost": 0, "token_tax_exposure": 1.0, "languages": []})
        assert fig.__class__.__name__ == "Figure"

    def test_has_two_bar_traces(self):
        """Should have English-equivalent cost + token tax surcharge stacked bars."""
        from charts import build_cost_waterfall

        fig = build_cost_waterfall(SAMPLE_PORTFOLIO)
        bar_traces = [t for t in fig.data if t.type == "bar"]
        assert len(bar_traces) == 2

    def test_bar_labels_are_languages(self):
        from charts import build_cost_waterfall

        fig = build_cost_waterfall(SAMPLE_PORTFOLIO)
        bar_trace = fig.data[0]
        assert list(bar_trace.y) == ["en", "ar"]
