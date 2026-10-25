#!/bin/bash
# E2 phase-diagram training runner (server side). One cohort dir -> one JSON,
# training seed == sim-seed suffix of the cohort (per guide §10.2).
cd /root/autodl-tmp/project/project4_cervix_multimodal
PY=/root/miniconda3/bin/python
mkdir -p results logs

for d in data/e2_phase/ax1_n*_s* data/e2_phase/ax2_k*_s*; do
    [ -d "$d/group_A" ] || continue
    tag=$(basename "$d")
    out="results/e2_phase_${tag}.json"
    if [ -f "$out" ]; then
        echo "[skip] $tag (json exists)"
        continue
    fi
    seed="${tag##*_s}"
    echo "[run] $tag  train_seed=$seed  $(date +%H:%M:%S)"
    $PY scripts/repair_e3_methodB_train.py \
        --data "$d/group_A" --out "$out" --seeds "$seed" \
        --device cuda:0 > "logs/e2_${tag}.log" 2>&1
    rc=$?
    echo "[done] $tag rc=$rc $(date +%H:%M:%S)"
done
echo "ALL-E2-DONE"
