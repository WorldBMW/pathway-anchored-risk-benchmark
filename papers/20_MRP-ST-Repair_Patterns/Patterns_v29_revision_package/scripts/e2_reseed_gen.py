# E2 boundary robustness reseed: seeds {3,4} at n in {16,32}, signals {1.0, 0.3}
# Purpose: 5-seed verification of the repairability donor-count boundary
# (manuscript Table S6). Generation params identical to e2/e2b grids.
import subprocess
import sys
from pathlib import Path

PY = sys.executable
SIM = r'g:\project4_cervix_multimodal\scripts\simulate_st_positive_control.py'
OUT = r'g:\project4_cervix_multimodal\data\e2_reseed'

jobs = []
for sig, name in [(1.0, 'e2r'), (0.3, 'e2br')]:
    for n in [16, 32]:
        n_norm = round(n * 50 / 90)
        n_ca = n - n_norm
        for s in [3, 4]:
            jobs.append(dict(tag=f'{name}_n{n}_s{s}', n_norm=n_norm,
                              n_ca=n_ca, sig=sig, seed=20261000 + s))

print(f'[plan] {len(jobs)} cohorts')
for j in jobs:
    out = Path(OUT) / j['tag']
    if (out / 'group_A').exists():
        print(f"[skip] {j['tag']}")
        continue
    cmd = [PY, SIM, '--out', str(out), '--only', 'A', '--seed',
           str(j['seed']), '--n_normal', str(j['n_norm']),
           '--n_diseased', str(j['n_ca']), '--signal_a', str(j['sig']),
           '--batch_a', '0.6']
    print('[run]', j['tag'], flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:])
        sys.exit(f'FAIL {j["tag"]}')
print('[done]')
