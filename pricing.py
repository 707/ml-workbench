"""Model pricing data for Token Tax Workbench.

Pricing is **illustrative and approximate** — intended to show relative
cost differences across models and languages, not billing-accurate numbers.
Update MODEL_PRICING and LAST_UPDATED when prices change.

Live pricing from OpenRouter is cached in _pricing_cache and merged with
static MODEL_PRICING.  Static entries (tokenizer keys) take precedence.
"""

from datetime import datetime, timezone

LAST_UPDATED = "2026-03-25"

# ---------------------------------------------------------------------------
# Live pricing cache (populated by refresh_from_openrouter)
# ---------------------------------------------------------------------------
_pricing_cache: dict[str, dict] = {}
_last_refreshed: datetime | None = None
_last_refresh_error: str = ""

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
    "gemma-2": {
        "input_per_million": 0.07,
        "output_per_million": 0.07,
        "context_window": 8192,
        "label": "Phi-2 (Gemma proxy)",
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

    Checks static MODEL_PRICING first (tokenizer keys), then the live
    pricing cache (OpenRouter model IDs).

    Args:
        model_name: Key in MODEL_PRICING or cached OpenRouter model ID.

    Returns:
        Dict with input_per_million, output_per_million, context_window, label.

    Raises:
        KeyError: If model_name is not found in either source.
    """
    if model_name in MODEL_PRICING:
        return MODEL_PRICING[model_name]
    if model_name in _pricing_cache:
        return _pricing_cache[model_name]
    raise KeyError(
        f"unknown model: '{model_name}'. "
        f"Choose from {sorted(set(MODEL_PRICING) | set(_pricing_cache))}"
    )


def available_models() -> list[str]:
    """Return a sorted list of model names with pricing data."""
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
    try:
        from openrouter import fetch_models

        models = fetch_models()
        for m in models:
            model_id = m.get("id", "")
            pricing = m.get("pricing", {})
            prompt_per_token = float(pricing.get("prompt", 0))
            completion_per_token = float(pricing.get("completion", 0))
            _pricing_cache[model_id] = {
                "input_per_million": prompt_per_token * 1_000_000,
                "output_per_million": completion_per_token * 1_000_000,
                "context_window": m.get("context_length", 0),
                "label": m.get("name", model_id),
            }
        _last_refreshed = datetime.now(timezone.utc)
        _last_refresh_error = ""
    except Exception as exc:
        _last_refresh_error = str(exc)
        # static fallback remains available


def get_last_refreshed() -> datetime | None:
    """Return the timestamp of the last successful OpenRouter refresh."""
    return _last_refreshed


def get_last_refresh_error() -> str:
    """Return the last refresh error, if any."""
    return _last_refresh_error


def pricing_status() -> dict:
    """Return freshness and error metadata for pricing/cached model data."""
    return {
        "last_updated": LAST_UPDATED,
        "last_refreshed": _last_refreshed.isoformat() if _last_refreshed else None,
        "last_refresh_error": _last_refresh_error or None,
        "cache_size": len(_pricing_cache),
    }


def _clear_cache() -> None:
    """Reset the live pricing cache (for testing)."""
    global _last_refreshed, _last_refresh_error
    _pricing_cache.clear()
    _last_refreshed = None
    _last_refresh_error = ""
