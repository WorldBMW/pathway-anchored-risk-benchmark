import subprocess, time

def run(c, t=90):
    return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t, executable="/bin/bash")

PROJ = "/root/autodl-tmp/project/project4_cervix_multimodal"
LOG = f"{PROJ}/logs/install_st3.log"

# test github direct reachability then set a China-friendly proxy for github
test = run("timeout 15 git ls-remote https://github.com/QIFEIDKN/STAGATE_pyG.git HEAD 2>&1 | head -3")
print("=== direct github test ===", test.returncode)
print(test.stdout, test.stderr)

installer = r"""
set -e
export PATH=/root/miniconda3/bin:$PATH
pip=/root/miniconda3/bin/pip
# walk around github blockage on CN node via a https proxy prefix
git config --global url."https://ghproxy.net/https://github.com/".insteadOf "https://github.com/"
echo "=== try STAGATE via ghproxy ==="
$pip install git+https://github.com/QIFEIDKN/STAGATE_pyG.git || echo STAGATE_FAIL
echo "=== try GraphST via ghproxy ==="
$pip install git+https://github.com/JinmiaoChenLab/GraphST.git || echo GRAPHST_FAIL
echo "=== git config clear (do not persist proxy) ==="
git config --global --unset-all url."https://ghproxy.net/https://github.com/".insteadOf || true
echo "=== verify ==="
/root/miniconda3/bin/python -c "import importlib;print('STAGATE_pyG',bool(importlib.util.find_spec('STAGATE_pyG')));print('GraphST',bool(importlib.util.find_spec('GraphST')))"
echo "INSTALL3_DONE/FAIL rc=$?"
"""
open(f"{PROJ}/scripts/_install_st3.sh", "w").write(installer)
run("rm -f " + LOG)
# fully detach so the SSH channel closes: redirect stdin, nohup setsid
run(f"cd {PROJ} && setsid nohup bash scripts/_install_st3.sh > {LOG} 2>&1 < /dev/null &")
time.sleep(3)
print("launched st3 (proxy retry) ->", LOG)