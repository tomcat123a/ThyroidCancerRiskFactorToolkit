from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path

import pandas as pd

from .config import AppConfig
from .io_utils import ProgressTracker
from .llm_client import LlmClient
from .subject_records import normalize_text


def assign_semantic_labels(records: pd.DataFrame, config: AppConfig, client: LlmClient) -> pd.DataFrame:
    unique_subjects = sorted(records["subject_name"].dropna().astype(str).str.strip().unique().tolist())
    label_map: dict[str, dict[str, str]] = {}

    if client.enabled:
        prompt_template = (config.prompt_dir / "en" / "semantic_clustering_en.txt").read_text(encoding="utf-8")
        tracker = ProgressTracker(total=max(len(unique_subjects), 1), label="semantic_clustering")
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.llm.max_workers) as executor:
            future_map = {
                executor.submit(_label_one_subject_with_llm, subject, prompt_template, client): subject
                for subject in unique_subjects
            }
            for future in concurrent.futures.as_completed(future_map):
                subject = future_map[future]
                try:
                    label_map[subject] = future.result()
                except Exception:
                    label_map[subject] = _label_one_subject_with_rules(subject)
                tracker.tick()
    else:
        tracker = ProgressTracker(total=max(len(unique_subjects), 1), label="semantic_clustering")
        for subject in unique_subjects:
            label_map[subject] = _label_one_subject_with_rules(subject)
            tracker.tick()

    work = records.copy()
    work["label_1"] = work["subject_name"].map(lambda value: label_map.get(str(value), {}).get("label_1", "Other"))
    work["label_2"] = work["subject_name"].map(lambda value: label_map.get(str(value), {}).get("label_2", "Other"))
    work["label"] = work["subject_name"].map(lambda value: label_map.get(str(value), {}).get("label", str(value)))
    return work


def _label_one_subject_with_llm(subject: str, prompt_template: str, client: LlmClient) -> dict[str, str]:
    prompt = (
        f"{prompt_template}\n\n"
        f"Input JSON:\n{json.dumps({'subject_name': subject}, ensure_ascii=False, indent=2)}"
    )
    response = client.complete_json("semantic_clustering", prompt)
    if isinstance(response, dict):
        return {
            "label_1": str(response.get("label_1", "Other")).strip() or "Other",
            "label_2": str(response.get("label_2", "Other")).strip() or "Other",
            "label": str(response.get("label", subject)).strip() or subject,
        }
    return _label_one_subject_with_rules(subject)


def _label_one_subject_with_rules(subject: str) -> dict[str, str]:
    normalized = normalize_text(subject)
    rules = [
        (("radiation", "radioactive", "iodine"), ("Environmental and Treatment Exposure", "Radiation", "Radiation-Related Exposure")),
        (("braf", "tert", "mutation", "gene", "mirna", "microrna", "snp"), ("Genomic and Molecular Features", "Genetic Alterations", "Genomic Alterations")),
        (("age", "male", "female", "sex", "ethnicity", "race"), ("Population and Demographic Features", "Demographic Factors", "Demographic Characteristics")),
        (("obesity", "bmi", "metabolic", "diabetes", "glucose"), ("Metabolic and Lifestyle Factors", "Metabolic Features", "Metabolic Dysregulation")),
        (("smoking", "alcohol", "diet", "exercise"), ("Metabolic and Lifestyle Factors", "Behavioral Exposure", "Lifestyle Exposure")),
        (("lymph", "metastasis", "recurrence", "prognosis"), ("Clinical and Pathology Features", "Outcome and Progression", "Clinical Outcome Indicators")),
    ]
    for keywords, labels in rules:
        if any(keyword in normalized for keyword in keywords):
            return {"label_1": labels[0], "label_2": labels[1], "label": labels[2]}
    return {"label_1": "Other", "label_2": "Other", "label": subject.strip()}
