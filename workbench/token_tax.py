"""Token Tax computation module."""

from __future__ import annotations

import csv
import io
import json
from statistics import median, quantiles
from typing import Callable

from workbench.corpora import DEFAULT_BENCHMARK_LANGUAGES, fetch_corpus_samples, list_corpora
from workbench.diagnostics import log_event
from workbench.model_registry import (
    artificial_analysis_status,
    build_catalog_entries,
    list_tokenizer_families,
    resolve_selection,
)
from workbench.pricing import get_pricing, pricing_status, refresh_from_openrouter
from workbench.provenance import (
    provenance_badge,
    provenance_description,
    provenance_visible,
)
from workbench.tokenizer import (
    byte_premium,
    context_window_usage,
    fragmentation_ratio,
    get_tokenizer,
    list_tokenizer_snapshot_status,
    quality_risk_level,
    relative_tokenization_cost,
    tokenize_text,
)
from workbench.tokenizer_registry import continuation_style_map

# ---------------------------------------------------------------------------
# Demo fixtures retained for backwards-compatible examples
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


# Average characters per token for the legacy portfolio estimator.
# English-centric BPE heuristic (~4 chars/token). Underestimates for CJK/Indic,
# overestimates for inflected European languages. Superseded by corpus-based
# benchmark_corpus() and scenario_analysis() for production cost projections.
LEGACY_CHARS_PER_TOKEN: float = 4.0


# ---------------------------------------------------------------------------
# Existing demo computations retained for compatibility
# ---------------------------------------------------------------------------


def analyze_text_across_models(
    text: str,
    english_text: str | None,
    model_names: list[str],
) -> list[dict]:
    """Analyze token tax for text across multiple tokenizer/model families."""
    results = []
    for model_name in model_names:
        selection = resolve_selection(model_name)
        tokenizer_key = selection["tokenizer_key"]
        tok = get_tokenizer(tokenizer_key)
        tokens = tokenize_text(text, tok)
        token_count = len(tokens)
        pricing = get_pricing(tokenizer_key)
        window = pricing["context_window"]

        if english_text is not None:
            eng_tokens = tokenize_text(english_text, tok)
            eng_count = len(eng_tokens)
            rtc = relative_tokenization_cost(token_count, eng_count)
            bp = byte_premium(text, english_text)
        else:
            rtc = 1.0
            bp = 1.0

        frag = fragmentation_ratio(text, tok)

        results.append({
            "model": model_name,
            "tokenizer_key": tokenizer_key,
            "token_count": token_count,
            "token_fertility": frag["ratio"],
            "rtc": rtc,
            "byte_premium": bp,
            "context_usage": context_window_usage(token_count, window),
            "risk_level": quality_risk_level(rtc),
            "cost_per_million": pricing["input_per_million"],
            "provenance": selection["provenance"],
            "mapping_quality": selection["mapping_quality"],
        })

    return results


def run_benchmark(
    languages: list[str] | None,
    model_names: list[str],
) -> list[dict]:
    """Zero-input demo benchmark using SAMPLE_PHRASES across selected models."""
    if not model_names:
        return []

    langs = languages if languages is not None else list(SAMPLE_PHRASES.keys())
    english_phrase = SAMPLE_PHRASES["en"]
    results = []

    eng_counts: dict[str, int] = {}
    for model_name in model_names:
        tokenizer_key = resolve_selection(model_name)["tokenizer_key"]
        tok = get_tokenizer(tokenizer_key)
        eng_counts[model_name] = len(tokenize_text(english_phrase, tok))

    for lang in langs:
        phrase = SAMPLE_PHRASES.get(lang, english_phrase)
        model_entries = []
        for model_name in model_names:
            tokenizer_key = resolve_selection(model_name)["tokenizer_key"]
            tok = get_tokenizer(tokenizer_key)
            token_count = len(tokenize_text(phrase, tok))
            rtc = relative_tokenization_cost(token_count, eng_counts[model_name])
            model_entries.append({
                "model": model_name,
                "token_count": token_count,
                "rtc": rtc,
                "risk_level": quality_risk_level(rtc),
            })
        results.append({"language": lang, "models": model_entries})

    return results


def benchmark_all(
    languages: list[str],
    model_names: list[str],
) -> dict[tuple[str, str], dict]:
    """Run SAMPLE_PHRASES through all models for demo compatibility."""
    english_phrase = SAMPLE_PHRASES["en"]
    results = {}

    for model_name in model_names:
        tokenizer_key = resolve_selection(model_name)["tokenizer_key"]
        tok = get_tokenizer(tokenizer_key)
        eng_count = len(tokenize_text(english_phrase, tok))

        for lang in languages:
            phrase = SAMPLE_PHRASES.get(lang, english_phrase)
            token_count = len(tokenize_text(phrase, tok))
            rtc = relative_tokenization_cost(token_count, eng_count)
            results[(lang, model_name)] = {"rtc": rtc, "token_count": token_count}

    return results


def cost_projection(
    token_count: int,
    price_per_million: float,
    monthly_requests: int,
    avg_tokens_per_request: int,
) -> dict:
    """Project monthly and annual cost for a token workload."""
    monthly = float(monthly_requests * avg_tokens_per_request * price_per_million) / 1_000_000
    return {"monthly_cost": monthly, "annual_cost": monthly * 12}


_MITIGATION_BANDS = {
    "low": [],
    "moderate": [
        "Expanded multilingual vocabularies are worth checking for this language band.",
    ],
    "high": [
        "Significant token tax. Compare exact tokenizer families before picking deployable models.",
        "Review post-hoc vocabulary expansion work such as arXiv:2601.13328.",
    ],
    "severe": [
        "Severe fragmentation. Consider language-specific or vocabulary-augmented alternatives.",
        "Inspect orthography/normalization effects before treating the tokenizer as the only bottleneck.",
    ],
}


def generate_recommendations(
    analysis_results: list[dict],
    language: str,
) -> dict:
    """Generate structured interpretation notes from analysis results."""
    empty = {
        "best_model": {"name": "", "reason": ""},
        "savings_opportunity": {"amount": "", "vs_model": ""},
        "risk_warnings": [],
        "mitigations": [],
        "executive_summary": "No models analyzed.",
    }
    if not analysis_results:
        return empty

    most_efficient = min(analysis_results, key=lambda r: r["rtc"])
    cheapest = min(analysis_results, key=lambda r: (r["cost_per_million"], r["rtc"]))
    worst = max(analysis_results, key=lambda r: r["rtc"])

    best = {
        "name": most_efficient["model"] if language != "en" else cheapest["model"],
        "reason": (
            f"Lowest RTC ({most_efficient['rtc']:.2f}x)."
            if language != "en"
            else "English text is near-optimal; cheapest visible option wins."
        ),
    }

    if len(analysis_results) > 1 and cheapest["model"] != worst["model"]:
        savings = {
            "amount": f"${worst['cost_per_million'] - cheapest['cost_per_million']:.4f}/1M input tokens",
            "vs_model": worst["model"],
        }
    else:
        savings = {"amount": "", "vs_model": ""}

    risk_warnings = [
        {"model": r["model"], "level": r["risk_level"], "rtc": f"{r['rtc']:.2f}x"}
        for r in analysis_results
        if r["risk_level"] in ("high", "severe")
    ]

    mitigations = []
    if language != "en":
        mitigations = list(_MITIGATION_BANDS.get(worst["risk_level"], []))

    summary = (
        f"Visible spread ranges from {most_efficient['rtc']:.2f}x to {worst['rtc']:.2f}x RTC."
        if language != "en"
        else f"English baseline across the visible set is cheapest at {cheapest['model']}."
    )

    return {
        "best_model": best,
        "savings_opportunity": savings,
        "risk_warnings": risk_warnings,
        "mitigations": mitigations,
        "executive_summary": summary,
    }


_EXPORT_COLUMNS = [
    "model",
    "tokenizer_key",
    "token_count",
    "token_fertility",
    "rtc",
    "byte_premium",
    "context_usage",
    "risk_level",
    "cost_per_million",
    "provenance",
]


def export_csv(results: list[dict]) -> str:
    """Export analysis results as CSV string."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_EXPORT_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for result in results:
        writer.writerow(result)
    return buf.getvalue()


def export_json(results: list[dict]) -> str:
    """Export analysis results as JSON string."""
    filtered = [{k: r[k] for k in _EXPORT_COLUMNS if k in r} for r in results]
    return json.dumps(filtered, indent=2)


_REQUIRED_CSV_COLUMNS = {"language", "request_count", "avg_chars"}


def parse_traffic_csv(file_path: str) -> list[dict]:
    """Parse a traffic CSV file."""
    with open(file_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
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
    """Analyze token tax exposure across a portfolio of languages."""
    if not traffic_data:
        return {
            "total_monthly_cost": 0.0,
            "token_tax_exposure": 1.0,
            "languages": [],
            "estimation_method": "heuristic",
        }

    tokenizer_key = resolve_selection(model_name)["tokenizer_key"]
    tok = get_tokenizer(tokenizer_key)
    pricing = get_pricing(tokenizer_key)
    english_phrase = SAMPLE_PHRASES["en"]
    eng_count = len(tokenize_text(english_phrase, tok))

    total_requests = sum(d["request_count"] for d in traffic_data)
    entries = []

    for row in traffic_data:
        lang = row["language"]
        phrase = SAMPLE_PHRASES.get(lang, english_phrase)
        token_count = len(tokenize_text(phrase, tok))
        rtc = relative_tokenization_cost(token_count, eng_count)
        avg_tokens_est = max(int(round(row["avg_chars"] / LEGACY_CHARS_PER_TOKEN)), 1)
        proj = cost_projection(
            token_count,
            pricing["input_per_million"],
            row["request_count"],
            max(int(round(avg_tokens_est * rtc)), 1),
        )
        traffic_share = row["request_count"] / total_requests if total_requests else 0.0
        entries.append({
            "language": lang,
            "traffic_share": traffic_share,
            "token_count": token_count,
            "rtc": rtc,
            "monthly_cost": proj["monthly_cost"],
            "cost_share": 0.0,
            "tax_ratio": rtc,
        })

    total_cost = sum(entry["monthly_cost"] for entry in entries)
    for entry in entries:
        if total_cost:
            entry["cost_share"] = entry["monthly_cost"] / total_cost
        else:
            entry["cost_share"] = 1.0 / len(entries) if entries else 0.0

    weighted_rtc = sum(entry["rtc"] * entry["traffic_share"] for entry in entries)

    return {
        "total_monthly_cost": total_cost,
        "token_tax_exposure": weighted_rtc,
        "languages": entries,
        "estimation_method": "heuristic",
    }


# ---------------------------------------------------------------------------
# Token Tax Workbench v2 helpers
# ---------------------------------------------------------------------------


def serialize_table(rows: list[dict], columns: list[str]) -> dict:
    """Convert row dicts to gr.DataFrame-compatible shape."""
    data = [[row.get(column) for column in columns] for row in rows]
    return {"headers": columns, "data": data}


def _safe_median(values: list[float | int | None]) -> float | None:
    filtered = [float(value) for value in values if isinstance(value, (int, float))]
    if not filtered:
        return None
    return float(median(filtered))


def _safe_iqr(values: list[float | int | None]) -> float | None:
    """Return the interquartile range of numeric values, or None if too few."""
    filtered = [float(v) for v in values if isinstance(v, (int, float))]
    if len(filtered) < 4:
        return None
    q1, _, q3 = quantiles(filtered, n=4)
    return q3 - q1


def _unit_count(text: str) -> int:
    if not text:
        return 0
    cjk_thai_count = sum(1 for ch in text if (
        '\u4e00' <= ch <= '\u9fff' or
        '\u3040' <= ch <= '\u309f' or
        '\u30a0' <= ch <= '\u30ff' or
        '\uac00' <= ch <= '\ud7af' or
        '\u0e00' <= ch <= '\u0e7f'
    ))
    if cjk_thai_count > len(text) * 0.3:
        return len(text)
    return len(text.split())


def _token_script(token_text: str) -> str:
    for char in token_text:
        code = ord(char)
        if 0x0600 <= code <= 0x06FF:
            return "Arabic"
        if 0x0900 <= code <= 0x097F:
            return "Devanagari"
        if 0x3040 <= code <= 0x30FF or 0x4E00 <= code <= 0x9FFF:
            return "CJK"
        if 0x0400 <= code <= 0x04FF:
            return "Cyrillic"
        if ("A" <= char <= "Z") or ("a" <= char <= "z"):
            return "Latin"
    return "Other"


def _sample_metrics(
    text: str,
    english_text: str | None,
    tokenizer_key: str,
    *,
    tokenizer=None,
    english_baseline_token_count: float | None = None,
) -> dict:
    tok = tokenizer or get_tokenizer(tokenizer_key)
    token_rows = tokenize_text(text, tok)
    token_count = len(token_rows)
    unit_count = _unit_count(text)
    fertility = (token_count / unit_count) if unit_count else 0.0
    text_bytes = len(text.encode("utf-8"))
    bytes_per_token = float(text_bytes) / token_count if token_count else 0.0
    token_texts = [token["token"] for token in token_rows]
    unique_tokens = len(set(token_texts))
    continued_count = sum(1 for token_text in token_texts if _is_continued_token(token_text, tokenizer_key))
    result = {
        "token_count": token_count,
        "token_fertility": fertility,
        "bytes_per_token": bytes_per_token,
        "unique_tokens": unique_tokens,
        "continued_word_rate": (continued_count / token_count) if token_count else 0.0,
        "token_texts": token_texts,
        "english_baseline_ratio": None,
    }
    if english_text:
        english_token_count = len(tokenize_text(english_text, tok))
        rtc = relative_tokenization_cost(token_count, english_token_count)
        result["rtc"] = rtc
        result["byte_premium"] = byte_premium(text, english_text)
        result["risk_level"] = quality_risk_level(rtc)
    else:
        result["rtc"] = None
        result["byte_premium"] = None
        result["risk_level"] = "low"
    if english_baseline_token_count:
        result["english_baseline_ratio"] = relative_tokenization_cost(token_count, english_baseline_token_count)
    return result


_PUNCTUATION = frozenset(".,;:!?()" + "[]{}\"'")
_CONTINUATION_STYLES = continuation_style_map()


def _is_continued_token(token_text: str, tokenizer_key: str) -> bool:
    """Return True when token_text is a subword continuation (not a word-start).

    The determination is tokenizer-family-aware:
    - tiktoken (o200k_base, cl100k_base): leading space marks word-start
    - GPT-2: Ġ prefix marks word-start
    - SentencePiece (llama-3, mistral, qwen-2.5, gemma-2): ▁ prefix marks word-start
    - BERT-style: ## prefix marks continuation
    - Unknown family: default to False (assume word-start — safer than assuming continuation)
    """
    # Universal pre-checks
    stripped = token_text.strip()
    if not stripped:
        return False
    if stripped[0] in _PUNCTUATION:
        return False

    if token_text.startswith("##"):
        return True

    continuation_style = _CONTINUATION_STYLES.get(tokenizer_key)

    if continuation_style == "space_prefix":
        return not token_text.startswith(" ")

    if continuation_style == "gpt2_prefix":
        return not token_text.startswith("Ġ")

    if continuation_style == "sentencepiece":
        return not token_text.startswith("▁")

    if continuation_style == "bert_hash":
        return token_text.startswith("##")

    if continuation_style == "auto":
        if token_text.startswith((" ", "Ġ", "▁")):
            return False
        return True

    # Unknown family — safe default: assume word-start, not continuation
    return False


def _lane_label(corpus_key: str) -> str:
    return "Strict Evidence" if corpus_key == "strict_parallel" else "Streaming Exploration"


def _iter_benchmark_payload(
    corpus_key: str,
    languages: list[str] | None,
    tokenizer_keys: list[str],
    *,
    row_limit: int = 25,
    include_estimates: bool = False,
    include_proxy: bool = False,
    include_raw_rows: bool = False,
    include_token_texts: bool = False,
    progress_callback: Callable[[float, str], None] | None = None,
):
    selected_languages = languages or list(DEFAULT_BENCHMARK_LANGUAGES)
    fetch_languages = list(selected_languages)
    if corpus_key == "streaming_exploration" and "en" not in fetch_languages:
        fetch_languages.append("en")
    log_event(
        "benchmark.samples.fetch.start",
        "Loading corpus samples",
        corpus_key=corpus_key,
        language_count=len(fetch_languages),
        row_limit=row_limit,
        lane=_lane_label(corpus_key),
    )
    samples = fetch_corpus_samples(corpus_key, fetch_languages, row_limit=row_limit)
    log_event(
        "benchmark.samples.fetch.success",
        "Loaded corpus samples",
        corpus_key=corpus_key,
        language_count=len(samples),
        sample_counts={language: len(rows) for language, rows in samples.items()},
        lane=_lane_label(corpus_key),
    )
    lane = _lane_label(corpus_key)
    raw_rows: list[dict] = []
    composition_counts: dict[tuple[str, str], int] = {}

    visible_selections = []
    for tokenizer in tokenizer_keys:
        selection = resolve_selection(tokenizer)
        if not provenance_visible(
            selection["provenance"],
            include_estimates=include_estimates,
            include_proxy=include_proxy,
        ):
            continue
        visible_selections.append(selection)

    total_tokenizers = len(visible_selections)

    for index, selection in enumerate(visible_selections):
        if progress_callback and total_tokenizers:
            progress_callback(
                index / total_tokenizers,
                f"Benchmarking {selection['label']}…",
            )

        log_event(
            "benchmark.tokenizer.load.start",
            "Loading tokenizer family",
            tokenizer_key=selection["tokenizer_key"],
            lane=lane,
        )
        try:
            tok = get_tokenizer(selection["tokenizer_key"])
        except Exception as exc:
            log_event(
                "benchmark.tokenizer.load.error",
                "Tokenizer family failed to load",
                tokenizer_key=selection["tokenizer_key"],
                lane=lane,
                error=str(exc),
            )
            if progress_callback and total_tokenizers:
                progress_callback(
                    (index + 1) / total_tokenizers,
                    f"Skipped {selection['label']}",
                )
            continue
        log_event(
            "benchmark.tokenizer.load.success",
            "Tokenizer family ready",
            tokenizer_key=selection["tokenizer_key"],
            lane=lane,
        )

        log_event(
            "benchmark.tokenizer.start",
            "Benchmarking tokenizer family",
            tokenizer_key=selection["tokenizer_key"],
            language_count=len(selected_languages),
            lane=lane,
        )

        english_baseline = None
        if corpus_key == "streaming_exploration":
            english_samples = samples.get("en", [])
            if english_samples:
                english_metrics = [
                    _sample_metrics(
                        sample.text,
                        None,
                        selection["tokenizer_key"],
                        tokenizer=tok,
                    )
                    for sample in english_samples
                ]
                english_baseline = _safe_median([item["token_count"] for item in english_metrics])

        for language in selected_languages:
            language_samples = samples.get(language, [])
            if not language_samples:
                log_event(
                    "benchmark.language.skip",
                    "Skipping language with no samples",
                    tokenizer_key=selection["tokenizer_key"],
                    language=language,
                    lane=lane,
                )
                continue

            computed: list[dict] = []
            observed_tokens: set[str] = set()
            for sample_index, sample in enumerate(language_samples):
                metrics = _sample_metrics(
                    sample.text,
                    sample.english_text if corpus_key == "strict_parallel" else None,
                    selection["tokenizer_key"],
                    tokenizer=tok,
                    english_baseline_token_count=english_baseline if corpus_key == "streaming_exploration" else None,
                )
                observed_tokens.update(metrics["token_texts"])
                for token in metrics["token_texts"]:
                    script = _token_script(token)
                    composition_key = (selection["tokenizer_key"], script)
                    composition_counts[composition_key] = composition_counts.get(composition_key, 0) + 1
                if include_raw_rows:
                    detail_row = {
                        "lane": lane,
                        "language": language,
                        "tokenizer_key": selection["tokenizer_key"],
                        "label": selection["label"],
                        "sample_index": sample_index,
                        "text": sample.text,
                        "token_count": metrics["token_count"],
                        "unique_tokens": metrics["unique_tokens"],
                        "continued_word_rate": round(metrics["continued_word_rate"], 4),
                        "token_fertility": round(metrics["token_fertility"], 4),
                        "bytes_per_token": round(metrics["bytes_per_token"], 4),
                        "rtc": round(metrics["rtc"], 4) if metrics.get("rtc") is not None else None,
                        "english_baseline_ratio": round(metrics["english_baseline_ratio"], 4)
                        if metrics.get("english_baseline_ratio") is not None else None,
                        "token_preview": " | ".join(metrics["token_texts"][:20]),
                        "provenance": sample.provenance,
                        "corpus_key": corpus_key,
                    }
                    if include_token_texts:
                        detail_row["token_texts"] = metrics["token_texts"]
                    raw_rows.append(detail_row)
                computed.append(metrics)

            rtc = _safe_median([item.get("rtc") for item in computed]) if corpus_key == "strict_parallel" else None
            rtc_iqr = _safe_iqr([item.get("rtc") for item in computed]) if corpus_key == "strict_parallel" else None
            english_baseline_ratio = (
                _safe_median([item.get("english_baseline_ratio") for item in computed])
                if corpus_key == "streaming_exploration"
                else None
            )
            aggregated = {
                "language": language,
                "label": selection["label"],
                "tokenizer_key": selection["tokenizer_key"],
                "token_count": round(_safe_median([item["token_count"] for item in computed]) or 0, 2),
                "token_fertility": round(_safe_median([item["token_fertility"] for item in computed]) or 0.0, 4),
                "bytes_per_token": round(_safe_median([item["bytes_per_token"] for item in computed]) or 0.0, 4),
                "unique_tokens": len(observed_tokens),
                "continued_word_rate": round(_safe_median([item["continued_word_rate"] for item in computed]) or 0.0, 4),
                "rtc": round(rtc, 4) if rtc is not None else None,
                "rtc_iqr": round(rtc_iqr, 4) if rtc_iqr is not None else None,
                "english_baseline_ratio": round(english_baseline_ratio, 4)
                if english_baseline_ratio is not None else None,
                "byte_premium": round(_safe_median([item.get("byte_premium") for item in computed]) or 0.0, 4)
                if rtc is not None else None,
                "risk_level": quality_risk_level(rtc) if rtc is not None else "exploratory",
                "sample_count": len(computed),
                "provenance": selection["provenance"],
                "mapping_quality": selection["mapping_quality"],
                "corpus_key": corpus_key,
                "lane": lane,
            }
            log_event(
                "benchmark.row.ready",
                "Benchmark row ready",
                tokenizer_key=selection["tokenizer_key"],
                language=language,
                sample_count=len(computed),
                lane=lane,
            )
            yield aggregated, raw_rows, composition_counts

        if progress_callback and total_tokenizers:
            progress_callback(
                (index + 1) / total_tokenizers,
                f"Finished {selection['label']}",
            )


def build_benchmark_detail_rows(
    corpus_key: str,
    languages: list[str] | None,
    tokenizer_keys: list[str],
    *,
    row_limit: int = 25,
) -> list[dict]:
    """Return per-sample benchmark details for preview/raw-data subviews."""
    rows: list[dict] = []
    for _, current_raw_rows, _ in _iter_benchmark_payload(
        corpus_key,
        languages,
        tokenizer_keys,
        row_limit=row_limit,
        include_raw_rows=True,
        include_token_texts=True,
    ):
        rows = current_raw_rows
    return rows


def iter_benchmark_rows(
    corpus_key: str,
    languages: list[str] | None,
    tokenizer_keys: list[str],
    *,
    row_limit: int = 25,
    include_estimates: bool = False,
    include_proxy: bool = False,
):
    """Yield aggregate benchmark rows one tokenizer/language at a time."""
    for row, _, _ in _iter_benchmark_payload(
        corpus_key,
        languages,
        tokenizer_keys,
        row_limit=row_limit,
        include_estimates=include_estimates,
        include_proxy=include_proxy,
    ):
        yield row


def benchmark_corpus(
    corpus_key: str,
    languages: list[str] | None,
    tokenizer_keys: list[str],
    *,
    row_limit: int = 25,
    include_estimates: bool = False,
    include_proxy: bool = False,
    include_raw_rows: bool = False,
    progress_callback: Callable[[float, str], None] | None = None,
) -> dict:
    """Compute aggregate tokenizer benchmark rows from a registered corpus."""
    log_event(
        "benchmark.run.start",
        "Running benchmark",
        corpus_key=corpus_key,
        languages=languages or list(DEFAULT_BENCHMARK_LANGUAGES),
        tokenizer_keys=tokenizer_keys,
        row_limit=row_limit,
    )
    selected_languages = languages or list(DEFAULT_BENCHMARK_LANGUAGES)
    rows: list[dict] = []
    raw_rows: list[dict] = []
    composition_counts: dict[tuple[str, str], int] = {}
    for row, current_raw_rows, current_composition_counts in _iter_benchmark_payload(
        corpus_key,
        selected_languages,
        tokenizer_keys,
        row_limit=row_limit,
        include_estimates=include_estimates,
        include_proxy=include_proxy,
        include_raw_rows=include_raw_rows,
        progress_callback=progress_callback,
    ):
        rows.append(row)
        raw_rows = current_raw_rows
        composition_counts = current_composition_counts
    matrix: dict[tuple[str, str], dict] = {
        (row["language"], row["tokenizer_key"]): row
        for row in rows
    }

    if not rows:
        log_event(
            "benchmark.run.empty",
            "Benchmark produced no rows",
            corpus_key=corpus_key,
            languages=selected_languages,
            tokenizer_keys=tokenizer_keys,
        )
        raise RuntimeError(
            "No benchmark rows were produced. The strict corpus fetch may have failed or returned zero samples."
        )

    log_event(
        "benchmark.run.success",
        "Benchmark completed",
        row_count=len(rows),
        language_count=len(selected_languages),
        tokenizer_count=len({row["tokenizer_key"] for row in rows}),
    )
    return {
        "rows": rows,
        "raw_rows": raw_rows,
        "matrix": matrix,
        "languages": selected_languages,
        "tokenizers": list(dict.fromkeys(row["tokenizer_key"] for row in rows)),
        "composition_rows": [
            {
                "tokenizer_key": tokenizer_key,
                "script": script,
                "token_count": count,
            }
            for (tokenizer_key, script), count in sorted(composition_counts.items())
        ],
    }


def scenario_analysis(
    *,
    corpus_key: str,
    languages: list[str] | None,
    tokenizer_keys: list[str],
    model_ids: list[str],
    row_limit: int,
    monthly_requests: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    reasoning_share: float,
    include_estimates: bool = False,
    include_proxy: bool = False,
    progress_callback: Callable[[float, str], None] | None = None,
) -> list[dict]:
    """Build scenario rows joining benchmark metrics and deployable model metadata."""
    if corpus_key != "strict_parallel":
        raise ValueError(
            "Scenario Lab uses Strict Evidence only for deploy-grade cost/context estimates."
        )
    log_event(
        "scenario.run.start",
        "Running scenario analysis",
        corpus_key=corpus_key,
        languages=languages,
        tokenizer_keys=tokenizer_keys,
        model_ids=model_ids,
    )
    def _benchmark_progress(ratio: float, desc: str) -> None:
        if progress_callback is None:
            return
        progress_callback(0.12 + (ratio * 0.63), desc)

    benchmark = benchmark_corpus(
        corpus_key,
        languages,
        tokenizer_keys,
        row_limit=row_limit,
        include_estimates=include_estimates,
        include_proxy=include_proxy,
        progress_callback=_benchmark_progress,
    )
    benchmark_lookup = {
        (row["language"], row["tokenizer_key"]): row
        for row in benchmark["rows"]
    }
    benchmark_tokenizers = set(
        benchmark.get("tokenizers")
        or [row["tokenizer_key"] for row in benchmark["rows"]]
    )
    missing_tokenizers = [
        selection["label"]
        for key in tokenizer_keys
        if key not in benchmark_tokenizers
        for selection in [resolve_selection(key)]
    ]
    if benchmark_tokenizers and missing_tokenizers:
        raise RuntimeError(
            "Scenario benchmark is missing tokenizer families: "
            + ", ".join(missing_tokenizers)
            + ". This usually means their local tokenizer files were unavailable at runtime."
        )

    catalog = build_catalog_entries(include_proxy=include_proxy, refresh_live=False)
    selected_models = {row["model_id"]: row for row in catalog if row["model_id"] in model_ids}

    rows = []
    if progress_callback is not None:
        progress_callback(0.82, "Joining model metadata…")
    for model_id, model in selected_models.items():
        for language in benchmark["languages"]:
            benchmark_row = benchmark_lookup.get((language, model["tokenizer_key"]))
            if not benchmark_row or benchmark_row.get("rtc") is None:
                continue

            rtc = float(benchmark_row["rtc"])
            monthly_input_tokens = monthly_requests * max(int(round(avg_input_tokens * rtc)), 1)
            billed_output_tokens = monthly_requests * max(int(round(avg_output_tokens * (1.0 + reasoning_share))), 1)
            input_cost = monthly_input_tokens * model["input_per_million"] / 1_000_000
            output_cost = billed_output_tokens * model["output_per_million"] / 1_000_000
            context_loss_pct = max(0.0, (1.0 - (1.0 / rtc)) * 100.0) if rtc else 0.0

            rows.append({
                "label": model["label"],
                "model_id": model_id,
                "language": language,
                "tokenizer_key": model["tokenizer_key"],
                "rtc": round(rtc, 4),
                "context_loss_pct": round(context_loss_pct, 2),
                "monthly_input_tokens": monthly_input_tokens,
                "monthly_output_tokens": billed_output_tokens,
                "monthly_cost": round(input_cost + output_cost, 6),
                "input_cost": round(input_cost, 6),
                "output_cost": round(output_cost, 6),
                "latency_ms": model["latency_ms"],
                "throughput_tps": model["throughput_tps"],
                "ttft_seconds": model.get("ttft_seconds"),
                "output_tokens_per_second": model.get("output_tokens_per_second"),
                "telemetry_provider": model.get("telemetry_provider"),
                "lane": benchmark_row.get("lane", _lane_label(corpus_key)),
                "provenance": model["provenance"],
                "mapping_quality": model["mapping_quality"],
            })
    if not rows:
        log_event(
            "scenario.run.empty",
            "Scenario analysis produced no rows",
            corpus_key=corpus_key,
            languages=benchmark["languages"],
            model_ids=model_ids,
        )
        raise RuntimeError(
            "No scenario rows were produced. This usually means benchmark data was unavailable for the selected languages/models."
        )
    log_event(
        "scenario.run.success",
        "Scenario analysis completed",
        row_count=len(rows),
        model_count=len(selected_models),
    )
    if progress_callback is not None:
        progress_callback(0.9, "Scenario rows ready")
    return rows


def build_source_manifest() -> list[dict]:
    """Return source inventory used by the workbench."""
    return [
        {
            "title": "FLORES-200 dataset",
            "url": "https://huggingface.co/datasets/haoranxu/FLORES-200",
            "category": "benchmark_corpus",
            "use": "Strict parallel benchmark for cross-language tokenizer comparison",
        },
        {
            "title": "OpenRouter Models API",
            "url": "https://openrouter.ai/api/v1/models",
            "category": "catalog_api",
            "use": "Deployable model metadata and pricing refresh",
        },
        {
            "title": "tokka-bench writeup",
            "url": "https://www.bengubler.com/posts/2025-08-25-tokka-bench-evaluate-tokenizers-multilingual",
            "category": "reference_methodology",
            "use": "Naturalistic benchmark design reference",
        },
        {
            "title": "FineWeb2 dataset",
            "url": "https://huggingface.co/datasets/HuggingFaceFW/fineweb-2",
            "category": "exploratory_corpus",
            "use": "Live natural-language streaming lane for exploratory tokenizer analysis",
        },
        {
            "title": "StarCoderData dataset",
            "url": "https://huggingface.co/datasets/bigcode/starcoderdata",
            "category": "planned_corpus",
            "use": "Future code-language layer",
        },
        {
            "title": "Tokenization Disparities as Infrastructure Bias",
            "url": "https://arxiv.org/html/2510.12389v1",
            "category": "paper",
            "use": "RTC framing and FLORES-backed methodology",
        },
        {
            "title": "Reducing Tokenization Premiums for Low-Resource Languages",
            "url": "https://arxiv.org/html/2601.13328v1",
            "category": "paper",
            "use": "Tokenization premium framing and mitigation references",
        },
    ]


def benchmark_appendix(corpus_key: str) -> str:
    """Build markdown appendix for the Benchmark tab."""
    corpus_rows = [row for row in list_corpora() if row["key"] == corpus_key]
    if not corpus_rows:
        return "No appendix available."
    corpus = corpus_rows[0]
    lines = [
        "### Benchmark Appendix",
        f"- Lane: **{_lane_label(corpus_key)}**",
        f"- Corpus: **{corpus['label']}**",
        f"- Source: {corpus['source_url']}",
        f"- Provenance: {provenance_badge(corpus['provenance'])} {provenance_description(corpus['provenance'])}",
        "- Formula: `bytes_per_token = utf8_bytes / token_count`",
        "- Formula: `token_fertility = token_count / language_unit_count`",
    ]
    if corpus_key == "strict_parallel":
        lines.append("- Formula: `rtc = source_tokens / english_tokens` on aligned parallel samples only")
        lines.append("- Caveat: strict benchmark claims use only the verified parallel corpus in v1")
    else:
        lines.append("- Formula: `english_baseline_ratio = source_tokens / median(english_token_count)` using live English samples from the same tokenizer family")
        lines.append("- Caveat: `english_baseline_ratio` is not aligned bilingual RTC and is benchmark-only exploratory context")
        lines.append("- Caveat: streaming exploration is live remote data and exploratory only; do not treat it as the default headline evidence lane")
    if corpus["note"]:
        lines.append(f"- Note: {corpus['note']}")
    return "\n".join(lines)


def catalog_appendix(include_proxy: bool) -> str:
    """Build markdown appendix for the Catalog tab."""
    status = pricing_status()
    aa_status = artificial_analysis_status()
    lines = [
        "### Catalog Appendix",
        "- Source API: https://openrouter.ai/api/v1/models",
        f"- Pricing file last updated: **{status['last_updated']}**",
        f"- Last live refresh: **{status['last_refreshed'] or 'not yet refreshed'}**",
        f"- Last refresh error: **{status['last_refresh_error'] or 'none'}**",
        f"- AA snapshot captured at: **{aa_status['captured_at'] or 'not available'}**",
        f"- AA benchmark matches loaded: **{aa_status['model_count']}**",
        "- Mapping policy: exact mappings are visible by default; proxy tokenizer stand-ins are hidden unless enabled",
        f"- Proxy mappings visible: **{'yes' if include_proxy else 'no'}**",
        "- Current proxy families: Gemma uses a Gemma-family stand-in and Command R uses a BLOOM stand-in until exact equivalence is documented",
    ]
    return "\n".join(lines)


def scenario_appendix() -> str:
    """Build markdown appendix for the Scenario Lab tab."""
    lines = [
        "### Scenario Appendix",
        "- Method: **Strict benchmark-driven estimate** using measured multilingual benchmark rows",
        "- Contrast: **Legacy heuristic estimate** remains separate and uses the 4 chars/token portfolio shortcut for CSV traffic demos only",
        "- Benchmark lane: **Strict Evidence**",
        "- Input cost formula: `monthly_requests * (avg_input_tokens * RTC) * input_price / 1e6`",
        "- Output cost formula: `monthly_requests * (avg_output_tokens * (1 + reasoning_share)) * output_price / 1e6`",
        "- Context loss formula: `1 - (1 / RTC)`",
        "- Streaming Exploration remains available in Benchmark only and is not used for deploy-grade cost/context estimates.",
        "- Speed metadata is benchmark-only in v1 and comes from the local Artificial Analysis snapshot when a model match exists.",
        "- Derived scenario rows are labeled as estimates even when the benchmark and catalog inputs are verified",
    ]
    return "\n".join(lines)


def audit_markdown() -> str:
    """Build markdown for the Audit tab."""
    manifest = build_source_manifest()
    families = list_tokenizer_families(include_proxy=True)
    lines = [
        "## Audit",
        "",
        "### Sources",
    ]
    for item in manifest:
        lines.append(f"- **{item['title']}** — {item['category']} — {item['url']}")
        lines.append(f"  Use: {item['use']}")

    lines.extend([
        "",
        "### Tokenizer Families",
    ])
    for family in families:
        lines.append(
            f"- **{family['label']}** (`{family['key']}`) — {'exact tokenizer mapping' if family['mapping_quality'] == 'exact' else 'proxy tokenizer mapping'} — {family['tokenizer_source']}"
        )

    lines.extend([
        "",
        "### Tokenizer Snapshot Health",
    ])
    for item in list_tokenizer_snapshot_status(include_proxy=False):
        lines.append(
            f"- **{item['label']}** (`{item['key']}`) — {item['status_label']}"
        )

    lines.extend([
        "",
        "### Data Dictionary",
        "- `rtc`: Relative Tokenization Cost against aligned English text",
        "- `english_baseline_ratio`: Exploratory normalization against live English streaming samples for the same tokenizer family",
        "- `byte_premium`: UTF-8 byte ratio against aligned English text",
        "- `token_fertility`: tokens per language unit in the sampled text",
        "- `context_loss_pct`: effective context loss derived from RTC",
        "- `provenance`: strict verified, surfaced metadata, estimated, proxy, or research forward",
    ])
    return "\n".join(lines)


def write_learning_log() -> str:
    """Return the learning log contents for writing to learning.md."""
    return """# learning.md

## Overview
- Shift the product from a demo-like token tax calculator to a Token Tax Workbench.
- Keep the product non-prescriptive: show evidence, not verdicts.

## Current State
- The original app used hardcoded multilingual sample phrases for benchmark-like views.
- The new workbench separates benchmark evidence, model catalog data, scenario analysis, and audit/provenance.

## Corpus Decisions
- Strict benchmark default: FLORES-200 via Hugging Face dataset viewer.
- Naturalistic human corpora: FineWeb/FineWeb2 registered as planned methodology sources.
- Naturalistic code corpus: StarCoderData registered as planned methodology source.
- Demo sample phrases remain only for compatibility and local examples.

## Metric Decisions
- Headline cross-language metrics: RTC, token count, byte premium, context loss, surcharge.
- Exploratory metrics: bytes/token, token fertility.
- Latency/throughput remain surfaced-metadata-only in v1.

## Product Decisions
- Four-tab IA: Benchmark, Catalog, Scenario Lab, Audit.
- Strict verified-only defaults.
- Proxy mappings hidden by default.
- Per-tab appendices explain formulas, sources, and caveats.

## Sources
- FLORES-200 dataset: https://huggingface.co/datasets/haoranxu/FLORES-200
- OpenRouter Models API: https://openrouter.ai/api/v1/models
- tokka-bench reference: https://www.bengubler.com/posts/2025-08-25-tokka-bench-evaluate-tokenizers-multilingual
- FineWeb2 dataset: https://huggingface.co/datasets/HuggingFaceFW/fineweb-2
- StarCoderData dataset: https://huggingface.co/datasets/bigcode/starcoderdata
- Tokenization Disparities as Infrastructure Bias: https://arxiv.org/html/2510.12389v1
- Reducing Tokenization Premiums for Low-Resource Languages: https://arxiv.org/html/2601.13328v1

## Known Gaps
- Naturalistic corpora are registered but not enabled as verified runtime benchmark sources in v1.
- Latency/throughput fields remain empty unless surfaced metadata becomes available through a stable API path.
- Gemma and Command R remain proxy tokenizer families and stay hidden by default.
"""


def refresh_catalog() -> tuple[list[dict], dict]:
    """Refresh live pricing cache and return visible catalog rows and status."""
    refresh_from_openrouter()
    rows = build_catalog_entries(include_proxy=False, refresh_live=False)
    log_event(
        "catalog.rows.ready",
        "Catalog rows prepared",
        row_count=len(rows),
    )
    return rows, pricing_status()
