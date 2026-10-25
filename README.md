# MRP-ST-Repair: auditing identity leakage in group-structured data

Code and result archive for the manuscript

> **Auditing label dependence and sibling-unit inflation in group-structured
> representations** (submitted to *Patterns*, Cell Press).

The paper is an audit instrument, not a model. It measures what survives a
group-level holdout after an attempt to remove group identity, and it reports
a negative result on repair utility. This repository carries the simulator, the
audit statistics, the cross-domain runners, the figure generators, and the
result JSONs every reported number is read from. Public cohorts are re-downloaded
by the scripts and are **not** redistributed here.

## What is in the box

| Path | Contents |
|---|---|
| `scripts/exp_crossdomain_audit.py` | the audit itself: tau_LOO, tau_LGO, tau_LDO, the refit-permutation null (B = 2000, seed 20261010), LDI and the dual gate |
| `scripts/refit_grid_audit.py` | the shared estimator behind the audit (ridge probe, closed-form holdouts, permutation machinery) |
| `scripts/exp_unit_ladder_cervical.py` | the unit-resolution ladder (Table S16) |
| `scripts/exp_within_group_label_geomx.py` | the within-group-label control on GeoMx (Table S17) |
| `scripts/exp_regate_v28.py` | the v28 remediation runs: group-preserving permutation null, identity decoding, nominal multiclass readouts, recoding sensitivity, frozen-scale convention, cervical donor map, GeoMx patient-pairing enumeration |
| `scripts/exp_outer_refit_v28.py` | outer-loop refit (encoder, adversary and probe retrained inside each fold) |
| `scripts/make_figures_patterns.py` | Figures 1 to 4, re-derived from `results/*.json` |
| `scripts/make_fig_crossdomain.py` | Figure 5 (cross-domain panels) |
| `scripts/make_graphical_abstract_square.py` | the 1200 x 1200 px graphical abstract |
| `results/` | every JSON the figures and tables read; nothing in the paper is hand-typed |
| `papers/20_MRP-ST-Repair_Patterns/` | manuscript sources, figure files, supplement |
| `src/` | the encoder stack used by the repair experiments |

The simulator and manifests are deterministic: every run is seeded, and the
seeds are recorded in the result JSONs alongside the numbers.

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-patterns.txt

# Figures 1-4 and Figure 5 from the archived results
python scripts/make_figures_patterns.py
python scripts/make_fig_crossdomain.py

# Re-run the audit at the frozen settings
python scripts/exp_crossdomain_audit.py
python scripts/exp_unit_ladder_cervical.py
python scripts/exp_within_group_label_geomx.py --epochs 30 --seeds 0,1,2 --doses 0,0.5,1,2,5

# The v28 remediation runs
python scripts/exp_regate_v28.py --patient-enum
python scripts/exp_outer_refit_v28.py --domain HAR --doses 0,2 --seeds 0
```

`REPRODUCE.md` is the long form: environment, data layout, the two joins that
silently halve a cohort if missed, and a manifest mapping every table and figure
to the command that rebuilds it.

## Data

Five public sources, all re-fetched by the scripts:

| Cohort | Role | Source |
|---|---|---|
| Cervical Visium, 35 sections / 34 donors | validation domain | 10x Genomics; GEO GSE208654, GSE217237 |
| GSE268014 (HNSCC, 16 sections) | external replication | GEO |
| GSE278936 (prostate, 52 sections) | external replication | GEO |
| GSE316098 (GeoMx, 186 compartments / 7 specimens / 6 patients) | within-group-label control | GEO |
| UCI HAR (30 subjects), UCI Gas Sensor Drift (10 batches) | audited predictions only | UCI ML Repository |

Raw participant data are not collected by this study, and the source licences
apply to each accession as deposited.

## What the numbers mean, in one line each

`tau_LOO` is the leave-one-unit-out Kendall tau of a ridge probe; `tau_LGO` holds
out every sibling unit of a group at once; `tau_LDO` holds out a whole group while
the probe is refit. `sigma` is the SD of the refit-permutation null at `tau_LOO`
(B = 2000). `LDI = (tau_LOO - 0.001) / sigma`, with a gate at 1.645; the dual gate
additionally requires `tau_LDO >= 0.7 * tau_base`.

Two caveats are load-bearing when numbers are compared across cohorts:

* LDI is comparable across cohorts **only at a fixed unit count**, because
  `sigma` shrinks as the number of units grows (Table S16).
* The 1.645 reference is a unit-level descriptive threshold, not a group-level 5%
  test. The group-preserving null is reported alongside it, and it is undefined
  where the label does not vary within group (the cervical cohort, sigma = 0).

## Licence

MIT. See `LICENSE`.
