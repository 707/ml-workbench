"""Token Tax Workbench — Gradio UI."""

from __future__ import annotations

import gradio as gr

from charts import (
    build_bubble_chart,
    build_category_bar,
    build_context_chart,
    build_cost_waterfall,
    build_distribution_chart,
    build_heatmap,
    build_metric_scatter,
)
from corpora import DEFAULT_BENCHMARK_LANGUAGES, list_corpora
from diagnostics import clear_events, render_markdown
from model_registry import (
    artificial_analysis_status,
    build_tokenizer_catalog,
    list_free_runtime_choices,
    list_tokenizer_families,
)
from token_tax import (
    analyze_text_across_models,
    audit_markdown,
    benchmark_appendix,
    benchmark_corpus,
    build_benchmark_detail_rows,
    iter_benchmark_rows,
    benchmark_all,
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


BENCHMARK_COLUMNS = [
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


def apply_language_preset(preset: str) -> list[str]:
    """Return the supported languages for a script-family preset."""
    return list(SCRIPT_FAMILY_PRESETS.get(preset, SCRIPT_FAMILY_PRESETS["All"]))


def _resolve_corpus_key(selection: str) -> str:
    return LANE_TO_CORPUS_KEY.get(selection, selection)

CATALOG_COLUMNS = [
    "label",
    "tokenizer_key",
    "tokenizer_source",
    "mapping_quality",
    "free_model_count",
    "free_models_summary",
    "aa_match_count",
    "aa_summary",
    "min_input_per_million",
    "max_context_window",
    "provenance",
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


def _catalog_display_rows(rows: list[dict]) -> list[dict]:
    display_rows: list[dict] = []
    for row in rows:
        free_models = row.get("free_models", [])
        aa_matches = row.get("aa_matches", [])
        display_rows.append({
            "label": row["label"],
            "tokenizer_key": row["tokenizer_key"],
            "tokenizer_source": row["tokenizer_source"],
            "mapping_quality": row["mapping_quality"],
            "free_model_count": row.get("free_model_count", len(free_models)),
            "free_models_summary": ", ".join(model["label"] for model in free_models) or "None attached",
            "aa_match_count": row.get("aa_match_count", len(aa_matches)),
            "aa_summary": ", ".join(match["label"] for match in aa_matches) or "No benchmark match",
            "min_input_per_million": row.get("min_input_per_million"),
            "max_context_window": row.get("max_context_window"),
            "provenance": row["provenance"],
        })
    return display_rows


def build_benchmark_preview_markdown(
    raw_rows: list[dict],
    preview_language: str,
    preview_tokenizer: str,
    preview_sample_index: int,
) -> str:
    """Render a tokenization preview for a selected benchmark sample."""
    if not raw_rows:
        return "### Preview\n- No benchmark detail rows available."
    match = next(
        (
            row for row in raw_rows
            if row["language"] == preview_language
            and row["tokenizer_key"] == preview_tokenizer
            and int(row["sample_index"]) == int(preview_sample_index)
        ),
        raw_rows[0],
    )
    return "\n".join([
        "### Preview",
        f"- Lane: **{match['lane']}**",
        f"- Language: **{match['language']}**",
        f"- Tokenizer: **{match['tokenizer_key']}**",
        f"- Sample index: **{match['sample_index']}**",
        f"- Token count: **{match['token_count']}**",
        "",
        "**Text**",
        "",
        match["text"],
        "",
        "**Token preview**",
        "",
        f"`{match['token_preview']}`",
    ])


def build_coverage_rows(rows: list[dict]) -> list[dict]:
    """Return coverage-oriented benchmark rows for plotting."""
    return [
        {
            "label": f"{row['language']} / {row['tokenizer_key']}",
            "language": row["language"],
            "tokenizer_key": row["tokenizer_key"],
            "unique_tokens": row.get("unique_tokens"),
            "continued_word_rate": row.get("continued_word_rate"),
            "bytes_per_token": row.get("bytes_per_token"),
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
):
    matrix = {
        (row["language"], row["tokenizer_key"]): row
        for row in rows
    }
    tokenizers = list(dict.fromkeys(row["tokenizer_key"] for row in rows))
    coverage_rows = build_coverage_rows(rows)
    composition_rows = build_observed_composition_rows(raw_rows)
    return (
        serialize_table(rows, BENCHMARK_COLUMNS),
        build_heatmap(matrix, selected_languages, tokenizers, metric_key=metric_key),
        build_distribution_chart(rows, metric_key),
        build_benchmark_preview_markdown(raw_rows, preview_language, preview_tokenizer, preview_sample_index),
        serialize_table(raw_rows, RAW_BENCHMARK_COLUMNS),
        build_metric_scatter(
            coverage_rows,
            x_key="unique_tokens",
            y_key="continued_word_rate",
            title="Coverage",
            x_title="Unique observed tokens",
            y_title="Continued-word rate",
        ),
        build_category_bar(
            composition_rows,
            category_key="script",
            value_key="token_count",
            title="Observed Composition",
            x_title="Observed script",
            y_title="Unique tokens seen",
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


def _build_scenario_outputs(
    rows: list[dict],
    corpus_key: str,
    x_key: str,
    y_key: str,
    size_key: str,
) -> tuple[dict, object, object, object, object, object, str, str]:
    table = serialize_table(rows, SCENARIO_COLUMNS)
    chart_rows = _aggregate_scenario_rows(rows)
    cost_plot = build_metric_scatter(
        chart_rows,
        x_key="rtc",
        y_key="monthly_cost",
        size_key="monthly_input_tokens",
        title="Cost",
        x_title="RTC",
        y_title="Monthly cost ($)",
    )
    context_plot = build_metric_scatter(
        chart_rows,
        x_key="rtc",
        y_key="context_loss_pct",
        size_key="monthly_input_tokens",
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
    return table, cost_plot, context_plot, speed_plot, scale_plot, custom_plot, scenario_appendix(corpus_key), render_markdown()


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
    if not tokenizer_keys:
        yield (
            {"headers": BENCHMARK_COLUMNS, "data": []},
            build_heatmap({}, [], []),
            build_distribution_chart([], metric_key),
            "### Preview\n- Select at least one tokenizer family.",
            serialize_table([], RAW_BENCHMARK_COLUMNS),
            build_metric_scatter([], x_key="unique_tokens", y_key="continued_word_rate"),
            build_category_bar([], category_key="script", value_key="token_count"),
            "Select at least one tokenizer family.",
            render_markdown(),
        )
        return

    try:
        clear_events()
        selected_languages = languages or list(DEFAULT_BENCHMARK_LANGUAGES)
        appendix = benchmark_appendix(corpus_key)
        raw_rows = build_benchmark_detail_rows(
            corpus_key,
            selected_languages,
            tokenizer_keys,
            row_limit=int(row_limit),
        )
        yield (
            {"headers": BENCHMARK_COLUMNS, "data": []},
            build_heatmap({}, [], [], metric_key=metric_key),
            build_distribution_chart([], metric_key),
            build_benchmark_preview_markdown(raw_rows, preview_language, preview_tokenizer, preview_sample_index),
            serialize_table(raw_rows, RAW_BENCHMARK_COLUMNS),
            build_metric_scatter([], x_key="unique_tokens", y_key="continued_word_rate"),
            build_category_bar([], category_key="script", value_key="token_count"),
            appendix,
            render_markdown(),
        )
        rows: list[dict] = []
        for row in iter_benchmark_rows(
            corpus_key,
            selected_languages,
            tokenizer_keys,
            row_limit=int(row_limit),
            include_estimates=include_estimates,
            include_proxy=include_proxy,
        ):
            rows.append(row)
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
                )
        if not rows:
            raise RuntimeError(
                "No benchmark rows were produced. The strict corpus fetch may have failed or returned zero samples."
            )
    except Exception as exc:
        yield (
            {"headers": BENCHMARK_COLUMNS, "data": []},
            build_heatmap({}, [], [], metric_key=metric_key),
            build_distribution_chart([], metric_key),
            "### Preview\n- Runtime error before preview generation.",
            serialize_table([], RAW_BENCHMARK_COLUMNS),
            build_metric_scatter([], x_key="unique_tokens", y_key="continued_word_rate"),
            build_category_bar([], category_key="script", value_key="token_count"),
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
    yield serialize_table([], CATALOG_COLUMNS), catalog_appendix(include_proxy), render_markdown()
    if refresh_live:
        refresh_catalog()
    rows = build_tokenizer_catalog(include_proxy=include_proxy)
    yield serialize_table(_catalog_display_rows(rows), CATALOG_COLUMNS), catalog_appendix(include_proxy), render_markdown()


def _handle_scenario_tab(
    lane_or_corpus: str,
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
    corpus_key = _resolve_corpus_key(lane_or_corpus)
    if not model_ids:
        empty = serialize_table([], SCENARIO_COLUMNS)
        yield (
            empty,
            build_metric_scatter([], x_key="rtc", y_key="monthly_cost"),
            build_metric_scatter([], x_key="rtc", y_key="context_loss_pct"),
            build_metric_scatter([], x_key="ttft_seconds", y_key="output_tokens_per_second"),
            build_metric_scatter([], x_key="monthly_input_tokens", y_key="monthly_cost"),
            build_metric_scatter([], x_key=x_key, y_key=y_key),
            "Select at least one attached free model.",
            render_markdown(),
        )
        return

    try:
        clear_events()
        yield (
            serialize_table([], SCENARIO_COLUMNS),
            build_metric_scatter([], x_key="rtc", y_key="monthly_cost"),
            build_metric_scatter([], x_key="rtc", y_key="context_loss_pct"),
            build_metric_scatter([], x_key="ttft_seconds", y_key="output_tokens_per_second"),
            build_metric_scatter([], x_key="monthly_input_tokens", y_key="monthly_cost"),
            build_metric_scatter([], x_key=x_key, y_key=y_key),
            scenario_appendix(corpus_key),
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
            build_metric_scatter([], x_key="ttft_seconds", y_key="output_tokens_per_second"),
            build_metric_scatter([], x_key="monthly_input_tokens", y_key="monthly_cost"),
            build_metric_scatter([], x_key=x_key, y_key=y_key),
            f"{scenario_appendix(corpus_key)}\n\n**Runtime error:** {exc}",
            render_markdown(),
        )
        return

    yield _build_scenario_outputs(rows, corpus_key, x_key, y_key, size_key)


def build_token_tax_ui() -> gr.Blocks:
    """Construct the Token Tax Workbench."""
    tokenizer_families = list_tokenizer_families(include_proxy=True)
    exact_tokenizers = [family["key"] for family in tokenizer_families if family["mapping_quality"] != "proxy"]
    free_runtime_choices = list_free_runtime_choices(include_proxy=False)
    model_choices = [(f"{row['label']} ({row['tokenizer_key']})", row["model_id"]) for row in free_runtime_choices]

    with gr.Blocks(title="Token Tax Workbench") as demo:
        gr.Markdown(
            "## Token Tax Workbench\n\n"
            "Strict verified corpus evidence is shown by default. "
            "Streaming exploration is opt-in and explicitly exploratory."
        )

        with gr.Tabs():
            with gr.TabItem("Benchmark"):
                with gr.Row():
                    benchmark_lane = gr.Radio(
                        choices=list(LANE_TO_CORPUS_KEY.keys()),
                        value="Strict Evidence",
                        label="Benchmark Lane",
                    )
                    benchmark_metric = gr.Dropdown(
                        choices=["rtc", "token_count", "bytes_per_token", "token_fertility", "byte_premium", "unique_tokens", "continued_word_rate"],
                        value="rtc",
                        label="Metric",
                    )
                    benchmark_limit = gr.Slider(5, 50, value=12, step=1, label="Rows per language")
                with gr.Row():
                    benchmark_preset = gr.Dropdown(
                        choices=list(SCRIPT_FAMILY_PRESETS.keys()),
                        value="All",
                        label="Script Preset",
                    )
                    benchmark_languages = gr.Dropdown(
                        choices=DEFAULT_BENCHMARK_LANGUAGES,
                        value=DEFAULT_BENCHMARK_LANGUAGES,
                        multiselect=True,
                        label="Languages",
                    )
                    benchmark_tokenizers = gr.Dropdown(
                        choices=[(family["label"], family["key"]) for family in tokenizer_families],
                        value=exact_tokenizers,
                        multiselect=True,
                        label="Tokenizer Families",
                    )
                benchmark_preset.change(
                    fn=apply_language_preset,
                    inputs=[benchmark_preset],
                    outputs=[benchmark_languages],
                )
                with gr.Row():
                    preview_language = gr.Dropdown(
                        choices=DEFAULT_BENCHMARK_LANGUAGES,
                        value="en",
                        label="Preview Language",
                    )
                    preview_tokenizer = gr.Dropdown(
                        choices=[(family["label"], family["key"]) for family in tokenizer_families],
                        value=exact_tokenizers[0] if exact_tokenizers else None,
                        label="Preview Tokenizer",
                    )
                    preview_sample_index = gr.Slider(0, 9, value=0, step=1, label="Preview Sample Index")
                with gr.Row():
                    benchmark_include_estimates = gr.Checkbox(label="Include estimated values", value=False)
                    benchmark_include_proxy = gr.Checkbox(label="Include proxy mappings", value=False)
                    benchmark_live_updates = gr.Checkbox(label="Live diagnostics", value=True)
                    benchmark_run = gr.Button("Run Benchmark", variant="primary")
                gr.Markdown(
                    "Why these controls matter: Strict Evidence is the stable headline lane, while Streaming Exploration trades reproducibility for more naturalistic text. "
                    "The diagnostics pane can stream progress while each tokenizer-language pair is processed."
                )

                with gr.Tabs():
                    with gr.TabItem("Overview"):
                        benchmark_heatmap = gr.Plot(label="Benchmark Heatmap")
                        benchmark_distribution = gr.Plot(label="Metric Distribution")
                        benchmark_table = gr.DataFrame(label="Benchmark Table", interactive=False)
                    with gr.TabItem("Preview"):
                        benchmark_preview_md = gr.Markdown(label="Preview")
                    with gr.TabItem("Raw Data"):
                        benchmark_raw_table = gr.DataFrame(label="Raw Benchmark Data", interactive=False)
                    with gr.TabItem("Coverage"):
                        benchmark_coverage_plot = gr.Plot(label="Coverage")
                    with gr.TabItem("Observed Composition"):
                        benchmark_composition_plot = gr.Plot(label="Observed Composition")
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
                        benchmark_table,
                        benchmark_heatmap,
                        benchmark_distribution,
                        benchmark_preview_md,
                        benchmark_raw_table,
                        benchmark_coverage_plot,
                        benchmark_composition_plot,
                        benchmark_appendix_md,
                        benchmark_diagnostics_md,
                    ],
                )

            with gr.TabItem("Catalog"):
                with gr.Row():
                    catalog_include_proxy = gr.Checkbox(label="Include proxy mappings", value=False)
                    catalog_refresh_live = gr.Checkbox(label="Refresh live pricing cache", value=False)
                    catalog_live_updates = gr.Checkbox(label="Live diagnostics", value=True)
                    catalog_run = gr.Button("Load Catalog", variant="primary")
                gr.Markdown(
                    "Why these controls matter: this catalog is tokenizer-first, with free runnable models attached as examples. "
                    "Refreshing live pricing only updates the in-memory OpenRouter cache for this running app instance."
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
                with gr.Row():
                    scenario_lane = gr.Radio(
                        choices=list(LANE_TO_CORPUS_KEY.keys()),
                        value="Strict Evidence",
                        label="Benchmark Lane",
                    )
                    scenario_languages = gr.Dropdown(
                        choices=DEFAULT_BENCHMARK_LANGUAGES,
                        value=["en", "ar", "hi", "ja"],
                        multiselect=True,
                        label="Languages",
                    )
                with gr.Row():
                    scenario_tokenizers = gr.Dropdown(
                        choices=[(family["label"], family["key"]) for family in tokenizer_families],
                        value=exact_tokenizers,
                        multiselect=True,
                        label="Benchmark Tokenizers",
                    )
                    scenario_models = gr.Dropdown(
                        choices=model_choices,
                        value=[row["model_id"] for row in free_runtime_choices[:4]],
                        multiselect=True,
                        label="Attached Free Models",
                    )
                with gr.Row():
                    monthly_requests = gr.Slider(1_000, 1_000_000, value=100_000, step=1_000, label="Monthly Requests")
                    avg_input_tokens = gr.Slider(10, 10_000, value=600, step=10, label="Avg Input Tokens")
                    avg_output_tokens = gr.Slider(10, 10_000, value=250, step=10, label="Avg Output Tokens")
                    reasoning_share = gr.Slider(0.0, 2.0, value=0.1, step=0.05, label="Reasoning Share")
                with gr.Row():
                    slice_x = gr.Dropdown(
                        choices=["rtc", "monthly_cost", "monthly_input_tokens", "context_loss_pct", "ttft_seconds", "output_tokens_per_second"],
                        value="rtc",
                        label="Custom X",
                    )
                    slice_y = gr.Dropdown(
                        choices=["monthly_cost", "rtc", "monthly_input_tokens", "context_loss_pct", "ttft_seconds", "output_tokens_per_second"],
                        value="monthly_cost",
                        label="Custom Y",
                    )
                    slice_size = gr.Dropdown(
                        choices=["none", "monthly_cost", "monthly_input_tokens", "rtc"],
                        value="monthly_input_tokens",
                        label="Bubble Size",
                    )
                with gr.Row():
                    scenario_include_estimates = gr.Checkbox(label="Include estimated values", value=False)
                    scenario_include_proxy = gr.Checkbox(label="Include proxy mappings", value=False)
                    scenario_live_updates = gr.Checkbox(label="Live diagnostics", value=True)
                    scenario_run = gr.Button("Run Scenario Lab", variant="primary")
                gr.Markdown(
                    "Why these controls matter: Scenario Lab reuses the chosen benchmark lane as the multilingual baseline, "
                    "then attaches model pricing, context windows, and optional benchmark-only speed metadata."
                )

                with gr.Tabs():
                    with gr.TabItem("Cost"):
                        scenario_cost_plot = gr.Plot(label="Cost")
                    with gr.TabItem("Context Loss"):
                        scenario_context_plot = gr.Plot(label="Context Loss")
                    with gr.TabItem("Speed Metadata"):
                        scenario_speed_plot = gr.Plot(label="Speed Metadata")
                    with gr.TabItem("Scale"):
                        scenario_scale_plot = gr.Plot(label="Scale")
                    with gr.TabItem("Custom Slice"):
                        scenario_custom_plot = gr.Plot(label="Custom Slice")
                scenario_table = gr.DataFrame(label="Scenario Rows", interactive=False)
                scenario_appendix_md = gr.Markdown(label="Scenario Appendix")
                with gr.Accordion("Diagnostics", open=False):
                    scenario_diagnostics_md = gr.Markdown()

                scenario_run.click(
                    fn=_handle_scenario_tab,
                    inputs=[
                        scenario_lane,
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
