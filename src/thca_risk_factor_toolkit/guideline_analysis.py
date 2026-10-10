"""Guideline-oriented concordance evaluation and gap analysis.

Reproduces the guideline module.  Each normalized risk factor (synonym group) is
compared against expert-curated guideline positive-label groups using a
deterministic two-stage procedure: an exact-group match, then (under the
``shared_term`` policy) a shared-term match.  Coverage is reported at the factor
level and stratified by composite-score percentile and taxonomy level.

Important: ``in_guideline_* == 0`` means "no legacy positive hit", which does
NOT prove the factor is absent from the guideline.
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict

import pandas as pd

from .factor_data import LABELS, YEAR_BINS
from .factor_scoring import year_to_bin
from .table_export import Progress

EXCLUDED_GUIDELINES = {"ESMO 2019"}
IGNORED_LABEL_FILES = {"nan.json"}


def normalized_term(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def load_legacy_labels(directory) -> tuple[dict, pd.DataFrame]:
    folders = sorted(
        folder for folder in directory.iterdir()
        if folder.is_dir() and folder.name not in EXCLUDED_GUIDELINES
    )
    if not folders:
        raise ValueError(f"No guideline folders found (excluding {sorted(EXCLUDED_GUIDELINES)}): {directory}")
    result, inventory = {}, []
    files = [
        (folder, path)
        for folder in folders
        for path in sorted(folder.glob("*.json"))
        if path.name not in IGNORED_LABEL_FILES
    ]
    for folder in folders:
        label_files = [path for path in folder.glob("*.json") if path.name not in IGNORED_LABEL_FILES]
        if not label_files:
            raise ValueError(f"Guideline folder has no JSON label files: {folder}")
        year = re.search(r"(?:19|20)\d{2}", folder.name)
        if not year:
            raise ValueError(f"Guideline name needs a publication year: {folder.name}")
        result[folder.name] = {"year": int(year[0]), "groups": {}, "terms": defaultdict(set)}
    progress = Progress("Guideline label files", len(files))
    for index, (folder, path) in enumerate(files, 1):
        groups = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(groups, list):
            raise ValueError(f"Guideline JSON must be list[list[str]]: {path}")
        target = result[folder.name]
        for group in groups:
            if not isinstance(group, list) or not group or not all(
                isinstance(term, str) and term.strip() for term in group
            ):
                raise ValueError(f"Malformed guideline group: {path}")
            key = tuple(sorted({normalized_term(term) for term in group}))
            target["groups"].setdefault(key, set()).add(path.name)
            for term in key:
                target["terms"][term].add(key)
        inventory.append({
            "guideline": folder.name, "year": target["year"],
            "source_file": path.name, "n_positive_groups": len(groups),
        })
        progress.report(index)
    return result, pd.DataFrame(inventory)


def annotate(overall: pd.DataFrame, directory, policy: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    legacy, inventory = load_legacy_labels(directory)
    if policy not in {"shared_term", "exact_group"}:
        raise ValueError("guideline_match_policy must be shared_term or exact_group.")
    result = overall.copy()
    normalized = [
        tuple(sorted({normalized_term(term) for term in json.loads(value)}))
        for value in result["factor_key"]
    ]
    audit, flag_columns, inclusion_years = [], [], []
    progress = Progress("Guideline factor matching", len(legacy))
    for index, (name, source) in enumerate(legacy.items(), 1):
        slug = re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_")
        flag = f"in_guideline_{slug}"
        flag_columns.append(flag)
        flags, statuses = [], []
        for factor_id, key in zip(result["factor_id"], normalized):
            exact = key in source["groups"]
            hits = {key} if exact else set()
            if not exact and policy == "shared_term":
                for term in key:
                    hits.update(source["terms"].get(term, set()))
            status = "exact_group" if exact else ("shared_term" if hits else "no_legacy_hit")
            flags.append(int(bool(hits)))
            statuses.append(status)
            for matched in sorted(hits):
                audit.append({
                    "factor_id": factor_id, "guideline": name, "match_method": status,
                    "matched_terms": json.dumps(sorted(set(key).intersection(matched)), ensure_ascii=False),
                    "legacy_group": json.dumps(list(matched), ensure_ascii=False),
                    "source_files": " | ".join(sorted(source["groups"][matched])),
                })
        result[flag] = flags
        result[f"match_status_{slug}"] = statuses
        inclusion_years.append(pd.Series(
            [source["year"] if hit else float("nan") for hit in flags], index=result.index
        ))
        progress.report(index)

    result["any_guideline"] = result[flag_columns].max(axis=1)
    result["guideline_match_policy"] = policy
    result["guideline_status"] = result["any_guideline"].map({
        1: "matched_legacy_positive", 0: "no_legacy_hit_not_confirmed_absent",
    })
    result["first_inclusion_year"] = pd.concat(inclusion_years, axis=1).min(axis=1)
    result["inclusion_lag_years"] = result["first_inclusion_year"] - result["first_published_year"]
    result["negative_lag_flag"] = result["inclusion_lag_years"].lt(0).astype(int)
    result["inclusion_lag_years"] = result["inclusion_lag_years"].clip(lower=0)
    audit_frame = pd.DataFrame(audit, columns=[
        "factor_id", "guideline", "match_method", "matched_terms", "legacy_group", "source_files",
    ])
    return result, audit_frame, inventory


def coverage_rows(frame: pd.DataFrame, extra: dict | None = None) -> list[dict]:
    rows = []
    for column in [c for c in frame if c.startswith("in_guideline_")] + ["any_guideline"]:
        count = int(frame[column].sum())
        rows.append({
            **(extra or {}), "guideline": column.removeprefix("in_guideline_"),
            "n_total": len(frame), "n_in_guideline": count,
            "n_no_legacy_hit": len(frame) - count,
            "ratio_in_guideline": count / len(frame) if len(frame) else float("nan"),
            "interpretation": "legacy_positive_match_rate_not_verified_absence",
        })
    return rows


def lag_summary(frame: pd.DataFrame, group: str) -> dict:
    lag = frame["inclusion_lag_years"].dropna()
    return {
        "group": group, "n_total": len(frame),
        "n_included_any_guideline": int(frame["any_guideline"].sum()),
        "included_ratio": float(frame["any_guideline"].mean()) if len(frame) else float("nan"),
        "n_with_lag": len(lag), "avg_lag_years": lag.mean(),
        "median_lag_years": lag.median(),
        "n_negative_lag": int(frame["negative_lag_flag"].sum()),
        "avg_nonnegative_lag_years": lag.mean(),
    }


def compute_guideline_tables(overall: pd.DataFrame, detail: pd.DataFrame, directory, policy: str = "shared_term") -> dict:
    annotated, audit, inventory = annotate(overall, directory, policy)
    tables = {
        "factor_score_overall": annotated,
        "guideline_coverage": pd.DataFrame(coverage_rows(annotated)),
        "guideline_match_audit": audit,
        "guideline_source_inventory": inventory,
    }
    rows = coverage_rows(annotated, {"scope": "all", "top_ratio": 1.0})
    for ratio in [0.10, 0.05, 0.02, 0.01]:
        count = max(1, math.ceil(len(annotated) * ratio))
        subset = annotated.nlargest(count, "score", keep="all")
        rows.extend(coverage_rows(subset, {"scope": f"top_{ratio:.0%}", "top_ratio": ratio}))
    tables["coverage_by_score_percentile"] = pd.DataFrame(rows)
    for label in LABELS:
        associations = detail[[label, "factor_id"]].drop_duplicates()
        associated = associations.merge(annotated, on="factor_id", validate="many_to_one", how="left")
        rows = []
        for name, subset in associated.groupby(label, sort=True):
            rows.extend(coverage_rows(subset, {label: name}))
        tables[f"{label}_guideline_coverage"] = pd.DataFrame(rows)
    cohorts = annotated["first_published_year"].map(year_to_bin)
    lag_rows = [lag_summary(annotated, "all")]
    for year_bin in YEAR_BINS:
        lag_rows.append(lag_summary(annotated[cohorts.eq(year_bin)], year_bin))
    first = annotated["first_published_year"]
    lag_rows.extend([
        lag_summary(annotated[first.ge(2010)], "first_pub>=2010"),
        lag_summary(annotated[first.between(2000, 2009)], "first_pub_2000_2009"),
    ])
    tables["inclusion_lag_summary"] = pd.DataFrame(lag_rows)
    tables["per_factor_lag"] = annotated[[
        "factor_id", "factor_name", "score", "first_published_year", "100_published_year",
        "first_inclusion_year", "inclusion_lag_years", "negative_lag_flag", "any_guideline",
    ]]
    unmatched = annotated[annotated["any_guideline"].eq(0)].sort_values(
        ["score", "num_publish_paper", "factor_name", "factor_id"], ascending=[False, False, True, True]
    )
    tables["top10_no_legacy_guideline_hit"] = unmatched.head(10)
    tables["top100_no_legacy_guideline_hit"] = unmatched.head(100)
    tables["unmatched_factors"] = unmatched
    return tables
