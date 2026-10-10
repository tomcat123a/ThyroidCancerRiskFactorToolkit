"""Build the public demo dataset from the full intermediate results.

This script is for the repository author (who holds the full data) only.  It is
NOT part of the runtime pipeline and is not required by public users, because
the sampled demo files are already committed under ``data/sample/``.

It produces:

* ``data/sample/09_factor_label_associations_semantic_merged_v2_demo_first100.csv``
  - the first ``sample_size`` synonym factors whose ``factor_key`` contains at
    least one ``subject_name`` that also appears in the demo workbook, so the
    Step 10 join in ``run_demo_pipeline`` stays resolvable.

* ``data/sample/preproc_thca_demo_first100.xlsx``
  - the first ``paper_rows`` rows of the full preprocessed workbook.

Run from the repository root::

    python scripts/build_demo_sample_main.py

No ``argparse`` is used; edit the module constants below to change defaults.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


# --- Default parameters (edit instead of using argparse) --------------------
FULL_PREPROC_XLSX = "data/preproc_thca.xlsx"
FULL_SEMANTIC_CSV = "backend/preproc_prisam/output/09_factor_label_associations_semantic_merged_v2.csv"

DEMO_PREPROC_XLSX = "data/sample/preproc_thca_demo_first100.xlsx"
DEMO_SEMANTIC_CSV = "data/sample/09_factor_label_associations_semantic_merged_v2_demo_first100.csv"

PAPER_ROWS = 100
SAMPLE_SIZE = 100
SUBJECT_COLUMNS = [f"causal_triplets_{i}.subject.name" for i in range(1, 13)]


def _resolve_root() -> Path:
    for origin in (Path.cwd(), Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()):
        for candidate in (origin, *origin.parents):
            if (candidate / "src").is_dir() and (candidate / "data").is_dir():
                return candidate
    return Path.cwd().resolve()


def _collect_subjects(preproc: pd.DataFrame) -> set[str]:
    subjects: set[str] = set()
    for column in SUBJECT_COLUMNS:
        if column in preproc.columns:
            subjects.update(
                str(value).strip()
                for value in preproc[column].dropna().tolist()
                if str(value).strip()
            )
    return subjects


def _factor_key_terms(raw: object) -> set[str]:
    text = "" if raw is None else str(raw).strip()
    if not text:
        return set()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return set()
    if not isinstance(parsed, list):
        return set()
    return {str(term).strip() for term in parsed if str(term).strip()}


def build_demo_preproc(root: Path) -> Path:
    source = root / FULL_PREPROC_XLSX
    if not source.exists():
        raise FileNotFoundError(f"Full preprocessed workbook not found: {source}")
    output = root / DEMO_PREPROC_XLSX
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.read_excel(source, dtype=object).head(PAPER_ROWS).to_excel(output, index=False)
    print(f"[demo] wrote {output}")
    return output


def build_demo_semantic(root: Path) -> Path:
    source = root / FULL_SEMANTIC_CSV
    if not source.exists():
        raise FileNotFoundError(f"Full semantic-merged CSV not found: {source}")
    preproc = pd.read_excel(root / DEMO_PREPROC_XLSX, dtype=object)
    demo_subjects = _collect_subjects(preproc)

    frame = pd.read_csv(source, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    covered = frame[frame["factor_key"].map(
        lambda value: bool(_factor_key_terms(value) & demo_subjects)
    )]
    pool = covered if len(covered) >= SAMPLE_SIZE else frame
    sampled = pool.head(SAMPLE_SIZE)

    output = root / DEMO_SEMANTIC_CSV
    output.parent.mkdir(parents=True, exist_ok=True)
    sampled.to_csv(output, index=False, encoding="utf-8-sig")
    print(
        f"[demo] wrote {output} with {len(sampled)} factors; "
        f"{len(covered)} factors overlap the demo workbook subjects"
    )
    return output


def main() -> None:
    root = _resolve_root()
    build_demo_preproc(root)
    build_demo_semantic(root)


if __name__ == "__main__":
    main()
