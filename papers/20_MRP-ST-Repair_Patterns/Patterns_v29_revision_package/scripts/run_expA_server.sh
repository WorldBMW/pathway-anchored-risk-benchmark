#!/bin/bash
# Server-side runner: MRP-ST-Repair Exp A (SOTA head-to-head) + Exp C-cervix.
# Usage:  bash scripts/run_expA_server.sh A|C|cervix
# Resumable: a run whose --out JSON already exists is skipped.
set -u
cd /root/autodl-tmp/project/project4_cervix_multimodal || exit 1
PY=/root/miniconda3/bin/python
mkdir -p logs results
TAG="$1"
LOG="logs/expA_${TAG}.log"
exec > >(tee -a "$LOG") 2>&1

C="--epochs 150 --hid 256 --warmup 50 --clip 1.0 --adv-sn --device cuda:0"

run() {
  local out=""
  for a in "$@"; do
    case "$a" in results/*.json) out="$a" ;; esac
  done
  if [ -n "$out" ] && [ -f "$out" ]; then
    echo "[$(date +%F_%H:%M:%S)] [skip] $out already exists"
    return 0
  fi
  echo "[$(date +%F_%H:%M:%S)] >> $*"
  "$PY" "$@"
  echo "[$(date +%F_%H:%M:%S)] << exit=$?"
}

echo "[runner] start $TAG $(date)"
case "$TAG" in
A)
  D=data/sim_st/group_A_expA
  run scripts/repair_e3_methodB_train.py --data $D --method mrp      --adv-list 0 --seeds 0 1 2 $C --out results/expA_A_baseline.json
  run scripts/repair_e3_methodB_train.py --data $D --method mrp      --adv-list 0.5 1 2 5 --seeds 0 1 2 $C --out results/expA_A_mrp.json
  run scripts/repair_e3_methodB_train.py --data $D --method groupdro --adv-list 1 10 --seeds 0 1 2 $C --out results/expA_A_groupdro.json
  run scripts/repair_e3_methodB_train.py --data $D --method irm      --adv-list 10 100 --seeds 0 1 2 $C --out results/expA_A_irm.json
  ;;
C)
  D=data/sim_st/group_C_expA
  run scripts/repair_e3_methodB_train.py --data $D --method mrp      --adv-list 0 --seeds 0 1 2 $C --out results/expA_C_baseline.json
  run scripts/repair_e3_methodB_train.py --data $D --method mrp      --adv-list 0.5 1 2 5 --seeds 0 1 2 $C --out results/expA_C_mrp.json
  run scripts/repair_e3_methodB_train.py --data $D --method groupdro --adv-list 1 10 --seeds 0 1 2 $C --out results/expA_C_groupdro.json
  run scripts/repair_e3_methodB_train.py --data $D --method irm      --adv-list 10 100 --seeds 0 1 2 $C --out results/expA_C_irm.json
  ;;
cervix)
  run scripts/repair_e3_methodB_train.py --data data/st_visium/cervix_all_ext --method mrp \
      --adv-list 0 1 2 --seeds 0 1 2 --epochs 300 --hid 256 --warmup 50 --clip 1.0 \
      --adv-sn --device cuda:0 --dump-xs --out results/expC_cervix_lodo.json
  ;;
*)
  echo "usage: $0 A|C|cervix"; exit 1;;
esac
echo "[runner] $TAG DONE $(date)"
