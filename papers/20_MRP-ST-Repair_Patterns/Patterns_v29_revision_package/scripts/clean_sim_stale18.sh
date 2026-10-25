#!/usr/bin/env bash
# ============================================================================
# Delete the 18 STALE group_B/group_C sim results so run_sim_fix27.sh reruns
# them instead of hitting its "JSON exists -> skip" guard.
#
# Why this script exists (2026-10-09):
#   The 2026-10-08 overnight batch only regenerated group_A's 9 runs
#   (21:27 -> 03:26, perm=10000). The 18 group_B/group_C target files were
#   never deleted, so run_sim_one.sh skipped all of them. Pasting the
#   multi-line `for` delete loop by hand is fragile (line-eating at the shell
#   continuation prompt has happened before), so deletion is scripted here.
#
# Deleted = group_{B,C} x {FULL,NOPROG,NOSUP} x seeds{0,1,2} = 18 JSON + npz:
#   * NOPROG (6)  : kendall_tau = null (old pre-fix train_st.py)
#   * NOSUP (6)   : seed1/2 null; seed0 valid tau but perm=200 (p=0.005)
#   * FULL  (6)   : valid tau but perm=200 -> upgrade to perm=10000 so the
#                   whole Supplementary Table S3 shares one B=10000 caliber
# KEPT UNTOUCHED:
#   * group_A ALL (the 9 fixed runs are paper-grade; the other 12 pre-existed)
#   * all NOALL npz/json (frozen-embedding LODO evidence; main verdicts must
#     not move) and NOIMAGE/NOHPV/NONEIGH (already perm=10000).
#
# Usage:  bash scripts/clean_sim_stale18.sh          # print + delete
#         bash scripts/clean_sim_stale18.sh --dry    # list only, delete nothing
# ============================================================================
set -u
DRY=0
[ "${1:-}" = "--dry" ] && DRY=1

n=0
for g in group_B group_C; do
  for v in FULL NOPROG NOSUP; do
    for s in 0 1 2; do
      for ext in json npz; do
        if [ "$ext" = "json" ]; then
          f="results/results_SIM_${g}_${v}_seed${s}.json"
        else
          f="results/fused_embs_SIM_${g}_${v}_seed${s}.npz"
        fi
        if [ -f "$f" ]; then
          if [ "$DRY" = "1" ]; then
            echo "[dry] would rm $f"
          else
            rm -fv "$f"
          fi
          n=$((n+1))
        else
          echo "[absent] $f"
        fi
      done
    done
  done
done

echo "------------------------------------------------------------------"
if [ "$DRY" = "1" ]; then
  echo "[dry-run] $n files would be removed; nothing deleted."
else
  echo "removed $n files (expect 36 = 18 JSON + 18 npz)."
  echo "remaining SIM JSON:  $(ls results/results_SIM_*.json 2>/dev/null | wc -l) (expect 45)"
  echo "remaining SIM npz :  $(ls results/fused_embs_SIM_*.npz 2>/dev/null | wc -l) (expect 45)"
fi
