"""LLM structured extraction: ``abstracts_final`` (title + abstract) to a
wide-format risk-factor table with ``causal_triplets_1..N`` columns.

Reproduces the manuscript's "Structured abstract extraction module".  DeepSeek-V4
Pro reads each title/abstract pair and returns a JSON object following the
schema in ``prompt/en/structured_extraction_en.txt``; the JSON is then flattened
into the wide columns consumed by the downstream steps (thyroid-triplet
filtering, classification, synonym grouping and scoring).

The LLM transport is OpenAI-message compatible (see :mod:`llm_client`); the user
only needs to fill ``model``, ``api_url`` and ``api_key`` in ``config.json``.
"""

from __future__ import annotations

import concurrent.futures
import json
import time
from typing import Any, Dict, List

import pandas as pd

from .common import normalized_text
from .llm_client import LlmClient

MAX_TRIPLETS = 12
EXTRACTION_PROMPT = "en/structured_extraction_en.txt"

# Nested triplet JSON path -> flattened wide column suffix (the slot number is
# prepended by the flattener, e.g. ``causal_triplets_1.subject.name``).
TRIPLET_FIELDS: Dict[str, str] = {
    "subject.name": "subject.name",
    "subject.category": "subject.category",
    "subject.is_novel": "subject.is_novel",
    "predicate.relation": "predicate.relation",
    "predicate.direction": "predicate.direction",
    "object.disease": "object.disease",
    "object.subtype": "object.subtype",
    "object.endpoint_type": "object.endpoint_type",
    "statistics.effect_size_type": "statistics.effect_size_type",
    "statistics.effect_size": "statistics.effect_size",
    "statistics.confidence_interval": "statistics.confidence_interval",
    "statistics.p_value": "statistics.p_value",
    "statistics.statistical_significance": "statistics.statistical_significance",
    "evidence_strength.initial_grade_based_on_design": "evidence_strength.initial_grade_based_on_design",
    "evidence_strength.grade_level": "evidence_strength.grade_level",
    "evidence_strength.upgrade_factors": "evidence_strength.upgrade_factors",
    "evidence_strength.downgrade_factors": "evidence_strength.downgrade_factors",
    "evidence_strength.grade_numeric_weight": "evidence_strength.grade_numeric_weight",
    "evidence_strength.justification": "evidence_strength.justification",
    "confounders_adjusted": "confounders_adjusted",
    "temporal_information.exposure_period": "temporal_information.exposure_period",
    "temporal_information.follow_up_duration": "temporal_information.follow_up_duration",
    "heterogeneity_and_conflict.contradictory_findings": "heterogeneity_and_conflict.contradictory_findings",
    "heterogeneity_and_conflict.description": "heterogeneity_and_conflict.description",
    "guideline_relevance.mentioned": "guideline_relevance.mentioned",
    "guideline_relevance.guideline_context": "guideline_relevance.guideline_context",
}

STUDY_FIELDS: Dict[str, str] = {
    "study_metadata.study_design": "study_metadata.study_design",
    "study_metadata.country_or_region": "study_metadata.country_or_region",
    "study_metadata.population_description": "study_metadata.population_description",
    "study_population.sample_size": "study_population.sample_size",
    "study_population.thyroid_cancer_cases": "study_population.thyroid_cancer_cases",
    "study_population.age_range": "study_population.age_range",
    "study_population.gender_distribution": "study_population.gender_distribution",
    "study_population.special_population": "study_population.special_population",
}

LIST_FIELDS: Dict[str, str] = {
    "molecular_markers": "molecular_markers",
    "novel_factors": "novel_factors",
}

NOTE_FIELDS: Dict[str, str] = {
    "summary_level_notes.overdiagnosis_discussed": "summary_level_notes.overdiagnosis_discussed",
    "summary_level_notes.limitations_mentioned": "summary_level_notes.limitations_mentioned",
    "summary_level_notes.key_conclusion_sentence": "summary_level_notes.key_conclusion_sentence",
}


def _cell(value: Any) -> str:
    """Serialize a scalar, list or nested value into a single CSV cell."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def flatten_extraction(extracted: dict, *, row_id: str, ti: str, py: str) -> Dict[str, str]:
    """Flatten one extracted JSON object into a single wide-table row."""
    row: Dict[str, str] = {"_source_row_id": row_id, "TI": ti}
    if py:
        row["publish_year"] = py

    for path, column in STUDY_FIELDS.items():
        top, _, key = path.partition(".")
        row[column] = _cell((extracted.get(top) or {}).get(key))

    for path, column in NOTE_FIELDS.items():
        top, _, key = path.partition(".")
        row[column] = _cell((extracted.get(top) or {}).get(key))

    for path, column in LIST_FIELDS.items():
        row[column] = _cell(extracted.get(path))

    triplets = extracted.get("causal_triplets") or []
    if not isinstance(triplets, list):
        triplets = []
    triplets = triplets[:MAX_TRIPLETS]
    for index in range(1, MAX_TRIPLETS + 1):
        triplet = triplets[index - 1] if index <= len(triplets) else {}
        for path, suffix in TRIPLET_FIELDS.items():
            value = triplet
            for key in path.split("."):
                value = (value or {}).get(key) if isinstance(value, dict) else None
            row[f"causal_triplets_{index}.{suffix}"] = _cell(value)
    return row


def extract_one(
    row_id: str,
    title: str,
    abstract: str,
    *,
    client: LlmClient,
    prompt_template: str,
    task_name: str,
    cache_dir,
) -> Dict[str, str]:
    """Extract and flatten one title/abstract pair (with a per-row JSON cache)."""
    cache_path = cache_dir / f"{row_id}.json"
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            return flatten_extraction(cached, row_id=row_id, ti=title, py="")
        except (OSError, json.JSONDecodeError):
            pass

    prompt = (
        f"{prompt_template}\n\n"
        "the title and abstract of the paper is as follows: title:, abstract:\n"
        f"title: {title}\n"
        f"abstract: {abstract}\n"
    )
    response = client.complete_json(task_name, prompt)
    extracted = response if isinstance(response, dict) else {}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(extracted, ensure_ascii=False, indent=2), encoding="utf-8")
    return flatten_extraction(extracted, row_id=row_id, ti=title, py="")


def run_structured_extraction(
    source: pd.DataFrame,
    config,
    client: LlmClient,
) -> pd.DataFrame:
    """Extract every row and return the wide-format factor table."""
    from .common import get_agent_data_dir, load_prompt

    ensure = ["_source_row_id", "TI", "AB"]
    missing = [c for c in ensure if c not in source.columns]
    if missing:
        raise ValueError(f"abstracts_final 缺少列：{missing}")

    prompt_template = load_prompt(EXTRACTION_PROMPT)
    cache_dir = get_agent_data_dir("structured_extraction")
    task_name = "structured_extraction"

    rows = []
    items = [
        (normalized_text(row["_source_row_id"]), normalized_text(row["TI"]), normalized_text(row["AB"]))
        for _, row in source[ensure].iterrows()
    ]

    if not client.enabled:
        # No LLM configured: return an empty wide table so the demo still runs
        # (downstream steps will then report an empty result).
        template = flatten_extraction({}, row_id="", ti="", py="")
        return pd.DataFrame(columns=list(template.keys()))

    started = time.monotonic()
    total = len(items)
    with concurrent.futures.ThreadPoolExecutor(max_workers=config.llm.max_workers) as executor:
        futures = {
            executor.submit(
                extract_one, row_id, title, abstract,
                client=client, prompt_template=prompt_template,
                task_name=task_name, cache_dir=cache_dir,
            ): (row_id, title)
            for row_id, title, abstract in items
        }
        for done, future in enumerate(concurrent.futures.as_completed(futures), 1):
            row_id, title = futures[future]
            flat = future.result()
            flat["_source_row_id"] = row_id
            flat["TI"] = title
            rows.append(flat)
            if done % 10 == 0 or done == total:
                elapsed = time.monotonic() - started
                eta = elapsed / done * (total - done)
                print(
                    f"[structured_extraction] {done}/{total} ({done / total:.1%}) "
                    f"average {elapsed / done:.2f}s ETA {eta:.1f}s", flush=True,
                )

    frame = pd.DataFrame(rows)
    if frame.empty:
        template = flatten_extraction({}, row_id="", ti="", py="")
        frame = pd.DataFrame(columns=list(template.keys()))
    # Preserve publication year from the source for scoring.
    if "publish_year" in source.columns:
        year_lookup = dict(zip(source["_source_row_id"].map(normalized_text), source["publish_year"].map(normalized_text)))
        frame["publish_year"] = frame["_source_row_id"].map(lambda rid: year_lookup.get(rid, ""))
    return frame
