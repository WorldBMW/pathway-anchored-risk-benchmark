import subprocess
def run(c, t=300):
    return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t, executable="/bin/bash")
PROJ = "/root/autodl-tmp/project/project4_cervix_multimodal"
# verify exact import/API signatures my benchmark relies on
print("=== API signature check ===")
print(run("/root/miniconda3/bin/python -c \""
          "import STAGATE_pyG as s; "
          "print('STAGATE_pyG train_STAGATE', hasattr(s, 'train_STAGATE')); "
          "import inspect; "
          "print('train_STAGATE sig', str(inspect.signature(s.train_STAGATE))[:120] if hasattr(s,'train_STAGATE') else 'N/A')\" 2>&1").stdout)
print(run("/root/miniconda3/bin/python -c \""
          "from GraphST import GraphST; "
          "print('GraphST class ok'); "
          "import inspect; "
          "print('GraphST.__init__', str(inspect.signature(GraphST.__init__))[:120])\" 2>&1").stdout)
# list which cohorts currently exist (data written) for smoke
print("=== sim_power cohorts present ===")
print(run(f"ls {PROJ}/data/sim_power/ 2>/dev/null").stdout or "(none yet)")