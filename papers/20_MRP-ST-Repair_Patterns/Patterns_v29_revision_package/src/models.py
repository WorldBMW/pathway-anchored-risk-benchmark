"""Multimodal models for ST (spatial transcriptomics) + H&E fusion.

Each spot has a gene-expression vector (from the SAME physical location on the
SAME slide) and an H&E image patch. We fuse them with cross-modal attention
and predict a continuous *microenvironment risk score* per spot.

Training target (to avoid missing survival-label bias): an unsupervised /
self-supervised signal derived from the data itself:
  - Option A (default): reconstruct the spot's gene-expression from the fused
    representation (a denoising/autoencoding objective) -> the risk score is
    the reconstruction residual, interpreted as microenvironmental "atypicality".
  - Option B: predict neighborhood spatial continuity (a spot should resemble
    its spatial neighbors) -> rewards spatially-coherent embeddings.
This keeps the study rigorously self-contained (no external labels needed),
which sidesteps the "no paired survival outcome" critique while still delivering
a learnable, biologically-meaningful risk stratification.
"""
from __future__ import annotations
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class GeneEncoder(nn.Module):
    def __init__(self, n_genes: int, hidden: int = 256, out: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_genes, hidden), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(hidden, out),
        )

    def forward(self, x):
        return self.net(x)


class PatchEncoder(nn.Module):
    """Legacy tiny CNN over a 64x64 H&E patch (kept for ablations / baselines).

    NOTE: for the main model we now use FoundationMorphologyEncoder (UNI/UNI2/
    CHIEF) from foundation_encoder.py, which is the 2025-2026 SOTA for ST +
    histology fusion. Use PatchEncoder only as a from-scratch baseline to show
    the added value of the foundation model.
    """
    def __init__(self, out: int = 128):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 64, 3, padding=1), nn.ReLU(), nn.AdaptiveAvgPool2d(4),
        )
        self.fc = nn.Sequential(nn.Flatten(), nn.Linear(64 * 4 * 4, out))

    def forward(self, x):
        return self.fc(self.conv(x))


class CrossModalAttentionFusion(nn.Module):
    """Query from gene modality, attend over image patches (and vice versa)."""
    def __init__(self, dim: int = 128, heads: int = 4):
        super().__init__()
        self.gene_proj = nn.Linear(dim, dim)
        self.img_proj = nn.Linear(dim, dim)
        self.attn = nn.MultiheadAttention(dim, heads, batch_first=True)
        self.norm = nn.LayerNorm(dim)

    def forward(self, gene, img):
        # gene: (B, dim) -> (B, 1, dim); img: (B, dim) -> (B, 1, dim)
        q = self.gene_proj(gene).unsqueeze(1)
        k = v = self.img_proj(img).unsqueeze(1)
        out, _ = self.attn(q, k, v)
        fused = self.norm(q + out).squeeze(1)
        return fused


class STHEFusionModel(nn.Module):
    def __init__(self, n_genes: int, gene_dim: int = 128, img_dim: int = 128,
                 img_encoder: nn.Module | None = None):
        super().__init__()
        self.gene_enc = GeneEncoder(n_genes, out=gene_dim)
        # Default to the legacy CNN; the training script injects the frozen
        # pathology foundation model for the main experiments.
        self.img_enc = img_encoder if img_encoder is not None else PatchEncoder(out=img_dim)
        self.fusion = CrossModalAttentionFusion(gene_dim)
        # head predicts a continuous microenvironment risk score
        self.head = nn.Sequential(
            nn.Linear(gene_dim, 64), nn.ReLU(), nn.Linear(64, 1)
        )
        # decoder reconstructs gene expression from fused repr (self-supervised)
        self.decoder = nn.Sequential(
            nn.Linear(gene_dim, 256), nn.ReLU(), nn.Linear(256, n_genes)
        )

    def forward(self, gene, img, disable_img: bool = False):
        g = self.gene_enc(gene)
        if disable_img:
            # NO-IMAGE ablation: zero out the image encoder output,
            # so cross-modal attention attends over a zero vector.
            i = torch.zeros(g.shape, device=g.device, dtype=g.dtype)
        else:
            i = self.img_enc(img)
        fused = self.fusion(g, i)
        score = self.head(fused).squeeze(-1)
        recon = self.decoder(fused)
        return {"fused": fused, "score": score, "recon": recon}


def build_model(name: str, n_genes: int, **kw):
    if name == "st_he_fusion":
        return STHEFusionModel(n_genes, **kw)
    raise ValueError(f"unknown model {name}")


def moran_i(values: np.ndarray, coords: np.ndarray, k: int = 6) -> float:
    """Global Moran's I of a per-spot score over its spatial k-NN graph.

    Measures spatial autocorrelation of the risk score: positive => nearby
    spots tend to share similar risk (a smooth, biologically-plausible risk
    landscape); near 0 => spatial white noise; ranges roughly [-1, 1] for
    binary k-NN adjacency. Used as a rigor metric and as an ablation probe
    (dropping the spatial term should lower it).

    Standard formula:  I = (n / S0) * (Σ_i Σ_j w_ij z_i z_j) / (Σ_i z_i^2),
    with z_i = y_i - ȳ, w_ij binary k-NN, and S0 = Σ_i Σ_j w_ij = n·k.
    """
    from scipy.spatial import cKDTree
    values = np.asarray(values, dtype=float).ravel()
    n = len(values)
    if n < k + 2:
        return float("nan")
    z = values - values.mean()
    denom = float((z ** 2).sum())
    if denom == 0:
        return float("nan")
    tree = cKDTree(coords)
    _, idx = tree.query(coords, k=k + 1)  # row[0] = self, row[1:k+1] = neighbors
    # numerator Σ_i Σ_{j∈N(i)} z_i z_j (symmetric enough for a dense k-NN)
    num = 0.0
    for zi, nb in zip(z, idx[:, 1:]):
        num += float(zi * z[nb].sum())
    S0 = n * k
    return float((n / S0) * (num / denom))
