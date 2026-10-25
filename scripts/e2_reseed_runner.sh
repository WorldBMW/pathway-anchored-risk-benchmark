#!/bin/bash
# Manuscript-hardening runs: (A) per-seed E4 decoder dumps for strict
# multi-seed C3-lite pairing; (B) 5-seed boundary robustness (Table S6).
cd /root/autodl-tmp/project/project4_cervix_multimodal
PY=/root/miniconda3/bin/python
mkdir -p results logs

# --- A) E4 per-seed decoder dumps (strict C3 pairs, stable-trio config) ---
for spec in "1 2.0 s1_lam2" "2 2.0 s2_lam2" "1 5.0 s1_lam5"; do
  set -- $spec
  sd=$1; lam=$2; tag=$3
  if [ ! -f "results/e4_dump_${tag}.json" ]; then
    echo "[dump] seed=$sd lam=$lam $(date +%H:%M:%S)"
    $PY scripts/repair_e3_methodB_train.py --data data/e4_hnscc2 \
      --out results/e4_dump_${tag}.json --seeds $sd \
      --warmup 50 --clip 1.0 --adv-sn --dump-xs \
      --dump-w results/e4_decoder_w_${tag}.npz --dump-lam $lam \
      --device cuda:0 > logs/e4_dump_${tag}.log 2>&1
  fi
done

# --- B) boundary robustness: wait for reseed data upload, then train ---
while [ ! -d data/e2_reseed/e2br_n32_s4/group_A ]; do
  echo "[wait] reseed data not uploaded yet $(date +%H:%M:%S)"; sleep 30
done
for tag in e2r_n16_s3 e2r_n16_s4 e2r_n32_s3 e2r_n32_s4 \
           e2br_n16_s3 e2br_n16_s4 e2br_n32_s3 e2br_n32_s4; do
  d=data/e2_reseed/$tag/group_A
  [ -d "$d" ] || continue
  out=results/${tag}.json
  if [ ! -f "$out" ]; then
    echo "[reseed] $tag $(date +%H:%M:%S)"
    $PY scripts/repair_e3_methodB_train.py --data "$d" --out "$out" \
      --seeds "${tag##*_s}" --device cuda:0 > logs/${tag}.log 2>&1
  fi
done
echo ALL-RESUPP2-DONE
