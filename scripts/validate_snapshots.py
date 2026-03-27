"""Validate committed benchmark and telemetry snapshots."""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from snapshot_tools import (
    validate_artificial_analysis_snapshot,
    validate_strict_parallel_snapshot,
)


def main() -> int:
    strict_path = REPO_ROOT / "data" / "strict_parallel" / "flores_v1.jsonl"
    aa_path = REPO_ROOT / "data" / "telemetry" / "artificial_analysis_snapshot.json"

    strict = validate_strict_parallel_snapshot(strict_path)
    aa = validate_artificial_analysis_snapshot(aa_path)

    print(
        "Validated snapshots:",
        {
            "strict_parallel": strict,
            "artificial_analysis": aa,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
