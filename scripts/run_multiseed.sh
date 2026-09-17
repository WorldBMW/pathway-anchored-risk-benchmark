#!/usr/bin/env bash
# =============================================================================
# Multi-seed ablation runner for reviewer comment M-7
#   FULL vs NO-IMAGE, 5 seeds each, EXACT main-experiment config.
#
# Usage:
#   bash scripts/run_multiseed.sh 0      # stage 0: env check + rebuild cervix_all_ext links
#   bash scripts/run_multiseed.sh 1      # stage 1: smoke test (1 seed, 3 epochs)
#   bash scripts/run_multiseed.sh 2      # stage 2: FULL seeds 0-4
#   bash scripts/run_multiseed.sh 3      # stage 3: NO-IMAGE seeds 0-4  (core evidence)
#   bash scripts/run_multiseed.sh 4      # stage 4: summarize all variants -> mean+/-SD + tests
#   bash scripts/run_multiseed.sh 5      # stage 5: NO-HPV + NO-NEIGH seeds 0-4
#   bash scripts/run_multiseed.sh core   # 0->1->2->3->4  (the two must-have ablations)
#   bash scripts/run_multiseed.sh all    # 0->1->2->3->5->4 (all four ablations)
# Each run also dumps results/fused_embs_<run_id>.npz (per-spot scores) for
# the downstream GSVA / Cox / violin analyses (no GPU needed).
#
# Every stage writes its own log under logs/multiseed/ so you can `tail -f`
# a separate terminal and always know which step you are in.
# =============================================================================
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

# ---- EXACT main-experiment config (from results_CERVIX35_PROG.json) ---------
DATA=data/st_visium/cervix_all_ext
LABELS=data/st_visium/labels/cervix_histology_labels_extended.csv
HPV_SET=kegg_hpv
L_RECON=0.2
L_NEIGH=0.3
L_HPV=1.0
L_SUP=5.0
L_PROG=1.5
PERMN=1000
EPOCHS_FULL=${EPOCHS_FULL:-40}
SEEDS="0 1 2 3 4"

# ---- spot-set policy --------------------------------------------------------
# The legacy hard-coded GLOBAL_PATCH_CAP=30000 silently truncated the 35-sample
# cohort (46820 spots) down to 30000. That is why the archived NO-IMAGE result
# (n_spots=30000, n_samples=41) is NOT on the same footing as the main run
# (n_spots=46820, n_samples=35) — the 0.866 vs 0.762 comparison in the paper is
# cross-protocol. We therefore run every multi-seed ablation on the FULL spot
# set (--global_patch_cap 0), so all variants share one identical cohort and the
# numbers are directly comparable to the 0.866 main result.
# RAM cost: 46820 float32 patches ~= 28 GB resident, ~56 GB peak during cat.
# The container has ~149 GB free, so this fits. If it OOMs, set GCAP=40000.
GCAP=${GCAP:-0}

LOGDIR=logs/multiseed
mkdir -p "$LOGDIR" results
export PYTHONUNBUFFERED=1

ts() { date '+%Y-%m-%d %H:%M:%S'; }
hr() { printf '=%.0s' {1..70}; printf '\n'; }

# -----------------------------------------------------------------------------
# ensure_dataset: rebuild cervix_all_ext from the source cohorts.
#
# On the local Windows workstation cervix_all_ext is a directory of JUNCTIONS
# (never rsync'd to the server), assembled from:
#     geo_cesc/{N_HPV,HSIL_HPV,CA_HPV_1,CA_HPV_2}   -> 4 samples
#     geo_ectocervix/P0xx                            -> 30 samples, renamed ecto_P0xx
#     cervical_cancer_1                              -> 1 sample
#   = 35 samples, exactly matching results_CERVIX35_PROG.json (n_spots=46820).
#
# On the server we rebuild it with SYMLINKS, which train_st.py's discover()
# follows transparently.
# -----------------------------------------------------------------------------
count_samples() {   # real dirs OR symlinks-to-dirs directly under $1
  find "$1" -maxdepth 1 -mindepth 1 \( -type d -o -type l \) 2>/dev/null | wc -l
}

ensure_dataset() {
  local n
  n=$(count_samples "$DATA")
  if [ -d "$DATA" ] && [ "$n" -ge 35 ]; then
    echo "[$(ts)] dataset $DATA present ($n entries) — no rebuild needed"
    return 0
  fi
  echo "[$(ts)] $DATA missing/incomplete -> rebuilding from source cohorts"
  for src in data/st_visium/geo_cesc data/st_visium/geo_ectocervix data/st_visium/cervical_cancer_1; do
    [ -e "$src" ] || { echo "[FAIL] source cohort missing: $src"; echo "       upload the data first"; return 1; }
  done
  mkdir -p "$DATA" || return 1

  # 4 cesc samples (N_HPV / HSIL_HPV / CA_HPV_1 / CA_HPV_2)
  for s in N_HPV HSIL_HPV CA_HPV_1 CA_HPV_2; do
    if [ -d "data/st_visium/geo_cesc/$s" ]; then
      ln -sfn "$(cd "data/st_visium/geo_cesc/$s" && pwd)" "$DATA/$s"
    else
      echo "[WARN] geo_cesc/$s not found on server"
    fi
  done

  # 30 ectocervix samples, renamed with the ecto_ prefix the label CSV expects
  for d in data/st_visium/geo_ectocervix/*/; do
    [ -d "$d" ] || continue
    b=$(basename "$d")
    ln -sfn "$(cd "$d" && pwd)" "$DATA/ecto_$b"
  done

  # 1 cervical_cancer_1
  if [ -d data/st_visium/cervical_cancer_1 ]; then
    ln -sfn "$(cd data/st_visium/cervical_cancer_1 && pwd)" "$DATA/cervical_cancer_1"
  fi

  n=$(count_samples "$DATA")
  echo "[$(ts)] rebuilt $DATA with $n sample links (expected 35)"
  [ "$n" -eq 35 ] || { echo "[FAIL] link count $n != 35 — inspect: ls -l $DATA"; return 1; }
  return 0
}

# -----------------------------------------------------------------------------
stage0() {
  hr; echo "[$(ts)] STAGE 0 — environment & data sanity"; hr

  # 0a. leftover processes from previous stuck runs hold the GPU and make
  #     `import torch` block on CUDA init. Warn (do not auto-kill).
  echo "--- leftover python processes ---"
  ps -eo pid,etime,pcpu,cmd | grep -E "[t]rain_st.py|[p]ython" | head -10
  if pgrep -f "train_st.py" >/dev/null 2>&1; then
    echo "[WARN] previous train_st.py still running -> it holds GPU memory and"
    echo "       will make this stage hang on CUDA init. Kill it with:"
    echo "         pkill -f train_st.py"
  fi
  echo "--- GPU state ---"
  nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv 2>/dev/null || echo "  (nvidia-smi unavailable)"

  # 0b. import check. `python -u` disables output buffering so every line
  #     appears immediately; `timeout` guarantees we never hang silently.
  echo "--- import check (timeout 180s) ---"
  timeout 180 python -u - <<'PY'
import sys, time
def step(msg):
    print(f"  -> {msg}", flush=True)
step("python      : " + sys.version.split()[0])
t = time.time(); import numpy; step(f"numpy       : {numpy.__version__}  ({time.time()-t:.1f}s)")
assert numpy.__version__.split('.')[0] == '1', \
    f"numpy {numpy.__version__} >=2 -> pip install 'numpy<2'"
t = time.time(); import torch;  step(f"torch       : {torch.__version__}  ({time.time()-t:.1f}s)")
t = time.time(); ok = torch.cuda.is_available()
step(f"cuda avail  : {ok}  ({time.time()-t:.1f}s)")
if ok:
    step("gpu         : " + torch.cuda.get_device_name(0))
    x = torch.zeros(8, device="cuda"); torch.cuda.synchronize()
    step("cuda tensor alloc: OK")
print("  imports OK", flush=True)
PY
  local rc=$?
  if [ $rc -eq 124 ]; then
    echo "[FAIL] import check TIMED OUT after 180s."
    echo "       Most likely the GPU is still held by a stuck process. Run:"
    echo "         pkill -9 -f train_st.py ; sleep 3 ; nvidia-smi"
    echo "       then retry: bash scripts/run_multiseed.sh 0"
    return 1
  elif [ $rc -ne 0 ]; then
    echo "[FAIL] env check rc=$rc"; return 1
  fi

  echo "--- UNI weights ---"
  if [ -f fm_cache/UNI/UNI-pytorch_model.bin ]; then
    ls -lh fm_cache/UNI/UNI-pytorch_model.bin
  else
    echo "[FAIL] UNI weights MISSING -> run: python download_fm_weights.py uni"
    return 1
  fi

  echo "--- dataset ($DATA) ---"
  ensure_dataset || return 1
  NSUB=$(count_samples "$DATA")
  echo "sample subdirs: $NSUB   (expected 35)"
  [ "$NSUB" -eq 35 ] || { echo "[FAIL] wrong sample count -> check --data path"; return 1; }

  echo "--- label csv ($LABELS) ---"
  if [ -f "$LABELS" ]; then
    echo "rows: $(( $(wc -l < "$LABELS") - 1 ))"
    python -u -c "
import pandas as pd
d = pd.read_csv('$LABELS')
print('  cols:', list(d.columns))
print('  progression_ordinal counts:', d['progression_ordinal'].value_counts().to_dict())
"
  else
    echo "[FAIL] label csv missing: $LABELS"; return 1
  fi

  echo "--- RAM / swap ---"
  free -g | head -3
  echo "--- existing FM cache (speeds up every seed after the first) ---"
  ls -lh results/cache/ 2>/dev/null | tail -5 || echo "  (none yet — first run pays the UNI pass)"
  echo "[$(ts)] STAGE 0 OK"
}

# -----------------------------------------------------------------------------
stage1() {
  hr; echo "[$(ts)] STAGE 1 — SMOKE TEST (seed 0, 3 epochs)"; hr
  local LOG="$LOGDIR/smoke.log"
  echo "log: $LOG"
  python -u scripts/train_st.py \
    --data "$DATA" \
    --histology_label_csv "$LABELS" \
    --hpv_gene_set "$HPV_SET" \
    --lambda_recon $L_RECON --lambda_neigh $L_NEIGH --lambda_hpv $L_HPV \
    --lambda_sup $L_SUP --lambda_prog $L_PROG \
    --permutation_n 200 \
    --epochs 3 --seed 0 --run_id SMOKE_full_s0 2>&1 | tee "$LOG"
  local rc=${PIPESTATUS[0]}
  if [ $rc -ne 0 ]; then echo "[FAIL] smoke rc=$rc — see $LOG"; return 1; fi
  if [ -f results/results_SMOKE_full_s0.json ]; then
    echo "--- smoke result ---"
    python -c "import json;d=json.load(open('results/results_SMOKE_full_s0.json'));print('moran_i =',d.get('moran_i'));print('n_spots =',d.get('n_spots'));print('n_samples =',d.get('n_samples'))"
    echo "[$(ts)] STAGE 1 OK — pipeline works, go to stage 2/3"
  else
    echo "[FAIL] no results JSON produced"; return 1
  fi
}

run_one() {  # $1=tag  $2=seed  $3=extra-flags
  local tag=$1 seed=$2 extra=$3
  local rid="${tag}_seed${seed}"
  local log="$LOGDIR/${rid}.log"
  if [ -f "results/results_${rid}.json" ]; then
    echo "[$(ts)] SKIP $rid (result exists)"; return 0
  fi
  echo "[$(ts)] START $rid  -> $log  (global_patch_cap=$GCAP)"
  # shellcheck disable=SC2086
  python -u scripts/train_st.py \
    --data "$DATA" --histology_label_csv "$LABELS" --hpv_gene_set "$HPV_SET" \
    --lambda_recon $L_RECON --lambda_neigh $L_NEIGH --lambda_hpv $L_HPV \
    --lambda_sup $L_SUP --lambda_prog $L_PROG --permutation_n $PERMN \
    --global_patch_cap $GCAP \
    --epochs "$EPOCHS_FULL" --seed "$seed" --run_id "$rid" --dump_fused $extra \
    > "$log" 2>&1
  local rc=$?
  if [ $rc -ne 0 ]; then
    echo "[FAIL] $rid rc=$rc  last 25 lines:"; tail -25 "$log"; return 1
  fi
  python -c "import json;d=json.load(open('results/results_${rid}.json'));print('[$(ts)] DONE $rid  moran_i=%.4f  n_spots=%s  n_samples=%s'%(d['moran_i'],d.get('n_spots'),d.get('n_samples')))" \
    || { echo "[FAIL] $rid produced no parseable JSON"; return 1; }
}

stage2() {
  hr; echo "[$(ts)] STAGE 2 — FULL, seeds: $SEEDS"; hr
  for s in $SEEDS; do run_one FULL "$s" "" || return 1; done
  echo "[$(ts)] STAGE 2 OK"
}

stage3() {
  hr; echo "[$(ts)] STAGE 3 — NO-IMAGE, seeds: $SEEDS"; hr
  for s in $SEEDS; do run_one NOIMAGE "$s" "--disable_image_branch" || return 1; done
  echo "[$(ts)] STAGE 3 OK"
}

stage4() {
  hr; echo "[$(ts)] STAGE 4 — summarize all variants (mean +/- SD + tests vs FULL)"; hr
  python -u - <<'PY'
import json, glob, numpy as np
from scipy import stats
TAGS = ["FULL", "NOIMAGE", "NOHPV", "NONEIGH"]
LABEL = {"FULL": "FULL", "NOIMAGE": "NO-IMAGE", "NOHPV": "NO-HPV", "NONEIGH": "NO-NEIGH"}
def collect(tag):
    rows = []
    for p in sorted(glob.glob(f"results/results_{tag}_seed*.json")):
        s = int(p.rsplit("seed", 1)[1].split(".")[0])
        d = json.load(open(p, encoding="utf-8"))
        rows.append((s, d["moran_i"],
                     d.get("progression_monotonicity", {}).get("kendall_p"),
                     d.get("hpv_proxy_auc")))
    return sorted(rows)
data = {t: collect(t) for t in TAGS}
if not data["FULL"]:
    print("[FAIL] no FULL runs — finish stage 2 first"); raise SystemExit(1)
present = [t for t in TAGS if data[t]]
print("variants found:", ", ".join(LABEL[t] for t in present))
def mi(rows): return np.array([r[1] for r in rows])
print("=" * 78)
print(f"{'variant':10s} {'n':>2s}  {'Moran I (mean+/-SD)':>22s}   {'Kendall p':>10s}  {'hpv AUC':>8s}")
for t in present:
    m = mi(data[t])
    kp = [r[2] for r in data[t] if r[2] is not None]
    au = [r[3] for r in data[t] if r[3] is not None]
    sd = m.std(ddof=1) if len(m) > 1 else float('nan')
    kps = f"{np.median(kp):.3f}" if kp else "NA"
    aus = f"{np.mean(au):.3f}" if au else "NA"
    print(f"{LABEL[t]:10s} {len(m):2d}  {m.mean():.4f} +/- {sd:.4f}        "
          f"   {kps:>10s}  {aus:>8s}")
print("-" * 78)
miF = mi(data["FULL"])
summary = {"full": {"seeds": [r[0] for r in data["FULL"]], "moran_i": miF.tolist()}}
for t in present:
    if t == "FULL" or len(data[t]) < 2:
        continue
    m = mi(data[t])
    d = miF.mean() - m.mean()
    try:
        tt, p = stats.ttest_ind(miF, m, equal_var=False)
    except Exception:
        tt, p = float('nan'), float('nan')
    try:
        u, pu = stats.mannwhitneyu(miF, m, alternative="greater")
    except Exception:
        u, pu = float('nan'), float('nan')
    print(f"{LABEL[t]:10s} vs FULL: delta(Moran)={d:+.4f} ({100*d/miF.mean():+.1f}%)  "
          f"Welch p={p:.4f}  MWU(one-sided) p={pu:.4f}")
    summary[t.lower()] = {"seeds": [r[0] for r in data[t]], "moran_i": m.tolist(),
                          "delta_vs_full": float(d), "welch_p": float(p),
                          "mwu_p_one_sided": float(pu)}
print("-" * 78)
print("KEY CHECK (NO-IMAGE effect must reproduce across seeds):")
if len(data["NOIMAGE"]) >= 2:
    nmi = mi(data["NOIMAGE"])
    print(f"  Moran drop: {miF.mean():.3f} -> {nmi.mean():.3f}  "
          f"{'STABLE (all FULL>all NOIMAGE)' if miF.min() > nmi.max() else 'OVERLAP - report range honestly'}")
    fk = [r[2] for r in data["FULL"] if r[2] is not None]
    nk = [r[2] for r in data["NOIMAGE"] if r[2] is not None]
    if fk and nk:
        print(f"  Kendall p: FULL median {np.median(fk):.4f} -> NOIMAGE median {np.median(nk):.4f}  "
              f"{'(significance lost: OK)' if np.median(nk) > 0.05 else '(still sig - re-examine)'}")
json.dump(summary, open("results/multiseed_ablation_summary.json", "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)
print("saved -> results/multiseed_ablation_summary.json")
PY
}

# -----------------------------------------------------------------------------
stage5() {
  hr; echo "[$(ts)] STAGE 5 — NO-HPV & NO-NEIGH, seeds: $SEEDS"; hr
  for s in $SEEDS; do run_one NOHPV   "$s" "--lambda_hpv 0" || return 1; done
  for s in $SEEDS; do run_one NONEIGH "$s" "--no_neigh"     || return 1; done
  echo "[$(ts)] STAGE 5 OK"
}

case "${1:-help}" in
  0) stage0 ;;
  1) stage1 ;;
  2) stage2 ;;
  3) stage3 ;;
  4) stage4 ;;
  5) stage5 ;;
  core) stage0 && stage1 && stage2 && stage3 && stage4 ;;
  all)  stage0 && stage1 && stage2 && stage3 && stage5 && stage4 ;;
  *) sed -n '1,34p' "$0" ;;
esac
