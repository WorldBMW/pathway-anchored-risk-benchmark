#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""e4_mtx_to_h5.py — E4 (GSE268014 HNSCC, 16 balanced patients) staging →
standard 10x Visium layout consumable by src/st_data.load_sample.

Input : data/e4_hnscc2_staging/{GSM8283xxx}_{Pxxxx}/{prefix}_{file}.gz
        (matrix.mtx, barcodes.tsv, features.tsv, tissue_positions_list.csv,
         scalefactors_json.json, tissue_hires_image.png)
Output: data/e4_hnscc2/{HPVp|HPVn}_{Pxxxx}/
          filtered_feature_bc_matrix.h5          (10x CSC, genes x spots)
          spatial/tissue_positions_list.csv      (gunzipped)
          spatial/scalefactors_json.json         (gunzipped)
          spatial/tissue_hires_image.png         (gunzipped)

Sample-dir names carry the label prefix probe_lodo.severity_of parses:
  HPVp_P5903 -> severity 1 (HPV+),  HPVn_P5909 -> severity 0 (HPV-).

Validation (fail loudly — never silently mis-align):
  1. mtx orientation resolved against barcodes/features counts (auto-transpose)
  2. every h5 barcode must appear in tissue_positions with in_tissue=1;
     uncovered spots are DROPPED from the h5 (loader would KeyError otherwise)
  3. scalefactors must expose tissue_hires_scalef / spot_diameter_fullres
     (standard Space Ranger branch of st_data) or spot_diameter_pixels (legacy)

Usage:
  python scripts/e4_mtx_to_h5.py                 # convert all 16
  python scripts/e4_mtx_to_h5.py --smoke 2      # convert all, load-sample-test 2
"""
from __future__ import annotations
import argparse
import gzip
import json
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

STAGE = ROOT / "data" / "e4_hnscc2_staging"
OUT = ROOT / "data" / "e4_hnscc2"

HPV_POS = ['GSM8283898', 'GSM8283899', 'GSM8283900', 'GSM8283901',
           'GSM8283905', 'GSM8283906', 'GSM8283909', 'GSM8283913']
HPV_NEG = ['GSM8283897', 'GSM8283902', 'GSM8283903', 'GSM8283904',
           'GSM8283907', 'GSM8283908', 'GSM8283910', 'GSM8283911']
PATIENT = {'GSM8283897': 'P5909', 'GSM8283898': 'P5903', 'GSM8283899': 'P5767',
           'GSM8283900': 'P5766', 'GSM8283901': 'P5764', 'GSM8283902': 'P5756',
           'GSM8283903': 'P5751', 'GSM8283904': 'P5736', 'GSM8283905': 'P5735',
           'GSM8283906': 'P5710', 'GSM8283907': 'P5709', 'GSM8283908': 'P5707',
           'GSM8283909': 'P5692', 'GSM8283910': 'P5684', 'GSM8283911': 'P5666',
           'GSM8283913': 'P5636'}


def _read_tsv_gz(p: Path):
    with gzip.open(p, 'rt', encoding='utf-8') as fh:
        return [l.rstrip('\n').split('\t') for l in fh if l.strip()]


def _parse_positions_gz(p: Path) -> dict[str, int]:
    """Mirror st_data._read_tissue_positions: barcode -> in_tissue flag.

    Requires >=6 columns; pxl coords read from last two (same as loader).
    Returns {barcode: in_tissue(0/1)} for ALL rows (header auto-detected).
    """
    import csv
    with gzip.open(p, 'rt', encoding='utf-8') as fh:
        rows = list(csv.reader(fh))
    if not rows:
        return {}
    if rows[0] and rows[0][0].strip().lower() == 'barcode':
        rows = rows[1:]  # header present
    out = {}
    for r in rows:
        if len(r) < 6:
            continue
        out[r[0]] = 1 if r[1] in ('1', 'True', 'true') else 0
    return out


def _gene_names_and_ids(feat_rows):
    """10x features.tsv is (id, name, type); some GEO uploads swap columns.

    Pick the name column as the one NOT dominated by Ensembl-style ids.
    """
    if not feat_rows:
        raise ValueError('empty features.tsv')
    ncols = min(len(r) for r in feat_rows)
    col0 = [r[0] for r in feat_rows]
    ens0 = sum(1 for v in col0 if v.upper().startswith('ENSG')
               or v.startswith('ENSMUSG'))
    if ncols >= 2:
        col1 = [r[1] for r in feat_rows]
        ens1 = sum(1 for v in col1 if v.upper().startswith('ENSG')
                   or v.startswith('ENSMUSG'))
    else:
        col1, ens1 = col0, ens0
    if ens0 > len(col0) * 0.5 and ens1 < len(col1) * 0.5:
        names, ids = col1, col0                     # (id, name) order
    elif ens1 > len(col1) * 0.5 and ens0 < len(col0) * 0.5:
        names, ids = col0, col1                     # (name, id) order
    else:
        names, ids = col1, col0                     # default 10x order
    if ncols >= 3:
        ftypes = [r[2] for r in feat_rows]
    else:
        ftypes = ['Gene Expression'] * len(names)
    return names, ids, ftypes


def _write_10x_h5(path: Path, Xcsc, barcodes, names, ids, ftypes):
    """Xcsc: scipy CSC (n_genes, n_spots). Same layout the simulator writes
    (and st_data._read_10x_h5 reads)."""
    import h5py
    n_genes, n_spots = Xcsc.shape
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, 'w') as f:
        grp = f.create_group('matrix')
        grp.create_dataset('data', data=Xcsc.data.astype(np.float32))
        grp.create_dataset('indices', data=Xcsc.indices.astype(np.int32))
        grp.create_dataset('indptr', data=Xcsc.indptr.astype(np.int64))
        grp.create_dataset('shape',
                           data=np.array([n_genes, n_spots], dtype=np.int64))
        dt = h5py.string_dtype(encoding='utf-8')
        grp.create_dataset('barcodes', data=np.array(barcodes, dtype=dt))
        feat = grp.create_group('features')
        feat.create_dataset('name', data=np.array(names, dtype=dt))
        feat.create_dataset('id', data=np.array(ids, dtype=dt))
        feat.create_dataset('feature_type', data=np.array(ftypes, dtype=dt))


def convert_one(gsm: str, tag: str) -> dict:
    d = STAGE / f'{gsm}_{PATIENT[gsm]}'
    prefix = f'{gsm}_{PATIENT[gsm]}'
    od = OUT / f'{tag}_{PATIENT[gsm]}'
    sp = od / 'spatial'
    sp.mkdir(parents=True, exist_ok=True)

    # --- expression ---
    from scipy.io import mmread
    X = mmread(d / f'{prefix}_matrix.mtx.gz').tocsc()
    feat_rows = _read_tsv_gz(d / f'{prefix}_features.tsv.gz')
    barcodes = [r[0] for r in _read_tsv_gz(d / f'{prefix}_barcodes.tsv.gz')]
    n_g, n_b = len(feat_rows), len(barcodes)
    if X.shape == (n_b, n_g):
        X = X.T.tocsc()                      # uploader stored (spots, genes)
    if X.shape != (n_g, n_b):
        raise ValueError(f'{prefix}: mtx shape {X.shape} matches neither '
                         f'({n_g} genes, {n_b} barcodes)')
    names, ids, ftypes = _gene_names_and_ids(feat_rows)

    # --- positions coverage (loader KeyErrors on uncovered barcodes) ---
    incov = _parse_positions_gz(d / f'{prefix}_tissue_positions_list.csv.gz')
    keep = [i for i, b in enumerate(barcodes) if incov.get(b) == 1]
    dropped = len(barcodes) - len(keep)
    if dropped:
        print(f'  [warn] {prefix}: dropping {dropped} spots without '
              f'in-tissue positions', flush=True)
    if not keep:
        raise ValueError(f'{prefix}: NO barcode covered by tissue_positions')
    if len(keep) < len(barcodes):
        X = X[:, keep]
        barcodes = [barcodes[i] for i in keep]

    # --- spatial files (gunzip into place) ---
    with gzip.open(d / f'{prefix}_tissue_positions_list.csv.gz', 'rb') as fin:
        (sp / 'tissue_positions_list.csv').write_bytes(fin.read())
    with gzip.open(d / f'{prefix}_scalefactors_json.json.gz', 'rb') as fin:
        sf_bytes = fin.read()
    (sp / 'scalefactors_json.json').write_bytes(sf_bytes)
    sf = json.loads(sf_bytes.decode('utf-8'))
    if not ({'tissue_hires_scalef', 'spot_diameter_fullres'} <= sf.keys()
            or 'spot_diameter_pixels' in sf):
        raise ValueError(f'{prefix}: scalefactors missing scale keys: '
                         f'{list(sf)[:6]}')

    hires_gz = d / f'{prefix}_tissue_hires_image.png.gz'
    hires = d / f'{prefix}_tissue_hires_image.png'
    if hires_gz.exists():
        with gzip.open(hires_gz, 'rb') as fin:
            (sp / 'tissue_hires_image.png').write_bytes(fin.read())
    elif hires.exists():
        shutil.copyfile(hires, sp / 'tissue_hires_image.png')
    else:
        raise FileNotFoundError(f'{prefix}: no tissue_hires_image.png(.gz) '
                                f'in staging (detector requires it)')

    _write_10x_h5(od / 'filtered_feature_bc_matrix.h5',
                  X, barcodes, names, ids, ftypes)
    return {'gsm': gsm, 'tag': tag, 'patient': PATIENT[gsm],
            'spots': int(X.shape[1]), 'genes': int(X.shape[0]),
            'dropped': int(dropped),
            'hires_kb': (sp / 'tissue_hires_image.png').stat().st_size // 1024,
            'hires_scalef': float(sf.get('tissue_hires_scalef', 1.0))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--smoke', type=int, default=1,
                    help='load-sample-test this many converted dirs via '
                         'st_data.load_sample (0 disables)')
    args = ap.parse_args()

    report = []
    for gsm in HPV_POS:
        report.append(convert_one(gsm, 'HPVp'))
        print(f'[ok] {gsm} -> HPVp_{PATIENT[gsm]}', flush=True)
    for gsm in HPV_NEG:
        report.append(convert_one(gsm, 'HPVn'))
        print(f'[ok] {gsm} -> HPVn_{PATIENT[gsm]}', flush=True)

    print('\n==== conversion summary ====')
    for r in report:
        print(f"  {r['tag']}_{r['patient']}  spots={r['spots']:<6} "
              f"genes={r['genes']:<6} dropped={r['dropped']:<3} "
              f"hires={r['hires_kb']}KB  scalef={r['hires_scalef']}")
    print(f'total spots = {sum(r["spots"] for r in report)}')

    if args.smoke > 0:
        from src import st_data as S
        from probe_lodo import severity_of
        print('\n==== load_sample smoke test ====')
        dirs = sorted(OUT.iterdir())
        for sd in dirs[:args.smoke]:
            s = S.load_sample(sd)
            print(f'  {s.name}: spots={s.expression.shape[0]} '
                  f'genes={len(s.genes)} image={s.image.size} '
                  f'radius_px={s.spot_radius_px:.1f} '
                  f'severity={severity_of(s.name)}')
    print('DONE')


if __name__ == '__main__':
    main()
