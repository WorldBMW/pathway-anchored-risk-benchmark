"""Audit g:\\project4_cervix_multimodal\\results against 二区 submission checklist.
Produces:
  * File inventory by category
  * Per-experiment PASS/FAIL against 二区 thresholds
  * Missing deliverables list mapped to paper Figure/Table
  * Remaining commands required
"""

import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "results"

def ok(cond):
    return "PASS" if bool(cond) else "FAIL"

def load(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def sigmark(p):
    if p is None: return "NA"
    p = float(p)
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"

def safe(d, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur

print("=" * 80)
print("RESULTS INVENTORY")
print("=" * 80)
files = sorted([p for p in R.iterdir() if p.is_file()])
for p in files:
    size_kb = p.stat().st_size / 1024.0
    print(f"  {p.name:40s}  {size_kb:8.1f} KB")

print()
print("=" * 80)
print("CATEGORY 1 — MAIN MODEL (results_CERVIX35_PROG.json, alias results_st.json)")
print("=" * 80)

p_main = R / "results_CERVIX35_PROG.json"
if not p_main.exists():
    print("FATAL: results_CERVIX35_PROG.json MISSING"); sys.exit(1)
main = load(p_main)
ha = main.get("histology_association") or {}
mwu = ha.get("mannwhitney_by_subtype_bonf5") or {}
mwu_ecto_scc = (mwu.get("Normal_Ecto_vs_SCC") or {}).get("p_bonf5")
sub_kw_p = ha.get("subtype_kruskal_p")
prog = main.get("progression_monotonicity") or {}

main_checks = [
    ("n_samples >= 30", main.get("n_samples", 0) >= 30, main.get("n_samples")),
    ("hpv_gene_set_mode == kegg_hpv", main.get("hpv_gene_set_mode") == "kegg_hpv", main.get("hpv_gene_set_mode")),
    ("hpv_proxy_auc >= 0.90", (main.get("hpv_proxy_auc") or 0) >= 0.90, f"{main.get('hpv_proxy_auc'):.4f}"),
    ("hpv_gene_high_low_gap >= 0.30", (main.get("hpv_gene_high_low_gap") or 0) >= 0.30, f"{main.get('hpv_gene_high_low_gap'):.3f}"),
    ("n_deg_perm_fdr05_effect >= 10", (main.get("n_deg_perm_fdr05_effect") or 0) >= 10, main.get("n_deg_perm_fdr05_effect")),
    ("moran_i >= 0.80", (main.get("moran_i") or 0) >= 0.80, f"{main.get('moran_i'):.4f}"),
    ("progression Kendall tau >= 0.40", (prog.get("kendall_tau") or 0) >= 0.40, f"{prog.get('kendall_tau'):.3f}"),
    ("progression perm_p < 0.01", (prog.get("permutation_p") or 1) < 0.01, f"{prog.get('permutation_p'):.2e}"),
    ("subtype Kruskal p < 0.05", (sub_kw_p or 1) < 0.05, f"{sub_kw_p:.2e} ({sigmark(sub_kw_p)})"),
    ("MWU Normal_Ecto_vs_SCC Bonf5 < 0.05", (mwu_ecto_scc or 1) < 0.05, f"{mwu_ecto_scc:.2e} ({sigmark(mwu_ecto_scc)})"),
    ("histology fields present (cin/sub_kruskal + dunn + mwu + spot_robust)",
     all(k in ha for k in ["cin_kruskal_p","subtype_kruskal_p","dunn_by_subtype","mannwhitney_by_subtype_bonf5","spot_level_robustness"]),
     {k: (k in ha) for k in ["cin_kruskal_p","subtype_kruskal_p","dunn_by_subtype","mannwhitney_by_subtype_bonf5","spot_level_robustness"]}),
    ("top_degs all positive delta (epi/immune/HPv up in high risk)",
     all(d > 0 for _, d, *_ in (main.get("top_degs") or [])[:10]),
     [f"{g}={d:+.3f}" for g,d,_,_ in (main.get("top_degs") or [])[:5]]),
]
main_pass_n = 0
for name, cond, extra in main_checks:
    print(f"{ok(cond):5s}  {name}: {extra}")
    if cond: main_pass_n += 1
print(f"  Main model checks: {main_pass_n}/{len(main_checks)} PASS")

# ====== category 2: ablation ======
print()
print("=" * 80)
print("CATEGORY 2 — ABLATION STUDY (ablation_summary.json + per-run JSONs)")
print("=" * 80)

ab_sum_p = R / "ablation_summary.json"
ablation_required_runs = ["FULL", "NO-HPV", "NO-NEIGH", "HPV-ROBUST-A", "HPV-ROBUST-B"]
ab_exist = {name: (R / f"results_{name}.json").exists() for name in ablation_required_runs}
for n, e in ab_exist.items():
    print(f"{ok(e):5s}  ablation results_{n}.json EXISTS")

if ab_sum_p.exists():
    absum = load(ab_sum_p)
    rows_list = absum.get("rows") or []  # list[dict], key field = "config"
    rows = {r.get("config") or r.get("run_id") or f"row_{i}": r for i, r in enumerate(rows_list)}
    # Required keys per row: hpv_auc, moran_i, n_deg_perm, spearman_rho_vs_full
    full_row = rows.get("FULL") or {}
    nohpv_row = rows.get("NO-HPV") or {}
    print(f"{ok(bool(full_row)):5s}  FULL row in ablation_summary")
    print(f"{ok(bool(nohpv_row)):5s}  NO-HPV row in ablation_summary")
    full_auc = full_row.get("hpv_auc"); nohpv_auc = nohpv_row.get("hpv_auc")
    if full_auc and nohpv_auc:
        print(f"  FULL.hpv_auc={full_auc:.3f}  NO-HPV.hpv_auc={nohpv_auc:.3f}  "
              f"FULL>NO-HPV = {ok(float(full_auc) > float(nohpv_auc))}")
    required_cols = ["hpv_auc","moran_i","n_deg_perm","spearman_rho_vs_full","lambda_hpv","lambda_sup","hpv_gene_set_mode","hpv_gene_set_size"]
    missing_cols = {}
    for name, r in rows.items():
        mis = [c for c in required_cols if c not in r]
        if mis: missing_cols[name] = mis
    if missing_cols:
        for k, v in missing_cols.items(): print(f"FAIL  ablation row {k} missing columns: {v}")
    else:
        print("PASS  all ablation rows have required columns")
    # Robustness A/B vs FULL Spearman rho >= 0.85
    for rname in ("HPV-ROBUST-A","HPV-ROBUST-B"):
        r_ = rows.get(rname) or {}
        rho = r_.get("spearman_rho_vs_full")
        try: rho_f = float(rho)
        except: rho_f = float("nan")
        cond = (rho_f >= 0.85)
        print(f"{ok(cond):5s}  {rname} Spearman vs FULL >= 0.85: rho={rho_f:.3f}")
else:
    print("FAIL  ablation_summary.json MISSING")

# ====== category 3: baseline ======
print()
print("=" * 80)
print("CATEGORY 3 — BASELINE COMPARISON (baseline_*.json + results_BASELINE-*.json)")
print("=" * 80)
base_he2st = R / "baseline_BASELINE_HE2ST.json"
base_cnn = R / "results_BASELINE-CNN.json"
for p, name in [(base_he2st, "baseline_BASELINE_HE2ST.json (HE-only proxy)"),
                (base_cnn, "results_BASELINE-CNN.json")]:
    print(f"{ok(p.exists()):5s}  {name}: {'YES' if p.exists() else 'MISSING'}")

# Baseline deliverables for 二区: at least 4 baselines + proposed vs all LOSO Pearson.
# We check the baselines stored inside baseline_BASELINE_HE2ST.json if it's the
# main baseline output (baseline_compare.py writes that).
if base_he2st.exists():
    b = load(base_he2st)
    methods = list((b.get("methods") or {}).keys())
    print(f"  baseline methods present: {methods if methods else b.keys()}")
    proposed = (b.get("ours") or b.get("proposed") or {}).get("pearson") or b.get("pearson")
    best_base_pearson = None
    for mk in ["ridge","lasso","svr","rf","xgb","xgboost","mlp","knn","he2st"]:
        v = safe(b, "methods", mk, "pearson")
        if v is None: v = safe(b, mk, "pearson")
        if v is None: continue
        try: vf = float(v)
        except: continue
        best_base_pearson = vf if (best_base_pearson is None or vf > best_base_pearson) else best_base_pearson
    if proposed is not None and best_base_pearson is not None:
        try: pf = float(proposed); bf = float(best_base_pearson)
        except: pf = bf = 0
        print(f"  proposed Pearson={pf:.3f}  best baseline Pearson={bf:.3f}  "
              f"proposed>=0.95*baseline={ok(pf >= 0.95*bf)}  proposed>=0.60={ok(pf >= 0.60)}")
    else:
        print("  INFO: baseline / proposed Pearson keys not found; inspect JSON manually")

# ====== category 4: FM comparison ======
print()
print("=" * 80)
print("CATEGORY 4 — FOUNDATION MODEL COMPARISON (UNI vs UNI2)")
print("=" * 80)
for fm in ("FM-UNI2",):
    p = R / f"results_{fm}.json"
    print(f"{ok(p.exists()):5s}  results_{fm}.json exists")
    if p.exists():
        d = load(p)
        print(f"  hpv_auc={d.get('hpv_proxy_auc'):.3f}  moran_i={d.get('moran_i'):.3f}  "
              f"n_deg={d.get('n_deg_perm_fdr05_effect')}  n_samples={d.get('n_samples')}")

# ====== category 5: downstream missing quick check ======
print()
print("=" * 80)
print("CATEGORY 5 — REMAINING EXPERIMENTS (TCGA Cox, explain, cross_cohort, clinical, cv, monotonicity, fused)")
print("=" * 80)
MISSING = {
    "results/align_hpv*.json (TCGA Cox / HPV alignment layers 1+2+3)": list(R.glob("align_hpv*.json")),
    "results/explain_cervix35/ (HPV spatial overlay PNGs + histology boxplot CSV)": list((R / "explain_cervix35").glob("*")) if (R / "explain_cervix35").exists() else [],
    "results/cross_cohort_*.json": list(R.glob("cross_cohort_*.json")),
    "results/clinical_association*.json": list(R.glob("clinical_association*.json")),
    "results/cross_validation*.json": list(R.glob("cross_validation*.json")),
    "results/monotonicity*.json": list(R.glob("monotonicity*.json")),
    "results/check_monotonicity*.json": list(R.glob("check_monotonicity*.json")),
    "results/fused_embs.npz (for niche/explain)": list(R.glob("fused_embs.npz")),
    "results/explain_* (sample PNGs, any)": list(R.glob("explain_*")),
    "results/ablation_summary.csv (tabular for Suppl)": list(R.glob("ablation_summary.csv")),
}
for name, hits in MISSING.items():
    print(f"{ok(len(hits) > 0):5s}  {name}")
    for h in hits[:5]:
        print(f"        -> {h.relative_to(R)}")
    if len(hits) > 5:
        print(f"        ... (+{len(hits)-5} more)")

print()
print("=" * 80)
print("DELIVERABLES × FIGURE/TABLE MAP (缺啥一目了然)")
print("=" * 80)

def have(cond):
    return "✅" if cond else "❌"

figs = [
    ("Fig1 Pipeline + Data Overview",
     True,  # pipeline schematic; independent of runs
     []),
    ("Fig2 Risk Score × Histology Subtype Boxplot (CIN/subtype + MWU/spot Dunn)",
     (sub_kw_p or 1) < 0.05 and (mwu_ecto_scc or 1) < 0.05,
     ["histology_association (pass)" if ((sub_kw_p or 1)<0.05 and (mwu_ecto_scc or 1)<0.05) else "RUN Step 10b patch via patch_histology_json.py",
      "RUN Step 14b explain_st.py → histology_risk_spot_boxplot.csv + PNG"]),
    ("Fig3 Spatial Risk Map × HPV gene overlay (case samples)",
     any("hpv_gene_spatial_overlay" in p.name for p in (R / "explain_cervix35").glob("*")) if (R / "explain_cervix35").exists() else False,
     ["RUN Step 14b explain_st.py (HPV-anchored gene spatial overlay PNGs per sample)"]),
    ("Fig4 Ablation: FULL vs NO-HPV vs NO-NEIGH vs HPV-ROBUST-A/B radar/bar",
     ab_sum_p.exists() and all(ab_exist.values()),
     [] if (ab_sum_p.exists() and all(ab_exist.values())) else ["RUN Step 12b ablation_study.py"]),
    ("Fig5 TCGA-CESC external survival validation (Cox PH Uni/Multi HR+95%CI)",
     bool(MISSING["results/align_hpv*.json (TCGA Cox / HPV alignment layers 1+2+3)"][1:]) if len(MISSING["results/align_hpv*.json (TCGA Cox / HPV alignment layers 1+2+3)"])>=1 else len(MISSING["results/align_hpv*.json (TCGA Cox / HPV alignment layers 1+2+3)"])>=1,
     ["RUN Step 13b align_hpv.py --enable_cox"]),
    ("Table 1 Proposed vs Baselines LOSO (ridge/svr/rf/xgb/mlp) Pearson/Spearman/MAE",
     base_he2st.exists() or base_cnn.exists(),
     ["RUN Step 11b baseline_compare.py --loso"] if not (base_he2st.exists() or base_cnn.exists()) else ["REFORMAT baseline JSON → Table 1 (if LOSO fields missing, RUN Step 11b)"]),
    ("Suppl Fig S1 FM comparison UNI vs UNI2 AUC/Moran",
     (R / "results_FM-UNI2.json").exists(),
     []),
    ("Suppl Fig S2 Cross-cohort generalization (breast/ovarian/prostate/colon-HD)",
     len(MISSING["results/cross_cohort_*.json"]) >= 1,
     ["RUN Step 5a-d cross_cohort_eval.py"]),
    ("Suppl Fig S3 Permutation DEG volcano × prior panel",
     (main.get("n_deg_perm_fdr05_effect") or 0) >= 10,
     ["OPTIONAL generate DEG CSV / volcano via scripts/explain_st.py or tmp script"]),
    ("Suppl Table S1 Per-sample case-level risk × histology × CIN",
     bool(ha.get("per_sample")),
     ["EXPORT JSON[histology_association][per_sample] to CSV (can script trivial)"]),
]
for title, cond, todo in figs:
    print(f"{have(cond)}  {title}")
    for t in todo:
        print(f"      ➜ {t}")

print()
print("=" * 80)
print("SUMMARY: GLOBAL ACCEPTANCE PROBABILITY SCORE")
print("=" * 80)

# Composite scoring (医学 35 / 技术 35 / 实验 30)
med_score = 0.0
med_items = [
    (main.get("n_samples", 0) >= 30, 4),
    ((main.get("hpv_proxy_auc") or 0) >= 0.90, 6),
    ((main.get("hpv_gene_high_low_gap") or 0) >= 0.30, 3),
    ((main.get("n_deg_perm_fdr05_effect") or 0) >= 10, 5),
    ((sub_kw_p or 1) < 0.05, 5),
    ((mwu_ecto_scc or 1) < 0.05, 6),
    ((prog.get("kendall_tau") or 0) >= 0.40, 3),
    (all(d > 0 for _, d, *_ in (main.get("top_degs") or [])[:10]), 3),
]
for c, s in med_items:
    if c: med_score += s

tech_score = 0.0
tech_items = [
    ((main.get("moran_i") or 0) >= 0.80, 6),
    ((prog.get("permutation_p") or 1) < 0.01, 4),
    (ab_sum_p.exists() and all(ab_exist.values()), 10),
    ((R / "results_FM-UNI2.json").exists(), 5),
    (base_he2st.exists() or base_cnn.exists(), 6),
    (bool(ha.get("spot_level_robustness")), 4),
]
for c, s in tech_items:
    if c: tech_score += s

exp_score = 0.0
exp_items = [
    (bool(ha.get("per_sample")), 4),
    (ab_sum_p.exists() and (lambda rr=((load(ab_sum_p).get("rows") or {}).get("FULL") or {}):
        all(c in rr for c in ["hpv_auc","moran_i","n_deg_perm","spearman_rho_vs_full"]))(), 8),
    (len(MISSING["results/align_hpv*.json (TCGA Cox / HPV alignment layers 1+2+3)"]) >= 1, 7),  # 外部验证
    (len(MISSING["results/explain_cervix35/ (HPV spatial overlay PNGs + histology boxplot CSV)"]) >= 3, 6),  # 3+ fig
    (len(MISSING["results/cross_cohort_*.json"]) >= 3, 5),  # ≥3 cross cohort
]
for c, s in exp_items:
    if c: exp_score += s

TOTAL = med_score + tech_score + exp_score
print(f"医学价值 (35): {med_score:.0f}/35")
print(f"技术创新 (35): {tech_score:.0f}/35")
print(f"实验严谨 (30): {exp_score:.0f}/30")
print(f"TOTAL         : {TOTAL:.0f}/100")
if TOTAL >= 85:
    accept = "≥ 85% 二区录用，小修接收概率极高"
elif TOTAL >= 75:
    accept = "65-85% 录用，补齐下游实验后稳录"
elif TOTAL >= 65:
    accept = "45-65% 录用，必须补齐 Step 11b/13b/14b/5a-d 才能送审"
else:
    accept = "低录用概率，证据链不完整"
print(f"二区录用概率评估 : {accept}")
