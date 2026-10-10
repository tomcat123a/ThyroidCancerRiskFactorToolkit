"""Clustering-ablation evaluation metrics.

Reproduces the agreement measures described in the manuscript's "Clustering
ablation test" section: ARI, NMI, purity, homogeneity, completeness and mapped
macro-F1.  The finalized Level-3 labels are used only as an external semantic
reference for post hoc evaluation, never for cluster assignment.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import (
    adjusted_rand_score,
    completeness_score,
    homogeneity_score,
    normalized_mutual_info_score,
    precision_recall_fscore_support,
)
from sklearn.preprocessing import LabelEncoder

try:
    from scipy.optimize import linear_sum_assignment
except Exception:  # pragma: no cover - scipy is available in the target env
    linear_sum_assignment = None


def _contingency(true_labels: Sequence[str], predicted_labels: Sequence[int]) -> pd.DataFrame:
    return pd.crosstab(
        pd.Series(list(true_labels), name="label_3"),
        pd.Series(list(predicted_labels), name="cluster_id"),
        dropna=False,
    )


def purity(true_labels: Sequence[str], predicted_labels: Sequence[int]) -> float:
    table = _contingency(true_labels, predicted_labels)
    if table.empty:
        return float("nan")
    values = table.to_numpy(dtype=float)
    return float(values.max(axis=0).sum() / values.sum())


def _hungarian_mapping(true_labels: Sequence[str], predicted_labels: Sequence[int]) -> Dict[str, str]:
    """One-to-one (Hungarian) mapping from cluster id to the best true label."""
    table = _contingency(true_labels, predicted_labels)
    if table.empty:
        return {}
    row_labels = table.index.tolist()
    col_labels = table.columns.tolist()
    matrix = table.to_numpy(dtype=int)
    mapping: Dict[str, str] = {}

    if linear_sum_assignment is not None:
        max_value = int(matrix.max()) if matrix.size else 0
        cost = max_value - matrix
        row_index, col_index = linear_sum_assignment(cost)
        for row_pos, col_pos in zip(row_index.tolist(), col_index.tolist()):
            mapping[str(col_labels[col_pos])] = str(row_labels[row_pos])

    assigned = set(mapping.values())
    for column in col_labels:
        name = str(column)
        if name in mapping:
            continue
        best_label = str(table[name].idxmax())
        while best_label in assigned:
            best_label = str(table[name].loc[table[name].index != best_label].idxmax())
        mapping[name] = best_label
        assigned.add(best_label)
    return mapping


def mapped_macro_f1(true_labels: Sequence[str], predicted_labels: Sequence[int]) -> float:
    mapping = _hungarian_mapping(true_labels, predicted_labels)
    mapped = [mapping.get(str(int(label)), "") for label in predicted_labels]
    _, _, f1, _ = precision_recall_fscore_support(
        list(true_labels), mapped, average="macro", zero_division=0
    )
    return float(f1)


def evaluate_clustering(
    true_labels: Sequence[str],
    predicted_labels: Sequence[int],
    *,
    label_1: str,
    cluster_scheme: str,
) -> Dict[str, float | int | str]:
    """Return all agreement metrics for one (label_1, cluster_scheme) run."""
    true_list = [str(t).strip() for t in true_labels]
    pred_list = [int(p) for p in predicted_labels]
    n = len(true_list)

    metrics: Dict[str, float | int | str] = {
        "label_1": label_1,
        "cluster_scheme": cluster_scheme,
        "sample_count": n,
        "true_label_count": len(set(true_list)),
        "predicted_cluster_count": len(set(pred_list)),
        "purity": float("nan"),
        "mapped_macro_f1": float("nan"),
        "ari": float("nan"),
        "nmi": float("nan"),
        "homogeneity": float("nan"),
        "completeness": float("nan"),
    }
    if n == 0:
        return metrics

    metrics["purity"] = purity(true_list, pred_list)
    metrics["mapped_macro_f1"] = mapped_macro_f1(true_list, pred_list)

    if n >= 2:
        encoder = LabelEncoder()
        true_encoded = encoder.fit_transform(true_list)
        metrics["ari"] = float(adjusted_rand_score(true_encoded, pred_list))
        metrics["nmi"] = float(normalized_mutual_info_score(true_encoded, pred_list))
        metrics["homogeneity"] = float(homogeneity_score(true_encoded, pred_list))
        metrics["completeness"] = float(completeness_score(true_encoded, pred_list))
    return metrics


def unweighted_mean(metric_rows: List[Dict], column: str) -> float:
    """Unweighted mean of a metric across the six Level-1 domains."""
    values = [float(row[column]) for row in metric_rows if column in row and not _is_nan(row[column])]
    if not values:
        return float("nan")
    return float(np.mean(values))


def _is_nan(value) -> bool:
    try:
        return bool(np.isnan(float(value)))
    except (TypeError, ValueError):
        return False
