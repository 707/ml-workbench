"""Chart builders for the Token Tax Workbench."""

from __future__ import annotations

import math

from tokenizer_registry import tokenizer_color_map

RISK_COLORS = {
    "low": "#4CAF50",
    "moderate": "#FF9800",
    "high": "#F44336",
    "severe": "#9C27B0",
}


TOKENIZER_COLORS = tokenizer_color_map()

_MIN_BUBBLE_SIZE = 14
_MAX_BUBBLE_SIZE = 34


def _empty_figure(message: str = "No data available for this view"):
    """Return an empty plotly Figure with a centered annotation."""
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
            "font": {"size": 16},
        }],
    )
    _apply_theme(fig)
    return fig


def _value(row: dict, key: str):
    return row.get(key)


def _apply_theme(fig):
    fig.update_layout(
        template="plotly",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"color": "#111111"},
        title={"font": {"color": "#111111"}},
        legend={"font": {"color": "#111111"}},
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


def _normalize_bubble_sizes(values: list[float]) -> list[float]:
    """Map raw size values to a bounded visual range."""
    if not values:
        return []

    positive = [max(float(value), 0.0) for value in values]
    sqrt_values = [math.sqrt(value) for value in positive]
    min_value = min(sqrt_values)
    max_value = max(sqrt_values)

    if math.isclose(min_value, max_value):
        midpoint = (_MIN_BUBBLE_SIZE + _MAX_BUBBLE_SIZE) / 2.0
        return [midpoint for _ in positive]

    span = max_value - min_value
    return [
        _MIN_BUBBLE_SIZE + ((value - min_value) / span) * (_MAX_BUBBLE_SIZE - _MIN_BUBBLE_SIZE)
        for value in sqrt_values
    ]


def build_metric_scatter(
    rows: list[dict],
    *,
    x_key: str,
    y_key: str,
    size_key: str | None = None,
    label_key: str = "label",
    color_key: str = "tokenizer_key",
    title: str = "",
    x_title: str | None = None,
    y_title: str | None = None,
):
    """Build a flexible scatter/bubble chart."""
    import plotly.graph_objects as go

    if not rows:
        return _empty_figure("No scenario data available. Run the scenario first.")

    filtered = [
        row for row in rows
        if isinstance(_value(row, x_key), (int, float))
        and isinstance(_value(row, y_key), (int, float))
    ]
    if not filtered:
        if x_key in {"latency_ms", "throughput_tps"}:
            label = "latency" if x_key == "latency_ms" else "throughput"
            return _empty_figure(
                f"No {label} metadata is wired for the selected models. "
                "Current catalog refresh surfaces pricing and context, not performance telemetry."
            )
        if {x_key, y_key} == {"ttft_seconds", "output_tokens_per_second"}:
            return _empty_figure(
                "No benchmark-only speed metadata matched the selected models. "
                "Attach an Artificial Analysis snapshot or choose models with a benchmark match."
            )
        return _empty_figure(
            f"No numeric data is available for {x_key} vs {y_key} in the current scenario rows."
        )

    fig = go.Figure()
    show_text = len(filtered) <= 12
    bubble_sizes = [16.0 for _ in filtered]
    if size_key:
        size_values = [
            float(row[size_key])
            for row in filtered
            if isinstance(row.get(size_key), (int, float))
        ]
        if len(size_values) == len(filtered):
            bubble_sizes = _normalize_bubble_sizes(size_values)

    for row, bubble_size in zip(filtered, bubble_sizes):
        color_name = row.get(color_key, "")
        color = TOKENIZER_COLORS.get(color_name, "#4C78A8")

        fig.add_trace(go.Scatter(
            x=[row[x_key]],
            y=[row[y_key]],
            mode="markers+text" if show_text else "markers",
            name=row.get(label_key, row.get("model", "item")),
            text=[row.get(label_key, row.get("model", "item"))] if show_text else None,
            textposition="top center",
            textfont={"size": 10},
            marker={
                "size": bubble_size,
                "color": color,
                "opacity": 0.82,
                "line": {"width": 1, "color": "#243447"},
            },
            hovertemplate="<b>%{text}</b><br>"
            + f"{x_key}: %{{x}}<br>"
            + f"{y_key}: %{{y}}<br>"
            + f"provenance: {row.get('provenance', 'n/a')}"
            + "<extra></extra>",
        ))

    fig.update_layout(
        title=title,
        xaxis_title=x_title or x_key,
        yaxis_title=y_title or y_key,
        showlegend=False,
    )
    return _apply_theme(fig)


def build_distribution_chart(rows: list[dict], metric_key: str, group_key: str = "tokenizer_key"):
    """Build a box plot for benchmark distributions."""
    import plotly.graph_objects as go

    filtered = [
        row for row in rows
        if isinstance(row.get(metric_key), (int, float))
    ]
    if not filtered:
        return _empty_figure("No distribution data available")

    groups: dict[str, list[float]] = {}
    for row in filtered:
        groups.setdefault(str(row.get(group_key, "unknown")), []).append(float(row[metric_key]))

    fig = go.Figure()
    for group, values in groups.items():
        fig.add_trace(go.Box(
            y=values,
            name=group,
            marker_color=TOKENIZER_COLORS.get(group, "#4C78A8"),
            boxmean=True,
        ))

    fig.update_layout(
        title=f"{metric_key} distribution",
        yaxis_title=metric_key,
        xaxis_title=group_key,
    )
    return _apply_theme(fig)


def build_heatmap(
    benchmark_results: dict[tuple[str, str], dict],
    languages: list[str],
    models: list[str],
    metric_key: str = "rtc",
):
    """Build a language x tokenizer heatmap."""
    import plotly.graph_objects as go

    if not benchmark_results or not languages or not models:
        return _empty_figure("No benchmark data")

    z = []
    for lang in languages:
        row = []
        for model in models:
            entry = benchmark_results.get((lang, model), {})
            row.append(entry.get(metric_key, 0.0))
        z.append(row)

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=z,
        x=models,
        y=languages,
        colorscale=[
            [0.0, "#22c55e"],
            [0.5, "#f59e0b"],
            [1.0, "#ef4444"],
        ],
        colorbar_title=metric_key,
        hovertemplate=f"Language: %{{y}}<br>Tokenizer: %{{x}}<br>{metric_key}: %{{z}}<extra></extra>",
    ))
    fig.update_layout(
        title=f"{metric_key} by language and tokenizer",
        xaxis_title="Tokenizer family",
        yaxis_title="Language",
    )
    return _apply_theme(fig)


def build_category_bar(
    rows: list[dict],
    *,
    category_key: str,
    value_key: str,
    series_key: str = "tokenizer_key",
    title: str = "",
    x_title: str | None = None,
    y_title: str | None = None,
):
    """Build a grouped bar chart for categorical benchmark breakdowns."""
    import plotly.graph_objects as go

    filtered = [
        row for row in rows
        if row.get(category_key) is not None and isinstance(row.get(value_key), (int, float))
    ]
    if not filtered:
        return _empty_figure("No categorical benchmark data available")

    categories = list(dict.fromkeys(str(row[category_key]) for row in filtered))
    series_names = list(dict.fromkeys(str(row.get(series_key, "series")) for row in filtered))

    fig = go.Figure()
    for series_name in series_names:
        values = []
        for category in categories:
            match = next(
                (
                    row for row in filtered
                    if str(row.get(series_key, "series")) == series_name and str(row[category_key]) == category
                ),
                None,
            )
            values.append(match[value_key] if match else 0)
        fig.add_trace(go.Bar(
            x=categories,
            y=values,
            name=series_name,
            marker_color=TOKENIZER_COLORS.get(series_name, "#4C78A8"),
        ))

    fig.update_layout(
        title=title,
        xaxis_title=x_title or category_key,
        yaxis_title=y_title or value_key,
        barmode="group",
    )
    return _apply_theme(fig)


def build_stacked_category_bar(
    rows: list[dict],
    *,
    category_key: str,
    value_key: str,
    stack_key: str,
    title: str = "",
    x_title: str | None = None,
    y_title: str | None = None,
):
    """Build a stacked bar chart for categorical composition breakdowns."""
    import plotly.graph_objects as go

    filtered = [
        row for row in rows
        if row.get(category_key) is not None
        and row.get(stack_key) is not None
        and isinstance(row.get(value_key), (int, float))
    ]
    if not filtered:
        return _empty_figure("No composition data available")

    categories = list(dict.fromkeys(str(row[category_key]) for row in filtered))
    stack_names = list(dict.fromkeys(str(row[stack_key]) for row in filtered))
    palette = [
        "#2563eb",
        "#06b6d4",
        "#f97316",
        "#22c55e",
        "#a855f7",
        "#ef4444",
        "#14b8a6",
        "#64748b",
    ]

    fig = go.Figure()
    for index, stack_name in enumerate(stack_names):
        values = []
        for category in categories:
            match = next(
                (
                    row for row in filtered
                    if str(row[stack_key]) == stack_name and str(row[category_key]) == category
                ),
                None,
            )
            values.append(match[value_key] if match else 0)
        fig.add_trace(go.Bar(
            x=categories,
            y=values,
            name=stack_name,
            marker_color=palette[index % len(palette)],
        ))

    fig.update_layout(
        title=title,
        xaxis_title=x_title or category_key,
        yaxis_title=y_title or value_key,
        barmode="stack",
    )
    return _apply_theme(fig)


def build_context_chart(analysis_results: list[dict], avg_english_tokens_per_word: float = 1.33):
    """Horizontal bar chart showing effective context window in words."""
    import plotly.graph_objects as go
    from pricing import get_pricing

    if not analysis_results:
        return _empty_figure("No data — run an analysis first")

    models = []
    effective = []
    colors = []

    for r in analysis_results:
        try:
            pricing = get_pricing(r["model"])
            window = pricing["context_window"]
        except KeyError:
            continue

        rtc = r.get("rtc", 1.0)
        eff_words = int(window / max(rtc * avg_english_tokens_per_word, 1e-9))
        models.append(r["model"])
        effective.append(eff_words)
        colors.append(RISK_COLORS.get(r.get("risk_level", "low"), "#999999"))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=models,
        x=effective,
        orientation="h",
        marker_color=colors,
        text=[f"{e:,} words" for e in effective],
        textposition="auto",
    ))
    fig.update_layout(
        title="Effective Context Window (words)",
        xaxis_title="Approximate words",
        yaxis_title="Model",
    )
    return _apply_theme(fig)


def build_cost_waterfall(portfolio_result: dict):
    """Stacked horizontal bars: base cost + token tax surcharge."""
    import plotly.graph_objects as go

    entries = portfolio_result.get("languages", [])
    if not entries:
        return _empty_figure("No portfolio data")

    languages = [e["language"] for e in entries]
    english_equiv = []
    surcharge = []

    for e in entries:
        rtc = e.get("rtc", 1.0)
        cost = e.get("monthly_cost", 0.0)
        base = cost / rtc if rtc else cost
        english_equiv.append(base)
        surcharge.append(cost - base)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=languages,
        x=english_equiv,
        name="English-equivalent cost",
        orientation="h",
        marker_color="#4CAF50",
    ))
    fig.add_trace(go.Bar(
        y=languages,
        x=surcharge,
        name="Token tax surcharge",
        orientation="h",
        marker_color="#F44336",
    ))
    fig.update_layout(
        barmode="stack",
        title="Monthly Cost Breakdown: Base vs Token Tax",
        xaxis_title="Estimated monthly cost ($)",
        yaxis_title="Language",
    )
    return _apply_theme(fig)


def build_bubble_chart(analysis_results: list[dict]):
    """Backward-compatible cost vs RTC bubble chart."""
    rows = [
        {
            "label": row.get("model", "item"),
            "tokenizer_key": row.get("model", ""),
            "rtc": row.get("rtc"),
            "cost_per_million": row.get("cost_per_million"),
            "token_count": row.get("token_count", 0),
            "provenance": row.get("provenance", "strict_verified"),
        }
        for row in analysis_results
    ]
    return build_metric_scatter(
        rows,
        x_key="rtc",
        y_key="cost_per_million",
        size_key="token_count",
        title="Cost vs relative tokenization cost",
        x_title="Relative Tokenization Cost (RTC)",
        y_title="Cost per 1M input tokens ($)",
    )
