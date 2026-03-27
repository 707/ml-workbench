"""Refresh the local Artificial Analysis benchmark snapshot."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from snapshot_tools import validate_artificial_analysis_snapshot


AA_API_URL = "https://artificialanalysis.ai/api/v2/data/llms/models"

TARGET_MODELS = {
    "meta-llama/llama-3.1-8b-instruct": "llama-3",
    "mistralai/mistral-7b-instruct:free": "mistral",
    "qwen/qwen-2.5-7b-instruct:free": "qwen-2.5",
}


def main() -> int:
    api_key = os.environ.get("AA_API_KEY")
    if not api_key:
        raise SystemExit("AA_API_KEY is required")

    response = requests.get(
        AA_API_URL,
        headers={"x-api-key": api_key},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    models = []
    for row in payload.get("data", []):
        model_id = row.get("slug")
        tokenizer_key = TARGET_MODELS.get(model_id)
        if not tokenizer_key:
            continue
        models.append({
            "model_id": model_id,
            "tokenizer_key": tokenizer_key,
            "label": row.get("name", model_id),
            "ttft_seconds": row.get("median_time_to_first_token_seconds"),
            "output_tokens_per_second": row.get("median_output_tokens_per_second"),
            "provider": "Artificial Analysis",
            "benchmark_url": "https://artificialanalysis.ai/",
        })

    output_path = REPO_ROOT / "data" / "telemetry" / "artificial_analysis_snapshot.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({
        "captured_at": response.headers.get("date"),
        "source": "Artificial Analysis snapshot",
        "models": models,
    }, indent=2) + "\n", encoding="utf-8")
    validate_artificial_analysis_snapshot(output_path)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
