from __future__ import annotations

import json
import math
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


def read_excel(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, dtype=object)


def write_excel_sheets(path: Path, sheets: dict[str, pd.DataFrame]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            frame.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return path


def write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def new_run_directory(root_dir: Path, task_name: str) -> Path:
    target = root_dir / f"{task_name}_{uuid.uuid4().hex}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def safe_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


@dataclass
class ProgressTracker:
    total: int
    label: str
    started_at: float = field(default_factory=time.time)
    completed: int = 0

    def tick(self, step: int = 1) -> None:
        self.completed += step
        elapsed = max(time.time() - self.started_at, 0.001)
        average = elapsed / max(self.completed, 1)
        remaining = max(self.total - self.completed, 0) * average
        print(
            f"{self.label}: {self.completed}/{self.total} "
            f"elapsed={elapsed:.1f}s avg={average:.2f}s eta={remaining:.1f}s"
        )
