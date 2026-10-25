#!/bin/bash
# Memory-monitored run: log cgroup + RSS + python output together.
cd /root/autodl-tmp/project/project4_cervix_multimodal || exit 1
mkdir -p logs
export OMP_NUM_THREADS=32
export MEMTRACE=1
sync; echo 3 > /proc/sys/vm/drop_caches 2>/dev/null
rm -f logs/_mem5.csv logs/_run5.log
(
  while true; do
    echo "$(date +%s) cur=$(cat /sys/fs/cgroup/memory.current)" >> logs/_mem5.csv
    sleep 3
  done
) &
MON=$!
/root/miniconda3/bin/python scripts/repair_e3_methodB_train.py \
    --data data/sim_st/group_A_expA --method mrp --adv-list 0 --seeds 0 \
    --epochs 3 --hid 256 --k 6 --warmup 1 --clip 1.0 --adv-sn --device cpu \
    --recon-chunk 4096 --log-every 1 --out results/_probe5.json \
    > logs/_run5.log 2>&1
echo "PY_EXIT=$?" >> logs/_run5.log
kill "$MON" 2>/dev/null
echo "DONE" >> logs/_run5.log
