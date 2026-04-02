"""Shared tokenizer-family registry used across benchmarking, UI, and charts."""

from __future__ import annotations

from dataclasses import dataclass

ContinuationStyle = str


@dataclass(frozen=True)
class TokenizerFamilySpec:
    key: str
    label: str
    tokenizer_source: str
    mapping_quality: str
    provenance: str
    continuation_style: ContinuationStyle
    chart_color: str


TOKENIZER_FAMILY_SPECS: dict[str, TokenizerFamilySpec] = {
    "o200k_base": TokenizerFamilySpec("o200k_base", "OpenAI o200k", "tiktoken:o200k_base", "exact", "strict_verified", "space_prefix", "#1f77b4"),
    "cl100k_base": TokenizerFamilySpec("cl100k_base", "OpenAI cl100k", "tiktoken:cl100k_base", "exact", "strict_verified", "space_prefix", "#2ca02c"),
    "llama-3": TokenizerFamilySpec("llama-3", "Llama 3 family", "NousResearch/Meta-Llama-3-8B", "exact", "strict_verified", "auto", "#d62728"),
    "mistral": TokenizerFamilySpec("mistral", "Mistral family", "mistralai/Mistral-7B-v0.1", "exact", "strict_verified", "sentencepiece", "#9467bd"),
    "qwen-2.5": TokenizerFamilySpec("qwen-2.5", "Qwen 2.5 family", "Qwen/Qwen2.5-7B", "exact", "strict_verified", "auto", "#8c564b"),
    "gpt2": TokenizerFamilySpec("gpt2", "GPT-2 legacy", "gpt2", "exact", "strict_verified", "gpt2_prefix", "#bcbd22"),
}


def supported_tokenizers_map() -> dict[str, str]:
    """Return tokenizer loader sources keyed by family key."""
    return {
        key: spec.tokenizer_source
        for key, spec in TOKENIZER_FAMILY_SPECS.items()
    }


def tokenizer_color_map() -> dict[str, str]:
    """Return chart colors keyed by tokenizer family."""
    return {
        key: spec.chart_color
        for key, spec in TOKENIZER_FAMILY_SPECS.items()
    }


def continuation_style_map() -> dict[str, ContinuationStyle]:
    """Return continuation-style metadata keyed by tokenizer family."""
    return {
        key: spec.continuation_style
        for key, spec in TOKENIZER_FAMILY_SPECS.items()
    }
