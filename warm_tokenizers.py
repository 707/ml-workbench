"""Preload a small tokenizer set into the local cache during image build."""

from __future__ import annotations

import json
import sys

from huggingface_hub import snapshot_download

from model_registry import list_free_runtime_choices
from tokenizer import (
    SNAPSHOT_MANIFEST_PATH,
    SUPPORTED_TOKENIZERS,
    AutoTokenizer,
    TiktokenAdapter,
    get_tokenizer,
)

TOKENIZER_FILE_PATTERNS = [
    "config.json",
    "tokenizer.json",
    "tokenizer.model",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "generation_config.json",
    "merges.txt",
    "vocab.json",
    "vocab.txt",
    "*.model",
]


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


def _warm_hf_tokenizer(repo_id: str) -> str:
    """Download only tokenizer-relevant files and verify they reopen locally."""
    snapshot_path = snapshot_download(repo_id, allow_patterns=TOKENIZER_FILE_PATTERNS)
    AutoTokenizer.from_pretrained(snapshot_path, local_files_only=True)
    return snapshot_path


def main(argv: list[str]) -> int:
    keys = argv or DEFAULT_KEYS
    snapshot_manifest: dict[str, str] = {}
    for key in keys:
        source = SUPPORTED_TOKENIZERS[key]
        if source.startswith("tiktoken:"):
            encoding_name = source.split(":", 1)[1]
            TiktokenAdapter(encoding_name)
        else:
            snapshot_manifest[source] = _warm_hf_tokenizer(source)
            get_tokenizer(key)
        print(f"warmed {key}", flush=True)
    SNAPSHOT_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_MANIFEST_PATH.write_text(json.dumps(snapshot_manifest, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
