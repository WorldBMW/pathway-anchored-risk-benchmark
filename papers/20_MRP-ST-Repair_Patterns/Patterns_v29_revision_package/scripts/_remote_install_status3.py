import subprocess
def run(c, t=45):
    return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t, executable="/bin/bash")
PROJ = "/root/autodl-tmp/project/project4_cervix_multimodal"
print("=== install_st3.log tail 40 ===")
print(run(f"tail -40 {PROJ}/logs/install_st3.log 2>/dev/null").stdout or "(no log yet)")
print("=== procs ===")
print(run(f"ps aux | grep -E 'pip install|_install_st3' | grep -v grep").stdout or "(none)")
print("=== pkg ===")
print(run("/root/miniconda3/bin/python -c \"import importlib;print('STAGATE_pyG',bool(importlib.util.find_spec('STAGATE_pyG')));print('GraphST',bool(importlib.util.find_spec('GraphST')))\" 2>&1").stdout)