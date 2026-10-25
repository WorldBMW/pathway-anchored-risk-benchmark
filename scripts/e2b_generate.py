# E2b weak-signal insurance grid (guide §10 extension)
# Rationale: amplitude panel showed signal 0.5 already saturates tau at the
# finite-sample cap (n=90). If E2@signal 1.0 comes back flat (R~1 everywhere),
# C2 dies. Weak-signal 0.3 grid is where fingerprint noise vs weak program
# competition should expose the phase boundary. Both grids together give a
# 3-panel (signal x n) phase map - a stronger C2 either way.
import subprocess
import sys
from pathlib import Path

PY = sys.executable
SIM = r'g:\project4_cervix_multimodal\scripts\simulate_st_positive_control.py'
OUT = r'g:\project4_cervix_multimodal\data\e2_phaseB'

AXIS1 = [4, 8, 16, 32, 64]
SEEDS = [0, 1, 2]

jobs = []
for n in AXIS1:
    n_norm = round(n * 50 / 90)
    n_ca = n - n_norm
    for s in SEEDS:
        jobs.append(dict(tag=f'ax1_n{n}_s{s}', n_norm=n_norm, n_ca=n_ca,
                         seed=20261000 + s))

print(f'[plan] {len(jobs)} cohorts (signal 0.3, batch 0.6, k=1)')
for j in jobs:
    out = Path(OUT) / j['tag']
    if (out / 'manifest.json').exists():
        print(f"[skip] {j['tag']}")
        continue
    cmd = [PY, SIM, '--out', str(out), '--only', 'A', '--seed',
           str(j['seed']), '--n_normal', str(j['n_norm']),
           '--n_diseased', str(j['n_ca']), '--signal_a', '0.3',
           '--batch_a', '0.6']
    print('[run]', j['tag'], flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:])
        sys.exit(f'FAIL {j["tag"]}')
print('[done]')
