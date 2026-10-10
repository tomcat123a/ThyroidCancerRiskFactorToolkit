"""Clustering ablation orchestration: cosine hierarchy vs. same-K KMeans.

For each Level-1 domain, embed the risk-factor terms, cluster them twice
(cosine-average agglomerative and KMeans, both with ``K`` = number of Level-3
categories), and evaluate agreement against the finalized Level-3 labels using
ARI, NMI, purity, homogeneity, completeness and mapped macro-F1.
"""

from __future__ import annotations

import time
from typing import Dict, List

import pandas as pd

from .clustering import (
    cosine_hierarchy_clustering,
    encode_subject_names,
    kmeans_clustering,
    load_embedding_model,
    load_v2_subjects,
)
from .config import AblationConfig, load_config
from .metrics import evaluate_clustering


def run_ablation(config: AblationConfig | None = None) -> dict[str, object]:
    config = config or load_config()
    subjects = load_v2_subjects(config.semantic_v2_csv)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    model = load_embedding_model(config.model_dir)
    summary_rows: List[Dict] = []
    metric_rows: List[Dict] = []
    started = time.monotonic()

    groups = subjects.groupby("label_1", sort=True)
    total = groups.ngroups
    for index, (label_1, group) in enumerate(groups, 1):
        group = group.reset_index(drop=True)
        k = int(group["label_3"].nunique())
        vectors = encode_subject_names(model, group["subject_name"].tolist(), config.preferred_task)

        hierarchy_labels = cosine_hierarchy_clustering(vectors, k)
        kmeans_labels = kmeans_clustering(
            vectors, k, random_state=config.random_state,
            n_init=config.kmeans_n_init, max_iter=config.kmeans_max_iter,
        )
        truth = group["label_3"].tolist()

        hierarchy_eval = evaluate_clustering(truth, hierarchy_labels, label_1=label_1, cluster_scheme="cosine_hierarchy")
        kmeans_eval = evaluate_clustering(truth, kmeans_labels, label_1=label_1, cluster_scheme="same_k_kmeans")

        for evaluation in (hierarchy_eval, kmeans_eval):
            metric_rows.append({"k": k, **evaluation})
        summary_rows.append({
            "label_1": label_1,
            "term_count": len(group),
            "v2_factor_count": group["factor_id"].nunique(),
            "v2_label_3_count": k,
            "hierarchy_vs_v2_ari": hierarchy_eval["ari"],
            "kmeans_vs_v2_ari": kmeans_eval["ari"],
            "hierarchy_vs_v2_nmi": hierarchy_eval["nmi"],
            "hierarchy_vs_v2_purity": hierarchy_eval["purity"],
            "kmeans_vs_v2_purity": kmeans_eval["purity"],
            "hierarchy_vs_v2_macro_f1": hierarchy_eval["mapped_macro_f1"],
            "kmeans_vs_v2_macro_f1": kmeans_eval["mapped_macro_f1"],
        })
        elapsed = time.monotonic() - started
        print(
            f"[ablation] {index}/{total} label_1={label_1} "
            f"terms={len(group)} K={k} elapsed={elapsed:.1f}s "
            f"eta={elapsed / index * (total - index):.1f}s", flush=True,
        )

    summary = pd.DataFrame(summary_rows).sort_values("label_1", kind="stable").reset_index(drop=True)
    metrics = pd.DataFrame(metric_rows).sort_values(["label_1", "cluster_scheme"], kind="stable").reset_index(drop=True)
    summary_path = config.output_dir / "clustering_ablation_summary.csv"
    metrics_path = config.output_dir / "clustering_ablation_metrics.csv"
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    metrics.to_csv(metrics_path, index=False, encoding="utf-8-sig")
    return {"summary": summary_path, "metrics": metrics_path, "output_dir": config.output_dir}


def main() -> None:
    for name, path in run_ablation().items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
