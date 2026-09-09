from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import AppConfig
from .io_utils import ProgressTracker, read_excel
from .llm_client import LlmClient
from .subject_records import normalize_text


def enrich_country_and_continent(records: pd.DataFrame, config: AppConfig, client: LlmClient) -> pd.DataFrame:
    reference = _load_country_reference(config.demo_country_reference_csv)
    work = records.copy()
    location_col = "study_metadata.country_or_region"

    pending = work[
        ((work["country_name"].astype(str).str.strip() == "") | (work["continent_name"].astype(str).str.strip() == ""))
        & (work[location_col].astype(str).str.strip() != "")
    ][location_col].drop_duplicates().tolist()

    resolved: dict[str, tuple[str, str]] = {}
    tracker = ProgressTracker(total=max(len(pending), 1), label="country_tagging")
    for raw_location in pending:
        resolved[raw_location] = _resolve_location(raw_location, reference, client, config.prompt_dir)
        tracker.tick()

    def _fill_country(row: pd.Series) -> str:
        value = str(row.get("country_name", "")).strip()
        if value:
            return value
        raw_location = str(row.get(location_col, "")).strip()
        return resolved.get(raw_location, ("", ""))[0]

    def _fill_continent(row: pd.Series) -> str:
        value = str(row.get("continent_name", "")).strip()
        if value:
            return value
        raw_location = str(row.get(location_col, "")).strip()
        return resolved.get(raw_location, ("", ""))[1]

    work["country_name"] = work.apply(_fill_country, axis=1)
    work["continent_name"] = work.apply(_fill_continent, axis=1)
    return work


def _load_country_reference(path: Path) -> dict[str, tuple[str, str]]:
    df = read_excel(path) if path.suffix.lower() in {".xlsx", ".xls"} else pd.read_csv(path, dtype=object)
    mapping: dict[str, tuple[str, str]] = {}
    for _, row in df.iterrows():
        key = normalize_text(row.get("raw_location"))
        if key:
            mapping[key] = (str(row.get("country_name", "")).strip(), str(row.get("continent_name", "")).strip())
    return mapping


def _resolve_location(
    raw_location: str,
    reference: dict[str, tuple[str, str]],
    client: LlmClient,
    prompt_dir: Path,
) -> tuple[str, str]:
    key = normalize_text(raw_location)
    if key in reference:
        return reference[key]

    for candidate_key, candidate_value in reference.items():
        if candidate_key and candidate_key in key:
            return candidate_value

    if client.enabled:
        prompt_text = (prompt_dir / "en" / "country_continent_tagging_en.txt").read_text(encoding="utf-8")
        prompt = f"{prompt_text}\n\nInput JSON:\n{{\"raw_location\": \"{raw_location}\"}}"
        response = client.complete_json("country_continent_tagging", prompt)
        if isinstance(response, dict):
            return (
                str(response.get("country_name", "")).strip(),
                str(response.get("continent_name", "")).strip(),
            )

    lowered = raw_location.lower()
    if "international" in lowered:
        return ("international", "international")
    if "unspecified" in lowered:
        return ("unspecified", "unspecified")
    return (raw_location.strip(), "")
