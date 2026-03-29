"""CLI entrypoint for screenshot-based UI review bundles."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from review_harness import (  # noqa: E402
    build_run_directory,
    capture_review_bundle,
    default_workbench_review_scenarios,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture a screenshot review bundle for the ML Workbench.")
    parser.add_argument(
        "--base-url",
        required=True,
        help="Base URL for the app under review, for example http://127.0.0.1:7860 or https://ml-workbench.onrender.com",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write screenshots into. Defaults to artifacts/review/<date>/<time>Z.",
    )
    parser.add_argument(
        "--include-runtime-tabs",
        action="store_true",
        help="Also capture Tokenizer Inspector and Model Comparison tabs. Model Comparison may consume hosted inference quota.",
    )
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Browser engine to use for capture.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run Chromium headed instead of headless.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=60_000,
        help="Page load timeout in milliseconds.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else build_run_directory()
    scenarios = default_workbench_review_scenarios(include_runtime_tabs=args.include_runtime_tabs)

    manifest_path, results = capture_review_bundle(
        base_url=args.base_url,
        output_dir=output_dir,
        scenarios=scenarios,
        browser_name=args.browser,
        headless=not args.headed,
        timeout_ms=args.timeout_ms,
    )

    print(f"Captured {len(results)} review scenarios into {output_dir}")
    print(f"Manifest: {manifest_path}")
    for result in results:
        warning_suffix = f" ({len(result.warnings)} warning(s))" if result.warnings else ""
        print(f"- {result.key}: {len(result.captures)} capture(s){warning_suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
