"""Embedding generation and the two clustering algorithms for the ablation.

Reproduces the manuscript's "Clustering ablation test": risk-factor terms are
embedded with ``jina-embeddings-v5-text-small``, L2-normalized, then clustered
within each Level-1 domain by (a) cosine-average-linkage agglomerative
clustering and (b) KMeans, both using ``K`` equal to the number of Level-3
categories in that domain.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Sequence

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import cut_tree, linkage
from scipy.spatial.distance import pdist
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize

V2_REQUIRED_COLUMNS = (
    "label_1", "label_2", "label_3", "factor_id", "factor_key",
    "factor_name", "factor_group_size",
)


def load_v2_subjects(path: Path) -> pd.DataFrame:
    """Read the semantic-merged v2 CSV and explode each factor into term rows.

    Returns one row per ``subject_name`` with columns
    ``[label_1, label_2, label_3, factor_id, factor_name, subject_name]``.
    """
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = set(V2_REQUIRED_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"v2 文件缺少列: {sorted(missing)}")
    frame = frame[list(V2_REQUIRED_COLUMNS)].copy()
    for column in ("label_1", "label_2", "label_3", "factor_id", "factor_name"):
        if frame[column].str.strip().eq("").any():
            raise ValueError(f"v2 文件的 {column} 有空值")
    if frame["factor_id"].duplicated().any():
        raise ValueError("v2 文件存在重复 factor_id")

    def parse_terms(row: pd.Series) -> List[str]:
        terms = json.loads(row["factor_key"])
        if (not isinstance(terms, list) or not terms
                or any(not isinstance(t, str) or not t.strip() for t in terms)
                or len(set(terms)) != len(terms)
                or len(terms) != int(row["factor_group_size"])):
            raise ValueError(f"因子同义词列表或组大小无效: {row['factor_id']}")
        return terms

    frame["subject_name"] = frame.apply(parse_terms, axis=1)
    subjects = frame.drop(columns=["factor_group_size"]).explode("subject_name", ignore_index=True)
    if subjects["subject_name"].duplicated().any():
        raise ValueError("v2 的 subject_name 跨因子重复，无法逐词对照")
    return subjects.sort_values(
        ["label_1", "label_2", "label_3", "subject_name"], kind="stable"
    ).reset_index(drop=True)


def load_embedding_model(model_dir: Path):
    import torch
    from sentence_transformers import SentenceTransformer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_kwargs = {"dtype": torch.bfloat16} if device == "cuda" else {}
    return SentenceTransformer(str(model_dir), trust_remote_code=True, device=device, model_kwargs=model_kwargs)


def encode_subject_names(model, subject_names: Sequence[str], task: str = "clustering") -> np.ndarray:
    embeddings = model.encode(
        sentences=list(subject_names),
        task=task,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return normalize(np.asarray(embeddings, dtype=np.float32), norm="l2").astype(np.float32)


def cosine_hierarchy_clustering(vectors: np.ndarray, k: int) -> np.ndarray:
    """Cosine-average-linkage agglomerative clustering, cut at ``k`` clusters."""
    n = len(vectors)
    if not 1 <= k <= n:
        raise ValueError(f"K 超出术语数范围: k={k}, n={n}")
    if k == 1:
        return np.zeros(n, dtype=int)
    if k == n:
        return np.arange(n, dtype=int)
    distances = pdist(vectors, metric="cosine")
    if not np.isfinite(distances).all():
        raise ValueError("余弦距离存在非有限值")
    tree = linkage(np.maximum(distances, 0), method="average")
    labels = cut_tree(tree, n_clusters=[k]).ravel().astype(int)
    if len(np.unique(labels)) != k:
        raise ValueError(f"层次聚类未得到目标类别数 {k}")
    return labels


def kmeans_clustering(vectors: np.ndarray, k: int, random_state: int = 42, n_init: int = 20, max_iter: int = 300) -> np.ndarray:
    """KMeans with the manuscript's fixed seed and Lloyd algorithm."""
    n = len(vectors)
    if k == n:
        return np.arange(n, dtype=int)
    model = KMeans(
        n_clusters=int(k),
        random_state=int(random_state),
        n_init=int(n_init),
        max_iter=int(max_iter),
        algorithm="lloyd",
    )
    return model.fit_predict(vectors).astype(int)
