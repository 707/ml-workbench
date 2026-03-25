"""Token Tax computation module.

Pure computation functions for multilingual tokenization cost analysis.
No Gradio imports — UI lives in token_tax_ui.py.
"""

from tokenizer import (
    get_tokenizer,
    tokenize_text,
    relative_tokenization_cost,
    byte_premium,
    context_window_usage,
    quality_risk_level,
)
from pricing import get_pricing


def analyze_text_across_models(
    text: str,
    english_text: str | None,
    model_names: list[str],
) -> list[dict]:
    """Analyze token tax for text across multiple tokenizer/model families.

    Args:
        text:         Source text (any language).
        english_text: English equivalent for RTC computation. None = skip RTC.
        model_names:  List of model keys (must exist in SUPPORTED_TOKENIZERS
                      and MODEL_PRICING).

    Returns:
        List of dicts, one per model, each with:
        model, token_count, rtc, byte_premium, context_usage,
        risk_level, cost_per_million, monthly_cost.
    """
    results = []
    for model in model_names:
        tok = get_tokenizer(model)
        tokens = tokenize_text(text, tok)
        token_count = len(tokens)
        pricing = get_pricing(model)
        window = pricing["context_window"]

        if english_text is not None:
            eng_tokens = tokenize_text(english_text, tok)
            eng_count = len(eng_tokens)
            rtc = relative_tokenization_cost(token_count, eng_count)
            bp = byte_premium(text, english_text)
        else:
            rtc = 1.0
            bp = 1.0

        results.append({
            "model": model,
            "token_count": token_count,
            "rtc": rtc,
            "byte_premium": bp,
            "context_usage": context_window_usage(token_count, window),
            "risk_level": quality_risk_level(rtc),
            "cost_per_million": pricing["input_per_million"],
            "monthly_cost": 0.0,
        })

    return results


def cost_projection(
    token_count: int,
    price_per_million: float,
    monthly_requests: int,
    avg_tokens_per_request: int,
) -> dict:
    """Project monthly and annual cost for a token workload.

    Args:
        token_count:            Tokens in the sample (informational).
        price_per_million:      Cost per 1M input tokens.
        monthly_requests:       Estimated monthly request volume.
        avg_tokens_per_request: Average tokens per request.

    Returns:
        Dict with monthly_cost and annual_cost (floats).
    """
    monthly = float(monthly_requests * avg_tokens_per_request * price_per_million) / 1_000_000
    return {
        "monthly_cost": monthly,
        "annual_cost": monthly * 12,
    }


def generate_recommendations(
    analysis_results: list[dict],
    language: str,
) -> str:
    """Generate actionable recommendation text from analysis results.

    Args:
        analysis_results: Output of analyze_text_across_models.
        language:         Detected language code (e.g. "ar", "en").

    Returns:
        Markdown-formatted recommendation string.
    """
    if not analysis_results:
        return "No models analyzed. Select at least one model to see recommendations."

    # Find cheapest (by cost_per_million, break ties by lower RTC)
    cheapest = min(analysis_results, key=lambda r: (r["cost_per_million"], r["rtc"]))

    # Find most efficient (lowest RTC)
    most_efficient = min(analysis_results, key=lambda r: r["rtc"])

    lines = []

    if language == "en":
        lines.append(
            f"Text is in English — tokenization is near-optimal for all models."
        )
    else:
        lines.append(
            f"**Most efficient tokenizer for this text:** {most_efficient['model']} "
            f"(RTC: {most_efficient['rtc']:.2f}x vs English)"
        )

    if cheapest["model"] != most_efficient["model"]:
        lines.append(
            f"**Cheapest model:** {cheapest['model']} "
            f"(${cheapest['cost_per_million']:.4f}/1M tokens)"
        )

    # Flag high-risk models
    risky = [r for r in analysis_results if r["risk_level"] in ("high", "severe")]
    if risky:
        names = ", ".join(r["model"] for r in risky)
        levels = ", ".join(r["risk_level"] for r in risky)
        lines.append(
            f"**Quality risk warning:** {names} — {levels} risk level. "
            f"Higher token inflation may correlate with lower accuracy."
        )

    return "\n\n".join(lines)
