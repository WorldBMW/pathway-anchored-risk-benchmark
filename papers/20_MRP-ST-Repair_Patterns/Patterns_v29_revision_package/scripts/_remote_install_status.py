import subprocess

def run(c, t=60):
    return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t, executable="/bin/bash")

PROJ = "/root/autodl-tmp/project/project4_cervix_multimodal"
LOG = f"{PROJ}/logs/install_st_methods.log"
print("=== install log (tail 25) ===")
print(run(f"tail -25 {LOG} 2>/dev/null").stdout or "(no log yet)")
print("=== install proc ===")
print(run(f"ps aux | grep -E '_install_st_methods|pip install' | grep -v grep").stdout or "(none running)")
print("=== pkg check ===")
print(run("/root/miniconda3/bin/python -c \"import importlib;print('SpaGCN',bool(importlib.util.find_spec('SpaGCN')));print('pyg',bool(importlib.util.find_spec('torch_geometric')))\"").stdout)
print("=== grid still alive? ===")
print(run(f"ps aux | grep train_st.py | grep -v grep | head -2").stdout or "(no grid proc!)")