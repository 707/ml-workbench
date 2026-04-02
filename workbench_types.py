"""Typed request/result objects for the workbench engines."""

from __future__ import annotations

from dataclasses import dataclass


def _normalize_strings(values: list[str] | None) -> tuple[str, ...]:
    return tuple(values or ())


@dataclass(frozen=True)
class BenchmarkRequest:
    corpus_key: str
    languages: tuple[str, ...]
    tokenizer_keys: tuple[str, ...]
    row_limit: int
    include_estimates: bool = False
    include_proxy: bool = False

    @classmethod
    def from_inputs(
        cls,
        *,
        corpus_key: str,
        languages: list[str] | None,
        tokenizer_keys: list[str] | None,
        row_limit: int,
        include_estimates: bool = False,
        include_proxy: bool = False,
    ) -> "BenchmarkRequest":
        return cls(
            corpus_key=corpus_key,
            languages=_normalize_strings(languages),
            tokenizer_keys=_normalize_strings(tokenizer_keys),
            row_limit=int(row_limit),
            include_estimates=bool(include_estimates),
            include_proxy=bool(include_proxy),
        )

    def cache_key(self) -> tuple[object, ...]:
        return (
            self.corpus_key,
            self.languages,
            self.tokenizer_keys,
            self.row_limit,
            self.include_estimates,
            self.include_proxy,
        )


@dataclass(frozen=True)
class BenchmarkResult:
    rows: list[dict]
    raw_rows: list[dict]
    matrix: dict[tuple[str, str], dict]
    languages: list[str]
    tokenizers: list[str]


@dataclass(frozen=True)
class ScenarioRequest:
    corpus_key: str
    languages: tuple[str, ...]
    tokenizer_keys: tuple[str, ...]
    row_limit: int
    monthly_requests: int
    avg_input_tokens: int
    avg_output_tokens: int
    reasoning_share: float
    include_estimates: bool = False
    include_proxy: bool = False

    @classmethod
    def from_inputs(
        cls,
        *,
        corpus_key: str,
        languages: list[str] | None,
        tokenizer_keys: list[str] | None,
        row_limit: int,
        monthly_requests: int,
        avg_input_tokens: int,
        avg_output_tokens: int,
        reasoning_share: float,
        include_estimates: bool = False,
        include_proxy: bool = False,
    ) -> "ScenarioRequest":
        return cls(
            corpus_key=corpus_key,
            languages=_normalize_strings(languages),
            tokenizer_keys=_normalize_strings(tokenizer_keys),
            row_limit=int(row_limit),
            monthly_requests=int(monthly_requests),
            avg_input_tokens=int(avg_input_tokens),
            avg_output_tokens=int(avg_output_tokens),
            reasoning_share=float(reasoning_share),
            include_estimates=bool(include_estimates),
            include_proxy=bool(include_proxy),
        )

    def to_benchmark_request(self) -> BenchmarkRequest:
        return BenchmarkRequest(
            corpus_key=self.corpus_key,
            languages=self.languages,
            tokenizer_keys=self.tokenizer_keys,
            row_limit=self.row_limit,
            include_estimates=self.include_estimates,
            include_proxy=self.include_proxy,
        )


@dataclass(frozen=True)
class ScenarioResult:
    rows: list[dict]
    model_ids: list[str]


@dataclass(frozen=True)
class CatalogRequest:
    include_proxy: bool = False
    refresh_live: bool = False
    live_updates: bool = False


@dataclass(frozen=True)
class CatalogResult:
    rows: list[dict]
    appendix: str
    diagnostics: str
