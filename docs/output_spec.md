# Output Specification

## 1. Intermediate workbook

- `outputs/thca_intermediate_demo.xlsx` (or `..._full.xlsx`)

Sheets:

- `triplet_labels` — Step 08 output: one row per risk-factor triplet with `subject_name`, `TI`, `relation`, `direction`, `object_endpoint_type`, `evidence_strength_grade_level`, `_source_row_id`, `label_1`, `label_2`, `label_3`.
- `factor_map` — Step 09 synonym factor map: one row per `subject_name` with `factor_id`, `factor_key`, `factor_name`, `factor_synonyms`, `factor_group_size`, `label_1`, `label_2`, `label_3`.
- `umls_match` — UMLS match per factor (`factor_id`, `umls_matcher_best_cui`, `umls_matcher_best_term`, `umls_matcher_best_similarity`, `umls_matcher_best_semtypes`, ...).

## 2. Statistics workbook

- `outputs/thca_statistics_demo.xlsx` (or `..._full.xlsx`)

Sheets (bibliometric + catalog):

- `paper_year_basic_stats` — publications per year bin.
- `study_type_stats` — publications per study type.
- `continent_year_bin_long` / `continent_year_bin_pivot` — publications by continent and year bin.
- `country_top10_papers` — top 10 countries by paper count.
- `factor_synonym_catalog` — canonical factor, synonym list, group size and taxonomy labels.
- `umls_coverage_summary` — matched vs unmatched factor counts.

## 3. Step 10 outputs

- `outputs/10_factor_scores_semantic/`

CSV (with an `.xlsx` presentation copy and a same-name subdirectory of full CSVs):

| File | Tables |
| --- | --- |
| `10_factor_scores.xlsx` | `factor_score_overall`, `factor_score_by_year_bin`, `year_score_top10`, `label_1_yearbin_top10`, `global_score_parameters`, `qa_overview` |
| `10_factor_scores_continent_year.xlsx` | `continent_year_label1_top10`, `continent_year_label1_summary`, `continent_year_label1_all`, `geo_score_parameters` |
| `10_factor_groupby_stats.xlsx` | `factor_summary`, `factor_synonyms_list`, `continent_*`, `country_top10_*`, and `{label_1,label_2,label_3,evidence_grade,disease,object_endpoint_type}_{overall,by_year_bin,top5_factors,year_top5}` |
| `10_guideline_analysis.xlsx` | `factor_score_overall`, `guideline_coverage`, `coverage_by_score_percentile`, `{label_1,label_2,label_3}_guideline_coverage`, `inclusion_lag_summary`, `per_factor_lag`, `top10_no_legacy_guideline_hit`, `unmatched_factors`, `guideline_match_audit` |
| `10_triplet_factor_audit.csv` | one row per source triplet with parsed p-value/sample/evidence fields |
| `10_factor_paper_audit.csv` | one row per paper-factor with merged components |
| `10_factor_label_associations.csv` | de-duplicated factor → taxonomy label association |
| `10_run_manifest.json` | run metadata, settings, QA counts |

## 4. Key scoring fields (in `factor_score_overall`)

- `num_publish_paper`, `total_sample_size`, `avg_statsig_grade`, `avg_evigrade` — the four raw components.
- `log_num_publish_paper`, `log_total_sample_size` — natural-log transforms.
- `z_*` — Z-standardized components; `score_*_component` — weighted components; `score` — the composite score.
- `first_published_year`, `100_published_year` — temporal benchmarks.
- `in_guideline_*`, `any_guideline`, `first_inclusion_year`, `inclusion_lag_years` — guideline fields.

## 5. Clustering ablation outputs

- `outputs/ablation_study/`
  - `clustering_ablation_summary.csv` — one row per Level-1 domain.
  - `clustering_ablation_metrics.csv` — one row per (Level-1, clustering scheme).
