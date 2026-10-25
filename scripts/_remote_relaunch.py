import os, subprocess, time

def run(cmd, timeout=120):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)

os.chdir("g:/project4_cervix_multimodal")
# upload the wrapper to remote scripts/, then run the relaunch instructions on the server
remote = r"""
import subprocess, time
def run(c,t=120): return subprocess.run(c,shell=True,capture_output=True,text=True,timeout=t)
os = None
# kill stale remnants
run("pkill -9 -f 'run_sim_power_grid.sh' 2>/dev/null; pkill -9 -f 'run_sim_one.sh' 2>/dev/null; pkill -9 -f 'train_st.py' 2>/dev/null; screen -S powergrid -X quit 2>/dev/null; screen -wipe >/dev/null 2>&1; rm -f logs/power_grid_clean.log; mkdir -p logs; true")
run("chmod +x scripts/power_grid_clean.sh")
# launch detached screen running the wrapper (banner/log to files)
run("cd /root/autodl-tmp/project/project4_cervix_multimodal && screen -dmS powergrid bash scripts/power_grid_clean.sh")
time.sleep(6)
print("=== screen list ==="); print(run("screen -ls").stdout)
print("=== grid log (last 15) ==="); print(run("tail -15 logs/power_grid_clean.log 2>/dev/null").stdout)
print("=== train procs ==="); print(run("ps aux | grep train_st.py | grep -v grep | head -3").stdout)
"""
open("scripts/_remote_relaunch_body.py","w").write(remote)
for attempt in range(3):
    r = run('python scripts/ssh_upload_run.py scripts/_remote_relaunch_body.py 90 scripts/power_grid_clean.sh')
    if r.stdout or r.returncode == 0:
        print(r.stdout)
        if r.stderr: print("STDERR:", r.stderr)
        sys_exit = r.returncode
        break
    print(f"attempt {attempt+1} transient fail; retrying..."); time.sleep(5)
else:
    sys_exit = 1
print("done rc=", sys_exit)