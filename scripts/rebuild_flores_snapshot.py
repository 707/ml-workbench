"""Rebuild the local FLORES strict benchmark snapshot from HF dataset viewer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from snapshot_tools import validate_strict_parallel_snapshot

LANGUAGE_CONFIGS = {
    "ar": "ar-en",
    "de": "de-en",
    "es": "es-en",
    "fr": "fr-en",
    "hi": "hi-en",
    "ja": "ja-en",
    "pt": "pt-en",
    "ru": "ru-en",
    "zh": "zh-en",
}

DATASET_URL = "https://datasets-server.huggingface.co/first-rows"


def _fetch_rows(config: str, rows: int) -> list[dict]:
    response = requests.get(
        DATASET_URL,
        params={
            "dataset": "haoranxu/FLORES-200",
            "config": config,
            "split": "devtest",
            "offset": 0,
            "length": rows,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("rows", [])


def main() -> int:
    output_path = REPO_ROOT / "data" / "strict_parallel" / "flores_v1.jsonl"
    entries: list[str] = []

    for language, config in LANGUAGE_CONFIGS.items():
        for row in _fetch_rows(config, rows=2):
            value = row.get("row", {})
            entries.append(json.dumps({
                "language": language,
                "text": value.get(language, ""),
                "english_text": value.get("en", ""),
                "corpus_key": "strict_parallel",
                "source_id": f"https://huggingface.co/datasets/haoranxu/FLORES-200?config={config}",
                "provenance": "strict_verified",
            }, ensure_ascii=False))
        if language == "fr":
            for row in _fetch_rows(config, rows=2):
                value = row.get("row", {})
                entries.append(json.dumps({
                    "language": "en",
                    "text": value.get("en", ""),
                    "english_text": value.get("en", ""),
                    "corpus_key": "strict_parallel",
                    "source_id": f"https://huggingface.co/datasets/haoranxu/FLORES-200?config={config}",
                    "provenance": "strict_verified",
                }, ensure_ascii=False))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(entries) + "\n", encoding="utf-8")
    validate_strict_parallel_snapshot(output_path)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
