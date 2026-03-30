"""Preload a small tokenizer set into the local cache during image build."""

from __future__ import annotations

import sys

from tokenizer import get_tokenizer

DEFAULT_KEYS = [
    "gpt2",
    "o200k_base",
    "llama-3",
    "mistral",
    "qwen-2.5",
]


def main(argv: list[str]) -> int:
    keys = argv or DEFAULT_KEYS
    for key in keys:
        get_tokenizer(key)
        print(f"warmed {key}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
