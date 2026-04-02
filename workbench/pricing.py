"""Model pricing data for Token Tax Workbench.

Pricing is **illustrative and approximate** — intended to show relative
cost differences across models and languages, not billing-accurate numbers.
Update MODEL_PRICING and LAST_UPDATED when prices change.

Live pricing from OpenRouter is cached in _pricing_cache and merged with
static MODEL_PRICING.  Static entries (tokenizer keys) take precedence.
"""

import threading
from datetime import datetime, timezone

from workbench.diagnostics import log_event

LAST_UPDATED = "2026-03-25"

# ---------------------------------------------------------------------------
# Live pricing cache (populated by refresh_from_openrouter)
# ---------------------------------------------------------------------------
_pricing_cache: dict[str, dict] = {}
_last_refreshed: datetime | None = None
_last_refresh_error: str = ""
_pricing_lock = threading.Lock()

MODEL_PRICING: dict[str, dict] = {
    "o200k_base": {
        "input_per_million": 2.50,
        "output_per_million": 10.00,
        "context_window": 128000,
        "label": "GPT-4o (o200k)",
    },
    "cl100k_base": {
        "input_per_million": 10.00,
        "output_per_million": 30.00,
        "context_window": 128000,
        "label": "GPT-4 Turbo (cl100k)",
    },
    "llama-3": {
        "input_per_million": 0.05,
        "output_per_million": 0.08,
        "context_window": 128000,
        "label": "Llama 3 8B",
    },
    "mistral": {
        "input_per_million": 0.04,
        "output_per_million": 0.04,
        "context_window": 32768,
        "label": "Mistral 7B v0.1",
    },
    "qwen-2.5": {
        "input_per_million": 0.15,
        "output_per_million": 0.15,
        "context_window": 131072,
        "label": "Qwen 2.5 7B",
    },
    "qwen3-next": {
        "input_per_million": 0.20,
        "output_per_million": 0.40,
        "context_window": 262144,
        "label": "Qwen3 Next 80B A3B",
    },
    "qwen3-coder": {
        "input_per_million": 0.30,
        "output_per_million": 0.60,
        "context_window": 262144,
        "label": "Qwen3 Coder 480B A35B",
    },
    "gpt-oss": {
        "input_per_million": 0.12,
        "output_per_million": 0.30,
        "context_window": 131072,
        "label": "OpenAI gpt-oss",
    },
    "glm-4.5-air": {
        "input_per_million": 0.12,
        "output_per_million": 0.28,
        "context_window": 131072,
        "label": "GLM 4.5 Air",
    },
    "nemotron-3-nano-30b": {
        "input_per_million": 0.08,
        "output_per_million": 0.18,
        "context_window": 256000,
        "label": "Nemotron 3 Nano 30B A3B",
    },
    "nemotron-3-super": {
        "input_per_million": 0.25,
        "output_per_million": 0.60,
        "context_window": 262144,
        "label": "Nemotron 3 Super 120B A12B",
    },
    "nemotron-nano-9b-v2": {
        "input_per_million": 0.04,
        "output_per_million": 0.10,
        "context_window": 128000,
        "label": "Nemotron Nano 9B V2",
    },
    "trinity-large": {
        "input_per_million": 0.20,
        "output_per_million": 0.45,
        "context_window": 131072,
        "label": "Trinity Large Preview",
    },
    "trinity-mini": {
        "input_per_million": 0.06,
        "output_per_million": 0.15,
        "context_window": 131072,
        "label": "Trinity Mini",
    },
    "gemma-2": {
        "input_per_million": 0.07,
        "output_per_million": 0.07,
        "context_window": 8192,
        "label": "Gemma 2 2B (unsloth/gemma-2-2b)",
    },
    "command-r": {
        "input_per_million": 0.15,
        "output_per_million": 0.60,
        "context_window": 128000,
        "label": "BLOOM (Command R proxy)",
    },
    "gpt2": {
        "input_per_million": 0.0,
        "output_per_million": 0.0,
        "context_window": 1024,
        "label": "GPT-2 (legacy)",
    },
}


def get_pricing(model_name: str) -> dict:
    """Look up pricing data for a model.

    Checks live pricing cache first (freshest data), then falls back
    to static MODEL_PRICING (tokenizer keys).

    Args:
        model_name: Key in MODEL_PRICING or cached OpenRouter model ID.

    Returns:
        Dict with input_per_million, output_per_million, context_window, label.

    Raises:
        KeyError: If model_name is not found in either source.
    """
    with _pricing_lock:
        if model_name in _pricing_cache:
            return _pricing_cache[model_name]
    if model_name in MODEL_PRICING:
        return MODEL_PRICING[model_name]
    with _pricing_lock:
        raise KeyError(
            f"unknown model: '{model_name}'. "
            f"Choose from {sorted(set(MODEL_PRICING) | set(_pricing_cache))}"
        )


def available_models() -> list[str]:
    """Return a sorted list of model names with pricing data."""
    with _pricing_lock:
        return sorted(set(MODEL_PRICING.keys()) | set(_pricing_cache.keys()))


# ---------------------------------------------------------------------------
# OpenRouter live pricing
# ---------------------------------------------------------------------------


def refresh_from_openrouter() -> None:
    """Fetch live pricing from OpenRouter and populate _pricing_cache.

    On failure, logs the error and leaves the cache unchanged — static
    MODEL_PRICING remains available as fallback.
    """
    global _last_refreshed, _last_refresh_error
    log_event("catalog.refresh.start", "Refreshing OpenRouter catalog pricing")
    try:
        from workbench.openrouter import fetch_models

        models = fetch_models()
        new_cache: dict[str, dict] = {}
        for m in models:
            model_id = m.get("id", "")
            pricing = m.get("pricing", {})
            prompt_per_token = float(pricing.get("prompt", 0))
            completion_per_token = float(pricing.get("completion", 0))
            new_cache[model_id] = {
                "input_per_million": prompt_per_token * 1_000_000,
                "output_per_million": completion_per_token * 1_000_000,
                "context_window": m.get("context_length", 0),
                "label": m.get("name", model_id),
            }
        with _pricing_lock:
            _pricing_cache.clear()
            _pricing_cache.update(new_cache)
            _last_refreshed = datetime.now(timezone.utc)
            _last_refresh_error = ""
        log_event(
            "catalog.refresh.success",
            "OpenRouter pricing refresh succeeded",
            model_count=len(models),
            cache_size=len(_pricing_cache),
        )
    except Exception as exc:
        with _pricing_lock:
            _last_refresh_error = str(exc)
        log_event(
            "catalog.refresh.error",
            "OpenRouter pricing refresh failed",
            error=str(exc),
        )
        # static fallback remains available


def get_last_refreshed() -> datetime | None:
    """Return the timestamp of the last successful OpenRouter refresh."""
    with _pricing_lock:
        return _last_refreshed


def get_last_refresh_error() -> str:
    """Return the last refresh error, if any."""
    with _pricing_lock:
        return _last_refresh_error


def pricing_status() -> dict:
    """Return freshness and error metadata for pricing/cached model data."""
    with _pricing_lock:
        return {
            "last_updated": LAST_UPDATED,
            "last_refreshed": _last_refreshed.isoformat() if _last_refreshed else None,
            "last_refresh_error": _last_refresh_error or None,
            "cache_size": len(_pricing_cache),
        }


def pricing_age_days() -> int | None:
    """Return days since last refresh, or None if never refreshed."""
    with _pricing_lock:
        if _last_refreshed is None:
            return None
        delta = datetime.now(timezone.utc) - _last_refreshed
        return delta.days


def _clear_cache() -> None:
    """Reset the live pricing cache (for testing)."""
    global _last_refreshed, _last_refresh_error
    with _pricing_lock:
        _pricing_cache.clear()
        _last_refreshed = None
        _last_refresh_error = ""
