# Patterns v29 local revision package

This is a candidate upload package, not an already published release. It accompanies
"Auditing label dependence and sibling-unit inflation in group-structured representations".
The existing public DOI 10.5281/zenodo.23640979 remains a historical manuscript and
associated code snapshot; it does not include the current audit implementation.

## Contents and provenance

Current v29 Word and Markdown files, scientific source scripts and modules, legacy
JSON/CSV result records, the new corrected HAR outer-refit result, figure assets,
and a file-level SHA-256 manifest are included. Public raw datasets, credentials,
trained model checkpoints, caches, and .git metadata are excluded. Some scripts
share utility code with earlier work; inclusion does not assert independent novelty.
The original legacy result records have not been silently replaced by v29 results.

## Environment and entry points

Use results/runtime_versions_v29.json for the actual environment of the new run.
requirements-patterns.txt supplies the recorded study dependency pins; full
raw-data environment reconstruction was not rerun for every historical experiment.

From the extracted package root, with its scientific dependencies available:

    python scripts/exp_outer_refit_v29.py

This runs the corrected HAR comparison (seed 0, 30 epochs, 30 subjects, doses 0/2),
writing results/outer_refit_v29.json. It requires the public HAR data in the layout
expected by scripts/exp_crossdomain_audit.py. It does not redownload every missing
dataset automatically; consult the loader paths and source accession documentation.

    python scripts/make_figures_patterns.py
    python scripts/make_fig_crossdomain.py

These regenerate legacy plotted panels from the included archived records. Their
interpretations are restricted by the v29 manuscript and review report. The older
REPRODUCE.md is included as a historical map; README_v29.md takes precedence where
its claims of public release or statistical interpretation differ.

## What this package does not certify

Within-group label shuffling is not whole-group permutation; the stored ratio is
not centered on that restricted null. The cervical grouping is a name-based
assumption and the GeoMx true patient pairing remains unresolved. The 21-pair
enumeration analyzes preprocessed raw features, not repaired embeddings. No
privacy guarantee, universal repair success, or equivalence claim is made.

## Publication step still required

Inspect the files, then upload a new version to Zenodo and/or create a new GitHub
release. Do not relabel the existing v1.0.0 archive as if it already held these
files. Obtain the new version-specific DOI and update current-revision citations.
Reconcile creator names, record title, commit and software/manuscript licences.
No remote upload, tag mutation or metadata edit was performed by this packaging step.
