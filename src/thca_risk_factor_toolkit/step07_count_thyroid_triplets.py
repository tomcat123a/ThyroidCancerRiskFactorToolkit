"""Step 07: count causal triplets and keep only thyroid-related triplets.

Reproduces ``step07_count_thyroid_causal_triplets_entry.py``.  A triplet is
considered thyroid-related when its ``object.disease`` contains the substring
``thyr`` (case-insensitive).  Non-thyroid triplets inside retained papers are
removed and the remaining triplets are compacted forward so slot numbering stays
contiguous.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

import pandas as pd

from .common import ensure_columns, normalized_text, read_stage_csv, write_csv, write_summary

TRIPLET_COLUMN_PATTERN = re.compile(r"^(causal_triplets?)_(\d+)\.(.+)$")
TripletGroup = Tuple[int, Dict[str, str]]


def discover_triplet_groups(columns: List[str]) -> List[TripletGroup]:
    """Collect every ``causal_triplets_N.*`` field, indexed by triplet number."""
    grouped_columns: Dict[int, Dict[str, str]] = {}
    naming_prefixes: Dict[int, str] = {}
    for column in columns:
        match = TRIPLET_COLUMN_PATTERN.match(str(column))
        if not match:
            continue
        naming_prefix, index_text, field_name = match.groups()
        index = int(index_text)
        existing_prefix = naming_prefixes.setdefault(index, naming_prefix)
        if existing_prefix != naming_prefix:
            raise ValueError(f"三元组 {index} 同时使用了 {existing_prefix} 和 {naming_prefix} 命名。")
        grouped_columns.setdefault(index, {})[field_name] = column

    if not grouped_columns:
        raise ValueError("输入 CSV 中没有发现 causal_triplets_N.subject.name 列。")

    indexes = sorted(grouped_columns)
    if indexes != list(range(1, max(indexes) + 1)):
        raise ValueError(f"三元组编号不连续：实际为 {indexes}，预期为 {list(range(1, max(indexes) + 1))}")

    required_fields = ("subject.name", "object.disease")
    for index in indexes:
        for field_name in required_fields:
            if field_name not in grouped_columns[index]:
                raise ValueError(f"三元组 {index} 缺少字段：{field_name}")

    all_field_names = {
        field_name for field_columns in grouped_columns.values() for field_name in field_columns
    }
    for index in indexes:
        field_columns = grouped_columns[index]
        group_prefix = field_columns["subject.name"].removesuffix(".subject.name")
        for field_name in all_field_names:
            field_columns.setdefault(field_name, f"{group_prefix}.{field_name}")
    return [(index, grouped_columns[index]) for index in indexes]


def filter_thyroid_triplets(
    dataframe: pd.DataFrame,
) -> Tuple[pd.DataFrame, Dict[str, object]]:
    """Return the thyroid-only compacted frame plus summary statistics."""
    ensure_columns(dataframe, ["TI"])
    triplet_groups = discover_triplet_groups(list(dataframe.columns))
    all_field_names = sorted(
        {field_name for _, field_columns in triplet_groups for field_name in field_columns}
    )
    generated_triplet_columns = [
        column
        for _, field_columns in triplet_groups
        for column in field_columns.values()
        if column not in dataframe.columns
    ]

    work = dataframe.copy()
    for column in generated_triplet_columns:
        work[column] = ""

    total_triplets = 0
    thyroid_triplets = 0
    retained_thyroid_triplets = 0

    row_triplet_counts = pd.Series(0, index=work.index, dtype="int64")
    row_thyroid_counts = pd.Series(0, index=work.index, dtype="int64")
    before_first_empty = pd.Series(True, index=work.index, dtype="bool")

    for _, field_columns in triplet_groups:
        subject_column = field_columns["subject.name"]
        disease_column = field_columns["object.disease"]
        subject_present = work[subject_column].map(normalized_text).ne("")
        valid_triplet = before_first_empty & subject_present
        thyroid_related = (
            valid_triplet
            & work[disease_column].fillna("").astype(str).str.contains("thyr", case=False, regex=False, na=False)
        )
        row_triplet_counts += valid_triplet.astype("int64")
        row_thyroid_counts += thyroid_related.astype("int64")
        before_first_empty &= subject_present

    total_triplets = int(row_triplet_counts.sum())
    thyroid_triplets = int(row_thyroid_counts.sum())
    thyroid_mask = row_thyroid_counts.gt(0)

    selected = work.loc[thyroid_mask].copy()
    retained_thyroid_triplets = _compact_thyroid_triplets(selected, triplet_groups, all_field_names)

    selected["_causal_triplet_count"] = row_thyroid_counts.loc[thyroid_mask]
    selected["_thyroid_related_triplet_count"] = row_thyroid_counts.loc[thyroid_mask]

    statistics = {
        "输入论文数": len(dataframe),
        "识别到的三元组编号": [item[0] for item in triplet_groups],
        "causal_triplet总数": total_triplets,
        "甲状腺相关causal_triplet总数": thyroid_triplets,
        "至少包含一个甲状腺相关三元组的论文数": int(thyroid_mask.sum()),
        "输出中保留并前移的甲状腺相关三元组数": retained_thyroid_triplets,
    }
    return selected, statistics


def _compact_thyroid_triplets(
    selected: pd.DataFrame,
    triplet_groups: List[TripletGroup],
    all_field_names: List[str],
) -> int:
    """Keep only thyroid triplets per row and move them forward; return count."""
    retained_count = 0
    for row_index in selected.index:
        retained_groups: List[Dict[str, object]] = []
        for _, field_columns in triplet_groups:
            subject_value = normalized_text(selected.at[row_index, field_columns["subject.name"]])
            if not subject_value:
                break
            disease_value = normalized_text(selected.at[row_index, field_columns["object.disease"]])
            if "thyr" not in disease_value.lower():
                continue
            retained_groups.append({
                field_name: selected.at[row_index, column]
                for field_name, column in field_columns.items()
            })
        retained_count += len(retained_groups)

        for destination_position, (_, field_columns) in enumerate(triplet_groups):
            source_values = (
                retained_groups[destination_position]
                if destination_position < len(retained_groups)
                else {}
            )
            for field_name in all_field_names:
                destination_column = field_columns.get(field_name)
                if destination_column is not None:
                    selected.at[row_index, destination_column] = source_values.get(field_name, "")
    return retained_count


def main() -> None:
    dataframe = read_stage_csv("06_匹配preproc并附加字段.csv")
    filtered, statistics = filter_thyroid_triplets(dataframe)
    write_csv(filtered, "筛选后甲状腺相关三元组的论文.csv")
    write_summary("07_甲状腺相关三元组", {
        **statistics,
        "筛选结果文件": "筛选后甲状腺相关三元组的论文.csv",
    })
    print(f"causal_triplet 总数：{statistics['causal_triplet总数']}")
    print(f"甲状腺相关 causal_triplet 总数：{statistics['甲状腺相关causal_triplet总数']}")
    print(f"至少包含一个甲状腺相关三元组的论文数：{statistics['至少包含一个甲状腺相关三元组的论文数']}")


if __name__ == "__main__":
    main()
