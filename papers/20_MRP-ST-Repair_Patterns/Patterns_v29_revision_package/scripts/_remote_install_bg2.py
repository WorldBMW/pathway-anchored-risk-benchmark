import subprocess, time

def run(cmd, timeout=60):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, executable="/bin/bash")

PROJ = "/root/autodl-tmp/project/project4_cervix_multimodal"
LOG = f"{PROJ}/logs/install_st2.log"
installer = r"""
set -e
export PATH=/root/miniconda3/bin:$PATH
pip=/root/miniconda3/bin/pip
echo "=== STAGATE_pyG from GitHub ==="
$pip install git+https://github.com/QIFEIDKN/STAGATE_pyG.git || echo STAGATE_FAIL
echo "=== GraphST from GitHub ==="
$pip install git+https://github.com/JinmiaoChenLab/GraphST.git || echo GRAPHST_FAIL
echo "=== verify ==="
/root/miniconda3/bin/python -c "import importlib;print('STAGATE_pyG',bool(importlib.util.find_spec('STAGATE_pyG')));print('GraphST',bool(importlib.util.find_spec('GraphST')))"
echo "INSTALL2_DONE rc=$?"
"""
open(f"{PROJ}/scripts/_install_st2.sh", "w").write(installer)
run("rm -f " + LOG)
run(f"cd {PROJ} && nohup bash scripts/_install_st2.sh > {LOG} 2>&1 &")