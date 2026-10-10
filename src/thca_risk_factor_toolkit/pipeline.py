"""End-to-end TCRiskFlow pipeline orchestration.

Reproduces the manuscript workflow (Steps 05 -> 07 -> 08 -> 09 -> 10) plus
UMLS matching and bibliometric statistics, running fully on the demo workbook.
No LLM call is required when ``config.json`` leaves the LLM disabled; a
deterministic rule fallback assigns Step 08 labels in that case.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .common import normalized_text
from .config import AppConfig, load_config
from .hierarchy import load_factor_hierarchy
from .io_utils import read_excel, write_excel_sheets
from .llm_client import LlmClient
from .statistics import build_paper_statistics, build_synonym_catalog, build_umls_coverage
from .step05_deduplicate_title import deduplicate_by_title
from .step07_count_thyroid_triplets import filter_thyroid_triplets
from .step08_extract_classify import run_extract_and_classify
from .step09_group_synonyms import load_semantic_factor_map, singleton_factor_map
from .step10_entry import run_step10
from .umls_match import match_umls

# Primary annotator model (manuscript: DeepSeek-V4-Pro). The actual model name
# is read from ``config.json``'s ``llm.model``; this constant is only a label.
MODEL = "DeepSeek-V4-Pro"


def run_demo_pipeline() -> dict[str, Path]:
    return run_pipeline(load_config(), mode_name="demo")


def run_full_pipeline() -> dict[str, Path]:
    return run_pipeline(load_config(), mode_name="full")


def _ensure_source_row_id(df: pd.DataFrame) -> pd.DataFrame:
    if "_source_row_id" in df.columns:
        return df
    df = df.copy()
    df.insert(0, "_source_row_id", [str(i) for i in range(2, len(df) + 2)])
    return df


def _ensure_publish_year(df: pd.DataFrame) -> pd.DataFrame:
    if "publish_year" in df.columns:
        return df
    df = df.copy()
    for candidate in ["PY", "YR", "DA"]:
        if candidate in df.columns:
            df["publish_year"] = df[candidate]
            return df
    df["publish_year"] = ""
    return df


def _ensure_factor_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for column in ["study_population.sample_size", "country_name", "continent_name", "study_type", "TI"]:
        if column not in df.columns:
            df[column] = ""
    return df


def _build_factor_map(semantic_path: Path, papers: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """Load the authoritative semantic CSV and cover any remaining subjects."""
    if semantic_path.exists():
        factor_map = load_semantic_factor_map(semantic_path)
    else:
        factor_map = pd.DataFrame()

    if factor_map.empty:
        return singleton_factor_map(papers_subjects(papers), labels)

    covered = set(factor_map["subject_name"].map(normalized_text).tolist())
    all_subjects = set(papers_subjects(papers))
    uncovered = sorted(all_subjects - covered)
    if uncovered:
        extra = singleton_factor_map(uncovered, labels)
        factor_map = pd.concat([factor_map, extra], ignore_index=True)
    return factor_map


def papers_subjects(papers: pd.DataFrame) -> list[str]:
    subjects = set()
    for column in papers.columns:
        if column.endswith(".subject.name"):
            subjects.update(normalized_text(value) for value in papers[column].tolist() if normalized_text(value))
    return sorted(subjects)


def run_pipeline(config: AppConfig, mode_name: str) -> dict[str, Path]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.agent_data_dir.mkdir(parents=True, exist_ok=True)

    source_df = _ensure_factor_columns(_ensure_publish_year(_ensure_source_row_id(read_excel(config.input_xlsx))))
    client = LlmClient(config.llm, config.agent_data_dir)

    # Step 05: title deduplication.
    deduped, _removed = deduplicate_by_title(source_df)

    # Step 07: keep only thyroid-related triplets.
    papers, _stats = filter_thyroid_triplets(deduped)

    # Step 08: extract triplets and classify subjects to Level-3 labels.
    hierarchy = load_factor_hierarchy(config.demo_hierarchy_json)
    _details, final_labels = run_extract_and_classify(papers, hierarchy, model=MODEL, client=client)

    # Step 09: authoritative synonym factor map (semantic-merged v2).
    factor_map = _build_factor_map(config.demo_semantic_csv, papers, final_labels)

    # Step 10: composite score, group statistics and guideline analysis.
    step10_output = config.output_dir / "10_factor_scores_semantic"
    step10_paths = run_step10(papers, factor_map, config.demo_guideline_dir, step10_output)

    # UMLS-style normalization.
    umls_match = match_umls(factor_map, config.demo_umls_lexicon_csv)

    # Manuscript-facing bibliometric tables.
    paper_stats = build_paper_statistics(papers)
    synonym_catalog = build_synonym_catalog(factor_map)
    umls_coverage = build_umls_coverage(umls_match)

    intermediate_path = config.output_dir / f"thca_intermediate_{mode_name}.xlsx"
    stats_path = config.output_dir / f"thca_statistics_{mode_name}.xlsx"
    write_excel_sheets(intermediate_path, {
        "triplet_labels": final_labels,
        "factor_map": factor_map,
        "umls_match": umls_match,
    })
    write_excel_sheets(stats_path, {
        **paper_stats,
        "factor_synonym_catalog": synonym_catalog,
        "umls_coverage_summary": umls_coverage,
    })

    print(f"Saved intermediate workbook: {intermediate_path}")
    print(f"Saved statistics workbook: {stats_path}")
    for name, path in step10_paths.items():
        print(f"Saved Step 10 output ({name}): {path}")
    return {
        "intermediate_workbook": intermediate_path,
        "statistics_workbook": stats_path,
        **step10_paths,
    }


if __name__ == "__main__":
    run_demo_pipeline()
