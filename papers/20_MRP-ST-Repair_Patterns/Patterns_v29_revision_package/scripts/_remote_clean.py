import os, glob, subprocess

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

os.chdir("/root/autodl-tmp/project/project4_cervix_multimodal")

out = run("ps aux | grep -E 'run_sim_power_grid.sh|run_sim_one.sh|train_st.py' | grep -v grep")
print("=== remaining grid procs (should be none) ===")
print(out.stdout if out.stdout else "(empty - all dead)")

# list contaminated sim_power A3 artifacts
json_paths = sorted(glob.glob("results/results_SIM_group_[AC]_g*.json"))
npz_paths = sorted(glob.glob("results/fused_embs_SIM_group_[AC]_g*.npz"))
print(f"\n=== contaminated A3 artifacts: {len(json_paths)} json, {len(npz_paths)} npz ===")
for f in json_paths: print("rm", f)
for f in npz_paths: print("rm", f)

# delete them
for f in json_paths + npz_paths:
    try: os.remove(f)
    except Exception as e: print("ERR", f, e)

# also remove the generated data cohort dir to force clean gen
has_data = os.path.isdir("data/sim_power")
print("\ndata/sim_power exists:", has_data)
if has_data:
    print("removing data/sim_power ...")
    out2 = run("rm -rf data/sim_power")
    print("rm data rc:", out2.returncode if hasattr(out2,'returncode') else 'n/a')

print("\n=== after cleanup ===")
print("remaining A3 json:", len(glob.glob("results/results_SIM_group_[AC]_g*.json")))
print("remaining A3 npz:", len(glob.glob("results/fused_embs_SIM_group_[AC]_g*.npz")))
print("data/sim_power exists:", os.path.isdir("data/sim_power"))