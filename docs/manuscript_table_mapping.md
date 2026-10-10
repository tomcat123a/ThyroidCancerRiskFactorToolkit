# Manuscript Table Mapping

This repository does not reproduce figures, but it exports table-ready data aligned with the TCRiskFlow manuscript themes.

## Covered table themes and their sources

| Manuscript theme | Output table(s) |
| --- | --- |
| Literature volume by period (Fig. 2b) | `paper_year_basic_stats` |
| Study-type composition (Fig. 2a) | `study_type_stats` |
| Continent-level counts by time bin | `continent_year_bin_long` / `continent_year_bin_pivot` |
| Top-10-country counts by time bin (Fig. 2c) | `country_top10_papers`, `country_top10_year_bin_long`, `country_top10_year_bin_pivot` |
| Three-level taxonomy distribution (Fig. 3c/d) | `label_1_overall`, `label_2_overall`, `label_3_overall`, `{label}_by_year_bin` |
| Synonym fusion catalog (Fig. 3b, Suppl. Fig. 3) | `factor_summary`, `factor_synonyms_list` |
| Evidence-grade distribution | `evidence_grade_overall`, `evidence_grade_by_year_bin` |
| Composite-score ranking (Fig. 5a/b) | `factor_score_overall`, `year_score_top10`, `label_1_yearbin_top10` |
| Continent × time trajectories (Fig. 5e) | `continent_year_label1_top10`, `continent_year_label1_summary` |
| Guideline coverage by score percentile (Fig. 6a) | `coverage_by_score_percentile`, `guideline_coverage` |
| Guideline coverage by taxonomy (Fig. 6b) | `{label_1,label_2,label_3}_guideline_coverage` |
| Guideline gaps | `unmatched_factors`, `top10_no_legacy_guideline_hit`, `top100_no_legacy_guideline_hit` |
| UMLS normalization (Fig. 3e/f/g) | `umls_coverage_summary`, `umls_match` |

## Not included

- any plotting output
- upstream preprocessing before `abstracts_final.xlsx`
- licensed full-scale UMLS content
- the full dataset (only demo samples are distributed)
