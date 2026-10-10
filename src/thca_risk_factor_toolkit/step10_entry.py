"""Step 10 entry: score factors and run guideline analysis (semantic variant).

Reproduces ``step10_factor_scores_semantic_entry.run``.  Takes the Step 07
paper table and the Step 09 semantic factor map, computes the composite score,
the year/continent/classification group statistics and the guideline-oriented
coverage, and writes CSV + Excel outputs under ``outputs/10_factor_scores_semantic``.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

from .step10_common import write_tables
from .step10_factor_data import FACTOR_COLUMNS, LABELS, YEAR_BINS
from .step10_factor_data_semantic import build_detail_semantic
from .step10_factor_scores import compute_tables, paper_factor_rows
from .step10_guidelines import compute_guideline_tables


def run_step10(
    papers: pd.DataFrame,
    factor_map: pd.DataFrame,
    guideline_dir: Path,
    output_dir: Path,
    *,
    policy: str = "shared_term",
) -> dict[str, Path]:
    detail, qa = build_detail_semantic(papers, factor_map)
    scores, geo, statistics = compute_tables(detail, qa)
    guidelines = compute_guideline_tables(scores["factor_score_overall"], detail, guideline_dir, policy)

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "scores": write_tables(output_dir, "10_factor_scores.xlsx", scores),
        "continent_year": write_tables(output_dir, "10_factor_scores_continent_year.xlsx", geo),
        "groupby": write_tables(output_dir, "10_factor_groupby_stats.xlsx", statistics),
        "guidelines": write_tables(output_dir, "10_guideline_analysis.xlsx", guidelines),
    }

    metadata = detail[FACTOR_COLUMNS].drop_duplicates("factor_id")
    factor_papers = paper_factor_rows(detail, []).merge(metadata, on="factor_id", validate="many_to_one")
    associations = detail[[*LABELS, *FACTOR_COLUMNS]].drop_duplicates()
    for filename, frame in [
        ("10_triplet_factor_audit.csv", detail),
        ("10_factor_paper_audit.csv", factor_papers),
        ("10_factor_label_associations.csv", associations),
    ]:
        path = output_dir / filename
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        paths[filename] = path

    manifest = output_dir / "10_run_manifest.json"
    record = {
        "run_id": uuid.uuid4().hex,
        "started_at": datetime.now().isoformat(),
        "status": "complete",
        "year_bins": YEAR_BINS,
        "score_method": "legacy_global_zscore_2_1_1_2_pvalue_and_grade_level",
        "synonym_source": "09_factor_label_associations_semantic_merged_v2",
        "guideline_match_policy": policy,
        "n_guideline_matched_factors": int(guidelines["factor_score_overall"]["any_guideline"].sum()),
        "outputs": {key: str(path) for key, path in paths.items()},
        "qa": qa.to_dict("records"),
    }
    manifest.write_text(
        __import__("json").dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    paths["manifest"] = manifest
    return paths
