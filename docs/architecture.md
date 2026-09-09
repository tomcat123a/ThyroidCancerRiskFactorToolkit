# Architecture

## Goal

This repository provides a modular workflow for thyroid cancer risk factor extraction starting from `preproc_thca.xlsx`, with emphasis on manuscript-facing statistical tables rather than figures.

## Module Relationships

1. `scripts/run_demo_pipeline_main.py` and `scripts/run_full_pipeline_main.py`
   - entry scripts
   - call the package pipeline without `argparse`

2. `src/thca_risk_factor_toolkit/config.py`
   - loads `config.json`
   - applies the required lookup order: current working directory first, repository root second

3. `src/thca_risk_factor_toolkit/subject_records.py`
   - reads the wide-format workbook
   - expands `causal_triplets_1` to `causal_triplets_12` into long-form subject records

4. `src/thca_risk_factor_toolkit/tagging.py`
   - fills missing `country_name` and `continent_name`
   - uses demo reference resources first
   - can optionally call an external LLM endpoint through placeholders in `config.json`

5. `src/thca_risk_factor_toolkit/clustering.py`
   - assigns semantic labels `label_1`, `label_2`, and `label`
   - uses rule-based fallback when LLM access is disabled

6. `src/thca_risk_factor_toolkit/synonyms.py`
   - groups semantically close subject names into synonym groups
   - creates `factor_key`, `factor_name`, `factor_synonyms`, and `factor_group_size`

7. `src/thca_risk_factor_toolkit/umls.py`
   - performs UMLS-style lexical matching against a demo lexicon
   - can be replaced with a full licensed terminology export

8. `src/thca_risk_factor_toolkit/statistics.py`
   - exports manuscript-oriented tables to Excel sheets
   - does not generate figures

9. `src/thca_risk_factor_toolkit/llm_client.py`
   - stores prompt and response logs under `agent_data/`
   - supports placeholder-ready DeepSeek-V3.2 and Gemini-3-pro profiles

## Output Flow

```text
preproc_thca.xlsx
  -> long-form triplet records
  -> country/continent enrichment
  -> semantic labels
  -> synonym fusion
  -> UMLS matching
  -> intermediate workbook
  -> manuscript statistics workbook
```

## Reproducibility Notes

- no `argparse`
- every script supports direct execution and import-based use
- the repository does not depend on `__file__` only
- prompt files live in `prompt/`
- request logs live in `agent_data/`
