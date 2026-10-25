
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
