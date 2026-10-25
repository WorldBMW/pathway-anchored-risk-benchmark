#!/bin/bash
# E2 supplementary chain (guide §10 + closure audit 2026-10-18)
# Runs AFTER the main E2 grid finishes (waits for ALL-E2-DONE marker).
# 1) E2b weak-signal (0.3) axis-1 grid   -> C2 insurance / 3-panel phase map
# 2) axis-2 rerun with tau_ldo trainer   -> sibling-gap metric (audit-paper
#    LODO semantics) for k>1 cohorts
# 3) E4 stable-trio rerun + dumps        -> acceptance-point replication +
#    PERM sensitivity + C3-lite decoder-gene-direction materials
# 4) GCN backbone: simA / simC / E4      -> generality (not GAT-specific)
cd /root/autodl-tmp/project/project4_cervix_multimodal
PY=/root/miniconda3/bin/python
mkdir -p results logs

echo "[chain] waiting for main E2 to finish ..."
while ! grep -q ALL-E2-DONE /tmp/e2_train.log 2>/dev/null; do
    sleep 60
done
echo "[chain] main E2 done, starting supplements $(date +%H:%M:%S)"

# --- 1) E2b weak signal ---
for d in data/e2_phaseB/ax1_n*_s*; do
    [ -d "$d/group_A" ] || continue
    tag=$(basename "$d"); out="results/e2b_${tag}.json"
    if [ ! -f "$out" ]; then
        echo "[chain] E2b $tag $(date +%H:%M:%S)"
        $PY scripts/repair_e3_methodB_train.py --data "$d/group_A" \
            --out "$out" --seeds "${tag##*_s}" --device cuda:0 \
            > "logs/e2b_${tag}.log" 2>&1
    fi
done

# --- 2) axis-2 rerun with tau_ldo (new output names) ---
for d in data/e2_phase/ax2_k*_s*; do
    tag=$(basename "$d"); out="results/e2_phase2_${tag}.json"
    if [ ! -f "$out" ]; then
        echo "[chain] axis2-rerun $tag $(date +%H:%M:%S)"
        $PY scripts/repair_e3_methodB_train.py --data "$d/group_A" \
            --out "$out" --seeds "${tag##*_s}" --device cuda:0 \
            > "logs/e2p2_${tag}.log" 2>&1
    fi
done

# --- 3) E4 stable rerun with dumps ---
if [ ! -f results/repair_e4_hnscc_stable.json ]; then
    echo "[chain] E4-stable rerun $(date +%H:%M:%S)"
    $PY scripts/repair_e3_methodB_train.py --data data/e4_hnscc2 \
        --out results/repair_e4_hnscc_stable.json --seeds 0 1 2 \
        --warmup 50 --clip 1.0 --adv-sn --dump-xs \
        --dump-w results/e4_decoder_w.npz --dump-lam 2.0 \
        --device cuda:0 > logs/e4_stable2.log 2>&1
fi

# --- 4) GCN backbone generality ---
if [ ! -f results/repair_gcn_simA.json ]; then
    echo "[chain] GCN simA $(date +%H:%M:%S)"
    $PY scripts/repair_e3_methodB_train.py --backbone gcn \
        --data data/sim_st/group_A --out results/repair_gcn_simA.json \
        --seeds 0 1 2 --device cuda:0 > logs/gcn_simA.log 2>&1
fi
if [ ! -f results/repair_gcn_simC.json ]; then
    echo "[chain] GCN simC $(date +%H:%M:%S)"
    $PY scripts/repair_e3_methodB_train.py --backbone gcn \
        --data data/sim_st/group_C --out results/repair_gcn_simC.json \
        --seeds 0 1 2 --device cuda:0 > logs/gcn_simC.log 2>&1
fi
if [ ! -f results/repair_gcn_e4.json ]; then
    echo "[chain] GCN E4 $(date +%H:%M:%S)"
    $PY scripts/repair_e3_methodB_train.py --backbone gcn \
        --data data/e4_hnscc2 --out results/repair_gcn_e4.json \
        --seeds 0 1 2 --device cuda:0 > logs/gcn_e4.log 2>&1
fi

echo "ALL-SUPP-DONE $(date +%H:%M:%S)"
