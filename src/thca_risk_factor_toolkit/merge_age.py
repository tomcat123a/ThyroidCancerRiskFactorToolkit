"""Manual consolidation of ``Older age`` / ``Younger age`` into ``Age``.

The second-round semantic CSV (``v2``) already collapses degree-differentiated
age terms into a single ``Age`` factor, so the public default is the ``v2``
path: it validates that the consolidation is already present and returns the
factor map unchanged.
"""

from __future__ import annotations

import json
from typing import List

import pandas as pd

from .common import normalized_text
from .factor_scoring import factor_id_from_key
from .group_synonyms import SEMANTIC_COLUMNS

AGE_LABEL = "Age-related Clinical Presentation"
AGE_NAMES = ("Age", "Older age", "Younger age")


def consolidate_age_factors(frame: pd.DataFrame) -> pd.DataFrame:
    """Ensure ``Age`` is a single factor; merge degree terms if still separate."""
    names = set(frame["factor_name"].map(normalized_text).tolist())
    if "Older age" not in names and "Younger age" not in names:
        return frame
    if "Age" not in names:
        raise ValueError("存在 Older age / Younger age 但缺少合并后的 Age 因子。")

    age_row = frame[frame["factor_name"].eq("Age")]
    if len(age_row) != 1:
        raise ValueError("Age 因子应恰好一行。")
    age_index = age_row.index[0]

    degree_rows = frame[frame["factor_name"].isin(["Older age", "Younger age"])]
    merged_terms: List[str] = []
    for _, row in degree_rows.iterrows():
        merged_terms.extend(json.loads(row["factor_key"]))
    merged_terms.extend(json.loads(frame.at[age_index, "factor_key"]))
    merged_terms = sorted(set(normalized_text(t) for t in merged_terms if normalized_text(t)))

    frame.at[age_index, "factor_key"] = json.dumps(merged_terms, ensure_ascii=False)
    frame.at[age_index, "factor_name"] = sorted(merged_terms, key=lambda x: (len(x), x))[0]
    frame.at[age_index, "factor_synonyms"] = " | ".join(merged_terms)
    frame.at[age_index, "factor_group_size"] = str(len(merged_terms))
    frame.at[age_index, "factor_id"] = factor_id_from_key(merged_terms)
    return frame.drop(index=degree_rows.index).reset_index(drop=True)


def validate_age_consolidation(frame: pd.DataFrame) -> None:
    names = set(frame["factor_name"].map(normalized_text).tolist())
    if "Older age" in names or "Younger age" in names:
        raise ValueError("v2 输入中仍存在独立的 Older age / Younger age 因子。")


def main() -> None:
    from .path_utils import find_project_root

    path = find_project_root() / "data" / "sample" / "09_factor_label_associations_semantic_merged_v2_demo_first100.csv"
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    validate_age_consolidation(frame)
    print("[merge age] v2 已合并 Age，无需再处理。")


if __name__ == "__main__":
    main()
