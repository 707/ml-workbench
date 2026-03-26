"""Token Tax computation module.

Pure computation functions for multilingual tokenization cost analysis.
No Gradio imports — UI lives in token_tax_ui.py.
"""

import csv

from tokenizer import (
    get_tokenizer,
    tokenize_text,
    relative_tokenization_cost,
    byte_premium,
    context_window_usage,
    quality_risk_level,
)
from pricing import get_pricing


# ---------------------------------------------------------------------------
# Sample phrases for portfolio analysis (GH-6)
# ---------------------------------------------------------------------------

SAMPLE_PHRASES: dict[str, str] = {
    "en": "The quick brown fox jumps over the lazy dog near the riverbank.",
    "zh": "快速的棕色狐狸跳过了河边那只懒惰的狗。",
    "ar": "القطة السوداء تجلس على السياج وتراقب الطيور في الحديقة.",
    "hi": "तेज़ भूरी लोमड़ी आलसी कुत्ते के ऊपर से कूद गई।",
    "ja": "素早い茶色の狐が怠けた犬の上を飛び越えました。",
    "ko": "빠른 갈색 여우가 게으른 개 위로 뛰어넘었습니다.",
    "fr": "Le renard brun rapide saute par-dessus le chien paresseux près de la rivière.",
    "de": "Der schnelle braune Fuchs springt über den faulen Hund am Flussufer.",
    "es": "El rápido zorro marrón salta sobre el perro perezoso cerca del río.",
    "pt": "A rápida raposa marrom pula sobre o cachorro preguiçoso perto do rio.",
    "ru": "Быстрая коричневая лиса перепрыгнула через ленивую собаку у реки.",
    "th": "สุนัขจิ้งจอกสีน้ำตาลตัวเร็วกระโดดข้ามสุนัขขี้เกียจ",
    "vi": "Con cáo nâu nhanh nhẹn nhảy qua con chó lười biếng gần bờ sông.",
    "bn": "দ্রুত বাদামি শিয়াল অলস কুকুরের উপর দিয়ে লাফিয়ে গেল।",
    "ta": "வேகமான பழுப்பு நரி சோம்பேறி நாயின் மீது குதித்தது.",
    "tr": "Hızlı kahverengi tilki tembel köpeğin üzerinden atladı.",
    "pl": "Szybki brązowy lis przeskoczył nad leniwym psem nad rzeką.",
    "uk": "Швидка руда лисиця перестрибнула через лінивого собаку біля річки.",
    "sw": "Mbweha wa kahawia mwepesi aliruka juu ya mbwa mvivu kando ya mto.",
    "id": "Rubah coklat yang cepat melompati anjing pemalas di dekat sungai.",
}


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
            "Text is in English — tokenization is near-optimal for all models."
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


# ---------------------------------------------------------------------------
# CSV parsing and portfolio analysis (GH-6)
# ---------------------------------------------------------------------------

_REQUIRED_CSV_COLUMNS = {"language", "request_count", "avg_chars"}


def parse_traffic_csv(file_path: str) -> list[dict]:
    """Parse a traffic CSV file.

    Required columns: language, request_count, avg_chars.
    Extra columns are ignored.

    Args:
        file_path: Path to the CSV file.

    Returns:
        List of dicts with language (str), request_count (int), avg_chars (int).

    Raises:
        ValueError: If required columns are missing or data is invalid.
    """
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return []
        missing = _REQUIRED_CSV_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV missing required columns: {sorted(missing)}")

        rows = []
        for i, row in enumerate(reader, start=2):
            try:
                rows.append({
                    "language": row["language"].strip(),
                    "request_count": int(row["request_count"]),
                    "avg_chars": int(row["avg_chars"]),
                })
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Row {i}: invalid data — {exc}") from exc
        return rows


def portfolio_analysis(
    traffic_data: list[dict],
    model_name: str,
    english_tokenizer_name: str = "gpt2",
) -> dict:
    """Analyze token tax exposure across a portfolio of languages.

    Uses SAMPLE_PHRASES to approximate tokenization cost per language.

    Args:
        traffic_data:            Output of parse_traffic_csv.
        model_name:              Tokenizer/model to analyze.
        english_tokenizer_name:  Tokenizer for English baseline (default gpt2).

    Returns:
        Dict with:
        - total_monthly_cost: float
        - token_tax_exposure: float (weighted average RTC)
        - languages: list of per-language dicts
    """
    if not traffic_data:
        return {
            "total_monthly_cost": 0.0,
            "token_tax_exposure": 1.0,
            "languages": [],
        }

    tok = get_tokenizer(model_name)
    pricing = get_pricing(model_name)
    english_phrase = SAMPLE_PHRASES["en"]
    eng_tokens = tokenize_text(english_phrase, tok)
    eng_count = len(eng_tokens)

    total_requests = sum(d["request_count"] for d in traffic_data)
    entries = []

    for row in traffic_data:
        lang = row["language"]
        phrase = SAMPLE_PHRASES.get(lang, english_phrase)
        tokens = tokenize_text(phrase, tok)
        token_count = len(tokens)
        rtc = relative_tokenization_cost(token_count, eng_count)
        traffic_share = row["request_count"] / total_requests if total_requests else 0.0

        proj = cost_projection(
            token_count,
            pricing["input_per_million"],
            row["request_count"],
            row["avg_chars"],
        )

        entries.append({
            "language": lang,
            "traffic_share": traffic_share,
            "token_count": token_count,
            "rtc": rtc,
            "monthly_cost": proj["monthly_cost"],
            "cost_share": 0.0,  # computed below
            "tax_ratio": rtc,
        })

    total_cost = sum(e["monthly_cost"] for e in entries)
    for e in entries:
        e["cost_share"] = e["monthly_cost"] / total_cost if total_cost else (
            1.0 / len(entries) if entries else 0.0
        )

    weighted_rtc = sum(
        e["rtc"] * e["traffic_share"] for e in entries
    )

    return {
        "total_monthly_cost": total_cost,
        "token_tax_exposure": weighted_rtc,
        "languages": entries,
    }
