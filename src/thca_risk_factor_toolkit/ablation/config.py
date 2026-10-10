"""Configuration and path resolution for the clustering ablation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def get_script_dir() -> Path:
    file_path = globals().get("__file__")
    return Path(file_path).resolve().parent if isinstance(file_path, str) and file_path else Path(os.getcwd()).resolve()


def find_project_root() -> Path:
    candidates = [get_script_dir(), Path(os.getcwd()).resolve()]
    seen = set()
    for base in candidates:
        for current in (base, *base.parents):
            if current in seen:
                continue
            seen.add(current)
            if (current / "pyproject.toml").exists() and (current / "src").exists():
                return current
    return Path(os.getcwd()).resolve()


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y", "on"}:
            return True
        if text in {"0", "false", "no", "n", "off"}:
            return False
    return bool(default)


@dataclass(frozen=True)
class AblationConfig:
    project_root: Path
    semantic_v2_csv: Path
    model_dir: Path
    output_dir: Path
    preferred_task: str
    random_state: int
    kmeans_n_init: int
    kmeans_max_iter: int


def load_config() -> AblationConfig:
    root = find_project_root()
    cwd_config = Path(os.getcwd()).resolve() / "config.json"
    config_path = cwd_config if cwd_config.exists() else root / "config.json"
    cfg = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    section = cfg.get("clustering_ablation", {})
    if not isinstance(section, dict):
        section = {}

    def resolve(value, default: Path) -> Path:
        path = Path(str(value)).expanduser() if value else default
        return path if path.is_absolute() else root / path

    return AblationConfig(
        project_root=root,
        semantic_v2_csv=resolve(
            section.get("semantic_v2_csv"),
            root / "data/sample/09_factor_label_associations_semantic_merged_v2_demo_first100.csv",
        ),
        model_dir=resolve(
            section.get("model_dir"),
            root / "embedding/model_cache/jina-embeddings-v5-text-small",
        ),
        output_dir=resolve(
            section.get("output_dir"),
            root / "outputs/ablation_study",
        ),
        preferred_task=str(section.get("preferred_task") or "clustering").strip() or "clustering",
        random_state=_to_int(section.get("random_state"), 42),
        kmeans_n_init=_to_int(section.get("kmeans_n_init"), 20),
        kmeans_max_iter=_to_int(section.get("kmeans_max_iter"), 300),
    )
