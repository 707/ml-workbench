"""Scenario engine wrappers with typed requests and benchmark-result reuse."""

from __future__ import annotations

from typing import Callable

from workbench.engines.benchmark import run_benchmark_request
from workbench.model_registry import (
    build_catalog_entries,
    list_free_runtime_choices,
    resolve_selection,
)
from workbench.types import ScenarioRequest, ScenarioResult


def derive_scenario_model_ids(
    tokenizer_keys: tuple[str, ...] | list[str] | None,
    *,
    include_proxy: bool,
) -> list[str]:
    selected = set(tokenizer_keys or [])
    if not selected:
        return []
    rows = list_free_runtime_choices(include_proxy=include_proxy)
    model_ids = [
        row["model_id"]
        for row in rows
        if row["tokenizer_key"] in selected
    ]
    return sorted(model_ids)


def run_scenario_request(
    request: ScenarioRequest,
    *,
    progress_callback: Callable[[float, str], None] | None = None,
) -> ScenarioResult:
    model_ids = derive_scenario_model_ids(
        request.tokenizer_keys,
        include_proxy=request.include_proxy,
    )
    def _benchmark_progress(ratio: float, desc: str) -> None:
        if progress_callback is None:
            return
        progress_callback(0.12 + (ratio * 0.63), desc)

    benchmark = run_benchmark_request(
        request.to_benchmark_request(),
        progress_callback=_benchmark_progress,
    )
    benchmark_lookup = {
        (row["language"], row["tokenizer_key"]): row
        for row in benchmark.rows
    }
    benchmark_tokenizers = set(benchmark.tokenizers or [row["tokenizer_key"] for row in benchmark.rows])
    missing_tokenizers = [
        selection["label"]
        for key in request.tokenizer_keys
        if key not in benchmark_tokenizers
        for selection in [resolve_selection(key)]
    ]
    if missing_tokenizers:
        raise RuntimeError(
            "Scenario benchmark is missing tokenizer families: "
            + ", ".join(missing_tokenizers)
            + ". This usually means their local tokenizer files were unavailable at runtime."
        )

    catalog = build_catalog_entries(include_proxy=request.include_proxy, refresh_live=False)
    selected_models = {row["model_id"]: row for row in catalog if row["model_id"] in model_ids}

    rows: list[dict] = []
    if progress_callback is not None:
        progress_callback(0.82, "Joining model metadata…")
    for model_id, model in selected_models.items():
        for language in benchmark.languages:
            benchmark_row = benchmark_lookup.get((language, model["tokenizer_key"]))
            if not benchmark_row or benchmark_row.get("rtc") is None:
                continue

            rtc = float(benchmark_row["rtc"])
            monthly_input_tokens = request.monthly_requests * max(int(round(request.avg_input_tokens * rtc)), 1)
            billed_output_tokens = request.monthly_requests * max(
                int(round(request.avg_output_tokens * (1.0 + request.reasoning_share))),
                1,
            )
            input_cost = monthly_input_tokens * model["input_per_million"] / 1_000_000
            output_cost = billed_output_tokens * model["output_per_million"] / 1_000_000
            context_loss_pct = max(0.0, (1.0 - (1.0 / rtc)) * 100.0) if rtc else 0.0

            rows.append({
                "label": model["label"],
                "model_id": model_id,
                "language": language,
                "tokenizer_key": model["tokenizer_key"],
                "rtc": round(rtc, 4),
                "context_loss_pct": round(context_loss_pct, 2),
                "monthly_input_tokens": monthly_input_tokens,
                "monthly_output_tokens": billed_output_tokens,
                "monthly_cost": round(input_cost + output_cost, 6),
                "input_cost": round(input_cost, 6),
                "output_cost": round(output_cost, 6),
                "latency_ms": model["latency_ms"],
                "throughput_tps": model["throughput_tps"],
                "ttft_seconds": model.get("ttft_seconds"),
                "output_tokens_per_second": model.get("output_tokens_per_second"),
                "telemetry_provider": model.get("telemetry_provider"),
                "lane": benchmark_row.get("lane", "Strict Evidence"),
                "provenance": model["provenance"],
                "mapping_quality": model["mapping_quality"],
            })
    if not rows:
        raise RuntimeError(
            "No scenario rows were produced. This usually means benchmark data was unavailable for the selected languages/models."
        )
    if progress_callback is not None:
        progress_callback(0.9, "Scenario rows ready")
    return ScenarioResult(rows=rows, model_ids=model_ids)
