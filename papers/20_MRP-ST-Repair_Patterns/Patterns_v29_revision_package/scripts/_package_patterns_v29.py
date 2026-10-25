from pathlib import Path
import json,hashlib,zipfile,sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path.cwd();P=Path('papers/20_MRP-ST-Repair_Patterns')
OUT=P/'Patterns_v29_revision_package.zip'
files=set()
for base in ['src','scripts']:
 for f in Path(base).rglob('*'):
  if not f.is_file() or f.suffix not in ['.py','.ps1','.sh','.json','.yaml','.yml']:continue
  if '__pycache__' in f.parts:continue
  # Exclude unrelated paper builders and one-off editorial histories; include the current build/audit runners.
  if f.name.startswith(('build_cmpb','_jbi','_rev_v','_qa_v','_fill_doi','make_chinese')):continue
  files.add(f)
for f in Path('results').glob('*'):
 if f.is_file() and (f.suffix in ['.json','.csv'] or f.name.startswith('e4_decoder_w') and f.suffix=='.npz'):files.add(f)
for n in ['requirements-patterns.txt','requirements.txt','LICENSE','REPRODUCE.md']:
 if Path(n).exists():files.add(Path(n))
for f in P.iterdir():
 if f.is_file() and ('v29' in f.name or f.name=='MRP-ST-Repair_manuscript_Patterns_v28.md') and f.suffix in ['.docx','.md','.json'] and 'pre_' not in f.name:files.add(f)
for f in (P/'figures').glob('*'):
 if f.suffix in ['.png','.pdf','.tif']:files.add(f)
needed=['scripts/exp_crossdomain_audit.py','scripts/refit_grid_audit.py','scripts/exp_regate_v28.py','scripts/make_figures_patterns.py','scripts/exp_outer_refit_v29.py','results/regate_v28.json','results/outer_refit_v29.json']
assert all(Path(n) in files for n in needed)
readme='''# Patterns v29 local revision package

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
'''
readme_bytes=readme.encode('utf-8');manifest=[]
for f in sorted(files,key=lambda p:p.as_posix()):
 raw=f.read_bytes();manifest.append({'path':f.as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
manifest.append({'path':'README_v29.md','bytes':len(readme_bytes),'sha256':hashlib.sha256(readme_bytes).hexdigest()})
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in sorted(files,key=lambda p:p.as_posix()):z.write(f,f.as_posix())
 z.writestr('README_v29.md',readme_bytes)
 z.writestr('SHA256_MANIFEST_v29.json',json.dumps(manifest,ensure_ascii=False,indent=2))
with zipfile.ZipFile(OUT) as z:
 assert z.testzip() is None
 for row in manifest:assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
summary={'archive':OUT.name,'bytes':OUT.stat().st_size,'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'manifest_entries':len(manifest),'all_member_checksums_verified':True,'publicly_uploaded':False}
(P/'PACKAGE_v29_manifest_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
