from __future__ import annotations

import json

import pandas as pd

from .config import AppConfig
from .io_utils import read_excel
from .subject_records import normalize_text


def match_umls(records: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    lexicon = _load_umls_lexicon(config.demo_umls_lexicon_csv)
    work = records.copy()
    work["umls_term"] = work["subject_name"].map(lambda value: _match_one(str(value), lexicon)[0])
    work["umls_cui"] = work["subject_name"].map(lambda value: _match_one(str(value), lexicon)[1])
    work["umls_semantic_type"] = work["subject_name"].map(lambda value: _match_one(str(value), lexicon)[2])
    work["umls_match_status"] = work["umls_cui"].map(lambda value: "matched" if str(value).strip() else "unmatched")
    return work


def _load_umls_lexicon(path) -> list[dict[str, str]]:
    if str(path).lower().endswith(".csv"):
        frame = pd.read_csv(path, dtype=object)
    else:
        frame = read_excel(path)
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            {
                "canonical_term": str(row.get("canonical_term", "")).strip(),
                "cui": str(row.get("cui", "")).strip(),
                "semantic_type": str(row.get("semantic_type", "")).strip(),
                "synonyms": str(row.get("synonyms", "")).strip(),
            }
        )
    return rows


def _match_one(subject_name: str, lexicon: list[dict[str, str]]) -> tuple[str, str, str]:
    normalized_subject = normalize_text(subject_name)
    best: tuple[str, str, str] = ("", "", "")
    for item in lexicon:
        candidates = [item["canonical_term"]]
        if item["synonyms"]:
            candidates.extend([part.strip() for part in item["synonyms"].split("|") if part.strip()])
        for candidate in candidates:
            normalized_candidate = normalize_text(candidate)
            if normalized_candidate and normalized_candidate == normalized_subject:
                return (item["canonical_term"], item["cui"], item["semantic_type"])
            if normalized_candidate and normalized_candidate in normalized_subject:
                best = (item["canonical_term"], item["cui"], item["semantic_type"])
    return best
