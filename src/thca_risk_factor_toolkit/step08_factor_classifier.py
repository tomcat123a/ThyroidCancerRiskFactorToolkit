"""Step 08 factor classification: single-stage mapping to a Level-3 label.

Reproduces ``step08_factor_classifier.classify_subjects_to_level_3``.  Each
unique ``subject_name`` is assigned directly to one fine-grained Level-3
category; the Level-1 domain is derived from the taxonomy and the Level-2
category is read back from ``factor-subcategory.json``.

When the LLM is disabled (the public default) a deterministic keyword-rule
fallback assigns labels so the demo remains runnable end-to-end.  The full
pipeline uses the manuscript's multi-model majority voting: DeepSeek-V4-Pro and
Doubao-1.8-Seed independently annotate each term and Gemini-3-Pro adjudicates
discordant assignments (see ``config.json`` ``llm`` / ``secondary_llm`` /
``adjudicator_llm``).  Generation is non-streaming with ``temperature=0.0``.
"""

from __future__ import annotations

import concurrent.futures
import json
from typing import Dict, List, Sequence

from .common import normalized_text
from .hierarchy import FactorHierarchy
from .llm_client import LlmClient

CLASSIFICATION_PROMPT = "en/factor_level_3_direct_classification_en.txt"
BATCH_SIZE = 50
MAX_WORKERS = 10


def classify_subjects_to_level_3(
    subject_names: Sequence[str],
    hierarchy: FactorHierarchy,
    model: str,
    task_name: str,
    client: LlmClient | None = None,
) -> Dict[str, Dict[str, str]]:
    """Classify each unique subject directly to a Level-3 label."""
    unique_names = list(dict.fromkeys(
        name for name in (normalized_text(value) for value in subject_names) if name
    ))
    if not unique_names:
        return {}

    taxonomy = {
        level_1: list(level_3_labels)
        for level_1, level_3_labels in hierarchy.level_3_by_level_1.items()
    }
    level_1_by_level_3 = {
        label_3: level_1
        for level_1, labels in taxonomy.items()
        for label_3 in labels
    }

    if client is not None and client.enabled:
        level_3_results = _classify_with_llm(unique_names, taxonomy, level_1_by_level_3, task_name, client)
    else:
        level_3_results = {
            name: _classify_with_rules(name, taxonomy, level_1_by_level_3)
            for name in unique_names
        }

    return {
        subject_name: {
            "label_1": level_1_by_level_3[level_3_results[subject_name]],
            "label_3": level_3_results[subject_name],
            "label_2": hierarchy.level_2_for(
                level_1_by_level_3[level_3_results[subject_name]],
                level_3_results[subject_name],
            ),
        }
        for subject_name in unique_names
    }


def _classify_with_llm(
    subject_names: Sequence[str],
    taxonomy: Dict[str, Sequence[str]],
    level_1_by_level_3: Dict[str, str],
    task_name: str,
    client: LlmClient,
) -> Dict[str, str]:
    from .common import load_prompt

    prompt_template = load_prompt(CLASSIFICATION_PROMPT)
    candidates = [label for labels in taxonomy.values() for label in labels]
    allowed = set(candidates)
    results: Dict[str, str] = {}
    batches = _chunked(list(subject_names), BATCH_SIZE)

    def _run_batch(batch: List[str]) -> Dict[str, str]:
        items = [{"id": str(index), "subject_name": name} for index, name in enumerate(batch, start=1)]
        prompt = (
            f"{prompt_template}\n\n"
            "TAXONOMY_JSON (first-level category -> third-level labels):\n"
            f"{json.dumps(taxonomy, ensure_ascii=False, indent=2)}\n\n"
            "INPUT_BATCH_JSON:\n"
            f"{json.dumps(items, ensure_ascii=False, indent=2)}"
        )
        response = client.complete_json(task_name, prompt)
        parsed = _parse_labels(response, batch, allowed)
        return parsed

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for batch_result in executor.map(_run_batch, batches):
            results.update(batch_result)

    # Fill any unresolved subjects with the rule fallback.
    for name in subject_names:
        if name not in results:
            results[name] = _classify_with_rules(name, taxonomy, level_1_by_level_3)
    return results


def _parse_labels(response, subject_names: Sequence[str], allowed: set) -> Dict[str, str]:
    if isinstance(response, dict) and isinstance(response.get("results"), list):
        response = response["results"]
    if not isinstance(response, list):
        return {}
    allowed_ids = {str(index): name for index, name in enumerate(subject_names, start=1)}
    labels: Dict[str, str] = {}
    for item in response:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")).strip()
        label = str(item.get("label", "")).strip()
        subject = allowed_ids.get(item_id)
        if subject and label in allowed and subject not in labels:
            labels[subject] = label
    return labels


def _chunked(items: Sequence[str], size: int):
    for start in range(0, len(items), size):
        yield list(items[start:start + size])


def _classify_with_rules(
    subject_name: str,
    taxonomy: Dict[str, Sequence[str]],
    level_1_by_level_3: Dict[str, str],
) -> str:
    """Deterministic keyword fallback used when no LLM is configured."""
    normalized = subject_name.casefold()
    rules = [
        ("radiation", "radioactive", "chernobyl", "fallout", "x-ray", "radiotherapy", "rai", "ionizing"),
        ("braf", "ras", "ret", "tert", "tp53", "mutation", "gene", "snp", "polymorphism", "mirna", "microrna", "lncrna", "methylation", "fusion", "rearrangement", "copy number", "cnv", "variant"),
        ("age", "older", "younger", "male", "female", "sex", "gender", "ethnicity", "race", "menopause"),
        ("obesity", "bmi", "body mass", "diabetes", "glucose", "insulin", "metabolic", "lipid", "cholesterol", "tsh", "thyroid hormone"),
        ("smoking", "tobacco", "alcohol", "diet", "exercise", "physical activity", "sleep", "coffee", "tea", "vitamin"),
        ("lymph node", "metastasis", "recurrence", "prognosis", "survival", "mortality", "stage", "extrathyroidal", "invasion"),
        ("tumor size", "tumour size", "multifocality", "bilaterality", "histolog", "patholog", "papillary", "follicular", "medullary", "anaplastic"),
    ]
    label_for_rule = [
        "Ionizing Radiation (Medical, Natural and Occupational Sources)",
        "Single Nucleotide Polymorphisms (SNPs)",
        "Age-related Clinical Presentation",
        "Body Composition and Anthropometry",
        "Tobacco and Alcohol Consumption",
        "Lymph Node Status and Involvement",
        "Tumor Morphology and Spatial Characteristics",
    ]
    for keywords, default_label in zip(rules, label_for_rule):
        if any(keyword in normalized for keyword in keywords) and default_label in level_1_by_level_3:
            return default_label

    for labels in taxonomy.values():
        if labels:
            return labels[0]
    return ""
