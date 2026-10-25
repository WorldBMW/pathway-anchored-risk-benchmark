import subprocess
def run(c, t=60):
    return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t, executable="/bin/bash")
# locate package dirs and grep the canonical call style
print("=== STAGATE_pyG location ===")
print(run("/root/miniconda3/bin/python -c \"import STAGATE_pyG,os;print(os.path.dirname(STAGATE_pyG.__file__))\"").stdout)
print("=== GraphST location ===")
print(run("/root/miniconda3/bin/python -c \"import GraphST,os;print(os.path.dirname(GraphST.__file__))\"").stdout)
print("=== STAGATE __init__ ===")
print(run("/root/miniconda3/bin/python -c \"import STAGATE_pyG,os;print(open(os.path.join(os.path.dirname(STAGATE_pyG.__file__),'__init__.py')).read())\"").stdout[:1500])