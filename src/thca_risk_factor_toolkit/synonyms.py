from __future__ import annotations

import concurrent.futures
import json

import pandas as pd

from .config import AppConfig
from .io_utils import ProgressTracker
from .llm_client import LlmClient
from .subject_records import normalize_text


def fuse_synonyms(records: pd.DataFrame, config: AppConfig, client: LlmClient) -> pd.DataFrame:
    group_map: dict[str, list[str]] = {}
    grouped = records.groupby("label", dropna=False)["subject_name"].apply(
        lambda series: sorted(series.dropna().astype(str).str.strip().unique().tolist())
    )
    tracker = ProgressTracker(total=max(len(grouped), 1), label="synonym_fusion")

    for label_name, subject_list in grouped.items():
        if not subject_list:
            tracker.tick()
            continue
        synonym_groups = _group_synonyms_for_label(str(label_name), subject_list, config, client)
        for group in synonym_groups:
            normalized_group = sorted({item.strip() for item in group if item.strip()})
            if not normalized_group:
                continue
            for item in normalized_group:
                group_map[item] = normalized_group
        tracker.tick()

    work = records.copy()
    work["synonym_group_json"] = work["subject_name"].map(
        lambda value: json.dumps(group_map.get(str(value).strip(), [str(value).strip()]), ensure_ascii=False)
    )
    work["factor_name"] = work["subject_name"].map(
        lambda value: sorted(group_map.get(str(value).strip(), [str(value).strip()]))[0]
    )
    work["factor_key"] = work["synonym_group_json"]
    work["factor_synonyms"] = work["subject_name"].map(
        lambda value: " | ".join(group_map.get(str(value).strip(), [str(value).strip()]))
    )
    work["factor_group_size"] = work["subject_name"].map(
        lambda value: len(group_map.get(str(value).strip(), [str(value).strip()]))
    )
    return work


def _group_synonyms_for_label(label_name: str, subject_list: list[str], config: AppConfig, client: LlmClient) -> list[list[str]]:
    if client.enabled:
        prompt_template = (config.prompt_dir / "en" / "synonym_grouping_en.txt").read_text(encoding="utf-8")
        prompt = (
            f"{prompt_template}\n\n"
            f"Input JSON:\n{json.dumps({'label': label_name, 'subject_names': subject_list}, ensure_ascii=False, indent=2)}"
        )
        response = client.complete_json("synonym_grouping", prompt)
        if isinstance(response, list):
            cleaned = [
                [str(item).strip() for item in group if str(item).strip()]
                for group in response
                if isinstance(group, list)
            ]
            if cleaned:
                return cleaned
    return _group_synonyms_with_rules(subject_list)


def _group_synonyms_with_rules(subject_list: list[str]) -> list[list[str]]:
    normalized_map: dict[str, list[str]] = {}
    for subject in subject_list:
        key = normalize_text(subject)
        if key.endswith("s") and len(key) > 3:
            key = key[:-1]
        normalized_map.setdefault(key, []).append(subject)
    return [sorted(set(group)) for group in normalized_map.values()]
