"""Screenshot review harness for repeatable UI state capture."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Literal


ActionKind = Literal["open_top_tab", "open_inner_tab", "click_button", "click_text", "wait_ms"]
CaptureKind = Literal["full_page"]


@dataclass(frozen=True)
class ReviewAction:
    kind: ActionKind
    target: str
    value: int | None = None
    optional: bool = False


@dataclass(frozen=True)
class CaptureRequest:
    name: str
    kind: CaptureKind = "full_page"
    description: str = ""


@dataclass(frozen=True)
class ReviewScenario:
    key: str
    title: str
    description: str
    actions: tuple[ReviewAction, ...]
    captures: tuple[CaptureRequest, ...]
    notes: tuple[str, ...] = ()


@dataclass
class CaptureArtifact:
    name: str
    path: str
    kind: str


@dataclass
class ScenarioResult:
    key: str
    title: str
    description: str
    captures: list[CaptureArtifact] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def slugify(value: str) -> str:
    """Return a filesystem-friendly slug."""
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized or "capture"


def build_run_directory(root: str | Path = "artifacts/review", *, stamp: datetime | None = None) -> Path:
    """Return a timestamped review artifact directory path."""
    timestamp = stamp or datetime.now(timezone.utc)
    return Path(root) / timestamp.strftime("%Y-%m-%d") / timestamp.strftime("%H%M%SZ")


def default_workbench_review_scenarios(*, include_runtime_tabs: bool = False) -> list[ReviewScenario]:
    """Return the default screenshot sweep for the workbench."""
    scenarios = [
        ReviewScenario(
            key="benchmark-strict-defaults",
            title="Benchmark Strict Defaults",
            description="Default strict benchmark run in the Benchmark tab.",
            actions=(
                ReviewAction("open_top_tab", "Token Tax Workbench"),
                ReviewAction("open_inner_tab", "Benchmark"),
                ReviewAction("click_button", "Run Benchmark"),
                ReviewAction("wait_ms", "settle", value=1500),
            ),
            captures=(CaptureRequest("benchmark-strict-defaults"),),
            notes=(
                "Use this as the headline benchmark baseline.",
                "Review both chart readability and diagnostics clarity.",
            ),
        ),
        ReviewScenario(
            key="benchmark-streaming-defaults",
            title="Benchmark Streaming Defaults",
            description="Streaming Exploration benchmark run with default settings.",
            actions=(
                ReviewAction("open_top_tab", "Token Tax Workbench"),
                ReviewAction("open_inner_tab", "Benchmark"),
                ReviewAction("click_text", "Streaming Exploration"),
                ReviewAction("click_button", "Run Benchmark"),
                ReviewAction("wait_ms", "settle", value=1500),
            ),
            captures=(CaptureRequest("benchmark-streaming-defaults"),),
            notes=(
                "Streaming is exploratory only.",
                "Check that the copy and charts do not overclaim equivalence with strict RTC.",
            ),
        ),
        ReviewScenario(
            key="catalog-defaults",
            title="Catalog Defaults",
            description="Tokenizer-first catalog load with default settings.",
            actions=(
                ReviewAction("open_top_tab", "Token Tax Workbench"),
                ReviewAction("open_inner_tab", "Catalog"),
                ReviewAction("click_button", "Load Catalog"),
                ReviewAction("wait_ms", "settle", value=1000),
            ),
            captures=(CaptureRequest("catalog-defaults"),),
            notes=(
                "Verify attached free models, AA matches, and pricing freshness copy.",
            ),
        ),
        ReviewScenario(
            key="scenario-defaults-cost",
            title="Scenario Defaults Cost",
            description="Scenario Lab default run on the Cost view.",
            actions=(
                ReviewAction("open_top_tab", "Token Tax Workbench"),
                ReviewAction("open_inner_tab", "Scenario Lab"),
                ReviewAction("click_button", "Run Scenario Lab"),
                ReviewAction("wait_ms", "settle", value=1500),
                ReviewAction("open_inner_tab", "Cost"),
            ),
            captures=(CaptureRequest("scenario-defaults-cost"),),
            notes=(
                "Default scenario should be visually legible and not dominated by bubble sizing.",
            ),
        ),
        ReviewScenario(
            key="scenario-defaults-context",
            title="Scenario Defaults Context",
            description="Scenario Lab default run on the Context Loss view.",
            actions=(
                ReviewAction("open_top_tab", "Token Tax Workbench"),
                ReviewAction("open_inner_tab", "Scenario Lab"),
                ReviewAction("click_button", "Run Scenario Lab"),
                ReviewAction("wait_ms", "settle", value=1500),
                ReviewAction("open_inner_tab", "Context Loss"),
            ),
            captures=(CaptureRequest("scenario-defaults-context"),),
        ),
        ReviewScenario(
            key="scenario-defaults-speed",
            title="Scenario Defaults Speed",
            description="Scenario Lab default run on the Speed Metadata view.",
            actions=(
                ReviewAction("open_top_tab", "Token Tax Workbench"),
                ReviewAction("open_inner_tab", "Scenario Lab"),
                ReviewAction("click_button", "Run Scenario Lab"),
                ReviewAction("wait_ms", "settle", value=1500),
                ReviewAction("open_inner_tab", "Speed Metadata"),
            ),
            captures=(CaptureRequest("scenario-defaults-speed"),),
            notes=(
                "Check empty states and partial benchmark coverage for speed metadata.",
            ),
        ),
        ReviewScenario(
            key="scenario-defaults-scale",
            title="Scenario Defaults Scale",
            description="Scenario Lab default run on the Scale view.",
            actions=(
                ReviewAction("open_top_tab", "Token Tax Workbench"),
                ReviewAction("open_inner_tab", "Scenario Lab"),
                ReviewAction("click_button", "Run Scenario Lab"),
                ReviewAction("wait_ms", "settle", value=1500),
                ReviewAction("open_inner_tab", "Scale"),
            ),
            captures=(CaptureRequest("scenario-defaults-scale"),),
        ),
        ReviewScenario(
            key="scenario-defaults-custom",
            title="Scenario Defaults Custom Slice",
            description="Scenario Lab default run on the Custom Slice view.",
            actions=(
                ReviewAction("open_top_tab", "Token Tax Workbench"),
                ReviewAction("open_inner_tab", "Scenario Lab"),
                ReviewAction("click_button", "Run Scenario Lab"),
                ReviewAction("wait_ms", "settle", value=1500),
                ReviewAction("open_inner_tab", "Custom Slice"),
            ),
            captures=(CaptureRequest("scenario-defaults-custom"),),
        ),
    ]

    if include_runtime_tabs:
        scenarios.extend([
            ReviewScenario(
                key="tokenizer-inspector-defaults",
                title="Tokenizer Inspector Defaults",
                description="Default Tokenizer Inspector landing view.",
                actions=(ReviewAction("open_top_tab", "Tokenizer Inspector"),),
                captures=(CaptureRequest("tokenizer-inspector-defaults"),),
            ),
            ReviewScenario(
                key="model-comparison-defaults",
                title="Model Comparison Defaults",
                description="Default Model Comparison landing view. This may consume hosted inference quota if run interactively.",
                actions=(ReviewAction("open_top_tab", "Model Comparison"),),
                captures=(CaptureRequest("model-comparison-defaults"),),
                notes=("Runtime tab excluded by default to avoid accidental hosted inference spend.",),
            ),
        ])

    return scenarios


def write_manifest(
    output_dir: str | Path,
    *,
    base_url: str,
    scenarios: list[ReviewScenario],
    results: list[ScenarioResult],
) -> Path:
    """Write a JSON manifest for a review capture run."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    manifest_path = output_path / "manifest.json"
    payload = {
        "base_url": base_url,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "scenario_count": len(scenarios),
        "scenarios": [
            {
                **asdict(result),
                "captures": [asdict(capture) for capture in result.captures],
            }
            for result in results
        ],
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


def _first_visible(locator):
    count = locator.count()
    for index in range(count):
        candidate = locator.nth(index)
        try:
            if candidate.is_visible():
                return candidate
        except Exception:
            continue
    raise LookupError("No visible locator matched the requested selector")


def _perform_action(page, action: ReviewAction) -> None:
    if action.kind in {"open_top_tab", "open_inner_tab"}:
        target = _first_visible(page.get_by_role("tab", name=action.target, exact=True))
        target.click()
        page.wait_for_timeout(250)
        return
    if action.kind == "click_button":
        target = _first_visible(page.get_by_role("button", name=action.target, exact=True))
        target.click()
        return
    if action.kind == "click_text":
        target = _first_visible(page.get_by_text(action.target, exact=True))
        target.click()
        page.wait_for_timeout(250)
        return
    if action.kind == "wait_ms":
        page.wait_for_timeout(int(action.value or 0))
        return
    raise ValueError(f"Unsupported action kind: {action.kind}")


def capture_review_bundle(
    *,
    base_url: str,
    output_dir: str | Path,
    scenarios: list[ReviewScenario] | None = None,
    browser_name: str = "chromium",
    headless: bool = True,
    viewport_width: int = 1600,
    viewport_height: int = 1300,
    timeout_ms: int = 60_000,
) -> tuple[Path, list[ScenarioResult]]:
    """Capture a screenshot bundle for the configured review scenarios."""
    scenario_list = scenarios or default_workbench_review_scenarios()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment-dependent
        raise RuntimeError(
            "Playwright is required for screenshot capture. Install the Python package and browser runtime first."
        ) from exc

    results: list[ScenarioResult] = []
    with sync_playwright() as playwright:
        try:
            browser_type = getattr(playwright, browser_name)
        except AttributeError as exc:
            raise ValueError(f"Unsupported browser: {browser_name}") from exc
        try:
            browser = browser_type.launch(headless=headless)
        except Exception as exc:  # pragma: no cover - environment-dependent
            raise RuntimeError(
                f"Playwright could not launch the {browser_name} browser runtime. "
                "Try `uv run playwright install chromium` or choose a different browser via the CLI."
            ) from exc
        context = browser.new_context(viewport={"width": viewport_width, "height": viewport_height})
        page = context.new_page()
        page.goto(base_url, wait_until="networkidle", timeout=timeout_ms)
        page.wait_for_timeout(1000)

        for scenario in scenario_list:
            result = ScenarioResult(
                key=scenario.key,
                title=scenario.title,
                description=scenario.description,
                notes=list(scenario.notes),
            )
            scenario_dir = output_path / slugify(scenario.key)
            scenario_dir.mkdir(parents=True, exist_ok=True)

            for action in scenario.actions:
                try:
                    _perform_action(page, action)
                except Exception as exc:
                    message = f"{action.kind}:{action.target} failed: {exc}"
                    if action.optional:
                        result.warnings.append(message)
                        continue
                    result.warnings.append(message)
                    break

            for capture in scenario.captures:
                capture_name = slugify(capture.name)
                capture_path = scenario_dir / f"{capture_name}.png"
                page.screenshot(path=str(capture_path), full_page=True)
                result.captures.append(CaptureArtifact(
                    name=capture.name,
                    path=str(capture_path),
                    kind=capture.kind,
                ))

            results.append(result)

        browser.close()

    manifest_path = write_manifest(
        output_path,
        base_url=base_url,
        scenarios=scenario_list,
        results=results,
    )
    return manifest_path, results
