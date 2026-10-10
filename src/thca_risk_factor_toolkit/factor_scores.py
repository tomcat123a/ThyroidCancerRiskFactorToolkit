"""Four-component composite evidence score (legacy formula, inclusive bins).

The composite score is a weighted sum of Z-standardized components::

    score = 2*z(log(n_paper)) + 1*z(log(n_sample)) + 1*z(statsig) + 2*z(evigrade)

Standardization parameters are computed once over the full factor table
(``ddof=0``) and reused for year and label slices.
"""

from __future__ import annotations

import pandas as pd

from .factor_data import FACTOR_COLUMNS, LABELS, YEAR_BINS
from .factor_scoring import (
    W_EVIGRADE,
    W_NUM,
    W_SIZE,
    W_STATSIG,
    compute_global_score_stats,
    safe_log,
    to_key,
)
from .table_export import Progress

COMPONENTS = [
    ("log_num_publish_paper", "num", W_NUM),
    ("log_total_sample_size", "size", W_SIZE),
    ("avg_statsig_grade", "statsig", W_STATSIG),
    ("avg_evigrade", "evigrade", W_EVIGRADE),
]
GROUP_FIELDS = [*LABELS, "evidence_strength_grade_level", "disease", "object_endpoint_type"]


def _zscore(value: float, mean: float, std: float) -> float:
    if std <= 0:
        return 0.0
    return float((value - mean) / std)


def paper_factor_rows(detail: pd.DataFrame, dimensions: list) -> pd.DataFrame:
    keys = list(dict.fromkeys([*dimensions, "_source_row_id", "factor_id"]))
    return detail.groupby(keys, dropna=False, sort=True).agg(
        sample_size_int=("sample_size_int", "max"),
        statsig_grade=("study_significance_numeric_grade", "max"),
        evigrade=("evidence_numeric_grade", "mean"),
        publish_year=("publish_year", "min"),
        n_triplets=("triplet_index", "size"),
    ).reset_index()


def aggregate_factors(detail: pd.DataFrame, dimensions: list) -> pd.DataFrame:
    per_paper = paper_factor_rows(detail, dimensions)
    factors = per_paper.groupby([*dimensions, "factor_id"], dropna=False, sort=True).agg(
        num_publish_paper=("_source_row_id", "nunique"),
        total_sample_size=("sample_size_int", "sum"),
        avg_statsig_grade=("statsig_grade", "mean"),
        avg_evigrade=("evigrade", "mean"),
    ).reset_index()
    metadata = detail[FACTOR_COLUMNS].drop_duplicates("factor_id")
    return factors.merge(metadata, on="factor_id", how="left", validate="many_to_one")


def add_scores(frame: pd.DataFrame, stats: tuple) -> pd.DataFrame:
    result = frame.copy()
    result["log_num_publish_paper"] = result["num_publish_paper"].map(lambda n: safe_log(max(n, 1)))
    result["log_total_sample_size"] = result["total_sample_size"].map(lambda n: safe_log(max(n, 1)))
    for index, (column, short, weight) in enumerate(COMPONENTS):
        mean, std = stats[index * 2:index * 2 + 2]
        result[f"z_{column}"] = result[column].map(lambda value: _zscore(float(value), mean, std))
        result[f"score_{short}_component"] = result[f"z_{column}"] * weight
    result["score"] = result[[f"score_{short}_component" for _, short, _ in COMPONENTS]].sum(axis=1)
    return result


def top_factors(frame: pd.DataFrame, dimensions: list, limit: int, by_score: bool = False) -> pd.DataFrame:
    metrics = ["score", "num_publish_paper"] if by_score else ["num_publish_paper", "score"]
    result = frame.sort_values(
        [*dimensions, *metrics, "factor_name", "factor_id"],
        ascending=[True] * len(dimensions) + [False, False, True, True],
    ).copy()
    result["rank"] = (
        result.groupby(dimensions, dropna=False).cumcount() + 1
        if dimensions else range(1, len(result) + 1)
    )
    return result[result["rank"].le(limit)].copy()


def counts(detail: pd.DataFrame, dimensions: list) -> pd.DataFrame:
    return detail.groupby(dimensions, dropna=False).agg(
        n_factors=("factor_id", "nunique"), n_papers=("_source_row_id", "nunique"),
    ).reset_index()


def first_years(detail: pd.DataFrame) -> pd.DataFrame:
    papers = detail[["factor_id", "_source_row_id", "publish_year"]].drop_duplicates()
    first = papers.groupby("factor_id")["publish_year"].min().rename("first_published_year")
    annual = papers.dropna(subset=["publish_year"]).groupby(
        ["factor_id", "publish_year"]
    ).size().rename("n").reset_index().sort_values(["factor_id", "publish_year"])
    annual["cumulative_n"] = annual.groupby("factor_id")["n"].cumsum()
    hundred = annual.loc[annual["cumulative_n"].ge(100)].groupby(
        "factor_id"
    )["publish_year"].min().rename("100_published_year")
    return first.to_frame().join(hundred).reset_index()


def compute_tables(detail: pd.DataFrame, qa: pd.DataFrame) -> tuple[dict, dict, dict]:
    detail = detail.copy()
    for column in GROUP_FIELDS:
        detail[column] = detail[column].map(to_key)

    overall = aggregate_factors(detail, [])
    stats = compute_global_score_stats(overall)
    overall = add_scores(overall, stats).sort_values(
        ["score", "num_publish_paper", "factor_name", "factor_id"], ascending=[False, False, True, True]
    )
    overall = overall.merge(first_years(detail), on="factor_id", validate="one_to_one", how="left")

    five = detail[detail["year_bin"].isin(YEAR_BINS)].copy()
    year_scores = add_scores(aggregate_factors(five, ["year_bin"]), stats)
    label_year = add_scores(aggregate_factors(five, ["label_1", "year_bin"]), stats)

    geo_dims = ["continent_norm", "year_bin", "label_1"]
    geo_papers = paper_factor_rows(five, geo_dims)
    geo_baseline = geo_papers.groupby("factor_id", dropna=False).agg(
        num_publish_paper=("_source_row_id", "count"),
        total_sample_size=("sample_size_int", "sum"),
        avg_statsig_grade=("statsig_grade", "mean"),
        avg_evigrade=("evigrade", "mean"),
    ).reset_index()
    geo_stats = compute_global_score_stats(geo_baseline)
    geo_scores = add_scores(aggregate_factors(five, geo_dims), geo_stats)
    geo_summary = counts(five, geo_dims).rename(columns={"continent_norm": "continent"})

    params = pd.DataFrame([
        {"component": column, "mean": stats[i * 2], "std_ddof0": stats[i * 2 + 1], "weight": weight}
        for i, (column, _, weight) in enumerate(COMPONENTS)
    ])
    factor_labels = detail[["factor_id", *LABELS]].drop_duplicates("factor_id")
    year_score_top10 = top_factors(year_scores, ["year_bin"], 10, by_score=True)
    year_score_top10 = year_score_top10.merge(factor_labels, on="factor_id", how="left", validate="many_to_one")
    columns = list(year_score_top10.columns)
    for label in reversed(LABELS):
        columns.remove(label)
        columns.insert(columns.index("factor_id") + 1, label)
    year_score_top10 = year_score_top10[columns]

    score_tables = {
        "label_1_yearbin_top10": top_factors(label_year, ["label_1", "year_bin"], 10),
        "factor_score_overall": overall,
        "factor_score_by_year_bin": year_scores,
        "year_score_top10": year_score_top10,
        "global_score_parameters": params,
        "qa_overview": qa,
    }
    geo_tables = {
        "continent_year_label1_top10": top_factors(geo_scores, geo_dims, 10).rename(
            columns={"continent_norm": "continent"}
        ),
        "continent_year_label1_summary": geo_summary,
        "continent_year_label1_all": geo_scores.rename(columns={"continent_norm": "continent"}),
        "geo_score_parameters": pd.DataFrame([
            {"component": column, "mean": geo_stats[i * 2], "std_ddof0": geo_stats[i * 2 + 1], "weight": weight}
            for i, (column, _, weight) in enumerate(COMPONENTS)
        ]),
    }
    stat_tables = {
        "factor_summary": pd.DataFrame([{
            "n_distinct_factors_after_synonym_merge": overall["factor_id"].nunique(),
            "n_papers": detail["_source_row_id"].nunique(),
        }]),
        "factor_synonyms_list": overall[FACTOR_COLUMNS],
        "qa_overview": qa,
    }
    for field, prefix in [("continent_norm", "continent"), ("country_norm", "country_top10")]:
        subset = detail
        if field == "country_norm":
            countries = detail.groupby(field)["_source_row_id"].nunique().rename("n_papers").reset_index()
            countries = countries.sort_values(["n_papers", field], ascending=[False, True]).head(10)
            stat_tables["country_top10_papers"] = countries
            subset = detail[detail[field].isin(countries[field])]
        grouped = counts(subset, [field, "year_bin"])
        stat_tables[f"{prefix}_year_bin_long"] = grouped
        pivot = grouped.pivot(index=field, columns="year_bin", values="n_factors")
        stat_tables[f"{prefix}_year_bin_pivot"] = pivot.reindex(
            columns=[*YEAR_BINS, "other_year", "MISSING"]
        ).fillna(0).astype(int).reset_index()

    progress = Progress("Classification groupby", len(GROUP_FIELDS))
    for index, field in enumerate(GROUP_FIELDS, 1):
        prefix = "evidence_grade" if field == "evidence_strength_grade_level" else field
        totals = counts(detail, [field])
        stat_tables[f"{prefix}_overall"] = totals
        stat_tables[f"{prefix}_by_year_bin"] = counts(detail, [field, "year_bin"])
        for dimensions, suffix in [([field], "top5_factors"), ([field, "year_bin"], "year_top5")]:
            sub = detail if len(dimensions) == 1 else five
            scored = add_scores(aggregate_factors(sub, dimensions), stats)
            top = top_factors(scored, dimensions, 5)
            denominators = counts(sub, dimensions)[[*dimensions, "n_papers"]].rename(
                columns={"n_papers": "group_total_papers"}
            )
            top = top.merge(denominators, on=dimensions, how="left", validate="many_to_one")
            top["paper_ratio"] = top["num_publish_paper"] / top["group_total_papers"]
            stat_tables[f"{prefix}_{suffix}"] = top
        progress.report(index)

    return score_tables, geo_tables, stat_tables
