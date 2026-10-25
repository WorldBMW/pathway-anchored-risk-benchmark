import subprocess
def run(c, t=90):
    return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t, executable="/bin/bash")
print("=== versions ===")
print(run("/root/miniconda3/bin/python -c \"import torch;print('torch',torch.__version__);print('cuda',torch.version.cuda)\" 2>&1").stdout)
print(run("/root/miniconda3/bin/python -c \"import numpy;print('numpy',numpy.__version__)\" 2>&1").stdout)
print(run("/root/miniconda3/bin/python -c \"import torch_geometric;print('pyg',torch_geometric.__version__)\" 2>&1").stdout)
# does a torch_sparse wheel exist on aliyun matching cp310/py2.1? We'll try pip install matching torch
print("=== try torch_scatter+torch_sparse compiled wheels from aliyun (py2.1) ===")
print(run("/root/miniconda3/bin/pip download torch-sparse -q -d /tmp/ts --no-deps 2>&1 | tail -3").stdout)
print(run("ls /tmp/ts 2>/dev/null").stdout)