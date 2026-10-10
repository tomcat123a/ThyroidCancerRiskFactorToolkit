"""Detail join from the semantic-merged synonym factor file.

Reproduces ``factor_data_semantic.build_detail_semantic``.  Instead of loading
the Step 08 labels plus the Step 09 manifest JSON, it reads the second-round
consolidated ``09_factor_label_associations_semantic_merged_v2.csv`` (already
exploded to one row per ``subject_name``) and treats it as the authoritative
synonym grouping.  The produced ``detail`` frame feeds the scoring and guideline
modules unchanged.
"""

from __future__ import annotations

import pandas as pd

from .factor_data import extract_source_triplets
from .factor_scoring import YEAR_BINS


def build_detail_semantic(
    papers: pd.DataFrame,
    factor_map: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Join source triplets with the semantic factor map; return (detail, qa)."""
    source = extract_source_triplets(papers)
    detail = source.merge(factor_map, on="subject_name", how="left", validate="many_to_one")
    if detail["factor_id"].isna().any():
        missing = sorted(detail.loc[detail["factor_id"].isna(), "subject_name"].unique())
        raise ValueError(f"部分源 subject 缺少同义词因子：{missing[:10]}")

    qa = pd.DataFrame([
        {"metric": "source_papers", "value": len(papers)},
        {"metric": "source_triplets", "value": len(source)},
        {"metric": "joined_triplets", "value": len(detail)},
        {"metric": "distinct_factors", "value": detail["factor_id"].nunique()},
        {"metric": "missing_p_value_triplets", "value": int(detail["p_value_num"].isna().sum())},
        {"metric": "zero_evidence_triplets", "value": int(detail["evidence_numeric_grade"].eq(0).sum())},
        {"metric": "zero_sample_size_papers", "value": detail.loc[
            detail["sample_size_int"].eq(0), "_source_row_id"
        ].nunique()},
        {"metric": "outside_five_bins_papers", "value": detail.loc[
            ~detail["year_bin"].isin(YEAR_BINS), "_source_row_id"
        ].nunique()},
    ])
    return detail, qa
