"""Shared path, CSV and normalization helpers for the TCRiskFlow steps.

This module mirrors the ``prisam_common`` helpers used by the original
``backend/preproc_prisam`` pipeline, but resolves paths against the public
repository layout (``outputs/``, ``prompt/``, ``agent_data/``) instead of the
private ``backend/preproc_prisam`` tree.

No function here depends on ``__file__``; every path is resolved through
:func:`get_project_root`, which uses the current working directory and the
calling script directory in that order (see :mod:`path_utils`).
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Iterable

import pandas as pd

from .path_utils import find_project_root

OUTPUT_ENCODING = "utf-8-sig"


def get_project_root() -> Path:
    return find_project_root()


def get_output_dir() -> Path:
    output_dir = get_project_root() / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_agent_data_dir(task_name: str) -> Path:
    import uuid

    path = get_project_root() / "agent_data" / f"{task_name}_{uuid.uuid5(uuid.NAMESPACE_URL, task_name)}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_prompt(prompt_name: str) -> str:
    prompt_path = get_project_root() / "prompt" / prompt_name
    if not prompt_path.exists():
        raise FileNotFoundError(f"未找到提示词文件：{prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


def read_stage_csv(filename: str) -> pd.DataFrame:
    path = get_output_dir() / filename
    if not path.exists():
        raise FileNotFoundError(f"未找到上一步结果：{path}")
    return pd.read_csv(path, dtype=object, keep_default_na=False, encoding=OUTPUT_ENCODING)


def write_csv(dataframe: pd.DataFrame, filename: str) -> Path:
    path = get_output_dir() / filename
    dataframe.to_csv(path, index=False, encoding=OUTPUT_ENCODING, quoting=csv.QUOTE_MINIMAL)
    return path


def write_summary(step_name: str, values: Dict[str, Any]) -> Path:
    path = get_output_dir() / f"{step_name}_统计.json"
    path.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def normalized_text(value: Any) -> str:
    return "" if pd.isna(value) else str(value).strip()


def ensure_columns(dataframe: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in dataframe.columns]
    if missing:
        raise ValueError(f"输入表缺少必要列：{', '.join(missing)}")


def get_script_dir() -> Path:
    """Return the calling script directory, never relying on ``__file__`` alone."""
    file_path = globals().get("__file__")
    if isinstance(file_path, str) and file_path.strip():
        return Path(file_path).resolve().parent
    return Path(os.getcwd()).resolve()


def get_llm_client() -> Callable[..., Dict[str, Any]]:
    """Return the project LLM callable; placeholder that raises without a key.

    The public repository ships without the private ``llm`` package.  Keep the
    LLM path behind :class:`LlmClient` in :mod:`llm_client` instead, which uses
    the OpenAI-compatible or Gemini-compatible HTTP endpoints from
    ``config.json``.
    """
    raise RuntimeError(
        "The public repository uses LlmClient from llm_client; "
        "configure config.json to enable API-based labeling."
    )
