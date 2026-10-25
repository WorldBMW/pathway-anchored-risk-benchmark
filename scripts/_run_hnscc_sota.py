"""Run SOTA comparison (Group-DRO, IRM) on HNSCC real cohort.
Also runs MRP baseline for direct comparison. CPU mode.
"""
import subprocess
import sys

BASE = [
    sys.executable, "scripts/repair_e3_methodB_train.py",
    "--data", "data/e4_hnscc2",
    "--seeds", "0", "1", "2",
    "--epochs", "150", "--hid", "256", "--warmup", "50",
    "--clip", "1.0", "--adv-sn", "--device", "cpu",
]

runs = [
    (["--method", "baseline", "--adv-list", "0"], "results/sota_hnscc_baseline.json"),
    (["--method", "mrp", "--adv-list", "0.5", "1", "2", "5"], "results/sota_hnscc_mrp.json"),
    (["--method", "groupdro", "--adv-list", "1", "10"], "results/sota_hnscc_groupdro.json"),
    (["--method", "irm", "--adv-list", "10", "100"], "results/sota_hnscc_irm.json"),
]

for args, out in runs:
    cmd = BASE + args + ["--out", out]
    print(f"Running: {' '.join(cmd[-4:])}", flush=True)
    proc = subprocess.run(cmd, cwd=r"g:\project4_cervix_multimodal",
                          capture_output=True, text=True, timeout=3600)
    print(f"  -> exit={proc.returncode}", flush=True)
    if proc.returncode != 0:
        print(f"  STDERR: {proc.stderr[-500:]}", flush=True)
    else:
        # print last few lines
        lines = proc.stdout.strip().split('\n')
        for l in lines[-3:]:
            print(f"  {l}", flush=True)

print("ALL DONE")
