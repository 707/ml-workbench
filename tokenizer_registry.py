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
    "qwen3-next": TokenizerFamilySpec("qwen3-next", "Qwen3 Next family", "Qwen/Qwen3-Next-80B-A3B-Instruct", "exact", "strict_verified", "auto", "#14b8a6"),
    "qwen3-coder": TokenizerFamilySpec("qwen3-coder", "Qwen3 Coder family", "Qwen/Qwen3-Coder-480B-A35B-Instruct", "exact", "strict_verified", "auto", "#0f766e"),
    "gpt-oss": TokenizerFamilySpec("gpt-oss", "OpenAI gpt-oss family", "openai/gpt-oss-20b", "exact", "strict_verified", "space_prefix", "#f97316"),
    "glm-4.5-air": TokenizerFamilySpec("glm-4.5-air", "GLM 4.5 Air family", "zai-org/GLM-4.5-Air-FP8", "exact", "strict_verified", "auto", "#f59e0b"),
    "nemotron-3-nano-30b": TokenizerFamilySpec("nemotron-3-nano-30b", "Nemotron 3 Nano family", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-FP8", "exact", "strict_verified", "auto", "#6366f1"),
    "nemotron-3-super": TokenizerFamilySpec("nemotron-3-super", "Nemotron 3 Super family", "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8", "exact", "strict_verified", "auto", "#4338ca"),
    "nemotron-nano-9b-v2": TokenizerFamilySpec("nemotron-nano-9b-v2", "Nemotron Nano 9B V2 family", "nvidia/NVIDIA-Nemotron-Nano-9B-v2", "exact", "strict_verified", "auto", "#818cf8"),
    "trinity-large": TokenizerFamilySpec("trinity-large", "Trinity Large family", "arcee-ai/Trinity-Large-Preview", "exact", "strict_verified", "auto", "#ec4899"),
    "trinity-mini": TokenizerFamilySpec("trinity-mini", "Trinity Mini family", "arcee-ai/Trinity-Mini", "exact", "strict_verified", "auto", "#db2777"),
    "gemma-2": TokenizerFamilySpec("gemma-2", "Gemma family", "unsloth/gemma-2-2b", "proxy", "proxy", "sentencepiece", "#e377c2"),
    "command-r": TokenizerFamilySpec("command-r", "Command R family (BLOOM proxy)", "bigscience/bloom-560m", "proxy", "proxy", "gpt2_prefix", "#7f7f7f"),
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
