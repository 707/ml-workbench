"""Model pricing data for Token Tax Calculator.

Pricing is **illustrative and approximate** — intended to show relative
cost differences across models and languages, not billing-accurate numbers.
Update MODEL_PRICING and LAST_UPDATED when prices change.
"""

LAST_UPDATED = "2026-03-25"

MODEL_PRICING: dict[str, dict] = {
    "gpt2": {
        "input_per_million": 0.0,
        "output_per_million": 0.0,
        "context_window": 1024,
        "label": "GPT-2",
    },
    "llama-3": {
        "input_per_million": 0.05,
        "output_per_million": 0.08,
        "context_window": 8192,
        "label": "Llama 3 8B",
    },
    "mistral": {
        "input_per_million": 0.04,
        "output_per_million": 0.04,
        "context_window": 32768,
        "label": "Mistral 7B v0.1",
    },
}


def get_pricing(model_name: str) -> dict:
    """Look up pricing data for a model.

    Args:
        model_name: Key in MODEL_PRICING (must match SUPPORTED_TOKENIZERS keys).

    Returns:
        Dict with input_per_million, output_per_million, context_window, label.

    Raises:
        KeyError: If model_name is not in MODEL_PRICING.
    """
    return MODEL_PRICING[model_name]


def available_models() -> list[str]:
    """Return a sorted list of model names with pricing data."""
    return sorted(MODEL_PRICING.keys())
