"""End-to-end TCRiskFlow pipeline orchestration.

The pipeline starts from the post-screening abstract table (``abstracts_final``,
one row per paper with title + abstract) and runs, in order: LLM structured
extraction -> geographic enrichment -> title deduplication -> thyroid-triplet
filtering -> Level-3 classification -> synonym harmonization -> evidence
quantification + guideline analysis -> UMLS matching -> bibliometric statistics.

The LLM transport is OpenAI-message compatible (see :mod:`llm_client`); the user
only fills ``model``, ``api_url`` and ``api_key`` in ``config.json``.  When the
LLM is disabled, extraction yields no rows and the pipeline reports a clear
message instead of failing.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .common import normalized_text
from .config import AppConfig, load_config
from .count_thyroid_triplets import filter_thyroid_triplets
from .deduplicate_title import deduplicate_by_title
from .evidence_quantification import run_evidence_quantification
from .group_synonyms import load_semantic_factor_map, singleton_factor_map
from .hierarchy import load_factor_hierarchy
from .io_utils import read_excel, write_excel_sheets
from .llm_client import LlmClient
from .classify_risk_factors import run_extract_and_classify
from .statistics import build_paper_statistics, build_synonym_catalog, build_umls_coverage
from .structured_extraction import run_structured_extraction
from .umls_match import match_umls

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
    for candidate in ["PY", "YR", "DA", "PUB_YEAR"]:
        if candidate in df.columns:
            df["publish_year"] = df[candidate]
            return df
    df["publish_year"] = ""
    return df


def _enrich_geo(df: pd.DataFrame, reference_path: Path) -> pd.DataFrame:
    """Map ``study_metadata.country_or_region`` to country/continent names."""
    work = df.copy()
    reference: dict[str, tuple[str, str]] = {}
    if reference_path.exists():
        ref = pd.read_csv(reference_path, dtype=object, keep_default_na=False)
        for _, row in ref.iterrows():
            key = str(row.get("raw_location", "")).strip().casefold()
            if key:
                reference[key] = (
                    str(row.get("country_name", "")).strip(),
                    str(row.get("continent_name", "")).strip(),
                )
    if "study_metadata.country_or_region" not in work.columns:
        work["study_metadata.country_or_region"] = ""
    work["country_name"] = work["study_metadata.country_or_region"].map(
        lambda value: reference.get(normalized_text(value).casefold(), (normalized_text(value), ""))[0]
    )
    work["continent_name"] = work["study_metadata.country_or_region"].map(
        lambda value: reference.get(normalized_text(value).casefold(), (normalized_text(value), ""))[1]
    )
    return work


def _build_factor_map(semantic_path: Path, papers: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    if semantic_path.exists():
        factor_map = load_semantic_factor_map(semantic_path)
    else:
        factor_map = pd.DataFrame()

    all_subjects = set(_papers_subjects(papers))
    if factor_map.empty:
        return singleton_factor_map(sorted(all_subjects), labels)

    covered = set(factor_map["subject_name"].map(normalized_text).tolist())
    uncovered = sorted(all_subjects - covered)
    if uncovered:
        extra = singleton_factor_map(uncovered, labels)
        factor_map = pd.concat([factor_map, extra], ignore_index=True)
    return factor_map


def _papers_subjects(papers: pd.DataFrame) -> list[str]:
    subjects = set()
    for column in papers.columns:
        if column.endswith(".subject.name"):
            subjects.update(normalized_text(value) for value in papers[column].tolist() if normalized_text(value))
    return sorted(subjects)


def run_pipeline(config: AppConfig, mode_name: str) -> dict[str, Path]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.agent_data_dir.mkdir(parents=True, exist_ok=True)

    source = _ensure_publish_year(_ensure_source_row_id(read_excel(config.input_xlsx)))
    client = LlmClient(config.llm, config.agent_data_dir)

    # 1) LLM structured extraction: title + abstract -> causal_triplets wide table.
    extracted = run_structured_extraction(source, config, client)

    if extracted.empty:
        print(
            "[pipeline] LLM 结构化抽取未产生结果。"
            "请在 config.json 填入 model / api_url / api_key 并启用 llm.enabled，"
            "或提供预生成的抽取结果。"
        )
        return {}

    # 2) Geographic enrichment.
    extracted = _enrich_geo(extracted, config.demo_country_reference_csv)

    # 3) Title deduplication.
    deduped, _removed = deduplicate_by_title(extracted)

    # 4) Thyroid-related triplet filtering.
    papers, _stats = filter_thyroid_triplets(deduped)
    if papers.empty:
        print("[pipeline] 甲状腺相关三元组筛选后无数据，流程结束。")
        return {}

    # 5) Level-3 classification.
    hierarchy = load_factor_hierarchy(config.demo_hierarchy_json)
    _details, final_labels = run_extract_and_classify(papers, hierarchy, model=MODEL, client=client)

    # 6) Synonym harmonization (authoritative semantic-merged v2).
    factor_map = _build_factor_map(config.demo_semantic_csv, papers, final_labels)

    # 7) Evidence quantification + guideline analysis.
    step10_output = config.output_dir / "10_factor_scores_semantic"
    step10_paths = run_evidence_quantification(papers, factor_map, config.demo_guideline_dir, step10_output)

    # 8) UMLS-style normalization.
    umls_match = match_umls(factor_map, config.demo_umls_lexicon_csv)

    # 9) Bibliometric statistics.
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
        print(f"Saved evidence-quantification output ({name}): {path}")
    return {
        "intermediate_workbook": intermediate_path,
        "statistics_workbook": stats_path,
        **step10_paths,
    }


if __name__ == "__main__":
    run_demo_pipeline()
