# TCRiskFlow — LLM-Based Thyroid Cancer Risk Factor Extraction Toolkit

![TCRiskFlow overview](docs/main_plot.png)

[中文说明](README.zh-CN.md)

**Author:** Yuqun Zeng
**Email:** zengyuqun@hmc.edu.cn
**Paper:** A scalable LLM-driven framework for evidence synthesis of disease associated risk factors: application to thyroid cancer.

This repository is the public, runnable implementation of the manuscript's methods. Starting from a post-screening abstract table (`abstracts_final.xlsx`, one row per paper with title and abstract), it runs LLM structured extraction, geographic enrichment, title deduplication and thyroid-related triplet filtering, then classifies risk factors into a three-level taxonomy, harmonizes them into synonym groups, matches them to UMLS concepts, and scores them with a composite evidence score that drives temporal, geographic and guideline-oriented analyses.

The LLM transport is OpenAI-message compatible (see below): the user only fills `model`, `api_url` and `api_key` in `config.json`. A bundled demo (100 random abstract rows plus a sampled synonym file) lets the pipeline be demonstrated without distributing the full dataset.

---

## Upstream preprocessing (not implemented here)

The pipeline implemented in this repository starts from `abstracts_final.xlsx`, the post-screening abstract table. The upstream literature-screening steps are described in the manuscript's "Data Source and Preprocessing" section and are **not** part of this repository; they proceed as follows:

1. **Retrieval** — bibliographic records are programmatically retrieved from the Web of Science Core Collection using predefined MeSH terms and free-text keywords for "thyroid cancer", spanning January 1980 to July 2025 (106,785 records with metadata including titles, abstracts, authors, affiliations, country/region and publication year).
2. **Language / source / abstract screening** — records are sequentially screened for language, publication source and abstract availability, leaving 56,800 records.
3. **Document-type filtering and deduplication** — further document-type filtering plus title/abstract-based deduplication yields 55,203 unique records, the final corpus (`abstracts_final.xlsx`) entering the TCRiskFlow pipeline.

---

## What this repository covers

| Capability | Paper section | Script(s) |
| --- | --- | --- |
| Structured abstract extraction (title + abstract → causal triplets) | Structured abstract extraction module | `structured_extraction.py` |
| Title-based deduplication | Data Source and Preprocessing | `deduplicate_title.py` |
| Thyroid-related triplet filtering | Structured abstract extraction module | `count_thyroid_triplets.py` |
| Three-level semantic classification | Semantic taxonomy construction module | `factor_classifier.py`, `classify_risk_factors.py`, `hierarchy.py` |
| Synonym harmonization (per Level-3) | Synonym aggregation and normalization module | `group_synonyms.py`, `merge_age.py` |
| UMLS-style normalization | Synonym aggregation and normalization module | `umls_match.py` |
| Composite evidence score + year/continent/group statistics | Evidence quantification module; Temporal and spatiotemporal evolution analyses | `factor_scoring.py`, `factor_data.py`, `factor_data_semantic.py`, `factor_scores.py`, `evidence_quantification.py` |
| Guideline concordance and gap analysis | Guideline-oriented concordance evaluation and gap analysis | `guideline_analysis.py` |
| Clustering ablation (cosine hierarchy vs. KMeans) | Clustering ablation test | `ablation/` |

---

## Paper-to-code mapping

| # | Paper section | What the paper says | Script(s) | Key parameters |
| --- | --- | --- | --- | --- |
| 1 | Structured abstract extraction module | "DeepSeek-V4 Pro ... JSON schema ... temperature 0.0 ... categorical variables restricted to predefined candidate options" | `structured_extraction.py` | `temperature=0.0`, non-streaming; up to 12 triplets per abstract |
| 2 | Data Source and Preprocessing | "title/abstract-based deduplication yielded unique records" | `deduplicate_title.py` | dedup key = `TI`, `keep="first"` |
| 3 | Structured abstract extraction module | "causal_triplets ... object.disease ... thyroid cancer" | `count_thyroid_triplets.py` | disease substring `thyr` (case-insensitive); compact non-thyroid triplets forward |
| 4 | Semantic taxonomy construction module | "DeepSeek-V4 Pro and Doubao-1.8-Seed ... majority voting ... Level-3 assignments" | `factor_classifier.py`, `classify_risk_factors.py`, `hierarchy.py` | single-stage Level-3 classification; `factor-subcategory.json` (6 Level-1 / 24 Level-2 / 113 Level-3); rule fallback when LLM disabled |
| 5 | Synonym aggregation and normalization module | "synonym harmonization ... within predefined Level-3 categories ... case-insensitive lexicographic rule" | `group_synonyms.py`, `merge_age.py` | canonical key sorted by `(length, term)`; `factor_id = SHA-256(factor_key)`; Age degree terms consolidated |
| 6 | Synonym aggregation and normalization module (UMLS) | "QuickUMLS ... overlapping_criteria='score' ... threshold 0.809 ... discard <0.90" | `umls_match.py` | `SIMILARITY_THRESHOLD = 0.90`; dedup by CUI; keep highest similarity |
| 7 | Evidence quantification module | "Score = w_num·Z[log(n_paper)] + w_size·Z[log(n_sample)] + w_statsig·Z(S_statsig) + w_evigrade·Z(E_evigrade)"; weights `W_num=2, W_size=1, W_statsig=1, W_evigrade=2` | `factor_scoring.py`, `factor_data.py`, `factor_scores.py`, `evidence_quantification.py` | p-value weights 1.0/0.5/0.1; GRADE High/Moderate/Low/Very low = 4/3/2/1; global Z-score with `ddof=0` |
| 8 | Temporal and spatiotemporal evolution analyses | "five predefined periods (before 2000, 2001–2010, 2011–2015, 2016–2020 and 2021–2025)" | `factor_scores.py` | `YEAR_BINS` inclusive endpoints; top-10 by score |
| 9 | Guideline-oriented concordance evaluation and gap analysis | "exact-group match ... shared-term match"; "Coverage = N_matched / N_total ×100%" | `guideline_analysis.py` | `guideline_match_policy="shared_term"`; coverage at 10%/5%/2%/1% |
| 10 | Clustering ablation test | "cosine average-linkage agglomerative ... k-means ... K = number of Level-3 categories ... ARI, NMI, purity, homogeneity, completeness, mapped macro-F1" | `ablation/` (see `docs/ablation_study.md`) | KMeans `random_state=42, n_init=20, max_iter=300, algorithm="lloyd"` |
| 11 | Statistical Analysis | "Counts and percentages ... medians with ranges ... χ², Cramér's V, NMI" | `statistics.py` | bibliometric tables; see `docs/output_spec.md` |

---

## Quick start

```bash
git clone <your-github-url>
cd github_repo
bash scripts/install.sh
bash scripts/run_demo.sh
```

The demo reads `data/sample/abstracts_final_demo_first100.xlsx` and runs structured extraction → geographic enrichment → deduplication → thyroid filtering → classification → synonym harmonization → evidence quantification → UMLS → statistics. Because structured extraction requires an LLM, the demo needs a configured API key to produce results; without it, the pipeline reports a clear message and stops.

For a full run, replace `input_xlsx` in `config.json` with your full `abstracts_final.xlsx` and run:

```bash
bash scripts/run_full.sh
```

### Running the clustering ablation

```bash
python scripts/run_ablation_main.py
```

See [docs/ablation_study.md](docs/ablation_study.md) for the required data format, the two clustering methods and the metric formulas.

---

## Repository layout

```text
github_repo/
├─ config.json / config.example.json
├─ data/
│  ├─ sample/
│  │  ├─ abstracts_final_demo_first100.xlsx
│  │  └─ 09_factor_label_associations_semantic_merged_v2_demo_first100.csv
│  └─ demo_resources/
│     ├─ factor-subcategory.json
│     ├─ umls_concepts_demo.csv
│     ├─ country_continent_reference.csv
│     └─ guideline/{ATA 2015, NCCN 2023}/*.json
├─ prompt/{en,zh}/*.txt
├─ scripts/
│  ├─ run_demo_pipeline_main.py
│  ├─ run_full_pipeline_main.py
│  ├─ run_ablation_main.py
│  └─ build_demo_sample_main.py
├─ src/thca_risk_factor_toolkit/
│  ├─ common.py, hierarchy.py, factor_scoring.py, config.py, path_utils.py
│  ├─ structured_extraction.py
│  ├─ deduplicate_title.py
│  ├─ count_thyroid_triplets.py
│  ├─ classify_risk_factors.py, factor_classifier.py
│  ├─ group_synonyms.py, merge_age.py
│  ├─ factor_data.py, factor_data_semantic.py, factor_scores.py
│  ├─ guideline_analysis.py, evidence_quantification.py
│  ├─ umls_match.py, statistics.py, pipeline.py
│  └─ ablation/{__init__,config,metrics,clustering,run_ablation}.py
├─ docs/
└─ outputs/
```

---

## Main outputs

- `outputs/thca_intermediate_demo.xlsx` — Step 08 triplet labels, the synonym factor map and UMLS matches.
- `outputs/thca_statistics_demo.xlsx` — bibliometric tables, the synonym catalog and UMLS coverage.
- `outputs/10_factor_scores_semantic/` — the evidence score, group statistics and guideline analysis (CSV + Excel).

Representative tables: `factor_score_overall`, `factor_score_by_year_bin`, `year_score_top10`, `continent_year_label1_top10`, `label_3_overall`, `evidence_grade_overall`, `coverage_by_score_percentile`, `unmatched_factors`. See [docs/output_spec.md](docs/output_spec.md).

---

## Dataset policy

The files under `data/sample/` are **randomly sampled 100-row excerpts of the full data**, included only so the pipeline can be demonstrated end-to-end. They are **for program demonstration only** and are not meant for analysis or publication.

The full `abstracts_final.xlsx` and the full `09_factor_label_associations_semantic_merged_v2.csv` are **not** distributed here. To request access, contact **Yuqun Zeng** at `zengyuqun@hmc.edu.cn`; access is granted only after approval.

To run the whole pipeline on the full data, place the full `abstracts_final.xlsx`, set `input_xlsx` in `config.json`, enable the LLM profile, and run `bash scripts/run_full.sh` (see [data/README.md](data/README.md)).

---

## LLM configuration

This repository ships an **OpenAI-message-format compatible** LLM client only (the `chat.completions` message shape), matching public endpoints such as [OpenRouter](https://openrouter.ai) or the [DeepSeek Open Platform](https://platform.deepseek.com). To enable API-based extraction and classification you fill `model`, `api_url` and `api_key` in `config.json`.

Generation always matches the manuscript ("Prompt engineering and model control"): **non-streaming** with **`temperature=0.0`**, and every request/response pair is logged under `agent_data/` for traceability. The model names follow the manuscript exactly:

- `llm` — `DeepSeek-V4-Pro` (OpenAI-compatible), the primary annotator (structured extraction, classification, synonym grouping).
- `secondary_llm` — `Doubao-1.8-Seed` (OpenAI-compatible), the second independent annotator.
- `adjudicator_llm` — `Gemini-3-Pro` (Gemini-compatible), used for long-context semantic clustering and adjudicating discordant assignments.

`provider` only selects the transport (`openai_compatible` vs `gemini_compatible`); it does not hard-code a vendor. Prompt files live under `prompt/en` (used by default) and `prompt/zh`.

## Documentation index

- [docs/architecture.md](docs/architecture.md)
- [docs/ablation_study.md](docs/ablation_study.md)
- [docs/output_spec.md](docs/output_spec.md)
- [docs/manuscript_table_mapping.md](docs/manuscript_table_mapping.md)
- [docs/pipeline_flow_en.txt](docs/pipeline_flow_en.txt)
