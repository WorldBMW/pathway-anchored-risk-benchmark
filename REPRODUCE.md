# Reproducing the MRP-ST-Repair manuscript

Auditable repair of identity leakage in group-structured data: the sibling-unit
trap, decision boundaries, and validation in spatial transcriptomics.

Everything reported in the paper is regenerated from public data by the scripts
listed below. The archive does not redistribute raw data; the scripts download
it. Released from the tagged GitHub release, archived at Zenodo (DOI in the
manuscript's Data and code availability statement).

## Environment

Python 3.13, CPU only (no GPU run is needed for any reported number).

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-patterns.txt
```

`requirements-patterns.txt` pins the versions that produced the reported
numbers. `requirements.txt` is the older CMPB-era pin and does not match this
manuscript; do not use it for this paper.

The full dose grid plus the two permutation-calibrated probes take a few hours
on a laptop CPU. The within-group-label control is the longest single run at
about 24 minutes.

## Data

| Cohort | Role in the paper | Where it comes from |
|---|---|---|
| Cervical Visium, 35 slides | validation domain, decision boundary I | 10x Genomics, Human Cervical Cancer FFPE |
| GSE268014 (HNSCC, 16 patients) | external replication, real-cohort head-to-head | GEO |
| GSE278936 (prostate, 52 sections) | external replication, real-cohort head-to-head | GEO |
| GSE316098 (GeoMx, 186 ROIs / 7 cases) | within-group-label control | GEO |
| UCI HAR (30 subjects) | audited predictions only | UCI ML Repository |
| UCI Gas Sensor Array Drift (10 batches) | audited predictions only | UCI ML Repository |

Put the downloaded files under `data/` using the layout in
`scripts/exp_crossdomain_audit.py` and `scripts/exp_within_group_label_geomx.py`
(the loaders print the exact path they expect). GEO series are fetched with the
accession as the folder name.

Two joining details cost hours if they are missed:

* In GSE316098 the count matrix labels ROIs as `1b-1.001.epi` while
  `sample_metadata.json` labels the same ROI `1b.1.001.epi`. A direct join
  matches 94 of 186 ROIs and silently halves the cohort. The loader falls back
  to `key.replace("-", ".")` and asserts 186.
* GSE278936 is distributed per section, not per donor; the loader derives the
  donor key from the section name and asserts the donor count.

## Reproducing the reported items

Run from the repository root.

```bash
# Figure 1-4: every plotted number is re-derived from results/*.json
python scripts/make_figures_patterns.py

# Figure 5: cross-domain panels A-D (UCI HAR, gas drift)
python scripts/make_fig_crossdomain.py

# Graphical abstract (1200 x 1200 px, 300 dpi, Arial)
python scripts/make_graphical_abstract_square.py

# The audit itself, at the frozen settings: B = 2000, seed 20261010,
# LDI = (tau_LOO - 0.001) / sigma, gate at 1.645
python scripts/exp_crossdomain_audit.py          # -> results/crossdomain_audit.json
python scripts/exp_unit_ladder_cervical.py       # -> results/unit_ladder_cervical.json
python scripts/exp_within_group_label_geomx.py --epochs 30 --seeds 0,1,2 \
       --doses 0,0.5,1,2,5                       # -> results/within_group_label_geomx.json

# Manuscript, supplement, title page, cover letter
python scripts/_md2docx.py papers/20_MRP-ST-Repair_Patterns/MRP-ST-Repair_manuscript_Patterns_v15.md papers/20_MRP-ST-Repair_Patterns/Manuscript_Patterns.docx
python scripts/_qa_v15.py
```

## What the numbers mean, in one line each

`tau_LOO` is the leave-one-unit-out Kendall tau of a ridge probe; `tau_LGO`
holds out every sibling unit of a group at once; `tau_LDO` holds out a whole
group while the probe is refit. `sigma` is the SD of the refit-permutation null
at `tau_LOO` (B = 2000). `LDI = (tau_LOO - 0.001) / sigma` with a gate at
1.645, and the dual gate additionally requires `tau_LDO >= 0.7 * tau_base`.

Two caveats that are load-bearing when comparing numbers across cohorts:

* LDI is comparable across cohorts **only at fixed unit count**, because
  `sigma` shrinks as the number of units grows (Table S16: 0.178 at K = 1 to
  0.072 at K = 8).
* The group-count feasibility boundary is a property of a configuration
  (encoder, SNR, overlap of the signal and identity subspaces). Its numeric
  placement is not a transferable cut-off; recalibrate it with the simulator
  before using it on a new cohort.

## Manuscript build chain

`papers/20_MRP-ST-Repair_Patterns/` holds the markdown sources
(`MRP-ST-Repair_manuscript_Patterns_v15.md`, `TitlePage_Patterns.md`,
`CoverLetter_Patterns.md`). The revision scripts `scripts/_rev_v14_*.py` and
`scripts/_rev_v15_*.py` record exactly which sentence was changed in which
version, and `scripts/_qa_v15.py` enforces the formatting constraints (no em
dashes, no literal markdown emphasis left in the docx, five main tables, the
word limits on In brief, Summary, Highlights and the Bigger picture box).

The supplement is **appended, never regenerated**: `Supplemental_Information_Patterns.docx`
is opened with python-docx and tables are added to it, because regenerating it
from markdown would drop S1-S17.

## Figure and table manifest

Every item below is rebuilt by one command. Nothing here is hand-typed: the
supplemental tables are generated straight from `results/*.json`, and the
main-text tables are transcribed from the same files.

| Item | Built by | Reads |
|---|---|---|
| Figures 2 to 4 | `scripts/gen_figures_v10.py` | `results/paper_v10_numbers.json` and the per-cohort JSONs listed above |
| Figure 5 (cross-domain) | `scripts/make_fig_crossdomain.py` | `results/crossdomain_audit.json` |
| Figure 1 (framework schematic) | `scripts/gen_fig1_framework.py` | no data (schematic) |
| Graphical abstract, 1200 x 1200 | `scripts/make_graphical_abstract_square.py` | no data (schematic) |
| Supplemental tables S1 to S9 | `scripts/make_supplemental_patterns.py` | `results/*.json`, no hand-typed numbers |
| Supplemental table S13 (cross-domain inflation) | `scripts/_rev_v8_s14.py` and the cross-domain runner | `results/crossdomain_audit.json` |
| Supplemental table S14 (dose-grid sigma drift) | `scripts/_rev_v8_s14.py` | `results/repair_e4_hnscc_stable.json`, `results/repair_prostate_gse278936_stable.json` |
| Supplemental table S15 (sensitivity to c) | `scripts/_rev_v9_s15.py` | same two cohort files |
| Supplemental table S16 (unit-resolution ladder) | `scripts/exp_unit_ladder_cervical.py` then `scripts/_rev_v13_s16.py` | `results/unit_ladder_cervical.json` |
| Supplemental table S17 (within-group-label control) | `scripts/exp_within_group_label_geomx.py` then `scripts/_rev_v14_s17.py` | `results/within_group_label_geomx.json` |
| Main tables 1 to 5 | transcribed from the same result JSONs | see the checksum index in the release |
| Main table 6 (key resources) | static, in `MRP-ST-Repair_manuscript_Patterns_v16.md` | this paper |

S10 to S12 are emitted by the backbone-ablation and aggregation runs
(`scripts/agg_backbone_ablation.py` and the audit scripts). The release carries
a checksum index mapping every table row and figure panel to the manifest and
result file it was computed from, which is the artefact a reader needs to
re-derive any reported value without contacting the authors.

Rebuild everything textual in one pass:

```bash
cd /g/project4_cervix_multimodal
python scripts/_md2docx.py papers/20_MRP-ST-Repair_Patterns/MRP-ST-Repair_manuscript_Patterns_v16.md papers/20_MRP-ST-Repair_Patterns/Manuscript_Patterns.docx
python scripts/_md2docx.py papers/20_MRP-ST-Repair_Patterns/TitlePage_Patterns.md          papers/20_MRP-ST-Repair_Patterns/TitlePage_Patterns.docx
python scripts/_md2docx.py papers/20_MRP-ST-Repair_Patterns/CoverLetter_Patterns.md         papers/20_MRP-ST-Repair_Patterns/CoverLetter_Patterns.docx
python scripts/_qa_v16.py
```
