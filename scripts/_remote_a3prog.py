#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Precise A3 progress + whether any train_st alive + power_grid.log tail."""
import subprocess, os
proj = "/root/autodl-tmp/project/project4_cervix_multimodal"
def run(cmd):
    r = subprocess.run(cmd, shell=True, executable="/bin/bash", capture_output=True, text=True, timeout=60)
    return r.stdout

grid = []
for g in ["20261006","20261007","20261008"]:
    for lab in ["L1","L2","L3","L4"]:
        for sz in ["main","small"]:
            tag=f"g{g}_{lab}{'_small' if sz=='small' else ''}"
            for ts in [0,1,2]:
                grid.append((f"group_A_{tag}","NOALL",ts))
    for sz in ["main","small"]:
        tag=f"g{g}_CTRL{'_small' if sz=='small' else ''}"
        for ts in [0,1,2]:
            grid.append((f"group_C_{tag}","NOALL",ts))
            grid.append((f"group_C_{tag}","FULL",ts))
done=0; missing=[]
for grp,var,ts in grid:
    fp=f"{proj}/results/results_SIM_{grp}_{var}_seed{ts}.json"
    if os.path.exists(fp): done+=1
    else: missing.append((grp,var,ts))
print(f"A3 done={done}/{len(grid)} missing={len(missing)}")
farthest=-1
for i,(g,v,t) in enumerate(grid):
    if os.path.exists(f"{proj}/results/results_SIM_{g}_{v}_seed{t}.json"): farthest=i
print(f"farthest idx={farthest}/{len(grid)-1}")
holes=[m for m in missing if grid.index(m)<farthest]
print(f"holes={len(holes)} remaining_after_farthest={len(missing)-len(holes)}")
print("first 12 remaining:")
for m in missing[len(holes):][:12]: print("   ",m)
print()
print("=== train_st / python GPU processes ===")
print(run("ps aux | grep -E 'train_st.py|benchmark_st' | grep -v grep | head -5"))
print("=== power_grid.log tail 12 ===")
print(run(f"tail -12 {proj}/logs/power_grid.log 2>/dev/null || echo NO_POWER_GRID_LOG"))
print("=== night_batch.log tail 6 ===")
print(run(f"tail -6 {proj}/logs/night_batch.log 2>/dev/null"))