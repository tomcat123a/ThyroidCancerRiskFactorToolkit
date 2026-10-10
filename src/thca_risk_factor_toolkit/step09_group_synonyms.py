"""Step 09: synonym harmonization within Level-3 categories.

Reproduces ``step09_group_factor_synonyms_entry.py`` (the second-round,
semantic-merged ``v2`` result).  In the public repository the authoritative
synonym grouping is shipped as a CSV
(``data/sample/09_factor_label_associations_semantic_merged_v2_demo_first100.csv``)
and is loaded directly by :func:`load_semantic_factor_map`.  The full pipeline
performs LLM synonym grouping per ``label_3`` and then exports this same CSV
schema; see ``scripts/run_full_pipeline_main.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pandas as pd

from .common import normalized_text

SEMANTIC_COLUMNS = [
    "label_1", "label_2", "label_3",
    "factor_id", "factor_key", "factor_name", "factor_synonyms", "factor_group_size",
]


def parse_factor_key(value: object) -> List[str]:
    """Parse the authoritative list-form synonyms from a ``factor_key`` cell."""
    text = normalized_text(value)
    if not text:
        raise ValueError(f"factor_key 为空：{value!r}")
    try:
        terms = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"factor_key 不是合法 JSON：{value!r}") from exc
    if not isinstance(terms, list) or not terms:
        raise ValueError(f"factor_key 必须是非空列表：{value!r}")
    clean = [normalized_text(term) for term in terms]
    if any(not term for term in clean):
        raise ValueError(f"factor_key 含空词：{value!r}")
    return clean


def load_semantic_factor_map(path: Path) -> pd.DataFrame:
    """Read the semantic-merged v2 CSV and explode each factor into subject rows.

    Returns one row per ``subject_name`` with columns ``[label_1, label_2,
    label_3, factor_id, factor_key, factor_name, factor_synonyms,
    factor_group_size, subject_name]``.
    """
    if not path.exists():
        raise FileNotFoundError(f"语义合并同义词文件不存在：{path}")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = sorted(set(SEMANTIC_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"语义合并文件缺少列：{missing}")
    frame = frame[SEMANTIC_COLUMNS].apply(lambda col: col.map(normalized_text))
    frame["_terms"] = frame["factor_key"].map(parse_factor_key)
    result = frame.explode("_terms").rename(columns={"_terms": "subject_name"})
    if result["subject_name"].duplicated().any():
        raise ValueError("语义合并文件的 subject_name 跨因子重复，无法逐词对照。")
    if result["factor_id"].eq("").any():
        raise ValueError("语义合并文件存在空 factor_id。")
    return result


def singleton_factor_map(subjects: List[str], labels: pd.DataFrame) -> pd.DataFrame:
    """Build a degenerate factor map where every subject is its own factor.

    Used as a no-LLM fallback so the demo still runs end-to-end when no
    authoritative synonym CSV is available.
    """
    from .factor_scoring import factor_id_from_key

    rows = []
    for subject in sorted(set(normalized_text(s) for s in subjects if normalized_text(s))):
        label_row = labels[labels["subject_name"].eq(subject)]
        if label_row.empty:
            continue
        first = label_row.iloc[0]
        key = [subject]
        rows.append({
            "label_1": first["label_1"],
            "label_2": first["label_2"],
            "label_3": first["label_3"],
            "factor_id": factor_id_from_key(key),
            "factor_key": json.dumps(key, ensure_ascii=False),
            "factor_name": subject,
            "factor_synonyms": subject,
            "factor_group_size": "1",
            "subject_name": subject,
        })
    columns = [*SEMANTIC_COLUMNS, "subject_name"]
    return pd.DataFrame(rows, columns=columns)
