import subprocess, time

def run(c, t=60):
    return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t, executable="/bin/bash")

PROJ = "/root/autodl-tmp/project/project4_cervix_multimodal"
LOG = f"{PROJ}/logs/install_st4.log"
installer = r"""
set -e
export PATH=/root/miniconda3/bin:$PATH
pip=/root/miniconda3/bin/pip
echo "=== ot / POT ==="
$pip install POT || echo POT_FAIL
echo "=== torch_sparse prebuilt from pyg wheel index (torch 2.1.0+cu121) ==="
$pip install torch-sparse==0.6.18 -f https://pytorch-geometric.com/whl/torch-2.1.0+cu121.html --no-cache-dir || echo TS_FAIL
echo "=== torch_scatter (STAGATE also uses) ==="
$pip install torch-scatter==2.1.2 -f https://pytorch-geometric.com/whl/torch-2.1.0+cu121.html --no-cache-dir || echo SCATTER_FAIL
echo "=== verify STAGATE + GraphST import ==="
/root/miniconda3/bin/python -c "import STAGATE_pyG; from GraphST import GraphST; print('STAGATE+GraphST OK')" 2>&1 | tail -5
echo "ST4_DONE rc=$?"
"""
open(f"{PROJ}/scripts/_install_st4.sh", "w").write(installer)
run("rm -f " + LOG)
run(f"cd {PROJ} && setsid nohup bash scripts/_install_st4.sh > {LOG} 2>&1 < /dev/null &")
time.sleep(3)
print("launched st4 ->", LOG)