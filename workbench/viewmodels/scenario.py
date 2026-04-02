"""Scenario view-model helpers."""

from __future__ import annotations

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


def language_label(code: str) -> str:
    return LANGUAGE_LABELS.get(code, code)


def shorten_model_label(label: str, max_length: int = 30) -> str:
    if len(label) <= max_length:
        return label
    return f"{label[: max_length - 3].rstrip()}..."


def format_metric_value(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int):
        return f"{value:,}"
    if abs(float(value)) >= 10:
        return f"{float(value):.1f}"
    return f"{float(value):.2f}"


def aggregate_scenario_rows(rows: list[dict]) -> list[dict]:
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


def build_scenario_language_detail_rows(rows: list[dict]) -> list[dict]:
    detail_rows: list[dict] = []
    for row in rows:
        detail_rows.append(
            {
                **row,
                "display_label": shorten_model_label(str(row.get("label", ""))),
                "language": language_label(str(row.get("language", ""))),
                "language_code": row.get("language"),
                "point_kind": "language",
            }
        )

    for row in aggregate_scenario_rows(rows):
        detail_rows.append(
            {
                **row,
                "language": "Average",
                "language_code": "avg",
                "point_kind": "average",
            }
        )
    return detail_rows


def build_scenario_speed_summary(chart_rows: list[dict]) -> str:
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
            f"- Fastest time-to-first-token: **{fastest['label']}** at **{format_metric_value(fastest['ttft_seconds'])}s**."
        )
        lines.append(
            f"- Highest output throughput: **{highest_tps['label']}** at **{format_metric_value(highest_tps['output_tokens_per_second'])} tok/s**."
        )
    if unmatched:
        labels = ", ".join(row["label"] for row in unmatched)
        lines.append(f"- No benchmark match yet: {labels}.")
    return "\n".join(lines)
