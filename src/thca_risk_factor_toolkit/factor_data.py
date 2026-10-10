"""Source-triplet extraction and numeric parsing for evidence quantification.

Reproduces ``factor_data.extract_source_triplets``.  The input is the
thyroid-filtered paper table with wide ``causal_triplets_N.*`` columns; the
output is one row per triplet with parsed sample size, p-value, significance
grade and evidence grade.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .factor_scoring import (
    evidence_grade_to_numeric,
    normalize_geo,
    parse_float_maybe,
    parse_sample_size_to_int,
    p_value_to_significance_grade,
    year_number,
    year_to_bin,
)
from .table_export import Progress, require_columns, text

YEAR_BINS = ["before_2000", "2001_2010", "2011_2015", "2016_2020", "2021_2025"]
LABELS = ["label_1", "label_2", "label_3"]
FACTOR_COLUMNS = ["factor_id", "factor_key", "factor_name", "factor_synonyms", "factor_group_size"]
TRIPLET_FIELDS = {
    "subject.name": "subject_name",
    "predicate.relation": "relation",
    "predicate.direction": "direction",
    "object.disease": "disease",
    "object.endpoint_type": "object_endpoint_type",
    "statistics.p_value": "p_value_raw",
    "statistics.statistical_significance": "statistical_significance_raw",
    "evidence_strength.grade_level": "evidence_strength_grade_level",
    "evidence_strength.grade_numeric_weight": "grade_numeric_weight_raw",
}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def extract_source_triplets(papers: pd.DataFrame) -> pd.DataFrame:
    """Expand wide triplet slots into one row per triplet with parsed fields."""
    require_columns(papers, [
        "_source_row_id", "publish_year", "study_population.sample_size", "country_name", "continent_name",
    ], "Source papers")
    papers = papers.copy()
    papers["_source_row_id"] = papers["_source_row_id"].map(text)
    if papers["_source_row_id"].eq("").any() or papers["_source_row_id"].duplicated().any():
        raise ValueError("Source _source_row_id must be nonempty and unique; refusing a many-to-many join.")

    slots = {}
    for column in papers.columns:
        match = re.fullmatch(r"causal_triplets?_(\d+)\.(.+)", column)
        if match:
            slots.setdefault(int(match[1]), {})[match[2]] = column

    frames = []
    progress = Progress("Source triplets", len(slots))
    for done, (slot, fields) in enumerate(sorted(slots.items()), 1):
        if "subject.name" not in fields:
            raise ValueError(f"Triplet slot {slot} lacks subject.name.")
        selected = papers.loc[papers[fields["subject.name"]].map(text).ne("")]
        frame = selected[[
            "_source_row_id", "publish_year", "study_population.sample_size", "country_name", "continent_name",
        ]].copy()
        frame["triplet_index"] = slot
        for source_field, target in TRIPLET_FIELDS.items():
            frame[target] = selected[fields[source_field]].map(text) if source_field in fields else ""
        frames.append(frame)
        progress.report(done)

    if not frames:
        raise ValueError("Source papers contain no causal_triplets_N columns.")
    result = pd.concat(frames, ignore_index=True)
    if result.empty:
        raise ValueError("Source papers contain no nonempty subjects.")
    if not result["disease"].str.contains("thyr", case=False, regex=False).all():
        raise ValueError("Source still contains non-thyroid triplets. Rebuild the thyroid filter before scoring.")

    result["publish_year_raw"] = result["publish_year"]
    result["publish_year"] = result["publish_year"].map(year_number)
    result["year_bin"] = result["publish_year"].map(year_to_bin)
    result["sample_size_int"] = result["study_population.sample_size"].map(parse_sample_size_to_int)
    result["country_norm"] = result["country_name"].map(normalize_geo)
    result["continent_norm"] = result["continent_name"].map(normalize_geo)
    result["p_value_num"] = result["p_value_raw"].map(parse_float_maybe)
    result["subject_min_p_value"] = result.groupby(
        ["_source_row_id", "subject_name"]
    )["p_value_num"].transform("min")
    result["study_significance_numeric_grade"] = result["subject_min_p_value"].map(
        p_value_to_significance_grade
    )
    result["evidence_numeric_grade"] = result["evidence_strength_grade_level"].map(evidence_grade_to_numeric)
    return result
