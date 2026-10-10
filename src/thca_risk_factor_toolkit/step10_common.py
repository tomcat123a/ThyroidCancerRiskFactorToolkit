"""Shared path/config/export utilities for Step 10 (evidence quantification)."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd

from .path_utils import find_project_root


def get_project_root() -> Path:
    return find_project_root()


def resolve_path(settings: dict, key: str, default: str) -> Path:
    path = Path(str(settings.get(key, default))).expanduser()
    return path if path.is_absolute() else get_project_root() / path


def text(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip()


def require_columns(frame: pd.DataFrame, columns: list, source: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{source}: missing columns {missing}")


class Progress:
    def __init__(self, name: str, total: int) -> None:
        self.name, self.total, self.started = name, total, time.monotonic()

    def report(self, completed: int) -> None:
        average = (time.monotonic() - self.started) / max(completed, 1)
        print(
            f"[{self.name}] {completed}/{self.total} "
            f"({completed / max(self.total, 1):.1%}), average {average:.2f}s, "
            f"ETA {average * (self.total - completed) / 60:.1f} min",
            flush=True,
        )


def write_tables(output_dir: Path, filename: str, tables: dict) -> Path:
    """Write each table to CSV and an optional Excel presentation workbook."""
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_dir = output_dir / Path(filename).stem
    csv_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    temporary = path.with_name(f".{path.stem}.tmp.xlsx")
    with pd.ExcelWriter(temporary, engine="openpyxl") as writer:
        used = {"export_index"}
        export_index = []
        for index, (name, frame) in enumerate(tables.items(), 1):
            sheet = name[:31]
            if sheet in used:
                raise ValueError(f"Duplicate Excel sheet name after truncation: {sheet}")
            used.add(sheet)
            csv_path = csv_dir / f"{name}.csv"
            tmp_csv = csv_path.with_suffix(".tmp")
            frame.to_csv(tmp_csv, index=False, encoding="utf-8-sig")
            os.replace(tmp_csv, csv_path)
            preview = frame.iloc[:1_048_575].copy()
            long_cells = 0
            for column in preview.select_dtypes(include=["object", "string"]).columns:
                long_cells += int(preview[column].map(
                    lambda value: isinstance(value, str) and len(value) > 32767
                ).sum())
                preview[column] = preview[column].map(
                    lambda value: value[:32000] + " [FULL VALUE IN CSV]"
                    if isinstance(value, str) and len(value) > 32767 else value
                )
                preview[column] = preview[column].map(
                    lambda value: ILLEGAL_CHARACTERS_RE.sub("", value) if isinstance(value, str) else value
                )
            preview.to_excel(writer, sheet_name=sheet, index=False)
            export_index.append({
                "table": name, "sheet": sheet, "csv": str(csv_path),
                "total_rows": len(frame), "excel_rows": len(preview),
                "truncated_excel_cells": long_cells,
            })
            for row in writer.sheets[sheet].iter_rows():
                for cell in row:
                    if cell.data_type == "f":
                        cell.data_type = "s"
        pd.DataFrame(export_index).to_excel(writer, sheet_name="export_index", index=False)
    os.replace(temporary, path)
    return path
