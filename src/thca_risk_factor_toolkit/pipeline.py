from __future__ import annotations

from pathlib import Path

from .clustering import assign_semantic_labels
from .config import AppConfig, load_config
from .io_utils import read_excel, write_excel_sheets, write_text
from .llm_client import LlmClient
from .statistics import build_statistics_workbook
from .subject_records import build_triplet_records
from .synonyms import fuse_synonyms
from .tagging import enrich_country_and_continent
from .umls import match_umls


def run_demo_pipeline() -> dict[str, Path]:
    config = load_config()
    return run_pipeline(config, mode_name="demo")


def run_full_pipeline() -> dict[str, Path]:
    config = load_config()
    return run_pipeline(config, mode_name="full")


def run_pipeline(config: AppConfig, mode_name: str) -> dict[str, Path]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.agent_data_dir.mkdir(parents=True, exist_ok=True)

    source_df = read_excel(config.input_xlsx)
    client = LlmClient(config.llm, config.agent_data_dir)

    triplets = build_triplet_records(source_df)
    triplets = enrich_country_and_continent(triplets, config, client)
    triplets = assign_semantic_labels(triplets, config, client)
    triplets = fuse_synonyms(triplets, config, client)
    triplets = match_umls(triplets, config)

    intermediate_path = config.output_dir / f"thca_intermediate_{mode_name}.xlsx"
    stats_path = config.output_dir / f"thca_statistics_{mode_name}.xlsx"
    summary_path = config.output_dir / f"run_summary_{mode_name}.md"

    write_excel_sheets(
        intermediate_path,
        {
            "triplet_records": triplets,
        },
    )
    write_excel_sheets(stats_path, build_statistics_workbook(triplets))
    write_text(summary_path, _build_run_summary(config, mode_name, triplets.shape[0], client.enabled))

    print(f"Saved intermediate workbook: {intermediate_path}")
    print(f"Saved statistics workbook: {stats_path}")
    print(f"Saved run summary: {summary_path}")
    return {
        "intermediate_workbook": intermediate_path,
        "statistics_workbook": stats_path,
        "run_summary": summary_path,
    }


def _build_run_summary(config: AppConfig, mode_name: str, triplet_rows: int, llm_enabled: bool) -> str:
    llm_mode = "enabled" if llm_enabled else "disabled (rule-based fallback)"
    return (
        f"# Run Summary\n\n"
        f"- Mode: `{mode_name}`\n"
        f"- Input workbook: `{config.input_xlsx}`\n"
        f"- Triplet rows exported: `{triplet_rows}`\n"
        f"- LLM mode: `{llm_mode}`\n"
        f"- Statistics workbook: `outputs/thca_statistics_{mode_name}.xlsx`\n"
        f"- Intermediate workbook: `outputs/thca_intermediate_{mode_name}.xlsx`\n"
    )
