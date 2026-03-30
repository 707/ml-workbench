"""Token Tax Workbench — Gradio UI."""

from __future__ import annotations

import csv
import html
import tempfile

import gradio as gr

from charts import (
    build_bubble_chart,
    build_category_bar,
    build_context_chart,
    build_cost_waterfall,
    build_distribution_chart,
    build_heatmap,
    build_metric_scatter,
    build_stacked_category_bar,
)
from corpora import DEFAULT_BENCHMARK_LANGUAGES
from diagnostics import clear_events, log_event, render_markdown
from model_registry import (
    build_tokenizer_catalog,
    list_free_runtime_choices,
    list_tokenizer_families,
)
from token_tax import (
    _iter_benchmark_payload,
    analyze_text_across_models,
    audit_markdown,
    benchmark_all,
    benchmark_appendix,
    catalog_appendix,
    cost_projection,
    export_csv,
    export_json,
    generate_recommendations,
    parse_traffic_csv,
    portfolio_analysis,
    refresh_catalog,
    run_benchmark,
    scenario_analysis,
    scenario_appendix,
    serialize_table,
)

SCRIPT_FAMILY_PRESETS = {
    "All": list(DEFAULT_BENCHMARK_LANGUAGES),
    "Latin": ["en", "fr", "de", "es", "pt"],
    "Cyrillic": ["ru"],
    "Arabic": ["ar"],
    "Devanagari": ["hi"],
    "CJK": ["ja", "zh"],
}
LANE_TO_CORPUS_KEY = {
    "Strict Evidence": "strict_parallel",
    "Streaming Exploration": "streaming_exploration",
}
LANGUAGE_LABELS = {
    "ar": "Arabic",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "hi": "Hindi",
    "ja": "Japanese",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
}

PLAIN_LANGUAGE_METRIC_LABELS = {
    "rtc": "Relative Token Cost (vs English)",
    "english_baseline_ratio": "Relative Token Cost (streaming baseline)",
    "token_fertility": "Tokens per word / character",
    "continued_word_rate": "Word split rate",
    "bytes_per_token": "Text packed into each token",
    "token_count": "Token count",
    "byte_premium": "Byte premium vs English",
    "unique_tokens": "Unique tokens used",
    "context_loss_pct": "Context loss",
    "monthly_cost": "Monthly cost",
    "monthly_input_tokens": "Monthly input tokens",
    "monthly_output_tokens": "Monthly output tokens",
    "ttft_seconds": "Time to first token",
    "output_tokens_per_second": "Output tokens / second",
}


STRICT_BENCHMARK_COLUMNS = [
    "lane",
    "language",
    "tokenizer_key",
    "rtc",
    "token_count",
    "bytes_per_token",
    "token_fertility",
    "unique_tokens",
    "continued_word_rate",
    "sample_count",
    "provenance",
]
STREAMING_BENCHMARK_COLUMNS = [
    "lane",
    "language",
    "tokenizer_key",
    "english_baseline_ratio",
    "token_count",
    "bytes_per_token",
    "token_fertility",
    "unique_tokens",
    "continued_word_rate",
    "sample_count",
    "provenance",
]
STRICT_BENCHMARK_METRICS = [
    "rtc",
    "token_count",
    "bytes_per_token",
    "token_fertility",
    "byte_premium",
    "unique_tokens",
    "continued_word_rate",
]
STREAMING_BENCHMARK_METRICS = [
    "bytes_per_token",
    "token_fertility",
    "unique_tokens",
    "continued_word_rate",
    "english_baseline_ratio",
    "token_count",
]


def apply_language_preset(preset: str) -> list[str]:
    """Return the supported languages for a script-family preset."""
    return list(SCRIPT_FAMILY_PRESETS.get(preset, SCRIPT_FAMILY_PRESETS["All"]))


def language_label(code: str) -> str:
    """Return a human-readable label for a benchmark language code."""
    return LANGUAGE_LABELS.get(code, code)


def language_choice_pairs(codes: list[str] | None = None) -> list[tuple[str, str]]:
    """Return Gradio dropdown choices with readable labels and stable codes."""
    selected = codes or list(DEFAULT_BENCHMARK_LANGUAGES)
    return [(language_label(code), code) for code in selected]

def metric_display_label(metric_key: str) -> str:
    return PLAIN_LANGUAGE_METRIC_LABELS.get(metric_key, metric_key.replace("_", " ").title())


def build_chart_help_markdown(title: str, body: str) -> str:
    return (
        f'<div class="chart-help"><strong>{html.escape(title)}</strong>'
        f"<p>{html.escape(body)}</p></div>"
    )


def exploratory_metric_badge_html() -> str:
    return '<span class="metric-badge">Exploratory only</span>'


def shorten_model_label(label: str, max_length: int = 30) -> str:
    if len(label) <= max_length:
        return label
    return f"{label[: max_length - 3].rstrip()}..."


def build_benchmark_chart_explainer_markdown(metric_key: str, section_name: str) -> str:
    metric_label = metric_display_label(metric_key)
    if metric_key == "english_baseline_ratio":
        return (
            '<div class="chart-help">'
            "<strong>How to read this chart</strong>"
            f"{exploratory_metric_badge_html()}"
            "<p>This is an exploratory metric, not aligned RTC. It compares live streaming samples against a same-tokenizer English baseline when that baseline was successfully captured, so sparse or blank states are expected.</p>"
            "</div>"
        )
    if section_name == "Coverage":
        return build_chart_help_markdown(
            "How to read this chart",
            f"These bars compare {metric_label}, Word split rate, and Tokens per word / character across languages. They answer one practical question: when two languages say the same meaning, which tokenizer breaks the text into more pieces?"
        )
    if section_name == "Observed Composition":
        return build_chart_help_markdown(
            "How to read this chart",
            "This stacked bar shows which writing systems the tokenizer actually used on the selected benchmark rows. It helps you see whether a tokenizer spreads its pieces across Arabic, Cyrillic, CJK, Latin, and other scripts or leans heavily on one script."
        )
    return build_chart_help_markdown(
        "How to read this chart",
        f"This view compares {metric_label} across languages and tokenizer families. Lower relative token cost usually means the tokenizer needs fewer pieces to express the same meaning."
    )


def export_serialized_table_csv(table: dict | None, prefix: str = "export") -> str | None:
    """Write a serialized table dict to a temporary CSV file."""
    if not table:
        return None
    headers = list(table.get("headers") or [])
    rows = list(table.get("data") or [])
    if not headers or not rows:
        return None

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", suffix=".csv", prefix=f"{prefix}-", delete=False) as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
        return handle.name


def _build_explanatory_empty_plot(message: str):
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.update_layout(
        annotations=[{
            "text": message,
            "xref": "paper",
            "yref": "paper",
            "x": 0.5,
            "y": 0.5,
            "showarrow": False,
            "font": {"size": 15, "color": "#111111"},
            "align": "center",
        }],
        template="plotly",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"color": "#111111"},
    )
    fig.update_xaxes(
        gridcolor="#e5e7eb",
        zerolinecolor="#e5e7eb",
        linecolor="#cbd5e1",
        tickfont={"color": "#111111"},
        title_font={"color": "#111111"},
    )
    fig.update_yaxes(
        gridcolor="#e5e7eb",
        zerolinecolor="#e5e7eb",
        linecolor="#cbd5e1",
        tickfont={"color": "#111111"},
        title_font={"color": "#111111"},
    )
    return fig


def _streaming_baseline_is_sparse(
    rows: list[dict],
    selected_languages: list[str],
    tokenizers: list[str],
) -> bool:
    if not rows:
        return True
    expected_cells = max(len(selected_languages), 1) * max(len(tokenizers), 1)
    numeric_cells = sum(
        1 for row in rows if isinstance(row.get("english_baseline_ratio"), (int, float))
    )
    return numeric_cells / expected_cells < 0.5


def _streaming_baseline_empty_message() -> str:
    return (
        "Relative Token Cost (streaming baseline) only appears when the app captured a "
        "same-tokenizer English baseline in the live sample. This run is too sparse, so "
        "use Text packed into each token, Word split rate, or Tokens per word / character instead."
    )


def _resolve_corpus_key(selection: str) -> str:
    return LANE_TO_CORPUS_KEY.get(selection, selection)

CATALOG_COLUMNS = [
    "Tokenizer Family",
    "Tokenizer Key",
    "Tokenizer Source",
    "Mapping",
    "Free Models",
    "Free Model Examples",
    "AA Benchmarks",
    "AA Match Examples",
    "Min $/1M In",
    "Max Context",
    "Provenance",
]

SCENARIO_COLUMNS = [
    "lane",
    "label",
    "model_id",
    "language",
    "tokenizer_key",
    "rtc",
    "context_loss_pct",
    "monthly_input_tokens",
    "monthly_output_tokens",
    "monthly_cost",
    "ttft_seconds",
    "output_tokens_per_second",
    "provenance",
]
RAW_BENCHMARK_COLUMNS = [
    "lane",
    "language",
    "tokenizer_key",
    "sample_index",
    "token_count",
    "unique_tokens",
    "continued_word_rate",
    "bytes_per_token",
    "rtc",
    "text",
    "english_text",
    "token_preview",
]
STREAMING_RAW_BENCHMARK_COLUMNS = [
    "lane",
    "language",
    "tokenizer_key",
    "sample_index",
    "token_count",
    "unique_tokens",
    "continued_word_rate",
    "bytes_per_token",
    "english_baseline_ratio",
    "text",
    "english_text",
    "token_preview",
]


def _benchmark_columns_for(corpus_key: str) -> list[str]:
    return STRICT_BENCHMARK_COLUMNS if corpus_key == "strict_parallel" else STREAMING_BENCHMARK_COLUMNS


def _raw_benchmark_columns_for(corpus_key: str) -> list[str]:
    return RAW_BENCHMARK_COLUMNS if corpus_key == "strict_parallel" else STREAMING_RAW_BENCHMARK_COLUMNS


def _benchmark_metric_choices_for(corpus_key: str) -> list[str]:
    return STRICT_BENCHMARK_METRICS if corpus_key == "strict_parallel" else STREAMING_BENCHMARK_METRICS


def _default_benchmark_metric_for(corpus_key: str) -> str:
    return "rtc" if corpus_key == "strict_parallel" else "bytes_per_token"


def configure_benchmark_metric(lane_or_corpus: str) -> dict[str, object]:
    corpus_key = _resolve_corpus_key(lane_or_corpus)
    return gr.update(
        choices=_benchmark_metric_choices_for(corpus_key),
        value=_default_benchmark_metric_for(corpus_key),
    )


def _catalog_display_rows(rows: list[dict]) -> list[dict]:
    display_rows: list[dict] = []
    for row in rows:
        free_models = row.get("free_models", [])
        aa_matches = row.get("aa_matches", [])
        display_rows.append({
            "Tokenizer Family": row["label"],
            "Tokenizer Key": row["tokenizer_key"],
            "Tokenizer Source": row["tokenizer_source"],
            "Mapping": row["mapping_quality"],
            "Free Models": row.get("free_model_count", len(free_models)),
            "Free Model Examples": ", ".join(model["label"] for model in free_models) or "None attached",
            "AA Benchmarks": row.get("aa_match_count", len(aa_matches)),
            "AA Match Examples": ", ".join(match["label"] for match in aa_matches) or "No benchmark match",
            "Min $/1M In": row.get("min_input_per_million"),
            "Max Context": row.get("max_context_window"),
            "Provenance": row["provenance"],
        })
    return display_rows


def _format_benchmark_value(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return f"{value:,}"
    if abs(float(value)) >= 10:
        return f"{float(value):.1f}"
    return f"{float(value):.2f}"


def _benchmark_row_label(row: dict) -> str:
    return f"{language_label(str(row.get('language', 'n/a')))} / {row.get('tokenizer_key', 'n/a')}"


def build_scenario_appendix_summary_html() -> str:
    return (
        '<div class="chart-help">'
        "<strong>Scenario assumptions</strong>"
        "<p>Scenario Lab turns Strict Evidence benchmark rows into business impact. It estimates monthly spend and context loss from the selected languages, tokenizer families, and attached free models.</p>"
        "</div>"
    )


def build_benchmark_summary_markdown(rows: list[dict], metric_key: str) -> str:
    """Render a formatted benchmark summary box above the chart stack."""
    if not rows:
        return (
            '<section class="benchmark-summary-box">'
            '<h3>Benchmark Summary</h3>'
            '<p class="benchmark-summary-empty">Run the benchmark to populate the overview.</p>'
            "</section>"
        )

    lane = rows[0].get("lane", "Benchmark")
    languages = sorted({row.get("language", "n/a") for row in rows})
    tokenizers = sorted({row.get("tokenizer_key", "n/a") for row in rows})
    headline_key = "rtc" if any(isinstance(row.get("rtc"), (int, float)) for row in rows) else "english_baseline_ratio"
    headline_label = (
        "Biggest Relative Token Cost jump"
        if headline_key == "rtc"
        else "Biggest streaming token-cost jump"
    )

    def _best_row(key: str):
        numeric = [row for row in rows if isinstance(row.get(key), (int, float))]
        if not numeric:
            return None
        return max(numeric, key=lambda row: float(row[key]))

    headline_row = _best_row(headline_key)
    bytes_row = _best_row("bytes_per_token")
    split_row = _best_row("continued_word_rate")
    metric_values = [float(row[metric_key]) for row in rows if isinstance(row.get(metric_key), (int, float))]
    metric_range = (
        f"{min(metric_values):.2f} to {max(metric_values):.2f}"
        if metric_values else
        "n/a"
    )

    summary_cards = [
        (
            "Lane",
            f"{lane} across {len(languages)} languages and {len(tokenizers)} tokenizer families",
        ),
        (
            f"{metric_display_label(metric_key)} {exploratory_metric_badge_html()}" if metric_key == "english_baseline_ratio" else metric_display_label(metric_key),
            f"Range: {metric_range}",
        ),
    ]
    if headline_row:
        summary_cards.append(
            (
                headline_label,
                f"{_benchmark_row_label(headline_row)} at {_format_benchmark_value(headline_row.get(headline_key))}",
            )
        )
    if bytes_row:
        summary_cards.append(
            (
                "Text packed into each token",
                f"{_benchmark_row_label(bytes_row)} at {_format_benchmark_value(bytes_row.get('bytes_per_token'))}",
            )
        )
    if split_row:
        summary_cards.append(
            (
                "Word split rate",
                f"{_benchmark_row_label(split_row)} at {_format_benchmark_value(split_row.get('continued_word_rate'))}",
            )
        )

    cards_html = "".join(
        (
            '<div class="summary-pill">'
            f'<span class="summary-pill-label">{label}</span>'
            f'<span class="summary-pill-value">{value}</span>'
            "</div>"
        )
        for label, value in summary_cards
    )
    return (
        '<section class="benchmark-summary-box">'
        "<h3>Benchmark Summary</h3>"
        f'<div class="summary-strip">{cards_html}</div>'
        "</section>"
    )


def build_benchmark_preview_markdown(
    raw_rows: list[dict],
    preview_language: str,
    preview_tokenizer: str,
    preview_sample_index: int,
) -> str:
    """Render a styled tokenization preview for a selected benchmark sample."""
    if not raw_rows:
        return (
            '<section class="preview-card">'
            "<h3>Tokenization Preview</h3>"
            '<p class="preview-empty">No benchmark detail rows available.</p>'
            "</section>"
        )
    match = next(
        (
            row for row in raw_rows
            if row["language"] == preview_language
            and row["tokenizer_key"] == preview_tokenizer
            and int(row["sample_index"]) == int(preview_sample_index)
        ),
        raw_rows[0],
    )
    token_texts = match.get("token_texts") or [token.strip() for token in str(match.get("token_preview", "")).split("|") if token.strip()]
    palette = [
        "preview-tone-0",
        "preview-tone-1",
        "preview-tone-2",
        "preview-tone-3",
        "preview-tone-4",
        "preview-tone-5",
    ]
    token_html = "".join(
        f'<span class="preview-token {palette[index % len(palette)]}">{html.escape(str(token))}</span>'
        for index, token in enumerate(token_texts)
    )
    language_name = language_label(match["language"])
    return (
        '<section class="preview-card">'
        "<h3>Tokenization Preview</h3>"
        '<p class="preview-subtitle">Preview the exact sample text used for a tokenizer-language pair.</p>'
        '<div class="preview-meta-grid">'
        f'<div class="preview-meta"><span class="preview-meta-label">Tokenizer</span><span class="preview-meta-value">{match["tokenizer_key"]}</span></div>'
        f'<div class="preview-meta"><span class="preview-meta-label">Language</span><span class="preview-meta-value">{language_name}</span></div>'
        f'<div class="preview-meta"><span class="preview-meta-label">Lane</span><span class="preview-meta-value">{match["lane"]}</span></div>'
        f'<div class="preview-meta"><span class="preview-meta-label">Token count</span><span class="preview-meta-value">{match["token_count"]}</span></div>'
        "</div>"
        '<div class="preview-text-box">'
        f'<div class="preview-text">{html.escape(str(match["text"]))}</div>'
        "</div>"
        '<div class="preview-token-box">'
        f"{token_html}"
        "</div>"
        "</section>"
    )


def build_coverage_rows(rows: list[dict]) -> list[dict]:
    """Return coverage-oriented benchmark rows for plotting."""
    return [
        {
            "label": f"{row['language']} / {row['tokenizer_key']}",
            "language": language_label(row["language"]),
            "tokenizer_key": row["tokenizer_key"],
            "unique_tokens": row.get("unique_tokens"),
            "continued_word_rate": row.get("continued_word_rate"),
            "bytes_per_token": row.get("bytes_per_token"),
            "token_fertility": row.get("token_fertility"),
            "lane": row.get("lane"),
            "provenance": row.get("provenance"),
        }
        for row in rows
    ]


def _token_script(token_text: str) -> str:
    for char in token_text:
        code = ord(char)
        if 0x0600 <= code <= 0x06FF:
            return "Arabic"
        if 0x0900 <= code <= 0x097F:
            return "Devanagari"
        if 0x3040 <= code <= 0x30FF or 0x4E00 <= code <= 0x9FFF:
            return "CJK"
        if 0x0400 <= code <= 0x04FF:
            return "Cyrillic"
        if ("A" <= char <= "Z") or ("a" <= char <= "z"):
            return "Latin"
    return "Other"


def build_observed_composition_rows(raw_rows: list[dict]) -> list[dict]:
    """Aggregate observed unique token composition from benchmark detail rows."""
    counts: dict[tuple[str, str], int] = {}
    seen_tokens: set[tuple[str, str, str]] = set()
    for row in raw_rows:
        tokens = row.get("token_texts") or []
        if not tokens:
            preview = row.get("token_preview", "")
            tokens = [token.strip() for token in preview.split("|") if token.strip()]
        for token in tokens:
            token_key = (row["tokenizer_key"], row["language"], token)
            if token_key in seen_tokens:
                continue
            seen_tokens.add(token_key)
            script = _token_script(token)
            counts[(row["tokenizer_key"], script)] = counts.get((row["tokenizer_key"], script), 0) + 1

    return [
        {
            "tokenizer_key": tokenizer_key,
            "script": script,
            "token_count": count,
        }
        for (tokenizer_key, script), count in sorted(counts.items())
    ]


def _build_benchmark_outputs(
    rows: list[dict],
    raw_rows: list[dict],
    selected_languages: list[str],
    metric_key: str,
    appendix: str,
    preview_language: str,
    preview_tokenizer: str,
    preview_sample_index: int,
    *,
    skip_plot_updates: bool = False,
):
    corpus_key = "strict_parallel"
    if rows:
        corpus_key = rows[0].get("corpus_key", corpus_key)
    elif raw_rows:
        corpus_key = raw_rows[0].get("corpus_key", corpus_key)
    matrix = {
        (row["language"], row["tokenizer_key"]): row
        for row in rows
    }
    tokenizers = list(dict.fromkeys(row["tokenizer_key"] for row in rows))
    coverage_rows = build_coverage_rows(rows)
    composition_rows = build_observed_composition_rows(raw_rows)
    sparse_streaming_baseline = (
        corpus_key == "streaming_exploration"
        and metric_key == "english_baseline_ratio"
        and _streaming_baseline_is_sparse(rows, selected_languages, tokenizers)
    )
    overview_heatmap = (
        _build_explanatory_empty_plot(_streaming_baseline_empty_message())
        if sparse_streaming_baseline
        else build_heatmap(matrix, selected_languages, tokenizers, metric_key=metric_key)
    )
    overview_distribution = (
        _build_explanatory_empty_plot(_streaming_baseline_empty_message())
        if sparse_streaming_baseline
        else build_distribution_chart(rows, metric_key)
    )
    return (
        build_benchmark_summary_markdown(rows, metric_key),
        serialize_table(rows, _benchmark_columns_for(corpus_key)),
        gr.skip() if skip_plot_updates else overview_heatmap,
        gr.skip() if skip_plot_updates else overview_distribution,
        build_benchmark_preview_markdown(raw_rows, preview_language, preview_tokenizer, preview_sample_index),
        serialize_table(raw_rows, _raw_benchmark_columns_for(corpus_key)),
        gr.skip() if skip_plot_updates else build_category_bar(
            coverage_rows,
            category_key="language",
            value_key="unique_tokens",
            title="Vocabulary Coverage",
            x_title="Language",
            y_title="Unique tokens used",
        ),
        gr.skip() if skip_plot_updates else build_category_bar(
            coverage_rows,
            category_key="language",
            value_key="continued_word_rate",
            title="Word Split Rate",
            x_title="Language",
            y_title="Word split rate",
        ),
        gr.skip() if skip_plot_updates else build_category_bar(
            coverage_rows,
            category_key="language",
            value_key="token_fertility",
            title="Tokens per Word / Character",
            x_title="Language",
            y_title="Tokens per word / character",
        ),
        gr.skip() if skip_plot_updates else build_stacked_category_bar(
            composition_rows,
            category_key="tokenizer_key",
            value_key="token_count",
            stack_key="script",
            title="Observed Script Distribution",
            x_title="Tokenizer family",
            y_title="Observed unique tokens",
        ),
        appendix,
        render_markdown(),
    )


def _aggregate_scenario_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for row in rows:
        key = row["model_id"]
        weight = float(row.get("monthly_input_tokens") or 0)
        current = grouped.setdefault(key, {
            "label": row["label"],
            "display_label": shorten_model_label(str(row["label"])),
            "model_id": row["model_id"],
            "tokenizer_key": row["tokenizer_key"],
            "rtc_weighted_sum": 0.0,
            "context_loss_weighted_sum": 0.0,
            "weight": 0.0,
            "monthly_input_tokens": 0,
            "monthly_output_tokens": 0,
            "monthly_cost": 0.0,
            "ttft_seconds": row.get("ttft_seconds"),
            "output_tokens_per_second": row.get("output_tokens_per_second"),
            "telemetry_provider": row.get("telemetry_provider"),
            "provenance": row.get("provenance"),
        })
        current["rtc_weighted_sum"] += float(row.get("rtc") or 0.0) * weight
        current["context_loss_weighted_sum"] += float(row.get("context_loss_pct") or 0.0) * weight
        current["weight"] += weight
        current["monthly_input_tokens"] += int(row.get("monthly_input_tokens") or 0)
        current["monthly_output_tokens"] += int(row.get("monthly_output_tokens") or 0)
        current["monthly_cost"] += float(row.get("monthly_cost") or 0.0)

    aggregated: list[dict] = []
    for item in grouped.values():
        weight = item.pop("weight")
        rtc_weighted_sum = item.pop("rtc_weighted_sum")
        context_loss_weighted_sum = item.pop("context_loss_weighted_sum")
        item["rtc"] = round(rtc_weighted_sum / weight, 4) if weight else 0.0
        item["context_loss_pct"] = round(context_loss_weighted_sum / weight, 2) if weight else 0.0
        item["monthly_cost"] = round(item["monthly_cost"], 6)
        aggregated.append(item)
    return sorted(aggregated, key=lambda row: row["label"].lower())


def build_scenario_speed_summary_markdown(chart_rows: list[dict]) -> str:
    """Render a speed coverage summary for the Scenario Lab speed tab."""
    if not chart_rows:
        return "### Speed Coverage\n- Run Scenario Lab to inspect benchmark-only speed coverage."

    matched = [
        row for row in chart_rows
        if isinstance(row.get("ttft_seconds"), (int, float))
        and isinstance(row.get("output_tokens_per_second"), (int, float))
    ]
    unmatched = [row for row in chart_rows if row not in matched]

    lines = [
        "### Speed Coverage",
        f"- Matched models: **{len(matched)} / {len(chart_rows)}** with benchmark-only speed metadata.",
    ]
    if matched:
        fastest = min(matched, key=lambda row: float(row["ttft_seconds"]))
        highest_tps = max(matched, key=lambda row: float(row["output_tokens_per_second"]))
        lines.append(
            f"- Fastest time-to-first-token: **{fastest['label']}** at **{_format_benchmark_value(fastest['ttft_seconds'])}s**."
        )
        lines.append(
            f"- Highest output throughput: **{highest_tps['label']}** at **{_format_benchmark_value(highest_tps['output_tokens_per_second'])} tok/s**."
        )
    if unmatched:
        labels = ", ".join(row["label"] for row in unmatched)
        lines.append(f"- No benchmark match yet: {labels}.")
    return "\n".join(lines)


def _build_scenario_outputs(
    rows: list[dict],
    corpus_key: str,
    x_key: str,
    y_key: str,
    size_key: str,
    *,
    skip_plot_updates: bool = False,
) -> tuple[dict, object, object, object, object, object, object, str, str]:
    table_rows = sorted(
        rows,
        key=lambda row: (float(row.get("monthly_cost") or 0.0), str(row.get("label", "")), str(row.get("language", ""))),
        reverse=True,
    )
    table_rows = [
        {**row, "label": shorten_model_label(str(row.get("label", "")), max_length=36)}
        for row in table_rows
    ]
    table = serialize_table(table_rows, SCENARIO_COLUMNS)
    chart_rows = _aggregate_scenario_rows(rows)
    cost_plot = build_metric_scatter(
        chart_rows,
        x_key="rtc",
        y_key="monthly_cost",
        title="Cost",
        x_title="RTC",
        y_title="Monthly cost ($)",
    )
    context_plot = build_metric_scatter(
        chart_rows,
        x_key="rtc",
        y_key="context_loss_pct",
        title="Context Loss",
        x_title="RTC",
        y_title="Context loss (%)",
    )
    speed_plot = build_metric_scatter(
        chart_rows,
        x_key="ttft_seconds",
        y_key="output_tokens_per_second",
        title="Speed Metadata",
        x_title="Time to first token (s)",
        y_title="Output tokens / sec",
    )
    scale_plot = build_metric_scatter(
        chart_rows,
        x_key="monthly_input_tokens",
        y_key="monthly_cost",
        size_key="monthly_cost",
        title="Scale",
        x_title="Monthly input tokens",
        y_title="Monthly cost ($)",
    )
    custom_plot = build_metric_scatter(
        chart_rows,
        x_key=x_key,
        y_key=y_key,
        size_key=size_key if size_key != "none" else None,
        title="Custom Slice",
        x_title=x_key,
        y_title=y_key,
    )
    return (
        table,
        gr.skip() if skip_plot_updates else cost_plot,
        gr.skip() if skip_plot_updates else context_plot,
        build_scenario_speed_summary_markdown(chart_rows),
        gr.skip() if skip_plot_updates else speed_plot,
        gr.skip() if skip_plot_updates else scale_plot,
        gr.skip() if skip_plot_updates else custom_plot,
        scenario_appendix(),
        render_markdown(),
    )


# ---------------------------------------------------------------------------
# Legacy handlers retained for compatibility and tests
# ---------------------------------------------------------------------------


def _handle_dashboard(
    text: str,
    english_text: str,
    selected_models: list[str],
    monthly_requests: int,
    avg_chars: int,
) -> tuple[dict, str, object, object, str]:
    headers = [
        "Model",
        "Tokens",
        "Fertility",
        "RTC",
        "Byte Premium",
        "Context %",
        "Risk",
        "$/1M Input",
        "Monthly Est.",
    ]
    empty_table = {"headers": headers, "data": []}
    if not selected_models:
        return empty_table, "", build_bubble_chart([]), build_context_chart([]), "No models selected."

    english = english_text.strip() if english_text else None
    try:
        results = analyze_text_across_models(text, english, selected_models)
    except Exception as exc:
        return empty_table, "", build_bubble_chart([]), build_context_chart([]), f"Error: {exc}"
    rows = []
    for result in results:
        projection = cost_projection(
            result["token_count"],
            result["cost_per_million"],
            monthly_requests,
            avg_chars,
        )
        rows.append([
            result["model"],
            result["token_count"],
            f"{result['token_fertility']:.2f}",
            f"{result['rtc']:.2f}x",
            f"{result['byte_premium']:.2f}x",
            f"{result['context_usage']:.4%}",
            result["risk_level"],
            f"${result['cost_per_million']:.4f}",
            f"${projection['monthly_cost']:.4f}",
        ])

    recs = generate_recommendations(results, "en" if not english else "x")
    recs_md = recs["executive_summary"]
    context_md = "\n".join(
        f"- {row['model']}: {row['token_count']} tokens" for row in results
    )
    return (
        {"headers": headers, "data": rows},
        context_md,
        build_bubble_chart(results),
        build_context_chart(results),
        recs_md,
    )


def _handle_traffic(csv_file, model_name: str) -> tuple[dict, object, str]:
    headers = [
        "Language",
        "Traffic Share %",
        "Token Count",
        "RTC",
        "Cost Share %",
        "Tax Ratio",
    ]
    empty_table = {"headers": headers, "data": []}
    if csv_file is None:
        return empty_table, build_cost_waterfall({"languages": []}), "Upload a CSV file to begin."

    file_path = csv_file if isinstance(csv_file, str) else csv_file.name
    try:
        traffic_data = parse_traffic_csv(file_path)
        if not traffic_data:
            return empty_table, build_cost_waterfall({"languages": []}), "CSV has no data rows."
        result = portfolio_analysis(traffic_data, model_name)
    except Exception as exc:
        message = f"{exc}"
        if message.startswith("CSV missing") or message.startswith("Row "):
            message = f"CSV error: {message}"
        else:
            message = f"Error: {message}"
        return empty_table, build_cost_waterfall({"languages": []}), message

    rows = [
        [
            entry["language"],
            f"{entry['traffic_share'] * 100:.1f}%",
            entry["token_count"],
            f"{entry['rtc']:.2f}x",
            f"{entry['cost_share'] * 100:.1f}%",
            f"{entry['tax_ratio']:.2f}x",
        ]
        for entry in result["languages"]
    ]
    summary_lines = [
        f"Total monthly cost: ${result['total_monthly_cost']:.4f}",
        f"Weighted token tax exposure: {result['token_tax_exposure']:.2f}x",
    ]
    if result["token_tax_exposure"] > 1.5:
        summary_lines.append("Your portfolio has significant token tax exposure.")
    summary = "\n\n".join(summary_lines)
    return {"headers": headers, "data": rows}, build_cost_waterfall(result), summary


def _handle_benchmark(selected_models: list[str]) -> tuple[dict, object, str]:
    if not selected_models:
        return {"headers": [], "data": []}, build_heatmap({}, [], []), "No models selected."
    languages = list(DEFAULT_BENCHMARK_LANGUAGES)
    benchmark_data = benchmark_all(languages, selected_models)
    benchmark_results = run_benchmark(languages, selected_models)
    headers = ["Language"] + selected_models
    rows = []
    for entry in benchmark_results:
        row = [entry["language"]]
        for model in entry["models"]:
            row.append(f"{model['rtc']:.2f}x")
        rows.append(row)
    summary = "**Demo benchmark uses bundled example phrases, not the strict corpus view.**"
    return {"headers": headers, "data": rows}, build_heatmap(benchmark_data, languages, selected_models), summary


def _handle_export_csv(text: str, english_text: str, selected_models: list[str]) -> str | None:
    if not selected_models or not text.strip():
        return None
    english = english_text.strip() if english_text else None
    results = analyze_text_across_models(text, english, selected_models)
    return export_csv(results)


def _handle_export_json(text: str, english_text: str, selected_models: list[str]) -> str | None:
    if not selected_models or not text.strip():
        return None
    english = english_text.strip() if english_text else None
    results = analyze_text_across_models(text, english, selected_models)
    return export_json(results)


# ---------------------------------------------------------------------------
# Workbench handlers
# ---------------------------------------------------------------------------


def _handle_benchmark_tab(
    lane_or_corpus: str,
    languages: list[str],
    tokenizer_keys: list[str],
    metric_key: str,
    row_limit: int,
    include_estimates: bool,
    include_proxy: bool,
    preview_language: str,
    preview_tokenizer: str,
    preview_sample_index: int,
    live_updates: bool,
):
    corpus_key = _resolve_corpus_key(lane_or_corpus)
    benchmark_columns = _benchmark_columns_for(corpus_key)
    raw_benchmark_columns = _raw_benchmark_columns_for(corpus_key)
    metric_key = metric_key if metric_key in _benchmark_metric_choices_for(corpus_key) else _default_benchmark_metric_for(corpus_key)
    empty_table = {"headers": benchmark_columns, "data": []}
    empty_raw_table = serialize_table([], raw_benchmark_columns)
    empty_heatmap = build_heatmap({}, [], [], metric_key=metric_key)
    empty_distribution = build_distribution_chart([], metric_key)
    empty_preview = build_benchmark_preview_markdown([], preview_language, preview_tokenizer, preview_sample_index)
    empty_coverage = build_category_bar([], category_key="language", value_key="unique_tokens")
    empty_split = build_category_bar([], category_key="language", value_key="continued_word_rate")
    empty_fertility = build_category_bar([], category_key="language", value_key="token_fertility")
    empty_composition = build_stacked_category_bar([], category_key="tokenizer_key", value_key="token_count", stack_key="script")
    if not tokenizer_keys:
        yield (
            build_benchmark_summary_markdown([], metric_key),
            empty_table,
            empty_heatmap,
            empty_distribution,
            empty_preview,
            empty_raw_table,
            empty_coverage,
            empty_split,
            empty_fertility,
            empty_composition,
            f"{benchmark_appendix(corpus_key)}\n\n**Select at least one tokenizer family.**",
            render_markdown(),
        )
        return

    try:
        clear_events()
        log_event(
            "benchmark.run.start",
            "Preparing benchmark run",
            lane=lane_or_corpus,
            language_count=len(languages or list(DEFAULT_BENCHMARK_LANGUAGES)),
            tokenizer_count=len(tokenizer_keys),
            row_limit=int(row_limit),
            live_updates=bool(live_updates),
        )
        selected_languages = languages or list(DEFAULT_BENCHMARK_LANGUAGES)
        appendix = benchmark_appendix(corpus_key)
        yield (
            build_benchmark_summary_markdown([], metric_key),
            empty_table,
            empty_heatmap,
            empty_distribution,
            empty_preview,
            empty_raw_table,
            empty_coverage,
            empty_split,
            empty_fertility,
            empty_composition,
            appendix,
            render_markdown(),
        )
        raw_rows: list[dict] = []
        rows: list[dict] = []
        for row, current_raw_rows in _iter_benchmark_payload(
            corpus_key,
            selected_languages,
            tokenizer_keys,
            row_limit=int(row_limit),
            include_estimates=include_estimates,
            include_proxy=include_proxy,
        ):
            rows.append(row)
            raw_rows = current_raw_rows
            if live_updates:
                yield _build_benchmark_outputs(
                    rows,
                    raw_rows,
                    selected_languages,
                    metric_key,
                    appendix,
                    preview_language,
                    preview_tokenizer,
                    preview_sample_index,
                    skip_plot_updates=True,
                )
        if not rows:
            raise RuntimeError(
                "No benchmark rows were produced. The strict corpus fetch may have failed or returned zero samples."
            )
    except Exception as exc:
        yield (
            build_benchmark_summary_markdown([], metric_key),
            empty_table,
            empty_heatmap,
            empty_distribution,
            (
                '<section class="preview-card">'
                "<h3>Tokenization Preview</h3>"
                '<p class="preview-empty">Runtime error before preview generation.</p>'
                "</section>"
            ),
            empty_raw_table,
            empty_coverage,
            empty_split,
            empty_fertility,
            empty_composition,
            f"{benchmark_appendix(corpus_key)}\n\n**Runtime error:** {exc}",
            render_markdown(),
        )
        return

    yield _build_benchmark_outputs(
        rows,
        raw_rows,
        selected_languages,
        metric_key,
        appendix,
        preview_language,
        preview_tokenizer,
        preview_sample_index,
    )


def _handle_catalog_tab(include_proxy: bool, refresh_live: bool, live_updates: bool):
    clear_events()
    log_event(
        "catalog.run.start",
        "Loading tokenizer catalog",
        include_proxy=bool(include_proxy),
        refresh_live=bool(refresh_live),
        live_updates=bool(live_updates),
    )
    yield serialize_table([], CATALOG_COLUMNS), catalog_appendix(include_proxy), render_markdown()
    if refresh_live:
        refresh_catalog()
    rows = build_tokenizer_catalog(include_proxy=include_proxy)
    yield serialize_table(_catalog_display_rows(rows), CATALOG_COLUMNS), catalog_appendix(include_proxy), render_markdown()


def _handle_scenario_tab(
    languages: list[str],
    tokenizer_keys: list[str],
    model_ids: list[str],
    monthly_requests: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    reasoning_share: float,
    x_key: str,
    y_key: str,
    size_key: str,
    include_estimates: bool,
    include_proxy: bool,
    live_updates: bool,
):
    corpus_key = "strict_parallel"
    if not model_ids:
        empty = serialize_table([], SCENARIO_COLUMNS)
        yield (
            empty,
            build_metric_scatter([], x_key="rtc", y_key="monthly_cost"),
            build_metric_scatter([], x_key="rtc", y_key="context_loss_pct"),
            build_scenario_speed_summary_markdown([]),
            build_metric_scatter([], x_key="ttft_seconds", y_key="output_tokens_per_second"),
            build_metric_scatter([], x_key="monthly_input_tokens", y_key="monthly_cost"),
            build_metric_scatter([], x_key=x_key, y_key=y_key),
            "Select at least one attached free model.",
            render_markdown(),
        )
        return

    try:
        clear_events()
        log_event(
            "scenario.run.start",
            "Preparing scenario analysis",
            language_count=len(languages or []),
            tokenizer_count=len(tokenizer_keys or []),
            model_count=len(model_ids or []),
            live_updates=bool(live_updates),
        )
        yield (
            gr.skip(),
            gr.skip(),
            gr.skip(),
            build_scenario_speed_summary_markdown([]),
            gr.skip(),
            gr.skip(),
            gr.skip(),
            scenario_appendix(),
            render_markdown(),
        )
        rows = scenario_analysis(
            corpus_key=corpus_key,
            languages=languages,
            tokenizer_keys=tokenizer_keys,
            model_ids=model_ids,
            row_limit=25,
            monthly_requests=int(monthly_requests),
            avg_input_tokens=int(avg_input_tokens),
            avg_output_tokens=int(avg_output_tokens),
            reasoning_share=float(reasoning_share),
            include_estimates=include_estimates,
            include_proxy=include_proxy,
        )
        if live_updates:
            yield _build_scenario_outputs(rows, corpus_key, x_key, y_key, size_key)
    except Exception as exc:
        empty = serialize_table([], SCENARIO_COLUMNS)
        yield (
            empty,
            build_metric_scatter([], x_key="rtc", y_key="monthly_cost"),
            build_metric_scatter([], x_key="rtc", y_key="context_loss_pct"),
            build_scenario_speed_summary_markdown([]),
            build_metric_scatter([], x_key="ttft_seconds", y_key="output_tokens_per_second"),
            build_metric_scatter([], x_key="monthly_input_tokens", y_key="monthly_cost"),
            build_metric_scatter([], x_key=x_key, y_key=y_key),
            f"{scenario_appendix()}\n\n**Runtime error:** {exc}",
            render_markdown(),
        )
        return

    yield _build_scenario_outputs(rows, corpus_key, x_key, y_key, size_key)


DEFAULT_BENCHMARK_TOKENIZER_KEYS = [
    "gpt2",
    "o200k_base",
    "llama-3",
    "qwen-2.5",
]

DEFAULT_SCENARIO_TOKENIZER_KEYS = [
    "llama-3",
    "mistral",
    "qwen-2.5",
]

DEFAULT_SCENARIO_MODEL_IDS = [
    "meta-llama/llama-3.2-3b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
]


def default_benchmark_tokenizers() -> list[str]:
    """Return a curated default tokenizer subset for Benchmark and Scenario."""
    available = {family["key"] for family in list_tokenizer_families(include_proxy=False)}
    return [key for key in DEFAULT_BENCHMARK_TOKENIZER_KEYS if key in available]


def default_scenario_models() -> list[str]:
    """Return a curated default free-model subset for Scenario Lab."""
    available = {row["model_id"] for row in list_free_runtime_choices(include_proxy=False)}
    return [model_id for model_id in DEFAULT_SCENARIO_MODEL_IDS if model_id in available]


def default_scenario_tokenizers() -> list[str]:
    """Return a curated tokenizer subset aligned to the default scenario models."""
    available = {family["key"] for family in list_tokenizer_families(include_proxy=False)}
    return [key for key in DEFAULT_SCENARIO_TOKENIZER_KEYS if key in available]


def build_token_tax_ui() -> gr.Blocks:
    """Construct the Token Tax Workbench."""
    tokenizer_families = list_tokenizer_families(include_proxy=True)
    exact_tokenizers = [family["key"] for family in tokenizer_families if family["mapping_quality"] != "proxy"]
    free_runtime_choices = list_free_runtime_choices(include_proxy=False)
    benchmark_default_tokenizers = default_benchmark_tokenizers() or exact_tokenizers[: min(6, len(exact_tokenizers))]
    scenario_default_tokenizers = default_scenario_tokenizers() or benchmark_default_tokenizers
    scenario_default_models = default_scenario_models() or [row["model_id"] for row in free_runtime_choices[:6]]
    model_choices = [(f"{row['label']} ({row['tokenizer_key']})", row["model_id"]) for row in free_runtime_choices]

    with gr.Blocks(title="Token Tax Workbench") as demo:
        gr.HTML(
            '<section class="section-header">'
            "<h2>Token Tax Workbench</h2>"
            "<p>Compare tokenizer behavior across languages, then translate that into cost, context, and decision-ready model trade-offs.</p>"
            "</section>"
        )

        with gr.Tabs():
            with gr.TabItem("Benchmark"):
                with gr.Row(equal_height=False, elem_classes="filter-grid"):
                    with gr.Column(elem_classes="filter-rail filter-rail--compact", min_width=280, scale=0):
                        benchmark_lane = gr.Radio(
                            choices=list(LANE_TO_CORPUS_KEY.keys()),
                            value="Strict Evidence",
                            label="Benchmark Lane",
                            info="Choose stable aligned evidence or exploratory live streaming text.",
                        )
                        benchmark_metric = gr.Dropdown(
                            choices=_benchmark_metric_choices_for("strict_parallel"),
                            value=_default_benchmark_metric_for("strict_parallel"),
                            label="Metric",
                            info="The benchmark metric plotted in the heatmap and distribution views.",
                        )
                        benchmark_limit = gr.Slider(
                            5,
                            50,
                            value=5,
                            step=1,
                            label="Rows per language",
                            info="How many corpus samples to benchmark per language and tokenizer family.",
                        )
                        benchmark_live_updates = gr.Checkbox(
                            label="Live diagnostics",
                            value=False,
                            info="Stream progress updates while the benchmark is running. Turning this off is faster.",
                        )
                        benchmark_run = gr.Button("Run Benchmark", variant="primary", size="sm", elem_classes="compact-action")
                    with gr.Column(elem_classes="filter-rail filter-rail--wide", min_width=520, scale=1):
                        benchmark_preset = gr.Dropdown(
                            choices=list(SCRIPT_FAMILY_PRESETS.keys()),
                            value="All",
                            label="Script Preset",
                            info="Quick-filter the language list by writing system family.",
                        )
                        benchmark_languages = gr.Dropdown(
                            choices=language_choice_pairs(list(DEFAULT_BENCHMARK_LANGUAGES)),
                            value=DEFAULT_BENCHMARK_LANGUAGES,
                            multiselect=True,
                            label="Languages",
                            info="Languages included in the benchmark run.",
                        )
                        benchmark_tokenizers = gr.Dropdown(
                            choices=[(family["label"], family["key"]) for family in tokenizer_families],
                            value=benchmark_default_tokenizers,
                            multiselect=True,
                            label="Tokenizer Families",
                            info="Tokenizer families to benchmark against the selected corpus samples.",
                        )
                    with gr.Column(elem_classes="filter-rail filter-rail--compact", min_width=300, scale=0):
                        preview_language = gr.Dropdown(
                            choices=language_choice_pairs(list(DEFAULT_BENCHMARK_LANGUAGES)),
                            value="en",
                            label="Preview Language",
                            info="Language shown in the tokenization preview card below.",
                        )
                        preview_tokenizer = gr.Dropdown(
                            choices=[(family["label"], family["key"]) for family in tokenizer_families],
                            value=benchmark_default_tokenizers[0] if benchmark_default_tokenizers else None,
                            label="Preview Tokenizer",
                            info="Tokenizer family used in the visual preview sample.",
                        )
                        preview_sample_index = gr.Slider(
                            0,
                            9,
                            value=0,
                            step=1,
                            label="Preview Sample Index",
                            info="Sample row from the selected corpus slice to preview.",
                        )
                        benchmark_include_estimates = gr.Checkbox(
                            label="Include estimated values",
                            value=False,
                            info="Show rows that are estimated rather than strict verified evidence.",
                        )
                        benchmark_include_proxy = gr.Checkbox(
                            label="Include proxy mappings",
                            value=False,
                            info="Include tokenizer families that use a documented proxy rather than an exact mapping.",
                        )
                benchmark_preset.change(
                    fn=apply_language_preset,
                    inputs=[benchmark_preset],
                    outputs=[benchmark_languages],
                    queue=False,
                )
                benchmark_lane.change(
                    fn=configure_benchmark_metric,
                    inputs=[benchmark_lane],
                    outputs=[benchmark_metric],
                    queue=False,
                )
                gr.HTML(
                    build_chart_help_markdown(
                        "Why these controls matter",
                        "Strict Evidence is the stable headline lane, while Streaming Exploration is the exploratory lane. The preview lets you inspect exactly how one tokenizer chopped up one sample before you trust the broader charts."
                    )
                )
                with gr.Group(elem_classes="workbench-box"):
                    benchmark_summary_md = gr.HTML(value=build_benchmark_summary_markdown([], "rtc"))

                with gr.Tabs():
                    with gr.TabItem("Overview"):
                        gr.HTML(
                            value=build_benchmark_chart_explainer_markdown("rtc", "Overview")
                        )
                        benchmark_heatmap = gr.Plot(label="Benchmark Heatmap")
                        gr.HTML(
                            build_chart_help_markdown(
                                "How to read this chart",
                                "The distribution view shows spread, not just averages. Wider boxes mean that tokenizer behaves less consistently across the selected languages."
                            )
                        )
                        benchmark_distribution = gr.Plot(label="Metric Distribution")
                        gr.HTML(
                            build_chart_help_markdown(
                                "How to read this table",
                                "This is the benchmark in spreadsheet form. Use it to inspect the exact language and tokenizer combinations feeding the overview charts."
                            )
                        )
                        benchmark_table = gr.DataFrame(label="Benchmark Table", interactive=False)
                    with gr.TabItem("Preview"):
                        benchmark_preview_md = gr.HTML(label="Preview")
                    with gr.TabItem("Coverage"):
                        gr.HTML(
                            value=build_benchmark_chart_explainer_markdown("token_fertility", "Coverage")
                        )
                        benchmark_coverage_plot = gr.Plot(label="Vocabulary Coverage")
                        benchmark_split_plot = gr.Plot(label="Word Split Rate")
                        benchmark_fertility_plot = gr.Plot(label="Tokens per Word / Character")
                    with gr.TabItem("Observed Composition"):
                        gr.HTML(
                            value=build_benchmark_chart_explainer_markdown("unique_tokens", "Observed Composition")
                        )
                        benchmark_composition_plot = gr.Plot(label="Observed Composition")
                    with gr.TabItem("Raw Data"):
                        gr.HTML(
                            build_chart_help_markdown(
                                "How to use this table",
                                "This is the analyst view. Each row is one sampled text and the exact tokenization metrics used to build the higher-level summaries."
                            )
                        )
                        with gr.Row(elem_classes="raw-export-row"):
                            benchmark_raw_export_btn = gr.Button("Download CSV", size="sm", elem_classes="compact-action")
                            benchmark_raw_export_file = gr.File(label="Raw Data CSV", interactive=False)
                        benchmark_raw_table = gr.DataFrame(label="Raw Benchmark Data", interactive=False)
                with gr.Accordion("Benchmark Appendix", open=False):
                    benchmark_appendix_md = gr.Markdown(label="Benchmark Appendix")
                with gr.Accordion("Diagnostics", open=False):
                    benchmark_diagnostics_md = gr.Markdown()

                benchmark_run.click(
                    fn=_handle_benchmark_tab,
                    inputs=[
                        benchmark_lane,
                        benchmark_languages,
                        benchmark_tokenizers,
                        benchmark_metric,
                        benchmark_limit,
                        benchmark_include_estimates,
                        benchmark_include_proxy,
                        preview_language,
                        preview_tokenizer,
                        preview_sample_index,
                        benchmark_live_updates,
                    ],
                    outputs=[
                        benchmark_summary_md,
                        benchmark_table,
                        benchmark_heatmap,
                        benchmark_distribution,
                        benchmark_preview_md,
                        benchmark_raw_table,
                        benchmark_coverage_plot,
                        benchmark_split_plot,
                        benchmark_fertility_plot,
                        benchmark_composition_plot,
                        benchmark_appendix_md,
                        benchmark_diagnostics_md,
                    ],
                )
                benchmark_raw_export_btn.click(
                    fn=lambda table: export_serialized_table_csv(table, prefix="benchmark-raw"),
                    inputs=[benchmark_raw_table],
                    outputs=[benchmark_raw_export_file],
                    queue=False,
                )

            with gr.TabItem("Catalog"):
                with gr.Row(equal_height=False, elem_classes="catalog-utility-row"):
                    catalog_include_proxy = gr.Checkbox(
                        label="Include proxy mappings",
                        value=False,
                        info="Include tokenizer families that rely on documented proxy mappings.",
                    )
                    catalog_refresh_live = gr.Checkbox(
                        label="Refresh live pricing cache",
                        value=False,
                        info="Refresh pricing from OpenRouter into the app's in-memory cache for this session.",
                    )
                    catalog_live_updates = gr.Checkbox(
                        label="Live diagnostics",
                        value=False,
                        info="Stream catalog refresh progress while loading the table.",
                    )
                    catalog_run = gr.Button("Load Catalog", variant="primary", size="sm", elem_classes="compact-action")
                gr.HTML(
                    build_chart_help_markdown(
                        "How to use this catalog",
                        "Each row starts with a tokenizer family, then shows which free models are attached to it. Live pricing refresh only updates the in-memory cache for the current app session."
                    )
                )
                catalog_table = gr.DataFrame(label="Catalog", interactive=False)
                catalog_appendix_md = gr.Markdown(label="Catalog Appendix")
                with gr.Accordion("Diagnostics", open=False):
                    catalog_diagnostics_md = gr.Markdown()
                catalog_run.click(
                    fn=_handle_catalog_tab,
                    inputs=[catalog_include_proxy, catalog_refresh_live, catalog_live_updates],
                    outputs=[catalog_table, catalog_appendix_md, catalog_diagnostics_md],
                )

            with gr.TabItem("Scenario Lab"):
                with gr.Row(equal_height=False, elem_classes="filter-grid"):
                    with gr.Column(elem_classes="filter-rail filter-rail--wide", min_width=520, scale=1):
                        scenario_languages = gr.Dropdown(
                            choices=language_choice_pairs(list(DEFAULT_BENCHMARK_LANGUAGES)),
                            value=["en", "ar", "hi", "ja"],
                            multiselect=True,
                            label="Languages",
                            info="Languages included in the strict multilingual scenario baseline.",
                        )
                        scenario_tokenizers = gr.Dropdown(
                            choices=[(family["label"], family["key"]) for family in tokenizer_families],
                            value=scenario_default_tokenizers,
                            multiselect=True,
                            label="Benchmark Tokenizers",
                            info="Tokenizer families used to supply the strict multilingual benchmark baseline.",
                        )
                        scenario_models = gr.Dropdown(
                            choices=model_choices,
                            value=scenario_default_models,
                            multiselect=True,
                            label="Attached Free Models",
                            info="Exact free OpenRouter models attached to the selected tokenizer families.",
                        )
                    with gr.Column(elem_classes="filter-rail filter-rail--scenario-inputs", min_width=420, scale=0):
                        with gr.Row(equal_height=False, elem_classes="scenario-control-grid"):
                            with gr.Column(elem_classes="scenario-control-column", min_width=180, scale=1):
                                monthly_requests = gr.Slider(
                                    1_000,
                                    1_000_000,
                                    value=100_000,
                                    step=1_000,
                                    label="Monthly Requests",
                                    info="Projected monthly request volume used to scale the scenario.",
                                )
                                avg_input_tokens = gr.Slider(
                                    10,
                                    10_000,
                                    value=600,
                                    step=10,
                                    label="Avg Input Tokens",
                                    info="Average input size before multilingual token inflation is applied.",
                                )
                            with gr.Column(elem_classes="scenario-control-column", min_width=180, scale=1):
                                avg_output_tokens = gr.Slider(
                                    10,
                                    10_000,
                                    value=250,
                                    step=10,
                                    label="Avg Output Tokens",
                                    info="Average completion length used in the monthly cost projection.",
                                )
                                reasoning_share = gr.Slider(
                                    0.0,
                                    2.0,
                                    value=0.1,
                                    step=0.05,
                                    label="Reasoning Share",
                                    info="Extra completion-token multiplier for reasoning-heavy workloads.",
                                )
                        with gr.Group(elem_classes="scenario-control-cluster"):
                            slice_x = gr.Dropdown(
                                choices=["rtc", "monthly_cost", "monthly_input_tokens", "context_loss_pct", "ttft_seconds", "output_tokens_per_second"],
                                value="rtc",
                                label="Custom X",
                                info="Metric plotted on the x-axis of the custom slice chart.",
                            )
                            slice_y = gr.Dropdown(
                                choices=["monthly_cost", "rtc", "monthly_input_tokens", "context_loss_pct", "ttft_seconds", "output_tokens_per_second"],
                                value="monthly_cost",
                                label="Custom Y",
                                info="Metric plotted on the y-axis of the custom slice chart.",
                            )
                            slice_size = gr.Dropdown(
                                choices=["none", "monthly_cost", "monthly_input_tokens", "rtc"],
                                value="none",
                                label="Bubble Size",
                                info="Optional bubble sizing field for the custom slice chart.",
                            )
                            with gr.Group(elem_classes="checkbox-stack"):
                                scenario_include_estimates = gr.Checkbox(
                                    label="Include estimated values",
                                    value=False,
                                    info="Include estimated or non-strict rows in the scenario comparison.",
                                )
                                scenario_include_proxy = gr.Checkbox(
                                    label="Include proxy mappings",
                                    value=False,
                                    info="Allow tokenizer families with documented proxy mappings into the scenario.",
                                )
                                scenario_live_updates = gr.Checkbox(
                                    label="Live diagnostics",
                                    value=False,
                                    info="Stream scenario progress while computing rows and charts. Turning this off is faster.",
                                )
                            scenario_run = gr.Button("Run Scenario Lab", variant="primary", size="sm", elem_classes="compact-action")
                gr.HTML(
                    build_chart_help_markdown(
                        "How to use Scenario Lab",
                        "This tab turns tokenizer evidence into business impact. It uses the strict benchmark as the baseline, then asks what those extra tokens mean for monthly cost and usable context window."
                    )
                )

                with gr.Tabs():
                    with gr.TabItem("Cost"):
                        gr.HTML(build_chart_help_markdown("How to read this chart", "Each point is a model. Farther right means more tokens for the same meaning; higher means more monthly spend."))
                        scenario_cost_plot = gr.Plot(label="Cost")
                    with gr.TabItem("Context Loss"):
                        gr.HTML(build_chart_help_markdown("How to read this chart", "This shows how much usable context window you lose when a tokenizer spends more tokens on the same message. Lower is better."))
                        scenario_context_plot = gr.Plot(label="Context Loss")
                    with gr.TabItem("Speed Metadata"):
                        scenario_speed_summary_md = gr.Markdown(
                            value="### Speed Coverage\n- Run Scenario Lab to inspect benchmark-only speed coverage."
                        )
                        gr.HTML(build_chart_help_markdown("How to read this chart", "This is external benchmark metadata, not the multilingual token tax itself. Use it as supporting context, not the headline decision."))
                        scenario_speed_plot = gr.Plot(label="Speed Metadata")
                    with gr.TabItem("Scale"):
                        gr.HTML(build_chart_help_markdown("How to read this chart", "This view links monthly token volume to projected spend so you can see which models become expensive fastest at scale."))
                        scenario_scale_plot = gr.Plot(label="Scale")
                    with gr.TabItem("Custom Slice"):
                        gr.HTML(build_chart_help_markdown("How to read this chart", "Pick any two metrics to compare and use bubble size when you want a third dimension."))
                        scenario_custom_plot = gr.Plot(label="Custom Slice")
                gr.HTML(build_chart_help_markdown("How to use this table", "These per-language rows feed the scenario charts above. Use them when you need the detailed assumptions behind a model-level point."))
                scenario_table = gr.DataFrame(label="Scenario Rows", interactive=False)
                gr.HTML(build_scenario_appendix_summary_html())
                with gr.Accordion("Scenario Appendix", open=False):
                    scenario_appendix_md = gr.Markdown(label="Scenario Appendix")
                with gr.Accordion("Diagnostics", open=False):
                    scenario_diagnostics_md = gr.Markdown()

                scenario_run.click(
                    fn=_handle_scenario_tab,
                    inputs=[
                        scenario_languages,
                        scenario_tokenizers,
                        scenario_models,
                        monthly_requests,
                        avg_input_tokens,
                        avg_output_tokens,
                        reasoning_share,
                        slice_x,
                        slice_y,
                        slice_size,
                        scenario_include_estimates,
                        scenario_include_proxy,
                        scenario_live_updates,
                    ],
                    outputs=[
                        scenario_table,
                        scenario_cost_plot,
                        scenario_context_plot,
                        scenario_speed_summary_md,
                        scenario_speed_plot,
                        scenario_scale_plot,
                        scenario_custom_plot,
                        scenario_appendix_md,
                        scenario_diagnostics_md,
                    ],
                )

            with gr.TabItem("Audit"):
                gr.Markdown(audit_markdown())

    return demo
