from thca_risk_factor_toolkit.ablation import run_ablation


def main() -> None:
    for name, path in run_ablation().items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
