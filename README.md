# THCA Risk Factor Extraction Toolkit

[中文说明](README.zh-CN.md)

**Author:** Yuqun Zeng  
**Email:** zengyuqun401@163.com  
**Project title:** Code Repository for LLM-Based Thyroid Cancer Risk Factor Extraction (including semantic clustering, semantic tagging, synonym fusion, statistics, and UMLS matching)

An installation-ready open-source repository for thyroid cancer risk factor mining from `preproc_thca.xlsx`, designed for manuscript-facing structured analysis rather than figure generation.

## What This Repository Delivers

This repository organizes the manuscript workflow described in `论文写作1-2.pdf` / `论文写作1-2.docx` into a reusable codebase that can be published, installed, and extended.

Included capabilities:

- triplet expansion from wide-format THCA workbooks
- country and continent tagging
- semantic clustering and hierarchical tagging
- synonym fusion
- post-clustering group labeling
- UMLS-style normalization
- manuscript-oriented table exports
- bilingual prompt assets, with English prompts used by default in code

Not included:

- plotting
- upstream preprocessing from earlier raw files to `preproc_thca.xlsx`

## Release Highlights

- Modular Python package under `src/thca_risk_factor_toolkit/`
- Demo dataset bundled as an `.xlsx` file with the first 100 rows
- Placeholder-ready LLM configuration for `DeepSeek-V3.2` and `Gemini-3-pro`
- Prompt files stored explicitly under `prompt/`
- Public-release-friendly documentation in both English and Chinese
- ASCII workflow diagrams in plain `.txt` files for quick GitHub browsing

## Quick Start

```bash
git clone <your-github-url>
cd github_repo
bash scripts/install.sh
bash scripts/run_demo.sh
```

For a full run, replace `input_xlsx` in `config.json` with your full workbook path, then run:

```bash
bash scripts/run_full.sh
```

## Workflow Overview

Plain-text workflow:

- [docs/pipeline_flow_en.txt](docs/pipeline_flow_en.txt)
- [docs/release_structure_flow.txt](docs/release_structure_flow.txt)

Pipeline summary:

```text
preproc_thca.xlsx
  -> triplet expansion
  -> country / continent enrichment
  -> semantic labels
  -> synonym fusion
  -> UMLS matching
  -> intermediate workbook
  -> statistics workbook
```

## Main Outputs

The pipeline writes outputs under `outputs/`:

- `thca_intermediate_demo.xlsx` or `thca_intermediate_full.xlsx`
- `thca_statistics_demo.xlsx` or `thca_statistics_full.xlsx`
- `run_summary_demo.md` or `run_summary_full.md`

Representative statistics sheets:

- `paper_year_basic_stats`
- `study_type_stats`
- `continent_year_bin_long`
- `continent_year_bin_pivot`
- `country_top10_papers`
- `country_top10_year_bin_long`
- `country_top10_year_bin_pivot`
- `label1_overall`
- `label1_year_bin`
- `evidence_grade_overall`
- `evidence_grade_year_bin`
- `endpoint_top3_factors`
- `factor_synonym_catalog`
- `umls_coverage_summary`

## Dataset Policy

This public repository includes only the demo workbook:

- `data/sample/preproc_thca_demo_first100.xlsx`

The full `preproc_thca.xlsx` is not distributed here. To request access, contact:

- Yuqun Zeng
- `zengyuqun401@163.com`

## LLM Configuration

The project loads `config.json` in this order:

1. `CWD/config.json`
2. repository-root `config.json`

The committed configuration contains placeholder URL and API key values only. Replace them with your own service endpoints before enabling API-based semantic labeling.

Supported placeholder-ready profiles:

- `DeepSeek-V3.2`
- `Gemini-3-pro`

## Repository Layout

```text
github_repo/
├─ config.json
├─ config.example.json
├─ data/
│  ├─ demo_resources/
│  └─ sample/
├─ docs/
├─ prompt/
│  ├─ en/
│  └─ zh/
├─ scripts/
├─ src/thca_risk_factor_toolkit/
├─ agent_data/
└─ outputs/
```

## Prompt Assets

All prompt assets are stored explicitly in:

- `prompt/en/*.txt`
- `prompt/zh/*.txt`

The repository keeps Chinese and English prompt versions, while the code reads the English prompt files by default. This includes synonym grouping, post-clustering group labeling, and candidate-label subject-name labeling prompts.

## Documentation Index

- [docs/architecture.md](docs/architecture.md)
- [docs/output_spec.md](docs/output_spec.md)
- [docs/manuscript_table_mapping.md](docs/manuscript_table_mapping.md)
- [docs/github_push.md](docs/github_push.md)
- [docs/homepage_snippets.txt](docs/homepage_snippets.txt)
- [docs/pipeline_flow_en.txt](docs/pipeline_flow_en.txt)
- [docs/release_structure_flow.txt](docs/release_structure_flow.txt)
