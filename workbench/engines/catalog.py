"""Catalog engine wrappers for typed requests/results."""

from __future__ import annotations

from workbench.diagnostics import render_markdown
from workbench.model_registry import build_tokenizer_catalog
from workbench.token_tax import catalog_appendix, refresh_catalog
from workbench.types import CatalogRequest, CatalogResult


def run_catalog_request(request: CatalogRequest) -> CatalogResult:
    if request.refresh_live:
        refresh_catalog()
    rows = build_tokenizer_catalog(include_proxy=request.include_proxy)
    return CatalogResult(
        rows=rows,
        appendix=catalog_appendix(request.include_proxy),
        diagnostics=render_markdown(),
    )
