"""Model registry for tokenizer families and deployable model examples."""

from __future__ import annotations

from dataclasses import dataclass

from pricing import get_pricing, refresh_from_openrouter
from tokenizer import SUPPORTED_TOKENIZERS


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
        "meta-llama/llama-3.1-8b-instruct",
        "meta-llama/llama-3.2-3b-instruct:free",
    ),
    "mistral": (
        "mistralai/mistral-7b-instruct:free",
    ),
    "qwen-2.5": (
        "qwen/qwen-2.5-7b-instruct:free",
    ),
    "gemma-2": (
        "google/gemma-3-27b-it:free",
    ),
    "command-r": (),
    "gpt2": (),
}


TOKENIZER_FAMILIES: dict[str, TokenizerFamily] = {
    "o200k_base": TokenizerFamily("o200k_base", "OpenAI o200k", "tiktoken:o200k_base", "exact", "strict_verified"),
    "cl100k_base": TokenizerFamily("cl100k_base", "OpenAI cl100k", "tiktoken:cl100k_base", "exact", "strict_verified"),
    "llama-3": TokenizerFamily("llama-3", "Llama 3 family", "NousResearch/Meta-Llama-3-8B", "exact", "strict_verified"),
    "mistral": TokenizerFamily("mistral", "Mistral family", "mistralai/Mistral-7B-v0.1", "exact", "strict_verified"),
    "qwen-2.5": TokenizerFamily("qwen-2.5", "Qwen 2.5 family", "Qwen/Qwen2.5-7B", "exact", "strict_verified"),
    "gemma-2": TokenizerFamily("gemma-2", "Gemma family", "microsoft/phi-2", "proxy", "proxy"),
    "command-r": TokenizerFamily("command-r", "Command R family", "bigscience/bloom-560m", "proxy", "proxy"),
    "gpt2": TokenizerFamily("gpt2", "GPT-2 legacy", "gpt2", "exact", "strict_verified"),
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
    "google/gemma-2-9b-it": ModelMapping("google/gemma-2-9b-it", "gemma-2", "Gemma 2 9B IT", "proxy", "proxy", "Tokenizer proxy until exact Gemma tokenizer is wired"),
    "google/gemma-3-27b-it:free": ModelMapping("google/gemma-3-27b-it:free", "gemma-2", "Gemma 3 27B IT (Free)", "proxy", "proxy", "Tokenizer proxy until exact Gemma tokenizer is wired"),
    "qwen/qwen-2.5-7b-instruct:free": ModelMapping("qwen/qwen-2.5-7b-instruct:free", "qwen-2.5", "Qwen 2.5 7B Instruct (Free)", "exact", "strict_verified", "Static exact mapping"),
    "qwen/qwen-2.5-72b-instruct": ModelMapping("qwen/qwen-2.5-72b-instruct", "qwen-2.5", "Qwen 2.5 72B Instruct", "exact", "strict_verified", "Static exact mapping"),
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
    for mapping in MODEL_MAPPINGS.values():
        if mapping.mapping_quality == "proxy" and not include_proxy:
            continue
        resolved = resolve_model(mapping.model_id)
        pricing = resolved["pricing"]
        entries.append({
            "model_id": mapping.model_id,
            "label": resolved["label"],
            "tokenizer_key": resolved["tokenizer_key"],
            "mapping_quality": resolved["mapping_quality"],
            "provenance": resolved["provenance"],
            "input_per_million": pricing["input_per_million"],
            "output_per_million": pricing["output_per_million"],
            "context_window": pricing["context_window"],
            "latency_ms": None,
            "throughput_tps": None,
            "source": resolved["source"],
        })
    return sorted(entries, key=lambda entry: entry["label"].lower())


def build_tokenizer_catalog(
    *,
    include_proxy: bool = False,
) -> list[dict]:
    """Return tokenizer-first catalog rows with attached free model examples."""
    rows: list[dict] = []

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
            free_models.append({
                "model_id": mapping.model_id,
                "label": mapping.label,
                "mapping_quality": mapping.mapping_quality,
                "provenance": mapping.provenance,
                "runtime_badge": "Runnable here for free",
                "mapping_badge": "Exact tokenizer mapping" if mapping.mapping_quality == "exact" else "Proxy mapping",
            })

        rows.append({
            "tokenizer_key": family.key,
            "label": family.label,
            "tokenizer_source": family.tokenizer_source,
            "mapping_quality": family.mapping_quality,
            "provenance": family.provenance,
            "free_models": sorted(free_models, key=lambda model: model["label"].lower()),
            "aa_matches": [],
        })

    return sorted(rows, key=lambda row: row["label"].lower())
