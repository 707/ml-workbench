"""Model registry for tokenizer families and deployable model examples."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pricing import get_pricing, refresh_from_openrouter
from tokenizer_registry import TOKENIZER_FAMILY_SPECS


@dataclass(frozen=True)
class TokenizerFamily:
    key: str
    label: str
    tokenizer_source: str
    mapping_quality: str
    provenance: str


@dataclass(frozen=True)
class ModelMapping:
    model_id: str
    tokenizer_key: str
    label: str
    mapping_quality: str
    provenance: str
    source: str


FREE_OPENROUTER_MODELS: dict[str, tuple[str, ...]] = {
    "o200k_base": (),
    "cl100k_base": (),
    "llama-3": (
        "meta-llama/llama-3.2-3b-instruct:free",
    ),
    "mistral": (
        "mistralai/mistral-7b-instruct:free",
    ),
    "qwen-2.5": (
        "qwen/qwen-2.5-7b-instruct:free",
    ),
    "qwen3-next": (
        "qwen/qwen3-next-80b-a3b-instruct:free",
    ),
    "qwen3-coder": (
        "qwen/qwen3-coder:free",
    ),
    "gpt-oss": (
        "openai/gpt-oss-20b:free",
        "openai/gpt-oss-120b:free",
    ),
    "glm-4.5-air": (
        "z-ai/glm-4.5-air:free",
    ),
    "nemotron-3-nano-30b": (
        "nvidia/nemotron-3-nano-30b-a3b:free",
    ),
    "nemotron-3-super": (
        "nvidia/nemotron-3-super-120b-a12b:free",
    ),
    "nemotron-nano-9b-v2": (
        "nvidia/nemotron-nano-9b-v2:free",
    ),
    "trinity-large": (
        "arcee-ai/trinity-large-preview:free",
    ),
    "trinity-mini": (
        "arcee-ai/trinity-mini:free",
    ),
    "gemma-2": (
        "google/gemma-3-27b-it:free",
    ),
    "command-r": (),
    "gpt2": (),
}

ARTIFICIAL_ANALYSIS_SNAPSHOT_PATH = (
    Path(__file__).resolve().parent / "data" / "telemetry" / "artificial_analysis_snapshot.json"
)


TOKENIZER_FAMILIES: dict[str, TokenizerFamily] = {
    key: TokenizerFamily(
        key=spec.key,
        label=spec.label,
        tokenizer_source=spec.tokenizer_source,
        mapping_quality=spec.mapping_quality,
        provenance=spec.provenance,
    )
    for key, spec in TOKENIZER_FAMILY_SPECS.items()
}


MODEL_MAPPINGS: dict[str, ModelMapping] = {
    "openai/gpt-4o": ModelMapping("openai/gpt-4o", "o200k_base", "GPT-4o", "exact", "strict_verified", "Static exact mapping"),
    "openai/gpt-4o-mini": ModelMapping("openai/gpt-4o-mini", "o200k_base", "GPT-4o mini", "exact", "strict_verified", "Static exact mapping"),
    "openai/gpt-4-turbo": ModelMapping("openai/gpt-4-turbo", "cl100k_base", "GPT-4 Turbo", "exact", "strict_verified", "Static exact mapping"),
    "openai/gpt-3.5-turbo": ModelMapping("openai/gpt-3.5-turbo", "cl100k_base", "GPT-3.5 Turbo", "exact", "strict_verified", "Static exact mapping"),
    "meta-llama/llama-3.1-8b-instruct": ModelMapping("meta-llama/llama-3.1-8b-instruct", "llama-3", "Llama 3.1 8B Instruct", "exact", "strict_verified", "Static exact mapping"),
    "meta-llama/llama-3.1-70b-instruct": ModelMapping("meta-llama/llama-3.1-70b-instruct", "llama-3", "Llama 3.1 70B Instruct", "exact", "strict_verified", "Static exact mapping"),
    "meta-llama/llama-3.2-3b-instruct:free": ModelMapping("meta-llama/llama-3.2-3b-instruct:free", "llama-3", "Llama 3.2 3B Instruct (Free)", "exact", "strict_verified", "Static exact mapping"),
    "mistralai/mistral-7b-instruct": ModelMapping("mistralai/mistral-7b-instruct", "mistral", "Mistral 7B Instruct", "exact", "strict_verified", "Static exact mapping"),
    "mistralai/mistral-7b-instruct:free": ModelMapping("mistralai/mistral-7b-instruct:free", "mistral", "Mistral 7B Instruct (Free)", "exact", "strict_verified", "Static exact mapping"),
    "google/gemma-2-9b-it": ModelMapping("google/gemma-2-9b-it", "gemma-2", "Gemma 2 9B IT", "proxy", "proxy", "Tokenizer proxy until exact Gemma tokenizer equivalence is documented"),
    "google/gemma-3-27b-it:free": ModelMapping("google/gemma-3-27b-it:free", "gemma-2", "Gemma 3 27B IT (Free)", "proxy", "proxy", "Tokenizer proxy until exact Gemma tokenizer equivalence is documented"),
    "qwen/qwen-2.5-7b-instruct:free": ModelMapping("qwen/qwen-2.5-7b-instruct:free", "qwen-2.5", "Qwen 2.5 7B Instruct (Free)", "exact", "strict_verified", "Static exact mapping"),
    "qwen/qwen-2.5-72b-instruct": ModelMapping("qwen/qwen-2.5-72b-instruct", "qwen-2.5", "Qwen 2.5 72B Instruct", "exact", "strict_verified", "Static exact mapping"),
    "qwen/qwen3-next-80b-a3b-instruct:free": ModelMapping("qwen/qwen3-next-80b-a3b-instruct:free", "qwen3-next", "Qwen3 Next 80B A3B Instruct (Free)", "exact", "strict_verified", "Static exact mapping"),
    "qwen/qwen3-coder:free": ModelMapping("qwen/qwen3-coder:free", "qwen3-coder", "Qwen3 Coder 480B A35B (Free)", "exact", "strict_verified", "Static exact mapping"),
    "openai/gpt-oss-20b:free": ModelMapping("openai/gpt-oss-20b:free", "gpt-oss", "gpt-oss-20b (Free)", "exact", "strict_verified", "Static exact mapping"),
    "openai/gpt-oss-120b:free": ModelMapping("openai/gpt-oss-120b:free", "gpt-oss", "gpt-oss-120b (Free)", "exact", "strict_verified", "Static exact mapping"),
    "z-ai/glm-4.5-air:free": ModelMapping("z-ai/glm-4.5-air:free", "glm-4.5-air", "GLM 4.5 Air (Free)", "exact", "strict_verified", "Static exact mapping"),
    "nvidia/nemotron-3-nano-30b-a3b:free": ModelMapping("nvidia/nemotron-3-nano-30b-a3b:free", "nemotron-3-nano-30b", "Nemotron 3 Nano 30B A3B (Free)", "exact", "strict_verified", "Static exact mapping"),
    "nvidia/nemotron-3-super-120b-a12b:free": ModelMapping("nvidia/nemotron-3-super-120b-a12b:free", "nemotron-3-super", "Nemotron 3 Super 120B A12B (Free)", "exact", "strict_verified", "Static exact mapping"),
    "nvidia/nemotron-nano-9b-v2:free": ModelMapping("nvidia/nemotron-nano-9b-v2:free", "nemotron-nano-9b-v2", "Nemotron Nano 9B V2 (Free)", "exact", "strict_verified", "Static exact mapping"),
    "arcee-ai/trinity-large-preview:free": ModelMapping("arcee-ai/trinity-large-preview:free", "trinity-large", "Trinity Large Preview (Free)", "exact", "strict_verified", "Static exact mapping"),
    "arcee-ai/trinity-mini:free": ModelMapping("arcee-ai/trinity-mini:free", "trinity-mini", "Trinity Mini (Free)", "exact", "strict_verified", "Static exact mapping"),
    "cohere/command-r": ModelMapping("cohere/command-r", "command-r", "Command R", "proxy", "proxy", "Tokenizer proxy until exact Command R tokenizer is wired"),
}


# Backward-compatible alias expected by existing tests.
MODEL_TOKENIZER_MAP: dict[str, str] = {
    model_id: mapping.tokenizer_key
    for model_id, mapping in MODEL_MAPPINGS.items()
}


def list_tokenizer_families(include_proxy: bool = True) -> list[dict]:
    """Return tokenizer families for UI selection."""
    families = []
    for family in TOKENIZER_FAMILIES.values():
        if not include_proxy and family.mapping_quality == "proxy":
            continue
        families.append({
            "key": family.key,
            "label": family.label,
            "tokenizer_source": family.tokenizer_source,
            "mapping_quality": family.mapping_quality,
            "provenance": family.provenance,
        })
    return sorted(families, key=lambda item: item["label"])


def get_tokenizer_for_model(model_id: str) -> str:
    """Return the tokenizer key for an OpenRouter model ID."""
    if model_id not in MODEL_TOKENIZER_MAP:
        raise KeyError(
            f"unknown model: '{model_id}'. "
            f"Choose from {sorted(MODEL_TOKENIZER_MAP)}"
        )
    return MODEL_TOKENIZER_MAP[model_id]


def get_models_for_tokenizer(tokenizer_key: str) -> list[str]:
    """Return all model IDs that use the given tokenizer key."""
    return [
        model_id
        for model_id, tok in MODEL_TOKENIZER_MAP.items()
        if tok == tokenizer_key
    ]


def resolve_selection(selection: str) -> dict:
    """Normalize a UI selection to a tokenizer family record."""
    if selection in TOKENIZER_FAMILIES:
        family = TOKENIZER_FAMILIES[selection]
        return {
            "selection": selection,
            "selection_type": "tokenizer_family",
            "tokenizer_key": family.key,
            "label": family.label,
            "mapping_quality": family.mapping_quality,
            "provenance": family.provenance,
        }
    if selection in MODEL_MAPPINGS:
        mapping = MODEL_MAPPINGS[selection]
        return {
            "selection": selection,
            "selection_type": "model",
            "tokenizer_key": mapping.tokenizer_key,
            "label": mapping.label,
            "mapping_quality": mapping.mapping_quality,
            "provenance": mapping.provenance,
        }
    raise KeyError(f"unknown selection: {selection}")


def resolve_model(model_id: str) -> dict:
    """Resolve a model ID to its tokenizer key, pricing, and metadata."""
    if model_id not in MODEL_MAPPINGS:
        raise KeyError(
            f"unknown model: '{model_id}'. "
            f"Choose from {sorted(MODEL_MAPPINGS)}"
        )
    mapping = MODEL_MAPPINGS[model_id]
    try:
        pricing = get_pricing(model_id)
    except KeyError:
        pricing = get_pricing(mapping.tokenizer_key)
    return {
        "tokenizer_key": mapping.tokenizer_key,
        "pricing": pricing,
        "context_window": pricing["context_window"],
        "label": mapping.label,
        "mapping_quality": mapping.mapping_quality,
        "provenance": mapping.provenance,
        "source": mapping.source,
    }


def build_catalog_entries(
    *,
    include_proxy: bool = False,
    refresh_live: bool = False,
) -> list[dict]:
    """Return deployable model examples with pricing and mapping provenance."""
    if refresh_live:
        refresh_from_openrouter()

    entries: list[dict] = []
    aa_by_model = _load_artificial_analysis_by_model()
    for mapping in MODEL_MAPPINGS.values():
        if mapping.mapping_quality == "proxy" and not include_proxy:
            continue
        resolved = resolve_model(mapping.model_id)
        pricing = resolved["pricing"]
        aa_match = aa_by_model.get(mapping.model_id, {})
        entries.append({
            "model_id": mapping.model_id,
            "label": resolved["label"],
            "tokenizer_key": resolved["tokenizer_key"],
            "mapping_quality": resolved["mapping_quality"],
            "provenance": resolved["provenance"],
            "input_per_million": pricing["input_per_million"],
            "output_per_million": pricing["output_per_million"],
            "context_window": pricing["context_window"],
            "latency_ms": aa_match.get("ttft_seconds"),
            "throughput_tps": aa_match.get("output_tokens_per_second"),
            "ttft_seconds": aa_match.get("ttft_seconds"),
            "output_tokens_per_second": aa_match.get("output_tokens_per_second"),
            "telemetry_provider": aa_match.get("telemetry_provider"),
            "telemetry_benchmark_url": aa_match.get("benchmark_url"),
            "telemetry_captured_at": aa_match.get("captured_at"),
            "source": resolved["source"],
        })
    return sorted(entries, key=lambda entry: entry["label"].lower())


def _load_artificial_analysis_matches() -> dict[str, list[dict]]:
    """Load benchmark-only speed metadata keyed by tokenizer family."""
    if not ARTIFICIAL_ANALYSIS_SNAPSHOT_PATH.exists():
        return {}

    payload = json.loads(ARTIFICIAL_ANALYSIS_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    captured_at = payload.get("captured_at")
    rows_by_tokenizer: dict[str, list[dict]] = {}

    for row in payload.get("models", []):
        tokenizer_key = row.get("tokenizer_key")
        if not tokenizer_key:
            continue
        rows_by_tokenizer.setdefault(tokenizer_key, []).append({
            "model_id": row.get("model_id", ""),
            "label": row.get("label") or row.get("model_id", ""),
            "ttft_seconds": row.get("ttft_seconds"),
            "output_tokens_per_second": row.get("output_tokens_per_second"),
            "telemetry_provider": row.get("provider", "Artificial Analysis"),
            "benchmark_url": row.get("benchmark_url"),
            "captured_at": captured_at,
            "runtime_badge": "Benchmark-only external",
        })

    for matches in rows_by_tokenizer.values():
        matches.sort(key=lambda match: match["label"].lower())
    return rows_by_tokenizer


def _load_artificial_analysis_by_model() -> dict[str, dict]:
    """Load benchmark-only speed metadata keyed by model ID."""
    rows: dict[str, dict] = {}
    for matches in _load_artificial_analysis_matches().values():
        for match in matches:
            model_id = match.get("model_id")
            if model_id:
                rows[model_id] = match
    return rows


def artificial_analysis_status() -> dict:
    """Return freshness metadata for the local AA benchmark snapshot."""
    if not ARTIFICIAL_ANALYSIS_SNAPSHOT_PATH.exists():
        return {
            "captured_at": None,
            "model_count": 0,
            "source": "Artificial Analysis snapshot",
        }
    payload = json.loads(ARTIFICIAL_ANALYSIS_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    return {
        "captured_at": payload.get("captured_at"),
        "model_count": len(payload.get("models", [])),
        "source": payload.get("source", "Artificial Analysis snapshot"),
    }


def build_tokenizer_catalog(
    *,
    include_proxy: bool = False,
) -> list[dict]:
    """Return tokenizer-first catalog rows with attached free model examples."""
    rows: list[dict] = []
    aa_matches_by_tokenizer = _load_artificial_analysis_matches()

    for family in TOKENIZER_FAMILIES.values():
        if family.mapping_quality == "proxy" and not include_proxy:
            continue

        free_models: list[dict] = []
        for model_id in FREE_OPENROUTER_MODELS.get(family.key, ()):
            mapping = MODEL_MAPPINGS.get(model_id)
            if mapping is None:
                continue
            if mapping.mapping_quality == "proxy" and not include_proxy:
                continue
            resolved = resolve_model(mapping.model_id)
            pricing = resolved["pricing"]
            free_models.append({
                "model_id": mapping.model_id,
                "label": mapping.label,
                "mapping_quality": mapping.mapping_quality,
                "provenance": mapping.provenance,
                "input_per_million": pricing["input_per_million"],
                "output_per_million": pricing["output_per_million"],
                "context_window": pricing["context_window"],
                "runtime_badge": "Runnable here for free",
                "mapping_badge": "Exact tokenizer mapping" if mapping.mapping_quality == "exact" else "Proxy tokenizer mapping",
            })

        free_input_prices = [model["input_per_million"] for model in free_models]
        free_output_prices = [model["output_per_million"] for model in free_models]
        free_context_windows = [model["context_window"] for model in free_models]
        rows.append({
            "tokenizer_key": family.key,
            "label": family.label,
            "tokenizer_source": family.tokenizer_source,
            "mapping_quality": family.mapping_quality,
            "provenance": family.provenance,
            "free_models": sorted(free_models, key=lambda model: model["label"].lower()),
            "aa_matches": aa_matches_by_tokenizer.get(family.key, []),
            "free_model_count": len(free_models),
            "aa_match_count": len(aa_matches_by_tokenizer.get(family.key, [])),
            "min_input_per_million": min(free_input_prices) if free_input_prices else None,
            "min_output_per_million": min(free_output_prices) if free_output_prices else None,
            "max_context_window": max(free_context_windows) if free_context_windows else None,
        })

    return sorted(rows, key=lambda row: row["label"].lower())


def list_free_runtime_choices(*, include_proxy: bool = False) -> list[dict]:
    """Flatten attached free OpenRouter models for interactive selections."""
    seen: set[str] = set()
    rows: list[dict] = []
    for family in build_tokenizer_catalog(include_proxy=include_proxy):
        for model in family["free_models"]:
            if model["model_id"] in seen:
                continue
            seen.add(model["model_id"])
            rows.append({
                **model,
                "tokenizer_key": family["tokenizer_key"],
            })
    return sorted(rows, key=lambda row: row["label"].lower())
