"""Catalog view-model helpers."""

from __future__ import annotations

from workbench.viewmodels.feedback import mapping_quality_label


def catalog_display_rows(rows: list[dict]) -> list[dict]:
    display_rows: list[dict] = []
    for row in rows:
        free_models = row.get("free_models", [])
        aa_matches = row.get("aa_matches", [])
        display_rows.append({
            "Tokenizer Family": row["label"],
            "Tokenizer Key": row["tokenizer_key"],
            "Tokenizer Source": row["tokenizer_source"],
            "Mapping": mapping_quality_label(row["mapping_quality"]),
            "Free Models": row.get("free_model_count", len(free_models)),
            "Free Model Examples": ", ".join(model["label"] for model in free_models) or "None attached",
            "AA Benchmarks": row.get("aa_match_count", len(aa_matches)),
            "AA Match Examples": ", ".join(match["label"] for match in aa_matches) or "No benchmark match",
            "Min $/1M In": row.get("min_input_per_million"),
            "Max Context": row.get("max_context_window"),
            "Provenance": row["provenance"],
        })
    return display_rows
