"""Build the public demo dataset from the full intermediate results.

This script is for the repository author (who holds the full data) only.  It is
NOT part of the runtime pipeline and is not required by public users, because
the sampled demo files are committed under ``data/sample/``.

It produces:

* ``data/sample/abstracts_final_demo_first100.xlsx``
  - a random 100-row (plus header) sample of ``abstracts_final.xlsx``, the
    post-screening abstract table that is the pipeline input.

* ``data/sample/09_factor_label_associations_semantic_merged_v2_demo_first100.csv``
  - a random 100-row sample of the Step 09 semantic-merged synonym file.

Run from the repository root::

    python scripts/build_demo_sample_main.py

No ``argparse`` is used; edit the module constants below to change defaults.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


# --- Default parameters (edit instead of using argparse) --------------------
FULL_ABSTRACTS_FINAL_XLSX = "backend/preproc_prisam/output/abstracts_final.xlsx"
FULL_SEMANTIC_CSV = "backend/preproc_prisam/output/09_factor_label_associations_semantic_merged_v2.csv"

DEMO_ABSTRACTS_XLSX = "data/sample/abstracts_final_demo_first100.xlsx"
DEMO_SEMANTIC_CSV = "data/sample/09_factor_label_associations_semantic_merged_v2_demo_first100.csv"

SAMPLE_SIZE = 100
RANDOM_STATE = 42


def _resolve_root() -> Path:
    for origin in (Path.cwd(), Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()):
        for candidate in (origin, *origin.parents):
            if (candidate / "src").is_dir() and (candidate / "data").is_dir():
                return candidate
    return Path.cwd().resolve()


def build_demo_abstracts(root: Path) -> Path:
    source = root / FULL_ABSTRACTS_FINAL_XLSX
    if not source.exists():
        raise FileNotFoundError(f"完整摘要表未找到：{source}")
    output = root / DEMO_ABSTRACTS_XLSX
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.read_excel(source, dtype=object)
    sampled = frame.sample(n=min(SAMPLE_SIZE, len(frame)), random_state=RANDOM_STATE)
    sampled.to_excel(output, index=False)
    print(f"[demo] wrote {output} with {len(sampled)} rows (random sample)")
    return output


def build_demo_semantic(root: Path) -> Path:
    source = root / FULL_SEMANTIC_CSV
    if not source.exists():
        raise FileNotFoundError(f"完整语义合并文件未找到：{source}")
    output = root / DEMO_SEMANTIC_CSV
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(source, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    sampled = frame.sample(n=min(SAMPLE_SIZE, len(frame)), random_state=RANDOM_STATE)
    sampled.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"[demo] wrote {output} with {len(sampled)} rows (random sample)")
    return output


def main() -> None:
    root = _resolve_root()
    build_demo_abstracts(root)
    build_demo_semantic(root)


if __name__ == "__main__":
    main()
