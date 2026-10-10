"""Title-based deduplication, keeping the first occurrence of each ``TI``.

Reproduces the title/abstract deduplication step of the original pipeline.
The function is importable (:func:`deduplicate_by_title`) and directly runnable
(:func:`main`), never depending on a fixed working directory.
"""

from __future__ import annotations

from typing import Tuple

import pandas as pd

from .common import ensure_columns, read_stage_csv, write_csv, write_summary


def deduplicate_by_title(dataframe: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return ``(remaining, removed)`` where removed holds TI duplicates."""
    ensure_columns(dataframe, ["TI"])
    duplicate_mask = dataframe.duplicated(subset=["TI"], keep="first")
    removed = dataframe.loc[duplicate_mask].copy()
    removed["_duplicate_reason"] = "TI 标题与此前记录重复"
    remaining = dataframe.loc[~duplicate_mask].copy()
    return remaining, removed


def main() -> None:
    dataframe = read_stage_csv("04_最终保留文献.csv")
    remaining, removed = deduplicate_by_title(dataframe)
    write_csv(removed, "05_TI标题重复删除文献.csv")
    write_csv(remaining, "05_最终去重保留文献.csv")
    write_summary("05_TI标题去重", {
        "输入文献数": len(dataframe),
        "因TI标题重复删除数": len(removed),
        "去重后剩余文献数": len(remaining),
    })
    print(f"去重完成：因 TI 标题重复删除 {len(removed)} 行，最终保留 {len(remaining)} 行。")


if __name__ == "__main__":
    main()
