"""Sync the BiB v1.1 evidence increment into the release repo and regenerate SHA256SUMS.

Copies (a) the refit-layer + unified-readout JSON files, (b) the updated 28-ref
references_verified.json, (c) the published-method embedding manifest (paths rewritten
to the release layout), and (d) the 12 exported STAGATE/GraphST embedding .npz files,
then regenerates evidence/SHA256SUMS.txt over the whole evidence tree with repo-relative
paths (evidence/...). Excludes the export log.
"""
from pathlib import Path
import json, shutil, hashlib

PROJ = Path(r'g:\project4_cervix_multimodal')
PAPER_EV = PROJ / 'papers/14_BiB_20261016/evidence'
EMB_SRC = PROJ / 'results/st_method_embeddings'
REPO = Path(r'G:\pathway-anchored-risk-benchmark')
EV = REPO / 'evidence'
EMB_DST = EV / 'st_method_embeddings'

# (1) new/updated JSON evidence files (updated references_verified.json has 28 refs)
sync_names = [
    'sim_power_summary_refit.json',
    'sim_power_raw_refit.json',
    'v2_ctrl_full_probe_refit.json',
    'v2_ours_subset_probe_refit.json',
    'unified_readout_probe.json',
    'references_verified.json',
]
for n in sync_names:
    shutil.copy2(PAPER_EV / n, EV / n)

# (2) manifest: copy, then rewrite export paths to the release layout
shutil.copy2(PAPER_EV / 'st_method_embeddings_manifest.json', EV / 'st_method_embeddings_manifest.json')
mani = json.loads((EV / 'st_method_embeddings_manifest.json').read_text(encoding='utf-8'))
for g in mani['groups'].values():
    for m in g['methods'].values():
        m['export'] = 'evidence/st_method_embeddings/' + Path(m['export']).name
(EV / 'st_method_embeddings_manifest.json').write_text(json.dumps(mani, indent=2, ensure_ascii=False), encoding='utf-8')

# (3) 12 published-method embedding npz (exclude p02_export.log)
EMB_DST.mkdir(parents=True, exist_ok=True)
npz = sorted(EMB_SRC.glob('*.npz'))
for f in npz:
    shutil.copy2(f, EMB_DST / f.name)

# (4) regenerate SHA256SUMS over the whole evidence tree
files = sorted(f for f in EV.rglob('*') if f.is_file() and f.name != 'SHA256SUMS.txt')
lines = [hashlib.sha256(f.read_bytes()).hexdigest() + '  ' + f.relative_to(REPO).as_posix() for f in files]
(EV / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')

print(f'synced {len(sync_names)} jsons + {len(npz)} npz')
print(f'SHA256 lines={len(lines)}')