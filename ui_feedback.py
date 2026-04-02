"""Shared UI feedback and view-model helpers for the workbench."""

from __future__ import annotations


def build_chart_help_html(title: str, body: str) -> str:
    import html

    return (
        f'<div class="chart-help"><strong>{html.escape(title)}</strong>'
        f"<p>{html.escape(body)}</p></div>"
    )


def build_empty_state_markdown(title: str, message: str) -> str:
    return f"**{title}**\n\n{message}"


def build_runtime_error_markdown(prefix: str, error: str) -> str:
    return f"{prefix}\n\n**Runtime error:** {error}"


def mapping_quality_label(mapping_quality: str) -> str:
    return "Exact tokenizer mapping" if mapping_quality == "exact" else "Proxy tokenizer mapping"
