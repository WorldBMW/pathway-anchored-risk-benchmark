import subprocess, sys
BASE = [sys.executable, "scripts/repair_e3_methodB_train.py",
    "--data", "data/e4_hnscc2", "--seeds", "0",
    "--epochs", "100", "--hid", "256", "--warmup", "30",
    "--clip", "1.0", "--adv-sn", "--device", "cpu"]
runs = [
    (["--method","mrp","--adv-list","0"], "results/sota_hnscc_baseline.json"),
    (["--method","mrp","--adv-list","0.5","1","2"], "results/sota_hnscc_mrp.json"),
    (["--method","groupdro","--adv-list","1","10"], "results/sota_hnscc_groupdro.json"),
    (["--method","irm","--adv-list","10","100"], "results/sota_hnscc_irm.json"),
]
for args, out in runs:
    cmd = BASE + args + ["--out", out]
    print(f"Running {out}", flush=True)
    proc = subprocess.run(cmd, cwd=r"g:\project4_cervix_multimodal", capture_output=True, text=True)
    print(f"  exit={proc.returncode}", flush=True)
    if proc.returncode != 0:
        print(f"  ERR: {proc.stderr[-300:]}", flush=True)
print("DONE")
