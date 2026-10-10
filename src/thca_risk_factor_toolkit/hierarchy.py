"""Three-level factor taxonomy loading and validation.

Reproduces ``step08_triplet_data.FactorHierarchy`` / ``load_factor_hierarchy``
from the original pipeline.  The taxonomy is a JSON object::

    {
      "<Level-1>": {
        "<Level-2>": ["<Level-3>", ...],
        ...
      },
      ...
    }

Level-3 labels are treated as the authoritative fine-grained categories; each
``(level_1, level_3)`` pair must map to exactly one ``level_2``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

from .common import normalized_text


class FactorHierarchy:
    """Validated first-, second- and third-level factor taxonomy."""

    def __init__(
        self,
        level_1_labels: Sequence[str],
        level_3_by_level_1: Mapping[str, Sequence[str]],
        level_2_by_pair: Mapping[Tuple[str, str], str],
    ) -> None:
        self.level_1_labels = list(level_1_labels)
        self.level_3_by_level_1 = {
            key: list(value) for key, value in level_3_by_level_1.items()
        }
        self.level_2_by_pair = dict(level_2_by_pair)

    def level_2_for(self, label_1: str, label_3: str) -> str:
        return self.level_2_by_pair.get((label_1, label_3), "")

    def all_level_3_labels(self) -> List[str]:
        labels: List[str] = []
        for values in self.level_3_by_level_1.values():
            labels.extend(values)
        return labels


def load_factor_hierarchy(path: Path) -> FactorHierarchy:
    if not path.exists():
        raise FileNotFoundError(f"未找到风险因素类别文件：{path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw:
        raise ValueError("factor-subcategory.json 顶层必须是非空对象。")

    level_3_by_level_1: Dict[str, List[str]] = {}
    level_2_by_pair: Dict[Tuple[str, str], str] = {}
    for raw_level_1, raw_level_2_groups in raw.items():
        label_1 = normalized_text(raw_level_1)
        if not label_1 or not isinstance(raw_level_2_groups, dict):
            raise ValueError(f"一级标签 {raw_level_1!r} 的结构无效。")
        level_3_labels: List[str] = []
        for raw_level_2, raw_level_3_labels in raw_level_2_groups.items():
            label_2 = normalized_text(raw_level_2)
            if not label_2 or not isinstance(raw_level_3_labels, list):
                raise ValueError(f"二级标签 {raw_level_2!r} 的结构无效。")
            for raw_label in raw_level_3_labels:
                label = normalized_text(raw_label)
                if not label:
                    continue
                pair = (label_1, label)
                previous = level_2_by_pair.get(pair)
                if previous and previous != label_2:
                    raise ValueError(
                        f"三级标签 {label!r} 在一级标签 {label_1!r} 下对应多个二级标签。"
                    )
                level_2_by_pair[pair] = label_2
                if label not in level_3_labels:
                    level_3_labels.append(label)
        if not level_3_labels:
            raise ValueError(f"一级标签 {label_1!r} 下没有可用的三级标签。")
        level_3_by_level_1[label_1] = level_3_labels

    return FactorHierarchy(
        level_1_labels=list(level_3_by_level_1),
        level_3_by_level_1=level_3_by_level_1,
        level_2_by_pair=level_2_by_pair,
    )
