import subprocess
def run(c, t=60):
    return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t, executable="/bin/bash")
print("=== signatures ===")
print(run("""
/root/miniconda3/bin/python -c "
import inspect
import STAGATE_pyG as s
print('train_STAGATE:', hasattr(s,'train_STAGATE'))
if hasattr(s,'train_STAGATE'):
    print(' sig:', str(inspect.signature(s.train_STAGATE))[:200])
from GraphST import GraphST
print('GraphST init:', str(inspect.signature(GraphST.__init__))[:200])
print('GraphST methods:', [m for m in dir(GraphST) if not m.startswith('_')][:15])
"
""").stdout, run(r"""
/root/miniconda3/bin/python -c "
import inspect
import STAGATE_pyG as s
print('train_STAGATE', inspect.signature(s.train_STAGATE) if hasattr(s,'train_STAGATE') else 'missing')
print([x for x in dir(s) if not x.startswith('_')])
"
""").stderr)