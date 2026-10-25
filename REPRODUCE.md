# Reproducing the MRP-ST-Repair manuscript

Auditing label dependence and sibling-unit inflation in group-structured
representations (submitted to *Patterns*, Cell Press).

Every reported number is re-derived from a file in `results/`. The scripts
download the public cohorts themselves; no dataset ships with this repository.

## Environment

Python 3.13. The exact versions that produced the reported numbers are pinned in
`requirements-patterns.txt`:

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-patterns.txt
```

`requirements.txt` is an older pin for a different project and does not match
this manuscript; do not use it for this paper.

The full dose grid plus the two permutation-calibrated probes take a few hours on
a laptop CPU. The within-group-label control is the longest single run, at about
24 minutes. The v28 group-preserving null adds B = 2,000 refit permutations per
run on top of that.

## Data

| Cohort | Role in the paper | Where it comes from |
|---|---|---|
| Cervical Visium, 35 sections / 34 donors | validation domain, decision boundary I | 10x Genomics plus GEO GSE208654 and GSE217237 |
| GSE268014 (HNSCC, 16 sections) | external replication, head-to-head | GEO |
| GSE278936 (prostate, 52 sections) | external replication, head-to-head | GEO |
| GSE316098 (GeoMx, 186 compartments, 7 specimens, 6 patients) | within-group-label control | GEO |
| UCI HAR (30 subjects) | audited predictions only | UCI ML Repository |
| UCI Gas Sensor Array Drift (10 batches) | audited predictions only | UCI ML Repository |

Put the downloaded files under `data/` using the layout the loaders expect in
`scripts/exp_crossdomain_audit.py` and `scripts/exp_within_group_label_geomx.py`
(each loader prints the exact path it opens). GEO series are fetched with the
accession as the folder name.

Two joins cost hours if they are missed:

* In GSE316098 the count matrix labels ROIs as `1b-1.001.epi` while
  `sample_metadata.json` labels the same ROI `1b.1.001.epi`. A direct join
  matches 94 of 186 ROIs and silently halves the cohort. The loader falls back to
  `key.replace("-", ".")` and asserts 186.
* GSE278936 is distributed per section, not per donor; the loader derives the
  donor key from the section name and asserts the donor count.

The cervical cohort is 35 sections from 34 donors: `CA_HPV_1` and `CA_HPV_2` are
two sections of one donor. The two GeoMx specimens that share a patient are not
identified in the source, so the v28 analysis enumerates all 21 possible
pairings instead of asserting one.

## Reproducing the reported items

Run from the repository root.

```bash
# Figures 1-4: every plotted number is re-derived from results/*.json
python scripts/make_figures_patterns.py

# Figure 5: cross-domain panels (UCI HAR, gas drift)
python scripts/make_fig_crossdomain.py

# Graphical abstract (1200 x 1200 px, 300 dpi, Arial)
python scripts/make_graphical_abstract_square.py

# The audit at the frozen settings: B = 2000, seed 20261010,
# LDI = (tau_LOO - 0.001) / sigma, gate at 1.645
python scripts/exp_crossdomain_audit.py          # -> results/crossdomain_audit.json
python scripts/exp_unit_ladder_cervical.py       # -> results/unit_ladder_cervical.json
python scripts/exp_within_group_label_geomx.py --epochs 30 --seeds 0,1,2 \
       --doses 0,0.5,1,2,5                       # -> results/within_group_label_geomx.json

# The v28 remediation experiments (Table 7, Tables S18-S19)
python scripts/exp_regate_v28.py --patient-enum  # -> results/regate_v28.json
python scripts/exp_outer_refit_v28.py --domain HAR --doses 0,2 --seeds 0
```

## What the numbers mean, in one line each

`tau_LOO` is the leave-one-unit-out Kendall tau of a ridge probe; `tau_LGO` holds
out every sibling unit of a group at once; `tau_LDO` holds out a whole group while
the probe is refit. `sigma` is the SD of the refit-permutation null at `tau_LOO`
(B = 2000). `LDI = (tau_LOO - 0.001) / sigma` with a gate at 1.645, and the dual
gate additionally requires `tau_LDO >= 0.7 * tau_base`.

Three caveats are load-bearing when numbers are compared across cohorts:

* LDI is comparable across cohorts **only at a fixed unit count**, because
  `sigma` shrinks as the number of units grows (Table S16: 0.178 at K = 1 to
  0.072 at K = 8).
* The 1.645 reference is a unit-level descriptive threshold. It is not a
  group-level 5% test; the group-preserving null is reported next to it (Table 7),
  and it is degenerate, hence undefined, where the label does not vary within
  group.
* The group-count feasibility boundary is a property of a configuration (encoder,
  SNR, overlap of the signal and identity subspaces). Its numeric placement is not
  a transferable cut-off; recalibrate it with the simulator before using it on a
  new cohort.

## Manuscript build chain

`papers/20_MRP-ST-Repair_Patterns/` holds the markdown sources
(`MRP-ST-Repair_manuscript_Patterns_v28.md`, `TitlePage_Patterns.md`,
`CoverLetter_Patterns.md`) and the figure files.

The revision scripts `scripts/_rev_v*_patterns.py` record which sentence changed
in which version. `scripts/_qa_v28.py` enforces the formatting constraints: no em
dashes, no literal markdown emphasis in the docx, seven main tables, four
Highlights of at most 85 characters, and the word limits on In brief, Summary and
the Bigger picture box.

Two build rules matter because breaking them loses content silently:

* The supplement is **appended, never regenerated**.
  `Supplemental_Information_Patterns.docx` is opened with python-docx and tables
  are added to it; regenerating it from markdown would drop S1 to S17.
* `Manuscript_Patterns.docx` carries five **embedded images**, so it is patched in
  place (`scripts/_rev_v28_patterns.py`, `scripts/_fill_doi_v28.py`). Running
  `_md2docx.py` on the manuscript would drop the images. `_md2docx.py` is safe for
  the title page and the cover letter only.

## Figure and table manifest

Nothing here is hand-typed: the supplemental tables are generated from
`results/*.json`, and the main-text tables are transcribed from the same files.

| Item | Built by | Reads |
|---|---|---|
| Figures 2 to 4 | `scripts/make_figures_patterns.py` | `results/*.json` |
| Figure 1 (framework schematic) | `scripts/make_figures_patterns.py` | no data (schematic) |
| Figure 5 (cross-domain) | `scripts/make_fig_crossdomain.py` | `results/crossdomain_audit.json` |
| Graphical abstract, 1200 x 1200 | `scripts/make_graphical_abstract_square.py` | no data (schematic) |
| Supplemental tables S1 to S9 | `scripts/make_supplemental_patterns.py` | `results/*.json` |
| Table S13 (cross-domain inflation) | `scripts/exp_crossdomain_audit.py` | `results/crossdomain_audit.json` |
| Tables S14-S15 (dose-grid sigma drift, sensitivity to c) | `scripts/_rev_v8_s14.py`, `scripts/_rev_v9_s15.py` | `results/repair_e4_hnscc_stable.json`, `results/repair_prostate_gse278936_stable.json` |
| Table S16 (unit-resolution ladder) | `scripts/exp_unit_ladder_cervical.py` | `results/unit_ladder_cervical.json` |
| Table S17 (within-group-label control) | `scripts/exp_within_group_label_geomx.py` | `results/within_group_label_geomx.json` |
| Tables S18-S19 (v28 run detail) | `scripts/_si_append_v28.py` | `results/regate_v28.json` |
| Main tables 1 to 5, and Table 7 | transcribed from the same result JSONs | see the checksum argument below |
| Main table 6 (key resources) | static, in the manuscript source | this paper |

S10 to S12 are emitted by the backbone-ablation and aggregation runs
(`scripts/agg_backbone_ablation.py` and the audit scripts).

## Cross-cohort comparability

`sigma` depends on the number of units, so an LDI value is meaningful only next to
the unit count it was computed at. The resolution ladder (Table S16) is the
measurement of that dependence, and it is the reason the paper does not rank
cohorts by a single LDI number.
