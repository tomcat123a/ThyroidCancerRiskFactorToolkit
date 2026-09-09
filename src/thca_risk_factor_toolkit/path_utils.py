from __future__ import annotations

import os
from pathlib import Path


def get_script_dir() -> Path:
    file_path = globals().get("__file__")
    if isinstance(file_path, str) and file_path:
        return Path(file_path).resolve().parent
    return Path(os.getcwd()).resolve()


def find_project_root() -> Path:
    candidates = [Path(os.getcwd()).resolve(), get_script_dir()]
    seen = set()
    for base in candidates:
        current = base
        while True:
            if current in seen:
                break
            seen.add(current)
            if (current / "pyproject.toml").exists() and (current / "src").exists():
                return current
            if current.parent == current:
                break
            current = current.parent
    return Path(os.getcwd()).resolve()


def resolve_repo_path(relative_or_absolute: str | Path) -> Path:
    path = Path(relative_or_absolute)
    if path.is_absolute():
        return path
    return find_project_root() / path


def resolve_config_path() -> Path:
    cwd_path = Path(os.getcwd()).resolve() / "config.json"
    if cwd_path.exists():
        return cwd_path
    repo_path = find_project_root() / "config.json"
    if repo_path.exists():
        return repo_path
    raise FileNotFoundError("config.json was not found in the current working directory or the repository root.")


def ensure_directory(path: str | Path) -> Path:
    target = resolve_repo_path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target
