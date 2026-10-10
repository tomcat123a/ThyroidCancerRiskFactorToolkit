# Data Notes

## Demo data (random 100 rows)

The files under `sample/` are **randomly sampled 100-row excerpts of the full
data**, provided only so the pipeline can be demonstrated end-to-end without
distributing the real dataset:

- `sample/preproc_thca_demo_first100.xlsx` — the first 100 rows of the
  preprocessed workbook (`preproc_thca.xlsx`).
- `sample/09_factor_label_associations_semantic_merged_v2_demo_first100.csv` —
  a sampled 100-row slice of the Step 09 semantic-merged synonym file.

These samples are **for program demonstration only** and are not meant for
analysis or publication.

## Full data access

The full `preproc_thca.xlsx` and the full
`09_factor_label_associations_semantic_merged_v2.csv` are **not** distributed
in this repository. To request access, contact **Yuqun Zeng** at
`zengyuqun@hmc.edu.cn`; access is granted only after approval.

## Running the full pipeline on the full data

Once you have received the full `preproc_thca.xlsx`:

1. Place the full workbook under `data/preproc_thca.xlsx` (or any path).
2. Edit `config.json`:
   - set `input_xlsx` to the full workbook path;
   - set `llm.enabled` to `true` and fill `model`, `api_url` and `api_key`
     for `llm` (DeepSeek-V4-Pro), `secondary_llm` (Doubao-1.8-Seed) and
     `adjudicator_llm` (Gemini-3-Pro).
3. Run:

```bash
bash scripts/run_full.sh
```

This runs Steps 05 → 07 → 08 → 09 → 10 plus UMLS matching and bibliometric
statistics on the complete dataset. The clustering ablation can then be run
with `python scripts/run_ablation_main.py` after pointing
`clustering_ablation.semantic_v2_csv` at the full Step 09 file.

The preprocessing steps from earlier raw files to `preproc_thca.xlsx` are
outside the scope of this repository.
