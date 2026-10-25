#!/bin/bash
# Clean PERM=2000 power grid launcher (run inside a detached screen).
export PATH=/root/miniconda3/bin:$PATH
export PERM=2000
cd /root/autodl-tmp/project/project4_cervix_multimodal || exit 1
echo "python -> $(command -v python)"
echo "PERM=$PERM"
exec bash scripts/run_sim_power_grid.sh