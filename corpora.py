"""Corpus registry and lightweight remote benchmark fetchers."""

from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock

import requests

from diagnostics import log_event

HF_DATASET_VIEWER_URL = "https://datasets-server.huggingface.co/first-rows"
STRICT_PARALLEL_SNAPSHOT_PATH = Path(__file__).resolve().parent / "data" / "strict_parallel" / "flores_v1.jsonl"
STREAMING_LANGUAGE_CONFIGS = {
    "en": "eng_Latn",
    "ar": "arb_Arab",
    "hi": "hin_Deva",
    "ja": "jpn_Jpan",
    "zh": "cmn_Hani",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "es": "spa_Latn",
    "pt": "por_Latn",
    "ru": "rus_Cyrl",
}


@dataclass(frozen=True)
class CorpusDefinition:
    key: str
    label: str
    source_url: str
    dataset_id: str
    split: str
    description: str
    supported_metrics: tuple[str, ...]
    provenance: str
    status: str
    note: str = ""


@dataclass(frozen=True)
class CorpusSample:
    language: str
    text: str
    english_text: str | None
    corpus_key: str
    source_url: str
    provenance: str


CORPUS_REGISTRY: dict[str, CorpusDefinition] = {
    "strict_parallel": CorpusDefinition(
        key="strict_parallel",
        label="Strict Parallel (FLORES-200)",
        source_url="https://huggingface.co/datasets/haoranxu/FLORES-200",
        dataset_id="haoranxu/FLORES-200",
        split="test",
        description="Aligned multilingual sentence pairs for strict cross-language tokenizer comparison.",
        supported_metrics=("rtc", "token_count", "byte_premium", "bytes_per_token", "token_fertility"),
        provenance="strict_verified",
        status="active",
    ),
    "naturalistic_human": CorpusDefinition(
        key="naturalistic_human",
        label="Naturalistic Human (FineWeb/FineWeb2)",
        source_url="https://huggingface.co/datasets/HuggingFaceFW/fineweb-2",
        dataset_id="HuggingFaceFW/fineweb-2",
        split="train",
        description="Natural web text for same-language tokenizer exploration.",
        supported_metrics=("token_count", "bytes_per_token", "token_fertility"),
        provenance="research_forward",
        status="planned",
        note="Registered for methodology and future expansion; strict benchmark visuals stay on FLORES-200 in v1.",
    ),
    "streaming_exploration": CorpusDefinition(
        key="streaming_exploration",
        label="Streaming Exploration (FineWeb-2)",
        source_url="https://huggingface.co/datasets/HuggingFaceFW/fineweb-2",
        dataset_id="HuggingFaceFW/fineweb-2",
        split="train",
        description="Live natural-language rows for exploratory tokenizer analysis on real web text.",
        supported_metrics=("english_baseline_ratio", "token_count", "bytes_per_token", "token_fertility", "unique_tokens", "continued_word_rate"),
        provenance="research_forward",
        status="active",
        note="Live remote fetches are exploratory only and are not the default evidence lane.",
    ),
    "naturalistic_code": CorpusDefinition(
        key="naturalistic_code",
        label="Naturalistic Code (StarCoderData)",
        source_url="https://huggingface.co/datasets/bigcode/starcoderdata",
        dataset_id="bigcode/starcoderdata",
        split="train",
        description="Programming-language text for tokenizer exploration on code.",
        supported_metrics=("token_count", "bytes_per_token", "token_fertility"),
        provenance="research_forward",
        status="planned",
        note="Registered for code-focused analysis; not enabled in strict verified visuals in v1.",
    ),
}


DEFAULT_BENCHMARK_LANGUAGES = [
    "en",
    "ar",
    "hi",
    "ja",
    "zh",
    "fr",
    "de",
    "es",
    "pt",
    "ru",
]


def list_corpora() -> list[dict]:
    """Return corpus definitions as serializable dicts."""
    return [
        {
            "key": corpus.key,
            "label": corpus.label,
            "source_url": corpus.source_url,
            "description": corpus.description,
            "supported_metrics": list(corpus.supported_metrics),
            "provenance": corpus.provenance,
            "status": corpus.status,
            "note": corpus.note,
        }
        for corpus in CORPUS_REGISTRY.values()
    ]


def get_corpus(corpus_key: str) -> CorpusDefinition:
    """Return a corpus definition."""
    if corpus_key not in CORPUS_REGISTRY:
        raise KeyError(f"unknown corpus: {corpus_key}")
    return CORPUS_REGISTRY[corpus_key]


def _pair_configs(language: str) -> list[str]:
    if language == "en":
        return ["fr-en"]
    return [f"{language}-en", f"en-{language}"]


def _extract_text_pair(row: dict, language: str) -> tuple[str, str] | None:
    if language == "en":
        english = row.get("en")
        if isinstance(english, str) and english.strip():
            return english, english
        return None

    source = row.get(language)
    english = row.get("en")
    if isinstance(source, str) and isinstance(english, str) and source.strip() and english.strip():
        return source, english
    return None


@lru_cache(maxsize=4)
def load_strict_parallel_snapshot(snapshot_path: str | None = None) -> dict[str, list[CorpusSample]]:
    """Load bundled strict benchmark samples from a local JSONL snapshot."""
    path = Path(snapshot_path) if snapshot_path else STRICT_PARALLEL_SNAPSHOT_PATH
    if not path.exists():
        return {}

    result: dict[str, list[CorpusSample]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            row = json.loads(raw)
            sample = CorpusSample(
                language=row["language"],
                text=row["text"],
                english_text=row.get("english_text"),
                corpus_key=row["corpus_key"],
                source_url=CORPUS_REGISTRY["strict_parallel"].source_url,
                provenance=row.get("provenance", "strict_verified"),
            )
            result.setdefault(sample.language, []).append(sample)
    return result


_FETCH_CACHE_MAX_ENTRIES = 32
_fetch_cache: OrderedDict[tuple, list[dict]] = OrderedDict()
_fetch_cache_lock = Lock()


def _fetch_first_rows(dataset_id: str, config: str, split: str) -> list[dict]:
    cache_key = (dataset_id, config, split)
    with _fetch_cache_lock:
        cached_rows = _fetch_cache.get(cache_key)
        if cached_rows is not None:
            _fetch_cache.move_to_end(cache_key)
            return cached_rows

    log_event("benchmark.fetch.start", "Fetching corpus rows", dataset_id=dataset_id, config=config, split=split)
    response = requests.get(
        HF_DATASET_VIEWER_URL,
        params={"dataset": dataset_id, "config": config, "split": split},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("rows", [])
    parsed_rows = []
    for entry in rows:
        row = entry.get("row", {})
        if isinstance(row, dict):
            parsed_rows.append(row)
    log_event(
        "benchmark.fetch.success",
        "Fetched corpus rows",
        dataset_id=dataset_id,
        config=config,
        split=split,
        row_count=len(parsed_rows),
    )
    if parsed_rows:
        with _fetch_cache_lock:
            _fetch_cache[cache_key] = parsed_rows
            _fetch_cache.move_to_end(cache_key)
            while len(_fetch_cache) > _FETCH_CACHE_MAX_ENTRIES:
                _fetch_cache.popitem(last=False)
    return parsed_rows


def fetch_strict_parallel_samples(
    languages: list[str],
    row_limit: int = 25,
) -> dict[str, list[CorpusSample]]:
    """Fetch aligned FLORES rows for the requested languages."""
    corpus = get_corpus("strict_parallel")
    snapshot = load_strict_parallel_snapshot(str(STRICT_PARALLEL_SNAPSHOT_PATH))
    if snapshot:
        result = {
            language: snapshot.get(language, [])[:row_limit]
            for language in languages
            if snapshot.get(language)
        }
        for language, rows in result.items():
            log_event(
                "benchmark.language.ready",
                "Prepared benchmark samples from local snapshot",
                language=language,
                sample_count=len(rows),
                corpus_key=corpus.key,
                source="local_snapshot",
            )
        if result:
            return result

    result: dict[str, list[CorpusSample]] = {}

    for language in languages:
        pair_rows: list[CorpusSample] = []
        errors: list[Exception] = []
        for config in _pair_configs(language):
            try:
                rows = _fetch_first_rows(corpus.dataset_id, config, corpus.split)
            except Exception as exc:  # pragma: no cover - exercised via callers
                errors.append(exc)
                log_event(
                    "benchmark.fetch.error",
                    "Corpus fetch failed",
                    language=language,
                    config=config,
                    error=str(exc),
                )
                continue

            for row in rows:
                text_pair = _extract_text_pair(row, language)
                if text_pair is None:
                    continue
                text, english_text = text_pair
                pair_rows.append(
                    CorpusSample(
                        language=language,
                        text=text,
                        english_text=english_text,
                        corpus_key=corpus.key,
                        source_url=corpus.source_url,
                        provenance=corpus.provenance,
                    )
                )
                if len(pair_rows) >= row_limit:
                    break
            if pair_rows:
                break

        if pair_rows:
            result[language] = pair_rows[:row_limit]
            log_event(
                "benchmark.language.ready",
                "Prepared benchmark samples",
                language=language,
                sample_count=len(result[language]),
                corpus_key=corpus.key,
            )
        # If all configs failed, skip this language silently.
        # Callers handle missing languages (e.g. samples.get(lang, [])).
        elif errors:
            log_event(
                "benchmark.language.empty",
                "No corpus samples available for language",
                language=language,
                corpus_key=corpus.key,
                error_count=len(errors),
            )

    return result


def fetch_corpus_samples(
    corpus_key: str,
    languages: list[str],
    row_limit: int = 25,
) -> dict[str, list[CorpusSample]]:
    """Fetch samples for a corpus key."""
    if corpus_key == "strict_parallel":
        return fetch_strict_parallel_samples(languages, row_limit=row_limit)
    if corpus_key == "streaming_exploration":
        try:
            rows = _fetch_streaming_rows(languages, row_limit=row_limit)
        except RuntimeError as exc:
            if "Streaming exploration fetch failed" in str(exc):
                raise
            raise RuntimeError(f"Streaming exploration fetch failed: {exc}") from exc

        normalized: dict[str, list[CorpusSample]] = {}
        for language, samples in rows.items():
            normalized[language] = [
                sample if isinstance(sample, CorpusSample) else CorpusSample(
                    language=language,
                    text=sample["text"],
                    english_text=sample.get("english_text"),
                    corpus_key="streaming_exploration",
                    source_url=get_corpus("streaming_exploration").source_url,
                    provenance=sample.get("provenance", get_corpus("streaming_exploration").provenance),
                )
                for sample in samples
            ]
        return normalized
    raise NotImplementedError(
        f"{corpus_key} is registered for methodology but not enabled as a verified runtime corpus in v1."
    )


def _fetch_streaming_rows(
    languages: list[str],
    row_limit: int = 25,
) -> dict[str, list[CorpusSample]]:
    """Fetch naturalistic text rows from FineWeb-2 for exploratory benchmarking."""
    corpus = get_corpus("streaming_exploration")
    result: dict[str, list[CorpusSample]] = {}
    errors: list[str] = []

    for language in languages:
        config = STREAMING_LANGUAGE_CONFIGS.get(language)
        if not config:
            log_event(
                "benchmark.streaming.skip",
                "Streaming exploration has no configured subset for language",
                language=language,
            )
            continue
        try:
            rows = _fetch_first_rows(corpus.dataset_id, config, corpus.split)
        except Exception as exc:
            errors.append(f"{language}: {exc}")
            log_event(
                "benchmark.streaming.error",
                "Streaming exploration fetch failed",
                language=language,
                config=config,
                error=str(exc),
            )
            continue

        samples: list[CorpusSample] = []
        for row in rows:
            text = row.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            samples.append(
                CorpusSample(
                    language=language,
                    text=text,
                    english_text=None,
                    corpus_key=corpus.key,
                    source_url=corpus.source_url,
                    provenance=corpus.provenance,
                )
            )
            if len(samples) >= row_limit:
                break
        if samples:
            result[language] = samples
            log_event(
                "benchmark.streaming.ready",
                "Prepared streaming exploration samples",
                language=language,
                sample_count=len(samples),
                corpus_key=corpus.key,
            )

    if not result and errors:
        raise RuntimeError(f"Streaming exploration fetch failed: {'; '.join(errors)}")
    return result
