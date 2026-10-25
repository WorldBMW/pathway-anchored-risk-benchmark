import subprocess
def run(c, t=45):
    return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t, executable="/bin/bash")
PROJ = "/root/autodl-tmp/project/project4_cervix_multimodal"
print("=== install_st4.log tail 40 ===")
print(run(f"tail -40 {PROJ}/logs/install_st4.log 2>/dev/null").stdout or "(no log)")
print("=== procs ===")
print(run(f"ps aux | grep -E 'pip install|_install_st4' | grep -v grep").stdout or "(none)")
print("=== import test ===")
print(run("/root/miniconda3/bin/python -c \"import importlib;print('torch_sparse',bool(importlib.util.find_spec('torch_sparse')));print('torch_scatter',bool(importlib.util.find_spec('torch_scatter')));print('ot',bool(importlib.util.find_spec('ot'))) \" 2>&1").stdout)