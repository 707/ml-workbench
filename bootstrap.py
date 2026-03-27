"""Container startup preflight for Hugging Face Spaces."""

from __future__ import annotations

import importlib.util
import os
import sys


REQUIRED_MODULES = [
    "app",
    "charts",
    "corpora",
    "diagnostics",
    "model_registry",
    "openrouter",
    "pricing",
    "provenance",
    "token_tax",
    "token_tax_ui",
    "tokenizer",
]


def _check_required_modules() -> None:
    missing = [
        module_name
        for module_name in REQUIRED_MODULES
        if importlib.util.find_spec(module_name) is None
    ]
    if missing:
        raise RuntimeError(
            "Space startup preflight failed. Missing runtime modules: "
            + ", ".join(sorted(missing))
        )


def main() -> None:
    _check_required_modules()

    from app import build_ui

    app = build_ui()
    app.launch(
        server_name=os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0"),
        server_port=int(os.environ.get("GRADIO_SERVER_PORT", "7860")),
        ssr_mode=False,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - exercised in container
        print(str(exc), file=sys.stderr, flush=True)
        raise
