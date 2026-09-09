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
    cluster_label_map: dict[str, str] = {}
    grouped = records.groupby("label", dropna=False)["subject_name"].apply(
        lambda series: sorted(series.dropna().astype(str).str.strip().unique().tolist())
    )
    tracker = ProgressTracker(total=max(len(grouped), 1), label="synonym_fusion")

    for label_name, subject_list in grouped.items():
        if not subject_list:
            tracker.tick()
            continue
        synonym_groups = _group_synonyms_for_label(str(label_name), subject_list, config, client)
        label_map_for_groups = _label_synonym_groups(str(label_name), synonym_groups, config, client)
        for group in synonym_groups:
            normalized_group = sorted({item.strip() for item in group if item.strip()})
            if not normalized_group:
                continue
            group_key = _group_key(normalized_group)
            group_label = label_map_for_groups.get(group_key, _build_cluster_label_with_rules(label_name, normalized_group))
            cluster_label_map[group_key] = group_label
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
    work["factor_cluster_label"] = work["subject_name"].map(
        lambda value: cluster_label_map.get(_group_key(group_map.get(str(value).strip(), [str(value).strip()])), str(value).strip())
    )
    work["factor_display_name"] = work["factor_cluster_label"].where(
        work["factor_cluster_label"].astype(str).str.strip() != "",
        work["factor_name"],
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


def _label_synonym_groups(
    parent_label: str,
    synonym_groups: list[list[str]],
    config: AppConfig,
    client: LlmClient,
) -> dict[str, str]:
    if not synonym_groups:
        return {}

    if client.enabled:
        prompt_template = (config.prompt_dir / "en" / "synonym_cluster_labeling_en.txt").read_text(encoding="utf-8")
        tracker = ProgressTracker(total=max(len(synonym_groups), 1), label="cluster_labeling")
        output: dict[str, str] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.llm.max_workers) as executor:
            future_map = {
                executor.submit(_label_one_group_with_llm, parent_label, group, prompt_template, client): _group_key(group)
                for group in synonym_groups
            }
            for future in concurrent.futures.as_completed(future_map):
                group_key = future_map[future]
                try:
                    output[group_key] = future.result()
                except Exception:
                    output[group_key] = _build_cluster_label_with_rules(parent_label, json.loads(group_key))
                tracker.tick()
        return output

    tracker = ProgressTracker(total=max(len(synonym_groups), 1), label="cluster_labeling")
    output = {}
    for group in synonym_groups:
        output[_group_key(group)] = _build_cluster_label_with_rules(parent_label, group)
        tracker.tick()
    return output


def _label_one_group_with_llm(
    parent_label: str,
    group: list[str],
    prompt_template: str,
    client: LlmClient,
) -> str:
    prompt = (
        f"{prompt_template}\n\n"
        f"Input JSON:\n{json.dumps({'parent_label': parent_label, 'synonym_group': group}, ensure_ascii=False, indent=2)}"
    )
    response = client.complete_json("synonym_cluster_labeling", prompt)
    if isinstance(response, dict):
        label = str(response.get("cluster_label", "")).strip()
        if label:
            return label
    return _build_cluster_label_with_rules(parent_label, group)


def _group_synonyms_with_rules(subject_list: list[str]) -> list[list[str]]:
    normalized_map: dict[str, list[str]] = {}
    for subject in subject_list:
        key = normalize_text(subject)
        if key.endswith("s") and len(key) > 3:
            key = key[:-1]
        normalized_map.setdefault(key, []).append(subject)
    return [sorted(set(group)) for group in normalized_map.values()]


def _build_cluster_label_with_rules(parent_label: str, group: list[str]) -> str:
    cleaned_group = sorted({str(item).strip() for item in group if str(item).strip()})
    if not cleaned_group:
        return str(parent_label).strip() or "Unlabeled Cluster"
    if len(cleaned_group) == 1:
        return cleaned_group[0]
    shortest = sorted(cleaned_group, key=lambda value: (len(value), value.lower()))[0]
    parent = str(parent_label).strip()
    if parent and parent.lower() != shortest.lower():
        return f"{shortest} ({parent})"
    return shortest


def _group_key(group: list[str]) -> str:
    return json.dumps(sorted({str(item).strip() for item in group if str(item).strip()}), ensure_ascii=False)
