# TCRiskFlow — LLM-Based Thyroid Cancer Risk Factor Extraction Toolkit

![TCRiskFlow overview](docs/main_plot.png)

[中文说明](README.zh-CN.md)

**Author:** Yuqun Zeng
**Email:** zengyuqun@hmc.edu.cn
**Paper:** A scalable LLM-driven framework for evidence synthesis of disease associated risk factors: application to thyroid cancer.

This repository is the public, runnable implementation of the manuscript's methods. It turns a wide-format preprocessed workbook (`preproc_thca.xlsx`) into a traceable, computable evidence resource: risk factors are classified into a three-level taxonomy, harmonized into synonym groups, matched to UMLS concepts, and scored by a composite evidence score that drives temporal, geographic and guideline-oriented analyses.

A bundled demo (first 100 papers plus a sampled synonym file) lets the whole pipeline run without any API key.

---

## What this repository covers

| Capability | Paper section |
| --- | --- |
| Title-based deduplication | Data Source and Preprocessing |
| Thyroid-related triplet filtering | Structured abstract extraction module |
| Three-level semantic classification | Semantic taxonomy construction module |
| Synonym harmonization (per Level-3) | Synonym aggregation and normalization module |
| UMLS-style normalization | Synonym aggregation and normalization module |
| Composite evidence score + year/continent/group statistics | Evidence quantification module; Temporal and spatiotemporal evolution analyses |
| Guideline concordance and gap analysis | Guideline-oriented concordance evaluation and gap analysis |
| Clustering ablation (cosine hierarchy vs. KMeans) | Clustering ablation test |

Not included (upstream of this repository): WOS retrieval, language/publication-type/abstract screening, and the initial LLM structured extraction that produces the `causal_triplets_*` columns in the preprocessed workbook.

---

## Paper-to-code mapping

Each manuscript method step maps to a module under `src/thca_risk_factor_toolkit/`. The table lists the paper section, the original prose, the corresponding script, and the runtime parameters.

| # | Paper section | What the paper says | Script(s) | Key parameters |
| --- | --- | --- | --- | --- |
| 1 | Data Source and Preprocessing | "title/abstract-based deduplication yielded unique records" | `step05_deduplicate_title.py` | dedup key = `TI`, `keep="first"` |
| 2 | Structured abstract extraction module | "each record ... causal_triplets ... constrained by a JSON schema"; "Fields without sufficient information ... null" | `step07_count_thyroid_triplets.py` | disease substring `thyr` (case-insensitive); compact non-thyroid triplets forward |
| 3 | Semantic taxonomy construction module | "DeepSeek-V4 Pro and Doubao ... majority voting ... Level-3 assignments" | `step08_factor_classifier.py`, `step08_extract_classify.py`, `hierarchy.py` | single-stage Level-3 classification; `factor-subcategory.json` (6 Level-1 / 24 Level-2 / 113 Level-3); rule fallback when LLM disabled |
| 4 | Synonym aggregation and normalization module | "synonym harmonization ... within predefined Level-3 categories ... canonical display name ... case-insensitive lexicographic rule" | `step09_group_synonyms.py`, `step09_merge_age.py` | canonical key sorted by `(length, term)`; `factor_id = SHA-256(factor_key)`; Age degree terms consolidated |
| 5 | Synonym aggregation and normalization module (UMLS) | "QuickUMLS ... overlapping_criteria='score' ... similarity threshold 0.809 ... discard <0.90" | `umls_match.py` | `SIMILARITY_THRESHOLD = 0.90`; dedup by CUI; keep highest similarity |
| 6 | Evidence quantification module | "Score = w_num·Z[log(n_paper)] + w_size·Z[log(n_sample)] + w_statsig·Z(S_statsig) + w_evigrade·Z(E_evigrade)"; weights `W_num=2, W_size=1, W_statsig=1, W_evigrade=2` | `factor_scoring.py`, `step10_factor_data.py`, `step10_factor_scores.py`, `step10_entry.py` | p-value weights 1.0/0.5/0.1; GRADE High/Moderate/Low/Very low = 4/3/2/1; global Z-score with `ddof=0` |
| 7 | Temporal and spatiotemporal evolution analyses | "five predefined periods (before 2000, 2001–2010, 2011–2015, 2016–2020 and 2021–2025)" | `step10_factor_scores.py` | `YEAR_BINS` inclusive endpoints; top-10 by score |
| 8 | Guideline-oriented concordance evaluation and gap analysis | "exact-group match ... shared-term match"; "Coverage = N_matched / N_total ×100%" | `step10_guidelines.py` | `guideline_match_policy="shared_term"`; coverage at 10%/5%/2%/1% |
| 9 | Clustering ablation test | "cosine average-linkage agglomerative clustering ... k-means ... K = number of Level-3 categories ... ARI, NMI, purity, homogeneity, completeness, mapped macro-F1" | `ablation/` (see `docs/ablation_study.md`) | KMeans `random_state=42, n_init=20, max_iter=300, algorithm="lloyd"` |
| 10 | Statistical Analysis | "Counts and percentages ... medians with ranges ... χ², Cramér's V, NMI" | `statistics.py` | bibliometric tables; see `docs/output_spec.md` |

---

## Quick start

```bash
git clone <your-github-url>
cd github_repo
bash scripts/install.sh
bash scripts/run_demo.sh
```

The demo runs Steps 05 → 07 → 08 → 09 → 10 plus UMLS matching and bibliometric statistics on `data/sample/preproc_thca_demo_first100.xlsx`, using the rule-based Step 08 fallback (no LLM key required).

For a full run, replace `input_xlsx` in `config.json` with your full workbook, enable the LLM profile, and run:

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
│  │  ├─ preproc_thca_demo_first100.xlsx
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
│  ├─ step05_deduplicate_title.py
│  ├─ step07_count_thyroid_triplets.py
│  ├─ step08_extract_classify.py, step08_factor_classifier.py
│  ├─ step09_group_synonyms.py, step09_merge_age.py
│  ├─ step10_factor_data.py, step10_factor_data_semantic.py
│  ├─ step10_factor_scores.py, step10_guidelines.py, step10_entry.py
│  ├─ umls_match.py, statistics.py, pipeline.py
│  └─ ablation/{__init__,config,metrics,clustering,run_ablation}.py
├─ docs/
└─ outputs/
```

---

## Main outputs

- `outputs/thca_intermediate_demo.xlsx` — Step 08 triplet labels, the synonym factor map and UMLS matches.
- `outputs/thca_statistics_demo.xlsx` — bibliometric tables, the synonym catalog and UMLS coverage.
- `outputs/10_factor_scores_semantic/` — the Step 10 evidence score, group statistics and guideline analysis (CSV + Excel).

Representative Step 10 tables: `factor_score_overall`, `factor_score_by_year_bin`, `year_score_top10`, `continent_year_label1_top10`, `label_3_overall`, `evidence_grade_overall`, `coverage_by_score_percentile`, `unmatched_factors`. See [docs/output_spec.md](docs/output_spec.md).

---

## Dataset policy

The files under `data/sample/` are **randomly sampled 100-row excerpts of the full data**, included only so the pipeline can be demonstrated end-to-end. They are **for program demonstration only** and are not meant for analysis or publication.

The full `preproc_thca.xlsx` and the full `09_factor_label_associations_semantic_merged_v2.csv` are **not** distributed here. To request access, contact **Yuqun Zeng** at `zengyuqun@hmc.edu.cn`; access is granted only after approval.

To run the whole pipeline on the full data, place the full workbook under `data/preproc_thca.xlsx`, set `input_xlsx` in `config.json`, enable the LLM profiles, and run `bash scripts/run_full.sh` (see [data/README.md](data/README.md)).

---

## LLM configuration

The project loads `config.json` in this order: current working directory first, repository root second. The committed config contains placeholder URL/API keys only; to enable API-based labeling you only need to fill `model`, `api_url` and `api_key`.

Generation always matches the manuscript ("Prompt engineering and model control"): **non-streaming** with **`temperature=0.0`**, and every request/response pair is logged under `agent_data/` for traceability. Three model profiles are defined in `config.json`:

- `llm` — `DeepSeek-V4-Pro` (OpenAI-compatible), the primary annotator.
- `secondary_llm` — `Doubao-1.8-Seed` (OpenAI-compatible), the second independent annotator.
- `adjudicator_llm` — `Gemini-3-Pro` (Gemini-compatible), used for long-context semantic clustering and for adjudicating discordant assignments.

`provider` only selects the transport (`openai_compatible` vs `gemini_compatible`); it does not hard-code a vendor. Prompt files live under `prompt/en` (used by default) and `prompt/zh`.

## Documentation index

- [docs/architecture.md](docs/architecture.md)
- [docs/ablation_study.md](docs/ablation_study.md)
- [docs/output_spec.md](docs/output_spec.md)
- [docs/manuscript_table_mapping.md](docs/manuscript_table_mapping.md)
- [docs/pipeline_flow_en.txt](docs/pipeline_flow_en.txt)
