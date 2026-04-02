"""Benchmark engine wrappers with typed requests and a small bounded cache."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from typing import Callable

from corpora import DEFAULT_BENCHMARK_LANGUAGES
from token_tax import benchmark_corpus
from workbench_types import BenchmarkRequest, BenchmarkResult

_BENCHMARK_CACHE_MAX_SIZE = 4
_benchmark_cache: OrderedDict[tuple[object, ...], BenchmarkResult] = OrderedDict()


def _clone_result(result: BenchmarkResult) -> BenchmarkResult:
    return BenchmarkResult(
        rows=deepcopy(result.rows),
        raw_rows=deepcopy(result.raw_rows),
        matrix=deepcopy(result.matrix),
        languages=list(result.languages),
        tokenizers=list(result.tokenizers),
    )


def clear_benchmark_cache() -> None:
    _benchmark_cache.clear()


def run_benchmark_request(
    request: BenchmarkRequest,
    *,
    progress_callback: Callable[[float, str], None] | None = None,
) -> BenchmarkResult:
    cache_key = request.cache_key()
    cached = _benchmark_cache.get(cache_key)
    if cached is not None:
        _benchmark_cache.move_to_end(cache_key)
        if progress_callback is not None:
            progress_callback(0.9, "Using cached benchmark…")
        return _clone_result(cached)

    payload = benchmark_corpus(
        request.corpus_key,
        list(request.languages) or list(DEFAULT_BENCHMARK_LANGUAGES),
        list(request.tokenizer_keys),
        row_limit=request.row_limit,
        include_estimates=request.include_estimates,
        include_proxy=request.include_proxy,
        progress_callback=progress_callback,
    )
    result = BenchmarkResult(
        rows=payload["rows"],
        raw_rows=payload["raw_rows"],
        matrix=payload["matrix"],
        languages=payload["languages"],
        tokenizers=payload["tokenizers"],
    )
    _benchmark_cache[cache_key] = _clone_result(result)
    while len(_benchmark_cache) > _BENCHMARK_CACHE_MAX_SIZE:
        _benchmark_cache.popitem(last=False)
    return result
