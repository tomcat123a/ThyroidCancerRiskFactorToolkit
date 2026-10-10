"""Extract risk-factor triplets and classify them to Level-3 labels.

The input is the thyroid-filtered paper table; the output is one row per
risk-factor triplet with ``label_1`` / ``label_2`` / ``label_3`` attached.
"""

from __future__ import annotations

import re
from typing import Dict, List, Mapping, Sequence, Tuple

import pandas as pd

from .common import ensure_columns, normalized_text
from .factor_classifier import classify_subjects_to_level_3
from .hierarchy import FactorHierarchy

MODEL = "DeepSeek-V4-Pro"
FINAL_COLUMNS = [
    "subject_name",
    "TI",
    "relation",
    "direction",
    "object_endpoint_type",
    "evidence_strength_grade_level",
    "_source_row_id",
    "label_1",
    "label_3",
    "label_2",
]

TRIPLET_COLUMN_PATTERN = re.compile(r"^causal_triplets?_(\d+)\.(.+)$")
TRIPLET_FIELDS: Mapping[str, str] = {
    "subject.name": "subject_name",
    "predicate.relation": "relation",
    "predicate.direction": "direction",
    "object.disease": "disease",
    "object.endpoint_type": "object_endpoint_type",
    "evidence_strength.grade_level": "evidence_strength_grade_level",
}
DETAIL_COLUMNS = [
    "subject_name",
    "TI",
    "relation",
    "direction",
    "disease",
    "object_endpoint_type",
    "evidence_strength_grade_level",
    "_source_row_id",
]


def discover_triplet_columns(columns) -> List[Tuple[int, Dict[str, str]]]:
    groups: Dict[int, Dict[str, str]] = {}
    for column in columns:
        match = TRIPLET_COLUMN_PATTERN.match(str(column))
        if match:
            index, field_name = match.groups()
            groups.setdefault(int(index), {})[field_name] = column
    if not groups:
        raise ValueError("输入中没有发现 causal_triplets_N.* 字段。")
    missing_subject = [str(i) for i, fields in sorted(groups.items()) if "subject.name" not in fields]
    if missing_subject:
        raise ValueError(f"以下三元组缺少 subject.name 字段：{', '.join(missing_subject)}")
    return sorted(groups.items())


def extract_triplet_details(source: pd.DataFrame) -> pd.DataFrame:
    """Convert paper-level wide triplet fields into one row per triplet."""
    ensure_columns(source, ["TI", "_source_row_id"])
    groups = discover_triplet_columns(source.columns)
    detail_frames: List[pd.DataFrame] = []

    for _, fields in groups:
        subject_column = fields["subject.name"]
        present = source[subject_column].map(normalized_text).ne("")
        if not present.any():
            continue
        selected = source.loc[present]
        values: Dict[str, object] = {
            "TI": selected["TI"].map(normalized_text),
            "_source_row_id": selected["_source_row_id"].map(normalized_text),
        }
        for source_field, output_column in TRIPLET_FIELDS.items():
            source_column = fields.get(source_field)
            values[output_column] = (
                selected[source_column].map(normalized_text) if source_column else ""
            )
        detail_frames.append(pd.DataFrame(values, index=selected.index))

    if not detail_frames:
        return pd.DataFrame(columns=DETAIL_COLUMNS)
    details = pd.concat(detail_frames, ignore_index=True)
    return details[DETAIL_COLUMNS]


def build_final_output(details: pd.DataFrame, labels: Dict[str, Dict[str, str]]) -> pd.DataFrame:
    final = details.copy()

    def get_labels(subject_name: object) -> Dict[str, str]:
        return labels[normalized_text(subject_name)]

    selected = final["subject_name"].map(get_labels)
    final["label_1"] = selected.map(lambda value: value["label_1"])
    final["label_3"] = selected.map(lambda value: value["label_3"])
    final["label_2"] = selected.map(lambda value: value["label_2"])
    return final[FINAL_COLUMNS]


def validate_final_labels(final: pd.DataFrame, hierarchy: FactorHierarchy) -> None:
    invalid = final[
        ~final.apply(
            lambda row: (
                row["label_1"] in hierarchy.level_1_labels
                and row["label_3"] in hierarchy.level_3_by_level_1[row["label_1"]]
                and row["label_2"] == hierarchy.level_2_for(row["label_1"], row["label_3"])
            ),
            axis=1,
        )
    ]
    if not invalid.empty:
        raise RuntimeError(f"最终结果中存在 {len(invalid)} 行无效标签。")


def run_extract_and_classify(
    source: pd.DataFrame,
    hierarchy: FactorHierarchy,
    model: str = MODEL,
    client=None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Extract triplet details, classify subjects, and return (details, final)."""
    details = extract_triplet_details(source)
    if details.empty:
        return details, pd.DataFrame(columns=FINAL_COLUMNS)

    unique_subjects = list(dict.fromkeys(
        details["subject_name"].map(normalized_text).tolist()
    ))
    unique_subjects = [name for name in unique_subjects if name]

    labels = classify_subjects_to_level_3(
        subject_names=unique_subjects,
        hierarchy=hierarchy,
        model=model,
        task_name="factor_classification",
        client=client,
    )
    final = build_final_output(details, labels)
    validate_final_labels(final, hierarchy)
    return details, final


def main() -> None:
    from .common import read_stage_csv, write_csv, write_summary
    from .hierarchy import load_factor_hierarchy

    source = read_stage_csv("筛选后甲状腺相关三元组的论文.csv")
    hierarchy = load_factor_hierarchy(_hierarchy_path())
    details, final = run_extract_and_classify(source, hierarchy)
    write_csv(final, "08_风险因素最终类别划分.csv")
    write_summary("08_风险因素提取与分类", {
        "输入明细行数": len(details),
        "唯一subject_name数": final["subject_name"].nunique(),
        "分类模型": MODEL,
        "最终结果文件": "08_风险因素最终类别划分.csv",
        "三级标签字段": "label_3",
    })


def _hierarchy_path():
    from .path_utils import find_project_root
    return find_project_root() / "data" / "demo_resources" / "factor-subcategory.json"


if __name__ == "__main__":
    main()
