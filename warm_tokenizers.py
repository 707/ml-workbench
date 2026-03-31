"""Preload a small tokenizer set into the local cache during image build."""

from __future__ import annotations

import sys

from model_registry import list_free_runtime_choices
from tokenizer import get_tokenizer


def default_keys() -> list[str]:
    """Return the tokenizer families that should be warmed during image build."""
    keys = [
        "gpt2",
        "o200k_base",
        "cl100k_base",
    ]
    keys.extend(
        row["tokenizer_key"]
        for row in list_free_runtime_choices(include_proxy=False)
    )
    return list(dict.fromkeys(keys))


DEFAULT_KEYS = default_keys()


def main(argv: list[str]) -> int:
    keys = argv or DEFAULT_KEYS
    for key in keys:
        get_tokenizer(key)
        print(f"warmed {key}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
