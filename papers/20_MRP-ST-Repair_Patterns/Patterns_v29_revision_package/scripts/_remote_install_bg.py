import subprocess, time

def run(cmd, timeout=120):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, executable="/bin/bash")

PROJ = "/root/autodl-tmp/project/project4_cervix_multimodal"
LOG = f"{PROJ}/logs/install_st_methods.log"
# launch install in background via nohup, log everything, return immediately
installer = r"""
set -e
export PATH=/root/miniconda3/bin:$PATH
pip=/root/miniconda3/bin/pip
echo "=== SpaGCN ===" 
$pip install "spaGCN>=1.2.0" || echo SPA_FAIL
echo "=== torch_geometric ==="
$pip install torch_geometric || echo PYG_FAIL
echo "=== verify ==="
/root/miniconda3/bin/python -c "import importlib;print('SpaGCN',bool(importlib.util.find_spec('SpaGCN')));print('pyg',bool(importlib.util.find_spec('torch_geometric')))"
echo "INSTALL_DONE rc=$?"
"""
open(f"{PROJ}/scripts/_install_st_methods.sh", "w").write(installer)

run("rm -f " + LOG)
run(f"cd {PROJ} && nohup bash scripts/_install_st_methods.sh > {LOG} 2>&1 &")
time.sleep(5)
print("launched install in background; log:", LOG)
print(run(f"tail -5 {LOG}").stdout)