# Architecture

## Goal

`thca_risk_factor_toolkit` is the public implementation of the TCRiskFlow manuscript workflow. It starts from a wide-format preprocessed workbook and produces a three-level taxonomy of harmonized, scored risk factors with temporal, geographic and guideline-oriented analyses.

## Module relationships

The pipeline (`pipeline.py`) orchestrates these modules in order:

```text
preproc_thca.xlsx
  -> step05_deduplicate_title.py     (title dedup)
  -> step07_count_thyroid_triplets.py (keep thyroid-related triplets)
  -> step08_extract_classify.py      (expand triplets + Level-3 classification)
  -> step09_group_synonyms.py        (authoritative synonym factor map)
  -> step10_entry.py                 (composite score + group + guideline)
  -> umls_match.py                   (UMLS-style normalization)
  -> statistics.py                   (bibliometric tables)
```

Supporting modules:

| Module | Responsibility |
| --- | --- |
| `config.py` | loads `config.json` (CWD first, then repo root) into `AppConfig` |
| `path_utils.py` | project-root resolution; never relies on `__file__` alone |
| `common.py` | `normalized_text`, CSV read/write, summaries, prompt loading |
| `hierarchy.py` | `FactorHierarchy` + `load_factor_hierarchy` from `factor-subcategory.json` |
| `factor_scoring.py` | numeric parsing, Z-score, composite-score primitives and normalization |
| `llm_client.py` | OpenAI/Gemini-compatible LLM client (placeholder in demo) |

## Step 08: classification

`step08_factor_classifier.classify_subjects_to_level_3` maps each unique `subject_name` directly to a Level-3 label, then derives `label_1` from the taxonomy and `label_2` from `factor-subcategory.json`. When the LLM is disabled, a deterministic keyword-rule fallback keeps the demo runnable. The full pipeline uses multi-model majority voting (manuscript "Semantic taxonomy construction module").

## Step 09: synonym harmonization

`step09_group_synonyms.load_semantic_factor_map` reads the authoritative semantic-merged `v2` CSV and explodes each `factor_key` into one row per synonym. `factor_id` is the SHA-256 of the canonical key (terms sorted by `(length, term)`). `step09_merge_age` consolidates the age degree terms (`Age` / `Older age` / `Younger age`).

## Step 10: evidence quantification

`step10_factor_data.extract_source_triplets` parses sample size, p-value, significance grade and evidence grade. `step10_factor_scores.compute_tables` computes the composite score and the year/continent/classification group tables. `step10_guidelines.compute_guideline_tables` runs the guideline concordance and gap analysis.

## Ablation

`ablation/` compares cosine-average agglomerative clustering and same-K KMeans against the finalized Level-3 labels; see `docs/ablation_study.md`.

## Reproducibility notes

- no `argparse`
- every module supports import and direct execution
- paths resolve via `path_utils.find_project_root`
- prompt files live in `prompt/`; request logs live in `agent_data/`
