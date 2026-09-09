from pathlib import Path

import pandas as pd


def main() -> None:
    source_path = Path("data/preproc_thca.xlsx")
    output_path = Path("data/sample/preproc_thca_demo_first100.xlsx")
    if not source_path.exists():
        raise FileNotFoundError(
            "The full workbook was not found. Place `preproc_thca.xlsx` under `data/` before running this script."
        )
    df = pd.read_excel(source_path, dtype=object)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.head(100).to_excel(output_path, index=False)
    print(f"Saved demo workbook: {output_path}")


if __name__ == "__main__":
    main()
