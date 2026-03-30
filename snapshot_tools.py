"""Helpers for validating and maintaining local benchmark snapshots."""

from __future__ import annotations

import json
from pathlib import Path

STRICT_REQUIRED_KEYS = {
    "language",
    "text",
    "english_text",
    "corpus_key",
    "source_id",
    "provenance",
}

AA_REQUIRED_KEYS = {
    "model_id",
    "tokenizer_key",
    "label",
    "ttft_seconds",
    "output_tokens_per_second",
    "provider",
    "benchmark_url",
}


def validate_strict_parallel_snapshot(path: Path) -> dict:
    """Validate the local strict benchmark snapshot."""
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        missing = STRICT_REQUIRED_KEYS - set(row)
        if missing:
            raise ValueError(f"{path}:{line_number} missing keys: {sorted(missing)}")
        rows.append(row)

    if not rows:
        raise ValueError(f"{path} contains no rows")

    return {
        "row_count": len(rows),
        "language_count": len({row["language"] for row in rows}),
    }


def validate_artificial_analysis_snapshot(path: Path) -> dict:
    """Validate the local benchmark-only speed snapshot."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    models = payload.get("models", [])
    captured_at = payload.get("captured_at")
    if not captured_at:
        raise ValueError(f"{path} is missing captured_at")
    if not models:
        raise ValueError(f"{path} contains no models")
    for index, row in enumerate(models, start=1):
        missing = AA_REQUIRED_KEYS - set(row)
        if missing:
            raise ValueError(f"{path}:models[{index}] missing keys: {sorted(missing)}")
    return {
        "captured_at": captured_at,
        "model_count": len(models),
    }
