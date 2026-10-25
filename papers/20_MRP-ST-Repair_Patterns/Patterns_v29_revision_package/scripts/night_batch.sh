#!/usr/bin/env bash
# =============================================================================
# night_batch.sh — 一晚串行任务链（不打断当前 powergrid 网格）
#   (1) 等待 A3 网格 (powergrid, run_sim_power_grid.sh + train_st.py) 彻底结束
#   (2) 重跑 run_sim_power_grid.sh：跳过已完成 json,只补跑 17 个 numpy 事故污染段
#   (3) STAGATE/SpaGCN/GraphST 三件套对比（降低 epochs + smoke 分层采样）
#   (4) 聚合 sim_power_grid.py -> operating characteristics
# =============================================================================
set -uo pipefail
export PATH=/root/miniconda3/bin:$PATH          # screen 不加载 conda 的兼容
export PERM=2000                                # 与 powergrid 网格同 PERM, 口径一致
ROOT=/root/autodl-tmp/project/project4_cervix_multimodal
cd "$ROOT"
mkdir -p logs results data
PY=/root/miniconda3/bin/python

echo "########## night_batch starting $(date) ##########"

# ---- (1) wait for the running powergrid grid to fully finish ----
echo "###### [wait] for active powergrid grid to finish $(date) ######"
{
  while pgrep -f "scripts/train_st.py" >/dev/null || pgrep -f "run_sim_power_grid.sh" >/dev/null; do
    echo "[wait] grid still running @ $(date +%H:%M:%S), sleeping 5min ..." 
    sleep 300
  done
} 2>&1 | tee -a logs/night_batch.log
if pgrep -f "scripts/train_st.py" >/dev/null || pgrep -f "run_sim_power_grid.sh" >/dev/null; then
  echo "[ABORT] grid still running after wait; aborting night_batch" | tee -a logs/night_batch.log
  exit 1
fi
echo "###### grid finished. starting catch-up re-run $(date) ######" | tee -a logs/night_batch.log

# ---- (2) catch-up: re-run grid (skips finished json, fills the 17 numpy-polluted NOALL) ----
PERM=2000 bash scripts/run_sim_power_grid.sh 2>&1 | tee -a logs/night_batch.log

# ---- (3) ST trio benchmark on L1 + CTRL (reduced epochs, stratified smoke) ----
echo "###### ST benchmark start $(date) ######" | tee -a logs/night_batch.log
$PY scripts/benchmark_st_methods.py \
    --groups group_A_g20261006_L1 group_C_g20261006_CTRL \
    --methods STAGATE,SpaGCN,GraphST \
    --n-perm 2000 --device cuda \
    --stagate-epochs 200 --graphst-epochs 100 --smoke 15 \
    --out results/st_methods_benchmark.json \
    2>&1 | tee -a logs/night_batch.log

# ---- (4) aggregate operating-characteristics grid ----
echo "###### aggregation start $(date) ######" | tee -a logs/night_batch.log
$PY scripts/sim_power_grid.py 2>&1 | tee -a logs/night_batch.log

echo "########## night_batch DONE $(date) ##########" | tee -a logs/night_batch.log