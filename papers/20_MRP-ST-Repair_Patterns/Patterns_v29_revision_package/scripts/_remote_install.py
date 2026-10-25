import subprocess, sys

def run(cmd, timeout=1800):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, executable="/bin/bash")
pip = "/root/miniconda3/bin/pip"

# 1) SpaGCN (CPU ok, logical as a baseline)
print("=== installing use_legacy optimizer-free SpaGCN from PyPI ===", flush=True)
r = run(f"{pip} install \"spaGCN>=1.2.0\" 2>&1 | tail -15")
print(r.stdout[-3000:] if r.stdout else r.stderr[-3000:])

# 2) torch_geometric (needed by STAGATE & GraphST) — pinned against torch 2.1.2
print("=== installing torch_geometric ===", flush=True)
r = run(f"{pip} install torch_geometric 2>&1 | tail -15")
print(r.stdout[-3000:] if r.stdout else r.stderr[-3000:])

# verify imports
print("=== verify ===", flush=True)
r = run("/root/miniconda3/bin/python -c \"import importlib;print('SpaGCN',bool(importlib.util.find_spec('SpaGCN')));print('torch_geometric',bool(importlib.util.find_spec('torch_geometric')))\"")
print(r.stdout, r.stderr[-1000:])