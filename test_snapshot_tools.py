"""Tests for local snapshot validation helpers."""

from pathlib import Path


def test_validate_strict_parallel_snapshot_accepts_current_repo_snapshot():
    from snapshot_tools import validate_strict_parallel_snapshot

    result = validate_strict_parallel_snapshot(
        Path(__file__).with_name("data") / "strict_parallel" / "flores_v1.jsonl"
    )

    assert result["row_count"] > 0
    assert "language_count" in result


def test_validate_artificial_analysis_snapshot_accepts_current_repo_snapshot():
    from snapshot_tools import validate_artificial_analysis_snapshot

    result = validate_artificial_analysis_snapshot(
        Path(__file__).with_name("data") / "telemetry" / "artificial_analysis_snapshot.json"
    )

    assert result["model_count"] > 0
    assert result["captured_at"]


def test_snapshot_refresh_scripts_exist():
    root = Path(__file__).resolve().parent

    assert (root / "scripts" / "rebuild_flores_snapshot.py").exists()
    assert (root / "scripts" / "refresh_aa_snapshot.py").exists()
    assert (root / "scripts" / "validate_snapshots.py").exists()
