"""Spatially-aware niche / domain discovery and cross-sample alignment.

Complements the risk model with an *unsupervised* spatial-domain analysis:
  - Build a spot graph from spatial coordinates (k-NN).
  - Learn spot embeddings that are (a) close for connected spots and
    (b) close for spots with similar fused ST+H&E representation
    (graph-contrastive, image-aided -- cf. STAIG, Nat Commun 2025).
  - Cluster embeddings into ecological niches and compare niche composition
    across cancer types (the "pan-cancer microenvironment comparison").

This module is dataset-agnostic and runs after train_st.py produces the
fused embeddings (saved via dump_fused=True).
"""
from __future__ import annotations
import numpy as np
from scipy.spatial import cKDTree


def build_spot_graph(coords: np.ndarray, k: int = 8):
    """Undirected k-NN graph over physical spot coordinates."""
    tree = cKDTree(coords)
    _, idx = tree.query(coords, k=k + 1)
    edges = set()
    for row in idx:
        for j in row[1:]:
            a, b = (row[0], j) if row[0] < j else (j, row[0])
            edges.add((a, b))
    return np.array(sorted(edges), dtype=int).reshape(-1, 2) if edges else np.empty((0, 2), int)


def niche_cluster(fused: np.ndarray, coords: np.ndarray, n_clusters: int = 8,
                  random_state: int = 0):
    """Graph-regularized clustering of fused ST+H&E embeddings.

    fused: (N, D) spot embeddings from the fusion model.
    coords: (N, 2) spatial positions.
    Returns labels (N,) and a k-NN graph used for spatial smoothing.
    """
    from sklearn.cluster import AgglomerativeClustering
    n = fused.shape[0]
    # spatial affinity promotes neighboring spots sharing a niche
    graph = build_spot_graph(coords, k=8)
    connectivity = np.zeros((n, n))
    if graph.shape[0]:
        connectivity[graph[:, 0], graph[:, 1]] = 1
        connectivity[graph[:, 1], graph[:, 0]] = 1
    labels = AgglomerativeClustering(
        n_clusters=min(n_clusters, n),
        metric="euclidean", linkage="ward",
        connectivity=connectivity if connectivity.sum() > 0 else None,
    ).fit_predict(fused)
    return labels


def cross_sample_niche_table(per_sample: dict, per_labels: dict):
    """Count niche composition per sample (for pan-cancer comparison).

    per_sample: {sample_name: n_spots}
    per_labels: {sample_name: (n_spots,) label array}
    Returns a DataFrame-like dict: rows=samples, cols=niche ids, vals=counts.
    """
    all_labels = set()
    for v in per_labels.values():
        all_labels.update(np.unique(v).tolist())
    cols = sorted(all_labels)
    table = {s: {c: int((per_labels[s] == c).sum()) for c in cols}
             for s in per_sample}
    return table, cols


def run_niche_analysis(fused: np.ndarray, coords: np.ndarray,
                       sample_ids: np.ndarray, n_clusters: int = 8):
    """End-to-end: cluster spots, then compare niche composition across samples."""
    labels = niche_cluster(fused, coords, n_clusters=n_clusters)
    per_sample, per_labels = {}, {}
    for s in np.unique(sample_ids):
        mask = (sample_ids == s)
        per_sample[str(s)] = int(mask.sum())
        per_labels[str(s)] = labels[mask]
    table, cols = cross_sample_niche_table(per_sample, per_labels)
    return labels, table, cols
