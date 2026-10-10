"""UMLS-style normalization of risk-factor synonym groups.

Reproduces the ``QuickUMLS`` matching described in the manuscript and the
reuse logic of ``match_umls_subject_and_synonym_entry.py``.  For each synonym
group (``factor_key``) the best matching UMLS concept is selected: candidate
synonyms are matched against a concept lexicon, deduplicated by CUI, and the
highest-similarity candidate wins.  The public repository ships a small demo
lexicon (``data/demo_resources/umls_concepts_demo.csv``); the full pipeline uses
a licensed UMLS vocabulary export.
"""

from __future__ import annotations

import json
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

import pandas as pd

from .common import normalized_text

# QuickUMLS threshold from the manuscript (discard matches below 0.90).
SIMILARITY_THRESHOLD = 0.90

UMLS_COLUMNS = [
    "factor_id", "factor_key", "factor_name", "matched_synonym",
    "umls_matcher_match_count", "umls_matcher_best_cui", "umls_matcher_best_term",
    "umls_matcher_best_preferred", "umls_matcher_best_similarity",
    "umls_matcher_best_semtypes", "umls_matcher_all_cui",
    "umls_matcher_all_preferred", "umls_matcher_all_semtypes",
]


def load_umls_lexicon(path) -> List[Dict[str, str]]:
    frame = pd.read_csv(path, dtype=object, keep_default_na=False)
    rows = []
    for _, row in frame.iterrows():
        rows.append({
            "canonical_term": normalized_text(row.get("canonical_term")),
            "cui": normalized_text(row.get("cui")),
            "semantic_type": normalized_text(row.get("semantic_type")),
            "synonyms": normalized_text(row.get("synonyms")),
        })
    return rows


def _lexicon_terms(item: Dict[str, str]) -> List[str]:
    terms = [item["canonical_term"]]
    if item["synonyms"]:
        terms.extend(part.strip() for part in item["synonyms"].split("|") if part.strip())
    return terms


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.casefold(), b.casefold()).ratio()


def match_factor_group(synonyms: List[str], lexicon: List[Dict[str, str]]) -> Dict[str, object] | None:
    """Return the best UMLS concept for a synonym group, or ``None``."""
    candidates: List[Tuple[str, Dict[str, str], float]] = []
    for synonym in synonyms:
        key = synonym.casefold()
        for item in lexicon:
            for term in _lexicon_terms(item):
                score = 1.0 if term.casefold() == key else _similarity(term, synonym)
                if score < SIMILARITY_THRESHOLD:
                    continue
                candidates.append((synonym, item, score))
                break

    if not candidates:
        return None

    best_by_cui: Dict[str, Tuple[str, Dict[str, str], float]] = {}
    for synonym, item, score in candidates:
        dedup_key = item["cui"] if item["cui"] else f"{item['canonical_term']}|{item['semantic_type']}"
        current = best_by_cui.get(dedup_key)
        if current is None or score > current[2]:
            best_by_cui[dedup_key] = (synonym, item, score)

    deduped = list(best_by_cui.values())
    best = max(deduped, key=lambda t: t[2])
    synonym, item, score = best
    return {
        "matched_synonym": synonym,
        "umls_matcher_match_count": str(len(deduped)),
        "umls_matcher_best_cui": item["cui"],
        "umls_matcher_best_term": item["canonical_term"],
        "umls_matcher_best_preferred": item["canonical_term"],
        "umls_matcher_best_similarity": f"{score:.4f}",
        "umls_matcher_best_semtypes": item["semantic_type"],
        "umls_matcher_all_cui": json.dumps(sorted({t[1]["cui"] for t in deduped if t[1]["cui"]}), ensure_ascii=False),
        "umls_matcher_all_preferred": json.dumps(sorted({t[1]["canonical_term"] for t in deduped}), ensure_ascii=False),
        "umls_matcher_all_semtypes": json.dumps(sorted({t[1]["semantic_type"] for t in deduped if t[1]["semantic_type"]}), ensure_ascii=False),
    }


def match_umls(factor_map: pd.DataFrame, lexicon_path) -> pd.DataFrame:
    """Attach UMLS match columns to a factor map (one row per factor)."""
    lexicon = load_umls_lexicon(lexicon_path)
    factors = factor_map.drop_duplicates("factor_id").copy()
    records = []
    for _, row in factors.iterrows():
        synonyms = json.loads(row["factor_key"])
        matched = match_factor_group(synonyms, lexicon)
        record = {
            "factor_id": row["factor_id"],
            "factor_key": row["factor_key"],
            "factor_name": row["factor_name"],
            "matched_synonym": "",
            "umls_matcher_match_count": "0",
            "umls_matcher_best_cui": "",
            "umls_matcher_best_term": "",
            "umls_matcher_best_preferred": "",
            "umls_matcher_best_similarity": "",
            "umls_matcher_best_semtypes": "",
            "umls_matcher_all_cui": "[]",
            "umls_matcher_all_preferred": "[]",
            "umls_matcher_all_semtypes": "[]",
        }
        if matched is not None:
            record.update(matched)
        records.append(record)
    return pd.DataFrame(records, columns=UMLS_COLUMNS)
