from __future__ import annotations

import re
from typing import Iterable

import pandas as pd

from .io_utils import safe_text

YEAR_BIN_ORDER = ["<=2000", "2001-2005", "2006-2010", "2011-2015", "2016-2026", "unknown"]


def build_triplet_records(df: pd.DataFrame) -> pd.DataFrame:
    slots = _detect_triplet_slots(df.columns)
    rows: list[dict[str, object]] = []
    for _, source_row in df.iterrows():
        paper_meta = _paper_meta_from_row(source_row)
        for slot in slots:
            subject_name = safe_text(source_row.get(f"causal_triplets_{slot}.subject.name"))
            if not subject_name:
                continue
            rows.append(
                {
                    **paper_meta,
                    "triplet_slot": slot,
                    "subject_name": subject_name,
                    "subject_category_raw": safe_text(source_row.get(f"causal_triplets_{slot}.subject.category")),
                    "relation": safe_text(source_row.get(f"causal_triplets_{slot}.predicate.relation")),
                    "direction": safe_text(source_row.get(f"causal_triplets_{slot}.predicate.direction")),
                    "disease": safe_text(source_row.get(f"causal_triplets_{slot}.object.disease")),
                    "object_endpoint_type": safe_text(source_row.get(f"causal_triplets_{slot}.object.object_endpoint_type")),
                    "evidence_strength_grade_level": safe_text(
                        source_row.get(f"causal_triplets_{slot}.object.evidence_strength_grade_level")
                    ),
                }
            )
    result = pd.DataFrame(rows)
    if result.empty:
        return pd.DataFrame(
            columns=[
                "_id",
                "publish_year",
                "year_bin",
                "study_type",
                "study_design",
                "country_name",
                "continent_name",
                "study_metadata.country_or_region",
                "sample_size",
                "subject_name",
                "subject_category_raw",
                "relation",
                "direction",
                "disease",
                "object_endpoint_type",
                "evidence_strength_grade_level",
            ]
        )
    result["subject_name_norm"] = result["subject_name"].map(normalize_text)
    return result


def _detect_triplet_slots(columns: Iterable[object]) -> list[int]:
    pattern = re.compile(r"causal_triplets_(\d+)\.subject\.name$")
    slots = []
    for name in columns:
        match = pattern.search(str(name))
        if match:
            slots.append(int(match.group(1)))
    return sorted(set(slots))


def _paper_meta_from_row(row: pd.Series) -> dict[str, object]:
    publish_year = _extract_publish_year(row)
    return {
        "_id": row.get("_id"),
        "TI": safe_text(row.get("TI")),
        "SO": safe_text(row.get("SO")),
        "publish_year": publish_year,
        "year_bin": build_year_bin(publish_year),
        "study_type": safe_text(row.get("study_type")),
        "study_design": safe_text(row.get("study_metadata.study_design")),
        "country_name": safe_text(row.get("country_name")),
        "continent_name": safe_text(row.get("continent_name")),
        "study_metadata.country_or_region": safe_text(row.get("study_metadata.country_or_region")),
        "sample_size": safe_text(row.get("study_population.sample_size")),
    }


def _extract_publish_year(row: pd.Series) -> int | None:
    for key in ["publish_year", "PY", "YR", "DA"]:
        raw = safe_text(row.get(key))
        match = re.search(r"(19|20)\d{2}", raw)
        if match:
            return int(match.group(0))
    return None


def build_year_bin(year: int | None) -> str:
    if year is None:
        return "unknown"
    if year <= 2000:
        return "<=2000"
    if year <= 2005:
        return "2001-2005"
    if year <= 2010:
        return "2006-2010"
    if year <= 2015:
        return "2011-2015"
    return "2016-2026"


def normalize_text(value: object) -> str:
    text = safe_text(value).lower()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
