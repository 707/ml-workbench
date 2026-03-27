"""Corpus registry and lightweight remote benchmark fetchers."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import requests


HF_DATASET_VIEWER_URL = "https://datasets-server.huggingface.co/first-rows"


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


@lru_cache(maxsize=64)
def _fetch_first_rows(dataset_id: str, config: str, split: str) -> list[dict]:
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
    return parsed_rows


def fetch_strict_parallel_samples(
    languages: list[str],
    row_limit: int = 25,
) -> dict[str, list[CorpusSample]]:
    """Fetch aligned FLORES rows for the requested languages."""
    corpus = get_corpus("strict_parallel")
    result: dict[str, list[CorpusSample]] = {}

    for language in languages:
        pair_rows: list[CorpusSample] = []
        errors: list[Exception] = []
        for config in _pair_configs(language):
            try:
                rows = _fetch_first_rows(corpus.dataset_id, config, corpus.split)
            except Exception as exc:  # pragma: no cover - exercised via callers
                errors.append(exc)
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
        # If all configs failed, skip this language silently.
        # Callers handle missing languages (e.g. samples.get(lang, [])).

    return result


def fetch_corpus_samples(
    corpus_key: str,
    languages: list[str],
    row_limit: int = 25,
) -> dict[str, list[CorpusSample]]:
    """Fetch samples for a corpus key."""
    if corpus_key == "strict_parallel":
        return fetch_strict_parallel_samples(languages, row_limit=row_limit)
    raise NotImplementedError(
        f"{corpus_key} is registered for methodology but not enabled as a verified runtime corpus in v1."
    )
