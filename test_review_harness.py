"""Tests for the screenshot review harness."""

from datetime import datetime, timezone


def test_slugify_normalizes_review_names():
    from review_harness import slugify

    assert slugify("Scenario Lab / Default Values") == "scenario-lab-default-values"


def test_build_run_directory_is_timestamped():
    from review_harness import build_run_directory

    stamp = datetime(2026, 3, 29, 22, 15, 0, tzinfo=timezone.utc)
    path = build_run_directory("artifacts/review", stamp=stamp)

    assert path.as_posix().endswith("artifacts/review/2026-03-29/221500Z")


def test_default_workbench_review_scenarios_have_unique_keys():
    from review_harness import default_workbench_review_scenarios

    scenarios = default_workbench_review_scenarios()
    keys = [scenario.key for scenario in scenarios]

    assert len(keys) == len(set(keys))
    assert "benchmark-strict-defaults" in keys
    assert "scenario-defaults-cost" in keys
    assert "scenario-defaults-speed" in keys


def test_default_workbench_review_scenarios_skip_runtime_tabs_by_default():
    from review_harness import default_workbench_review_scenarios

    scenarios = default_workbench_review_scenarios()
    keys = {scenario.key for scenario in scenarios}

    assert "model-comparison-defaults" not in keys
    assert "tokenizer-inspector-defaults" not in keys


def test_runtime_tabs_can_be_opted_in():
    from review_harness import default_workbench_review_scenarios

    scenarios = default_workbench_review_scenarios(include_runtime_tabs=True)
    keys = {scenario.key for scenario in scenarios}

    assert "model-comparison-defaults" in keys
    assert "tokenizer-inspector-defaults" in keys
