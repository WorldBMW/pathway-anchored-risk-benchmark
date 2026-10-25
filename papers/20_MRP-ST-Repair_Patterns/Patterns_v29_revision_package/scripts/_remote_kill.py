import os, subprocess, signal

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

out = run("ps aux | grep -E 'run_sim_power_grid.sh|run_sim_one.sh|train_st.py' | grep -v grep")
print("=== targets ===")
print(out.stdout)
# parse PIDs (col 1 = user, col 2 = pid for ps aux on Linux)
pids = []
scratch = out.stdout
# ps aux: user pid ppid %cpu ... -> pid is 2nd field
for line in scratch.splitlines():
    parts = line.split()
    if len(parts) >= 2:
        pids.append(int(parts[1]))
print("sending SIGKILL to PIDs:", pids)
for p in pids:
    try:
        os.kill(p, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except Exception as e:
        print("kill err", p, e)
print("kill issued")