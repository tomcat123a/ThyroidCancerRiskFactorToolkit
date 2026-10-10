"""Manuscript-facing bibliometric statistics.

These tables complement the Step 10 factor-level exports with paper-level
descriptive statistics (publication counts by year bin, study type, continent
and country) and the synonym/UMLS catalogs described in the manuscript's
"Bibliometric characteristics" and "Semantic taxonomy" sections.
"""

from __future__ import annotations

import pandas as pd

from .factor_scoring import YEAR_BINS, year_to_bin


def _year_bin_sort_key(value: object) -> int:
    text = str(value).strip()
    order = [*YEAR_BINS, "other_year", "MISSING"]
    return order.index(text) if text in order else len(order) + 1


def build_paper_statistics(papers: pd.DataFrame) -> dict[str, pd.DataFrame]:
    work = papers.copy()
    if "publish_year" in work.columns:
        work["year_bin"] = work["publish_year"].map(year_to_bin)
    for column in ["study_type", "continent_name", "country_name"]:
        if column in work.columns:
            work[column] = work[column].fillna("").astype(str).str.strip()

    paper_id = "_source_row_id" if "_source_row_id" in work.columns else "TI"
    overall = work[[paper_id, "year_bin", "study_type", "continent_name", "country_name"]].drop_duplicates()

    paper_year_basic_stats = (
        overall.groupby("year_bin", dropna=False)
        .agg(n_papers=(paper_id, "nunique"))
        .reset_index()
        .sort_values("year_bin", key=lambda series: series.map(_year_bin_sort_key))
    )

    study_type_stats = (
        overall.groupby("study_type", dropna=False)
        .agg(n_papers=(paper_id, "nunique"))
        .reset_index()
        .sort_values(["n_papers", "study_type"], ascending=[False, True])
    )

    continent_long = (
        overall.groupby(["continent_name", "year_bin"], dropna=False)
        .agg(n_papers=(paper_id, "nunique"))
        .reset_index()
        .rename(columns={"continent_name": "continent_norm"})
    )
    continent_pivot = continent_long.pivot(index="continent_norm", columns="year_bin", values="n_papers").fillna(0).reset_index()

    country_counts = (
        overall.groupby("country_name", dropna=False)
        .agg(n_papers=(paper_id, "nunique"))
        .reset_index()
        .rename(columns={"country_name": "country_norm"})
        .sort_values(["n_papers", "country_norm"], ascending=[False, True])
    )
    country_top10 = country_counts.head(10)

    return {
        "paper_year_basic_stats": paper_year_basic_stats,
        "study_type_stats": study_type_stats,
        "continent_year_bin_long": continent_long,
        "continent_year_bin_pivot": continent_pivot,
        "country_top10_papers": country_top10,
    }


def build_synonym_catalog(factor_map: pd.DataFrame) -> pd.DataFrame:
    columns = ["factor_id", "factor_key", "factor_name", "factor_synonyms", "factor_group_size", "label_1", "label_2", "label_3"]
    available = [c for c in columns if c in factor_map.columns]
    return factor_map[available].drop_duplicates("factor_id").sort_values(["label_1", "label_3", "factor_name"])


def build_umls_coverage(umls_match: pd.DataFrame) -> pd.DataFrame:
    matched = umls_match["umls_matcher_best_cui"].astype(str).str.strip().ne("")
    return pd.DataFrame([{
        "n_total_factors": len(umls_match),
        "n_matched_factors": int(matched.sum()),
        "n_unmatched_factors": int((~matched).sum()),
        "umls_coverage_ratio": float(matched.mean()) if len(umls_match) else 0.0,
    }])
