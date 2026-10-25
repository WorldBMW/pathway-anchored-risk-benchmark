# E2 phase-diagram cohort generation (guide §10.2)
# Axis 1: n_patients in {4,8,16,32,64}, k=1
# Axis 2: k in {2,4,8}, n=16
# Fixed: signal_a=1.0, batch_a=0.6, 1500 spots/slice, 50/40 N/CA ratio,
#        3 sim seeds (=train seeds 0/1/2), group A shared mode only.
import subprocess
import sys
from pathlib import Path

PY = sys.executable
SIM = r'g:\project4_cervix_multimodal\scripts\simulate_st_positive_control.py'
OUT = r'g:\project4_cervix_multimodal\data\e2_phase'

AXIS1 = [4, 8, 16, 32, 64]      # donors, k=1
AXIS2 = [2, 4, 8]               # slices/donor, n=16 donors
SEEDS = [0, 1, 2]

jobs = []
for n in AXIS1:
    n_norm = round(n * 50 / 90)
    n_ca = n - n_norm
    for s in SEEDS:
        jobs.append(dict(tag=f'ax1_n{n}_s{s}', n_norm=n_norm, n_ca=n_ca,
                         k=1, seed=20261000 + s))
for k in AXIS2:
    n_norm = round(16 * 50 / 90)
    n_ca = 16 - n_norm
    for s in SEEDS:
        jobs.append(dict(tag=f'ax2_k{k}_s{s}', n_norm=n_norm, n_ca=n_ca,
                         k=k, seed=20261000 + s))

print(f'[plan] {len(jobs)} cohorts')
for j in jobs:
    out = Path(OUT) / j['tag']
    if (out / 'manifest.json').exists():
        print(f"[skip] {j['tag']} exists")
        continue
    cmd = [PY, SIM, '--out', str(out), '--only', 'A', '--seed',
           str(j['seed']), '--n_normal', str(j['n_norm']),
           '--n_diseased', str(j['n_ca']), '--slices-per-donor', str(j['k']),
           '--signal_a', '1.0', '--batch_a', '0.6']
    print('[run]', ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        sys.exit(f'FAIL {j["tag"]}')
    tail = [ln for ln in r.stdout.splitlines() if ln.strip()]
    print('   ', tail[-1] if tail else '(no output)')
print('[done] all cohorts generated')
