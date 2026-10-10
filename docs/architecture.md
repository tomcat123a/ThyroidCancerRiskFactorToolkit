# Architecture

## Goal

`thca_risk_factor_toolkit` is the public implementation of the TCRiskFlow manuscript workflow. It starts from the post-screening abstract table (`abstracts_final.xlsx`, one row per paper with title + abstract) and produces a three-level taxonomy of harmonized, scored risk factors with temporal, geographic and guideline-oriented analyses.

## Module relationships

The pipeline (`pipeline.py`) orchestrates these modules in order:

```text
abstracts_final.xlsx  (title + abstract + metadata)
  -> structured_extraction.py       (LLM: title+abstract -> causal_triplets)
  -> geographic enrichment          (country_or_region -> country/continent)
  -> deduplicate_title.py           (title dedup)
  -> count_thyroid_triplets.py      (keep thyroid-related triplets)
  -> classify_risk_factors.py       (expand triplets + Level-3 classification)
  -> group_synonyms.py              (authoritative synonym factor map)
  -> evidence_quantification.py     (composite score + group + guideline)
  -> umls_match.py                  (UMLS-style normalization)
  -> statistics.py                  (bibliometric tables)
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

## Structured extraction

`structured_extraction.py` runs the manuscript's "Structured abstract extraction module": each title/abstract pair is sent to DeepSeek-V4-Pro with the JSON schema in `prompt/en/structured_extraction_en.txt`, and the returned JSON is flattened into the wide `causal_triplets_1..N` columns consumed downstream. Requests are non-streaming, `temperature=0.0`, and cached/logged under `agent_data/`.

## Classification

`factor_classifier.classify_subjects_to_level_3` maps each unique `subject_name` directly to a Level-3 label, then derives `label_1` from the taxonomy and `label_2` from `factor-subcategory.json`. When the LLM is disabled, a deterministic keyword-rule fallback keeps the demo runnable. The full pipeline uses multi-model majority voting (manuscript "Semantic taxonomy construction module").

## Synonym harmonization

`group_synonyms.load_semantic_factor_map` reads the authoritative semantic-merged `v2` CSV and explodes each `factor_key` into one row per synonym. `factor_id` is the SHA-256 of the canonical key (terms sorted by `(length, term)`). `merge_age` consolidates the age degree terms (`Age` / `Older age` / `Younger age`).

## Evidence quantification

`factor_data.extract_source_triplets` parses sample size, p-value, significance grade and evidence grade. `factor_scores.compute_tables` computes the composite score and the year/continent/classification group tables. `guideline_analysis.compute_guideline_tables` runs the guideline concordance and gap analysis. `evidence_quantification.run_evidence_quantification` writes the outputs.

## Ablation

`ablation/` compares cosine-average agglomerative clustering and same-K KMeans against the finalized Level-3 labels; see `docs/ablation_study.md`.

## Reproducibility notes

- no `argparse`
- every module supports import and direct execution
- paths resolve via `path_utils.find_project_root`
- prompt files live in `prompt/`; request logs live in `agent_data/`
