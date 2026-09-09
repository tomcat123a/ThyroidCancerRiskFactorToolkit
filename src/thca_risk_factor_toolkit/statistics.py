from __future__ import annotations

import pandas as pd

from .subject_records import YEAR_BIN_ORDER


def build_statistics_workbook(records: pd.DataFrame) -> dict[str, pd.DataFrame]:
    work = records.copy()
    for column in [
        "country_name",
        "continent_name",
        "study_type",
        "study_design",
        "label_1",
        "label_2",
        "label",
        "evidence_strength_grade_level",
        "object_endpoint_type",
    ]:
        if column in work.columns:
            work[column] = work[column].fillna("").astype(str).str.strip()

    overall_papers = (
        work[["_id", "publish_year", "year_bin", "study_type", "study_design", "country_name", "continent_name"]]
        .drop_duplicates()
    )
    overall_papers["publish_year_sort"] = pd.to_numeric(overall_papers["publish_year"], errors="coerce")
    overall_papers = overall_papers.sort_values(["publish_year_sort", "_id"], ascending=[True, True]).drop(
        columns=["publish_year_sort"]
    )

    paper_year_basic_stats = (
        overall_papers.groupby("year_bin", dropna=False)
        .agg(n_papers=("_id", "nunique"))
        .reset_index()
        .sort_values("year_bin", key=lambda series: series.map(_year_bin_sort_key))
    )

    study_type_stats = (
        overall_papers.groupby("study_type", dropna=False)
        .agg(n_papers=("_id", "nunique"))
        .reset_index()
        .sort_values(["n_papers", "study_type"], ascending=[False, True])
    )

    continent_year_bin_long = (
        work.groupby(["continent_name", "year_bin"], dropna=False)
        .agg(n_factors=("factor_key", "nunique"), n_papers=("_id", "nunique"))
        .reset_index()
        .rename(columns={"continent_name": "continent_norm"})
        .sort_values(["continent_norm", "year_bin"], key=lambda series: series.map(_sort_value))
    )

    continent_year_bin_pivot = (
        continent_year_bin_long.pivot(index="continent_norm", columns="year_bin", values="n_factors")
        .fillna(0)
        .reset_index()
    )

    country_top10 = (
        work.groupby("country_name", dropna=False)
        .agg(n_papers=("_id", "nunique"))
        .reset_index()
        .rename(columns={"country_name": "country_norm"})
        .sort_values(["n_papers", "country_norm"], ascending=[False, True])
        .head(10)
    )
    top10_names = set(country_top10["country_norm"].tolist())
    country_top10_year_bin_long = (
        work[work["country_name"].isin(top10_names)]
        .groupby(["country_name", "year_bin"], dropna=False)
        .agg(n_factors=("factor_key", "nunique"), n_papers=("_id", "nunique"))
        .reset_index()
        .rename(columns={"country_name": "country_norm"})
        .sort_values(["country_norm", "year_bin"], key=lambda series: series.map(_sort_value))
    )
    country_top10_year_bin_pivot = (
        country_top10_year_bin_long.pivot(index="country_norm", columns="year_bin", values="n_factors")
        .fillna(0)
        .reset_index()
    )

    label1_overall = _build_group_table(work, "label_1")
    label1_year_bin = _build_group_year_table(work, "label_1")
    evidence_grade_overall = _build_group_table(work, "evidence_strength_grade_level")
    evidence_grade_year_bin = _build_group_year_table(work, "evidence_strength_grade_level")
    umls_coverage_summary = _build_group_table(work, "umls_match_status")

    endpoint_top3_factors = (
        work.groupby(["object_endpoint_type", "factor_name", "factor_synonyms"], dropna=False)
        .agg(num_publish_paper=("_id", "nunique"))
        .reset_index()
    )
    endpoint_top3_factors["rank"] = endpoint_top3_factors.groupby("object_endpoint_type")["num_publish_paper"].rank(
        method="first", ascending=False
    )
    endpoint_top3_factors = endpoint_top3_factors[endpoint_top3_factors["rank"] <= 3].sort_values(
        ["object_endpoint_type", "rank", "factor_name"]
    )

    factor_synonym_catalog = (
        work[
            [
                "factor_name",
                "factor_synonyms",
                "factor_group_size",
                "label_1",
                "label_2",
                "label",
                "umls_term",
                "umls_cui",
                "umls_semantic_type",
            ]
        ]
        .drop_duplicates()
        .sort_values(["factor_name", "label_1", "label_2"])
    )

    return {
        "paper_year_basic_stats": paper_year_basic_stats,
        "study_type_stats": study_type_stats,
        "continent_year_bin_long": continent_year_bin_long,
        "continent_year_bin_pivot": continent_year_bin_pivot,
        "country_top10_papers": country_top10,
        "country_top10_year_bin_long": country_top10_year_bin_long,
        "country_top10_year_bin_pivot": country_top10_year_bin_pivot,
        "label1_overall": label1_overall,
        "label1_year_bin": label1_year_bin,
        "evidence_grade_overall": evidence_grade_overall,
        "evidence_grade_year_bin": evidence_grade_year_bin,
        "endpoint_top3_factors": endpoint_top3_factors,
        "factor_synonym_catalog": factor_synonym_catalog,
        "umls_coverage_summary": umls_coverage_summary,
    }


def _build_group_table(work: pd.DataFrame, field: str) -> pd.DataFrame:
    return (
        work.groupby(field, dropna=False)
        .agg(n_factors=("factor_key", "nunique"), n_papers=("_id", "nunique"))
        .reset_index()
        .sort_values(["n_factors", field], ascending=[False, True])
    )


def _build_group_year_table(work: pd.DataFrame, field: str) -> pd.DataFrame:
    table = (
        work.groupby([field, "year_bin"], dropna=False)
        .agg(n_factors=("factor_key", "nunique"), n_papers=("_id", "nunique"))
        .reset_index()
    )
    return table.sort_values([field, "year_bin"], key=lambda series: series.map(_sort_value))


def _sort_value(value: object) -> tuple[int, str]:
    text = str(value).strip()
    if text in YEAR_BIN_ORDER:
        return (0, f"{YEAR_BIN_ORDER.index(text):02d}")
    return (1, text.lower())


def _year_bin_sort_key(value: object) -> int:
    text = str(value).strip()
    if text in YEAR_BIN_ORDER:
        return YEAR_BIN_ORDER.index(text)
    return len(YEAR_BIN_ORDER) + 1
