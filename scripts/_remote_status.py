#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check nightbatch chain + powergrid grid status."""
import subprocess
proj = "/root/autodl-tmp/project/project4_cervix_multimodal"
def run(cmd):
    r = subprocess.run(cmd, shell=True, executable="/bin/bash", capture_output=True, text=True, timeout=60)
    return r.stdout
print("=== screen -ls ===")
print(run("screen -ls 2>&1 | head -12"))
print("=== processes ===")
print(run("ps aux | grep -E 'train_st.py|night_batch.sh|run_sim_power_grid.sh' | grep -v grep | head -6"))
print("=== night_batch.log (last 15) ===")
print(run(f"tail -15 {proj}/logs/night_batch.log 2>/dev/null || echo NO_LOG"))
print("=== completed results_SIM json count ===")
print(run(f"ls {proj}/results/results_SIM_*.json 2>/dev/null | wc -l"))