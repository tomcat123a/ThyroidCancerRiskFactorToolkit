# Output Specification

## 1. Intermediate Workbook

File:

- `outputs/thca_intermediate_demo.xlsx`
- `outputs/thca_intermediate_full.xlsx`

Sheet:

- `triplet_records`

Important columns:

- `_id`: paper identifier
- `TI`: title
- `SO`: journal
- `publish_year`
- `year_bin`
- `study_type`
- `study_design`
- `country_name`
- `continent_name`
- `subject_name`
- `subject_category_raw`
- `relation`
- `direction`
- `disease`
- `object_endpoint_type`
- `evidence_strength_grade_level`
- `label_1`
- `label_2`
- `label`
- `synonym_group_json`
- `factor_name`
- `factor_key`
- `factor_synonyms`
- `factor_group_size`
- `umls_term`
- `umls_cui`
- `umls_semantic_type`
- `umls_match_status`

## 2. Statistics Workbook

File:

- `outputs/thca_statistics_demo.xlsx`
- `outputs/thca_statistics_full.xlsx`

Sheets:

1. `paper_year_basic_stats`
   - one row per year bin
   - `n_papers`

2. `study_type_stats`
   - one row per study type
   - `n_papers`

3. `continent_year_bin_long`
   - long table by continent and year bin
   - `n_factors`
   - `n_papers`

4. `continent_year_bin_pivot`
   - pivot version of the continent table

5. `country_top10_papers`
   - top 10 countries by number of papers

6. `country_top10_year_bin_long`
   - long table for top 10 countries

7. `country_top10_year_bin_pivot`
   - pivot version of the top-10-country table

8. `label1_overall`
   - overall factor and paper counts by level-1 semantic label

9. `label1_year_bin`
   - time-binned factor and paper counts by level-1 semantic label

10. `evidence_grade_overall`
    - overall factor and paper counts by evidence grade

11. `evidence_grade_year_bin`
    - time-binned factor and paper counts by evidence grade

12. `endpoint_top3_factors`
    - top 3 factors by associated paper count inside each endpoint type

13. `factor_synonym_catalog`
    - canonical factor name
    - fused synonym display string
    - group size
    - semantic labels
    - UMLS fields

14. `umls_coverage_summary`
    - matched vs unmatched factor counts

## 3. Run Summary

Files:

- `outputs/run_summary_demo.md`
- `outputs/run_summary_full.md`

Content:

- input workbook path
- number of exported triplet rows
- whether LLM mode was enabled
- output workbook paths
