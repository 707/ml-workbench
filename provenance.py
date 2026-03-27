"""Provenance helpers for benchmark, catalog, and scenario records."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProvenanceInfo:
    key: str
    label: str
    badge: str
    description: str


PROVENANCE_REGISTRY: dict[str, ProvenanceInfo] = {
    "strict_verified": ProvenanceInfo(
        key="strict_verified",
        label="Strict Verified",
        badge="verified",
        description="Direct API field or corpus-backed measurement with exact mapping.",
    ),
    "surfaced_metadata": ProvenanceInfo(
        key="surfaced_metadata",
        label="Surfaced Metadata",
        badge="metadata",
        description="Value surfaced by a provider platform, not benchmarked in this app.",
    ),
    "estimated": ProvenanceInfo(
        key="estimated",
        label="Estimated",
        badge="estimate",
        description="Derived from user assumptions or heuristic conversion.",
    ),
    "proxy": ProvenanceInfo(
        key="proxy",
        label="Proxy",
        badge="proxy",
        description="Approximate tokenizer/model mapping; not safe for headline comparisons.",
    ),
    "research_forward": ProvenanceInfo(
        key="research_forward",
        label="Research Forward",
        badge="research",
        description="Literature-backed or planned source not yet wired into strict visuals.",
    ),
}


PROVENANCE_ORDER = [
    "strict_verified",
    "surfaced_metadata",
    "estimated",
    "proxy",
    "research_forward",
]


def normalize_provenance(level: str | None) -> str:
    """Return a known provenance key."""
    if level in PROVENANCE_REGISTRY:
        return str(level)
    return "estimated"


def provenance_badge(level: str | None) -> str:
    """Return a short badge label for a provenance level."""
    info = PROVENANCE_REGISTRY[normalize_provenance(level)]
    return f"[{info.badge}]"


def provenance_description(level: str | None) -> str:
    """Return a human-readable explanation for a provenance level."""
    return PROVENANCE_REGISTRY[normalize_provenance(level)].description


def provenance_rank(level: str | None) -> int:
    """Return numeric rank for stable sorting."""
    normalized = normalize_provenance(level)
    return PROVENANCE_ORDER.index(normalized)


def provenance_visible(
    level: str | None,
    *,
    include_estimates: bool = False,
    include_proxy: bool = False,
    include_research_forward: bool = False,
) -> bool:
    """Gate records based on the UI visibility policy."""
    normalized = normalize_provenance(level)
    if normalized in ("strict_verified", "surfaced_metadata"):
        return True
    if normalized == "estimated":
        return include_estimates
    if normalized == "proxy":
        return include_proxy
    if normalized == "research_forward":
        return include_research_forward
    return False
