#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Positive-control simulation for MRP-ST / LDI audit validation.

Generates synthetic Visium-format spatial-transcriptomics cohorts with KNOWN
ground-truth signal strength, then the same 7-variant audit (train_st.py) is
run on each to verify the audit discriminates correctly:

  Group A (strong signal)  -> disease ordering is intrinsic to expression
                              -> audit should grade SUPPORTED
  Group B (weak signal)    -> weak intrinsic expression-disease correlation
                              -> audit should grade SUGGESTIVE
  Group C (no signal + batch artifact) -> no real disease signal, only batch
                              -> audit should grade UNSUPPORTED

This is the discriminative-validity validation that a methodology paper must
provide: proving the audit does NOT cry "label memorization" at everything.

Output layout:
  data/sim_st/group_A/{N_001,HSIL_001,CA_001,...}/filtered_feature_bc_matrix.h5
  data/sim_st/group_A/<sample>/spatial/tissue_positions_list.csv
  data/sim_st/group_A/<sample>/spatial/scalefactors_json.json
  data/sim_st/group_A/<sample>/spatial/tissue_hires_image.png  (placeholder)

Usage:
  python scripts/simulate_st_positive_control.py --out data/sim_st --seed 20261006
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import h5py
from scipy.sparse import csc_matrix
from PIL import Image

# allow importing train_st.py (sibling in scripts/) for KEGG gene set
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _write_10x_h5(path: Path, exp: np.ndarray, genes: list[str]):
    """Write a (n_spots, n_genes) dense array as 10x CSC h5 (genes x spots)."""
    n_genes, n_spots = exp.shape[1], exp.shape[0]
    X = csc_matrix(exp.T)  # (n_genes, n_spots)
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as f:
        grp = f.create_group("matrix")
        grp.create_dataset("data", data=X.data.astype(np.float32))
        grp.create_dataset("indices", data=X.indices.astype(np.int32))
        grp.create_dataset("indptr", data=X.indptr.astype(np.int64))
        grp.create_dataset("shape", data=np.array([n_genes, n_spots], dtype=np.int64))
        barcodes = [f"AAACAA{i:06d}" for i in range(n_spots)]
        dt = h5py.string_dtype(encoding="utf-8")
        grp.create_dataset("barcodes", data=np.array(barcodes, dtype=dt))
        feat = grp.create_group("features")
        feat.create_dataset("name", data=np.array(genes, dtype=dt))
        # minimal feature type so readers don't crash
        feat.create_dataset("feature_type",
                            data=np.array(["Gene Expression"] * n_genes, dtype=dt))
        feat.create_dataset("id", data=np.array(genes, dtype=dt))


def _write_positions(path: Path, coords: np.ndarray):
    """coords: (n_spots, 2) array of (pxl_row, pxl_col) in hires pixels."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        fh.write("barcode,in_tissue,array_row,array_col,pxl_row,pxl_col\n")
        for i, (r, c) in enumerate(coords):
            bc = f"AAACAA{i:06d}"
            fh.write(f"{bc},1,{i // 50},{i % 50},{r:.1f},{c:.1f}\n")


def _write_scalefactors(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as fh:
        json.dump({
            "tissue_hires_scalef": 1.0,
            "tissue_lowres_scalef": 0.5,
            "fiducial_diameter_fullres": 100.0,
            "spot_diameter_fullres": 50.0,
        }, fh)


def _write_placeholder_image(path: Path, w: int = 800, h: int = 800):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (w, h), color=(240, 230, 220))
    img.save(path)


def make_grid_coords(n_spots: int, rng: np.random.Generator) -> np.ndarray:
    """Place spots on a roughly hexagonal grid with jitter (spatial autocorr)."""
    side = int(np.ceil(np.sqrt(n_spots)))
    xs, ys = [], []
    for i in range(n_spots):
        row, col = divmod(i, side)
        x = col * 50.0 + (row % 2) * 25.0 + rng.normal(0, 5)
        y = row * 50.0 + rng.normal(0, 5)
        xs.append(x)
        ys.append(y)
    return np.column_stack([ys, xs])  # (row, col)


def generate_cohort(group: str, n_normal: int, n_diseased: int,
                     n_genes: int, n_spots: int, signal_strength: float,
                     batch_strength: float, rng: np.random.Generator,
                     out_dir: Path, pathway_gene_names: list[str],
                     mode: str = "shared",
                     response_low: float = 0.9, response_high: float = 1.1,
                     nonresponder_frac: float = 0.0,
                     prog_present_prob: float = 1.0,
                     slices_per_donor: int = 1):
    """Generate one simulated cohort.

    signal_strength: amplitude of the disease program in diseased samples.
    batch_strength:  per-sample technical noise (independent of disease).
    mode:
      "shared"   -> ONE fixed disease program (same affected pathway genes in
                    every diseased donor). Each diseased donor has:
                      - a response coefficient r_i = 0 for a
                        `nonresponder_frac` fraction (indistinguishable from
                        normal — NO expression change at all, no footprint),
                        else r_i ~ Uniform(response_low, response_high);
                      - each program gene is active in that donor with
                        probability `prog_present_prob` (donor-level dropout).
                    These two knobs are what make the weak arm genuinely
                    borderline rather than "weak but perfectly separable".
      "spurious"  -> IDENTITY-CONFOUNDING arm. EVERY donor (normal AND disease)
                    receives a donor-specific random zero-sum fingerprint of
                    the SAME amplitude over the pathway panel. Classes
                    therefore have identical marginal mean AND dispersion:
                    there is NO class-level feature to transfer (the v1 bug
                    was that only diseased donors were perturbed, leaking a
                    generic "has-perturbation" footprint that any linear LODO
                    probe could detect, τ=0.705 ceiling). Labels can only be
                    fit by memorising per-donor fingerprints -> in-sample
                    learnable, LODO must fail.
    """
    # --- gene panel ---
    n_pathway = len(pathway_gene_names)
    n_bg = n_genes - n_pathway
    bg_gene_names = [f"BG_{i:04d}" for i in range(n_bg)]
    genes = pathway_gene_names + bg_gene_names

    # --- spatial layout (shared across samples for comparability) ---
    coords = make_grid_coords(n_spots, rng)

    # SHARED-arm setup: ONE fixed disease program, identical across donors.
    # Affected-gene draw moved OUT of the per-sample loop (previously re-drawn
    # per donor, which partially destroyed the very transferability we want to
    # validate in groups A/B).
    shared_affected = None
    if mode == "shared" and signal_strength > 0:
        n_affected = max(1, int(n_pathway * 0.6))
        shared_affected = rng.choice(n_pathway, size=n_affected, replace=False)

    # --- generate per-donor expression ---
    # E2 phase-diagram: donor-level params (batch fingerprint, program
    # response, spurious-fingerprint indices) are drawn ONCE per donor and
    # shared across that donor's `slices_per_donor` slices; slice-level
    # randomness (capture mask, lognormal values, spatial-field phase,
    # spot layout) is redrawn per slice. This is the synthetic analogue of
    # the patient-block leakage structure the repair targets.
    severity_names = []  # for filename
    for i in range(n_normal + n_diseased):
        is_disease = i >= n_normal
        sev = 2 if is_disease else 0  # normal=0, cancer=2 (skip HSIL for clean signal)
        prefix = "CA" if is_disease else "N"
        base = f"{prefix}_{i:03d}"

        # ============ DONOR-LEVEL params (shared across slices) ============
        # BATCH ARTIFACT as a DONOR-SPECIFIC per-gene log-offset vector
        # (constant within a donor across spots, re-drawn per donor). This is
        # nuisance that can be fit in-sample but cannot transfer across donors;
        # a global multiplicative shift was rejected because finite-sample class
        # means of the shift correlate with labels (observed LODO leakage).
        batch_vec = rng.normal(0.0, batch_strength, size=n_genes).astype(np.float32)

        # donor-level spurious-fingerprint indices (identity-confounding arm)
        spurious_idx = None
        if mode == "spurious" and signal_strength > 0:
            perm = rng.permutation(n_pathway)
            n_up = max(1, int(n_pathway * 0.30))
            spurious_idx = (perm[:n_up], perm[n_up:2 * n_up])

        # donor-level program response (shared arm, diseased donors only)
        donor_prog = None
        if mode == "shared" and is_disease and shared_affected is not None:
            # NONRESPONDER donors get literally zero perturbation (no
            # footprint at all) -> indistinguishable from normals.
            if rng.random() >= nonresponder_frac:
                r_i = rng.uniform(response_low, response_high)
                amp = signal_strength * r_i
                # donor-level dropout of individual program genes
                active = shared_affected[rng.random(len(shared_affected))
                                         < prog_present_prob]
                if len(active) == 0:
                    active = shared_affected[:1]  # avoid an empty program
                # CONTINUOUS, amplitude-coupled capture gain. v1 used a hard
                # amp>0.05 switch that injected large lognormal(mean=amp)
                # entries, producing an on/off detection cliff (tau 0.13 -> 0.71
                # between amp 0.05 and 0.10). v2 draws the extra entries from
                # the SAME baseline distribution and applies the same program
                # boost, with gain ramping linearly in amp -> graded footprint.
                cap_gain = 0.30 * r_i * float(np.clip(amp / 0.20, 0.0, 1.0))
                donor_prog = (amp, active, cap_gain)

        # ============ SLICE-LEVEL loop (independent randomness) ============
        for s in range(slices_per_donor):
            sname = base if slices_per_donor == 1 else f"{base}_s{s}"
            severity_names.append(sname)

            coords = make_grid_coords(n_spots, rng)

            # SPARSE expression: real Visium is ~90% zero. We draw a per-spot,
            # per-gene Bernoulli mask (capture rate ~8-12%) so the CSC h5 stays small.
            # Nonzero values are log-normal; batch shift scales everything.
            capture_rate = 0.10  # ~10% nonzero per spot, mimicking Visium
            mask = rng.random((n_spots, n_genes)) < capture_rate
            # pathway genes have higher capture rate (they're "real" biology)
            mask[:, :n_pathway] = rng.random((n_spots, n_pathway)) < 0.40

            exp = np.zeros((n_spots, n_genes), dtype=np.float32)
            nonzero = np.where(mask)
            exp[nonzero] = rng.lognormal(mean=0.0, sigma=1.0, size=len(nonzero[0])).astype(np.float32)

            with np.errstate(over="ignore"):
                exp = exp * np.exp(batch_vec)[None, :]

            # spatial smooth field; randomise phase per SLICE
            yy, xx = coords[:, 0], coords[:, 1]
            ph1, ph2 = rng.uniform(0, 2 * np.pi, size=2)
            smooth = (np.sin(xx / 200.0 + ph1) * np.cos(yy / 200.0 + ph2) + 1.0) / 2.0

            if spurious_idx is not None:
                # IDENTITY-CONFOUNDING FINGERPRINT, applied to EVERY donor (normal
                # AND disease) with the SAME amplitude. Only existing nonzero
                # entries are rescaled (no capture-rate change), up/down counts are
                # equal (zero-sum in log space), so the two classes have identical
                # marginal mean/dispersion: nothing transferable across donors.
                up_idx, dn_idx = spurious_idx
                for gidx in up_idx:
                    boost = signal_strength * (0.5 + 0.5 * smooth)
                    cm = mask[:, gidx]
                    exp[cm, gidx] = exp[cm, gidx] * np.exp(boost[cm])
                for gidx in dn_idx:
                    damp = signal_strength * (0.5 + 0.5 * smooth)
                    cm = mask[:, gidx]
                    exp[cm, gidx] = exp[cm, gidx] * np.exp(-damp[cm])

            elif donor_prog is not None:
                amp, active, cap_gain = donor_prog
                boost = amp * (0.5 + 0.5 * smooth)
                for gidx in active:
                    col_mask = mask[:, gidx]
                    exp[col_mask, gidx] = exp[col_mask, gidx] * np.exp(boost[col_mask])
                    if cap_gain > 0.0:
                        zero_mask = ~col_mask
                        new_mask = zero_mask & (rng.random(n_spots) < cap_gain)
                        if new_mask.any():
                            base_vals = rng.lognormal(
                                mean=0.0, sigma=1.0,
                                size=int(new_mask.sum())).astype(np.float32)
                            exp[new_mask, gidx] = base_vals * np.exp(boost[new_mask])

            # LIBRARY-SIZE NORMALIZATION (per spot, fixed target). Removes every
            # total-count class channel (multiplicative zero-sum perturbations are
            # NOT zero-sum on raw counts: exp(+a)+exp(-a)=2cosh(a)>2, which left a
            # donor-level "total activity" correlate even for random fingerprints).
            # Only COMPOSITIONAL signal survives: a shared program direction (arms
            # A/B) transfers; a per-donor random direction (arm C) cannot.
            lib = exp.sum(axis=1, keepdims=True)
            lib[lib == 0] = 1.0
            exp = (exp * (1e4 / lib)).astype(np.float32)

            # write (exp is sparse -> CSC h5 is compact)
            sdir = out_dir / sname
            _write_10x_h5(sdir / "filtered_feature_bc_matrix.h5", exp, genes)
            _write_positions(sdir / "spatial" / "tissue_positions_list.csv", coords)
            _write_scalefactors(sdir / "spatial" / "scalefactors_json.json")
            _write_placeholder_image(sdir / "spatial" / "tissue_hires_image.png")

    # write manifest
    manifest = {
        "group": group,
        "n_normal": n_normal,
        "n_diseased": n_diseased,
        "n_genes": n_genes,
        "n_pathway": n_pathway,
        "n_spots": n_spots,
        "signal_strength": signal_strength,
        "batch_strength": batch_strength,
        "mode": mode,
        "response_low": response_low,
        "response_high": response_high,
        "nonresponder_frac": nonresponder_frac,
        "prog_present_prob": prog_present_prob,
        "slices_per_donor": slices_per_donor,
        "samples": severity_names,
    }
    with open(out_dir / "manifest.json", "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"  [{group}] wrote {len(severity_names)} samples to {out_dir}")
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/sim_st",
                    help="output root for simulated cohorts")
    ap.add_argument("--seed", type=int, default=20261006)
    ap.add_argument("--n_normal", type=int, default=50)
    ap.add_argument("--n_diseased", type=int, default=40)
    ap.add_argument("--n_genes", type=int, default=3000)
    ap.add_argument("--n_spots", type=int, default=1500)
    ap.add_argument("--n_pathway", type=int, default=108,
                    help="number of 'pathway' genes (mimics HPV panel)")
    ap.add_argument("--only", type=str, default="",
                    help="regenerate a single arm: A | B | C (default: all)")
    ap.add_argument("--tag", type=str, default="",
                    help="suffix appended to group dir names, e.g. 'small' -> "
                         "group_A_small. Use with --out for a scale-matched "
                         "cohort so run_ids never collide with the main arms.")
    # per-arm signal / batch controls (tune without editing code)
    ap.add_argument("--signal_a", type=float, default=2.5)
    ap.add_argument("--signal_b", type=float, default=0.20,
                    help="weak-arm per-responder amplitude")
    ap.add_argument("--signal_c", type=float, default=1.2,
                    help="group C identity-confounding arm: amplitude of the "
                         "donor-specific zero-sum fingerprint applied to ALL "
                         "donors (normals too). NOT a disease signal.")
    ap.add_argument("--batch_a", type=float, default=0.3)
    # arm-A response heterogeneity (v2 graded-difficulty design)
    ap.add_argument("--nonresp_a", type=float, default=0.0,
                    help="fraction of arm-A diseased donors with ZERO response "
                         "(no footprint). Grades cross-donor detection rate.")
    ap.add_argument("--present_a", type=float, default=1.0,
                    help="per-donor activation probability of each program "
                         "gene in arm A (donor-level program dropout)")
    ap.add_argument("--batch_b", type=float, default=1.5)
    ap.add_argument("--batch_c", type=float, default=0.5)
    # weak-arm per-donor response envelope + heterogeneity
    ap.add_argument("--resp_b_low", type=float, default=0.15)
    ap.add_argument("--resp_b_high", type=float, default=0.95)
    ap.add_argument("--nonresp_b", type=float, default=0.35,
                    help="fraction of diseased arm-B donors with zero response")
    ap.add_argument("--present_b", type=float, default=0.5,
                    help="per-donor activation probability of each program gene "
                         "in arm B (donor-level program dropout)")
    ap.add_argument("--slices-per-donor", type=int, default=1,
                    help="E2 phase-diagram knob: number of Visium slices per "
                         "donor. Donor-level params (batch fingerprint, program "
                         "response) are shared across a donor's slices; slice-"
                         "level randomness is redrawn per slice. k>1 names "
                         "slices CA_003_s0..s{k-1}.")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    out_root = Path(args.out)

    # Reuse real KEGG-HPV gene names for the pathway panel so the model's
    # HPV-pathway regularizer and proxy label operate on real gene symbols.
    try:
        from train_st import KEGG_HPV_INFECTION_GENES
        pathway_names = sorted(KEGG_HPV_INFECTION_GENES)[:args.n_pathway]
        if len(pathway_names) < args.n_pathway:
            pathway_names += [f"HPV_{i:03d}" for i in range(args.n_pathway - len(pathway_names))]
    except Exception:
        pathway_names = [f"HPV_{i:03d}" for i in range(args.n_pathway)]

    print(f"[sim] pathway genes: {len(pathway_names)} (first 5: {pathway_names[:5]})")

    manifests = {}
    only = args.only.upper()
    suffix = f"_{args.tag}" if args.tag else ""

    def _want(tag):
        return (not only) or (only == tag)

    # Group A: STRONG shared cross-donor program -> expected SUPPORTED.
    if _want("A"):
        gname = f"group_A{suffix}"
        manifests[gname] = generate_cohort(
            gname, args.n_normal, args.n_diseased, args.n_genes, args.n_spots,
            signal_strength=args.signal_a, batch_strength=args.batch_a, rng=rng,
            out_dir=out_root / gname, pathway_gene_names=pathway_names,
            mode="shared", response_low=0.9, response_high=1.1,
            nonresponder_frac=args.nonresp_a,
            prog_present_prob=args.present_a,
            slices_per_donor=args.slices_per_donor)

    # Group B: WEAK shared program: low amplitude, 35% non-responders, 50%
    # per-donor gene dropout, strong batch -> expected SUGGESTIVE.
    if _want("B"):
        gname = f"group_B{suffix}"
        manifests[gname] = generate_cohort(
            gname, args.n_normal, args.n_diseased, args.n_genes, args.n_spots,
            signal_strength=args.signal_b, batch_strength=args.batch_b, rng=rng,
            out_dir=out_root / gname, pathway_gene_names=pathway_names,
            mode="shared", response_low=args.resp_b_low,
            response_high=args.resp_b_high,
            nonresponder_frac=args.nonresp_b,
            prog_present_prob=args.present_b)

    # Group C: SPURIOUS donor-specific zero-sum programs (identity confounding):
    # in-sample separable, LODO must fail -> expected UNSUPPORTED.
    if _want("C"):
        gname = f"group_C{suffix}"
        manifests[gname] = generate_cohort(
            gname, args.n_normal, args.n_diseased, args.n_genes, args.n_spots,
            signal_strength=args.signal_c, batch_strength=args.batch_c, rng=rng,
            out_dir=out_root / gname, pathway_gene_names=pathway_names,
            mode="spurious")

    with open(out_root / ("manifests.json" if not only else f"manifest_{only}.json"),
              "w") as fh:
        json.dump(manifests, fh, indent=2)
    print(f"\n[done] cohorts written to {out_root} (only={only or 'ALL'})")
    print("Next: bash scripts/run_sim_one.sh <group> <variant> <seed> [perm_n]")


if __name__ == "__main__":
    main()
