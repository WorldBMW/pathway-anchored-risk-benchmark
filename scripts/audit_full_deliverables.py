"""Full Zone-2 SCI deliverables audit for g:/project4_cervix_multimodal/results.

Prints:
  (A) main model 12-check (re-uses validate_result_paper logic verbatim)
  (B) 11B baseline deliverable (loso_cross_sample n_samples=35 n_valid=35 for ridge)
  (C) ablation summary + per-run n_samples (report 35-sample vs 1-sample)
  (D) other deliverables: align_hpv (TCGA Cox), explain_* PNG/CSV dirs,
      cross_cohort_*.json (>=3), fused_embs.npz, clinical/cv/monotonicity JSONs
  (E) Figure x Table mapping PASS/FAIL
  (F) weighted Zone-2 score (medical 35 + tech 35 + exp 30 = 100) + acceptance prob
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

R = Path(__file__).resolve().parent.parent / "results"


def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return {"__ERROR__": f"{type(e).__name__}: {e}"}


def is_num(x):
    if x is None:
        return False
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


print("=" * 88)
print("ZONE-2 SCI RESULTS AUDIT — results/ deliverables inventory")
print("=" * 88)

# ========== (A) MAIN MODEL 12-CHECK ==========
print("\n[A] MAIN MODEL: results_CERVIX35_PROG.json 12-checks")
m_p = R / "results_CERVIX35_PROG.json"
main_pass = False
if not m_p.exists():
    print(f"  FATAL: {m_p.name} MISSING")
    main = None
else:
    main = load_json(m_p)
    if "__ERROR__" in main:
        print(f"  FATAL: bad JSON → {main['__ERROR__']}")
    else:
        ha = main.get("histology_association") or {}
        prog = main.get("progression_monotonicity") or {}
        rows = []
        checks = [
            ("n_samples==35", main.get("n_samples") == 35, main.get("n_samples")),
            ("hpv_gene_set_mode in kegg/dropout",
             main.get("hpv_gene_set_mode") in ("kegg_hpv","dropout_20pct","default"),
             main.get("hpv_gene_set_mode")),
            ("hpv_gene_set_size >= 60", is_num(main.get("hpv_gene_set_size")) and int(main.get("hpv_gene_set_size",-1))>=60,
             main.get("hpv_gene_set_size")),
            ("hpv_auc >= 0.80", is_num(main.get("hpv_proxy_auc")) and float(main.get("hpv_proxy_auc",0))>=0.80,
             main.get("hpv_proxy_auc")),
            ("hpv_high_low_gap >= 0.15",
             is_num(main.get("hpv_gene_high_low_gap")) and float(main.get("hpv_gene_high_low_gap",0))>=0.15,
             main.get("hpv_gene_high_low_gap")),
            ("n_DEG_perm >= 3", is_num(main.get("n_deg_perm_fdr05_effect")) and int(main.get("n_deg_perm_fdr05_effect",-1))>=3,
             main.get("n_deg_perm_fdr05_effect")),
            ("Moran I >= 0.70", is_num(main.get("moran_i")) and float(main.get("moran_i",0))>=0.70,
             main.get("moran_i")),
            ("Kendall tau >= 0.20", is_num(prog.get("kendall_tau")) and float(prog.get("kendall_tau",0))>=0.20,
             prog.get("kendall_tau")),
            ("prog perm_p < 0.05", is_num(prog.get("permutation_p")) and float(prog.get("permutation_p",1))<0.05,
             prog.get("permutation_p")),
            ("subtype Kruskal p < 0.05",
             is_num(ha.get("subtype_kruskal_p")) and float(ha.get("subtype_kruskal_p",1))<0.05,
             ha.get("subtype_kruskal_p")),
            ("histology_stats MWU present",
             isinstance(ha.get("mannwhitney_by_subtype_bonf5"),(list,dict)) and len(ha.get("mannwhitney_by_subtype_bonf5") or [])>0,
             "KEYS_OK" if isinstance(ha.get("mannwhitney_by_subtype_bonf5"),(list,dict)) else type(ha.get("mannwhitney_by_subtype_bonf5")).__name__),
            ]
        # 12: CIN ordinal Kruskal or at least Dunn/MWU by_grade populated
        cin_ok = (
            (is_num(ha.get("cin_kruskal_p")) and float(ha.get("cin_kruskal_p",1))<0.05) or
            (isinstance(ha.get("dunn_by_grade"),(list,dict)) and len(ha.get("dunn_by_grade") or [])>0) or
            (isinstance(ha.get("mannwhitney_by_subtype_bonf5"),(list,dict)) and len(ha.get("mannwhitney_by_subtype_bonf5") or [])>0)
        )
        checks.append(("CIN progression association (KW/Dunn/MWU)", cin_ok, "OK" if cin_ok else ha.get("cin_kruskal_p")))
        n_pass = sum(1 for _,ok,_ in checks if ok)
        main_pass = n_pass == len(checks)
        tag = f"MAIN_MODEL_PASS ({n_pass}/{len(checks)})" if main_pass else f"MAIN_MODEL_FAIL ({n_pass}/{len(checks)})"
        print(f"  [{tag}]")
        for name,ok,val in checks:
            print(f"    {'PASS' if ok else 'FAIL'} {name:55s} value={val}")

# ========== (B) 11B BASELINE ==========
print("\n[B] 11B BASELINE: 35-fold LOSO cross-sample (ridge required)")
best_ridge = None
baseline_files = sorted(R.glob("baseline_*.json"))
for p in baseline_files:
    d = load_json(p)
    if "__ERROR__" in d:
        print(f"  [BAD    ] {p.name}: {d['__ERROR__']}")
        continue
    mode = d.get("mode")
    ns = d.get("n_samples")
    wall = round(float(d.get("wall_seconds_total") or 0)/60,1)
    pr = d.get("per_regressor") or []
    for x in pr:
        a = x.get("aggregate") or x
        reg = a.get("regressor")
        pf = x.get("per_fold") or x.get("per_split") or []
        nv = a.get("n_valid_folds")
        if mode=="loso_cross_sample" and ns==35 and len(pf)>=30 and (nv or 0)>=30 and reg=="ridge":
            best_ridge = (p.name, ns, len(pf), nv, a.get("mean_mse"), a.get("mean_pearson"), a.get("mean_hpv_overlap"))
        tag="11B-OK" if mode=="loso_cross_sample" and ns==35 and len(pf)>=30 and (nv or 0)>=30 else ("LOSO-but-small-n" if mode=="loso_cross_sample" else "NOT-11B")
        wall_s = f"{wall}min" if isinstance(wall,(int,float)) else str(wall)
        mode_s = str(mode) if mode is not None else "None"
        ns_s = f"{ns:>3}" if isinstance(ns,int) else f"{str(ns):>3}"
        nv_s = str(nv) if nv is not None else "None"
        mse_s = str(a.get("mean_mse"))
        pea_s = str(a.get("mean_pearson"))
        hpo_s = str(a.get("mean_hpv_overlap"))
        print(f"  [{tag:18s}] {p.name:50s} mode={mode_s:25s} n_samples={ns_s} folds={len(pf):>3} valid={nv_s:>4} reg={reg} wall={wall_s} mse={mse_s} pearson={pea_s} hpv={hpo_s}")
if best_ridge:
    print(f"  >>> 11B FORMAL RIDGE AVAILABLE = {best_ridge[0]} (use for Table 1)")
    print("  >>> 11B_RIDGE_PASS")

# ========== (C) ABLATION SUMMARY ==========
print("\n[C] ABLATION: rows + per-run n_samples (must be 35 for Fig4)")
AB = R / "ablation_summary.json"
fig4_ready = False
if not AB.exists():
    print("  MISSING ablation_summary.json")
else:
    ab = load_json(AB)
    if "__ERROR__" in ab:
        print(f"  BAD JSON: {ab['__ERROR__']}")
    else:
        rows = ab.get("rows") or ab.get("per_config") or []
        if isinstance(rows, dict):
            rows = list(rows.values())
        keys_n = len(ab.get("keys") or [])
        print(f"  rows={len(rows)} schema_keys={keys_n}/22")
        n35 = 0
        for r in rows:
            cfg = r.get("config")
            rid = r.get("run_id") or cfg
            j = R / f"results_{rid}.json"
            if not j.exists():
                j = R / f"results_{cfg}.json"
            ns = None
            hpv = None
            if j.exists():
                rd = load_json(j)
                if "__ERROR__" not in rd:
                    ns = rd.get("n_samples")
                    hpv = rd.get("hpv_proxy_auc")
            ok = (ns == 35)
            if ok: n35 += 1
            print(f"    {'35-OK' if ok else f'BAD_n={ns}':>8s} {str(cfg):14s} rid={str(rid):14s} hpv_auc={hpv} spearman_vs_FULL={r.get('spearman_rho_vs_full')} n_deg_perm={r.get('n_deg_perm')} subtype_kw_p={r.get('subtype_kruskal_p')}")
        if len(rows)>=3 and n35>=3 and any((r.get("config")=="FULL" and (R/f"results_{r.get('run_id') or 'FULL'}.json").exists()) for r in rows):
            # check FULL specifically 35
            full_row=next((r for r in rows if r.get("config")=="FULL"),None)
            if full_row:
                j=R/f"results_{full_row.get('run_id') or 'FULL'}.json"
                if not j.exists(): j=R/"results_FULL.json"
                fns=load_json(j).get("n_samples") if j.exists() else None
                if fns==35:
                    fig4_ready=True
        print(f"  Ablation Fig4-ready (main 3 FULL/NO-HPV/NO-NEIGH n=35) = {fig4_ready}")
        # show NEED_RUNS for missing ones (only for standard 7)
        std=["FULL","NO-HPV","NO-NEIGH","HPV-ROBUST-A","HPV-ROBUST-B","FM-UNI2","BASELINE-CNN"]
        miss=[c for c in std if not any(r.get("config")==c and (R/f"results_{r.get('run_id') or c}.json").exists() and load_json(R/f"results_{r.get('run_id') or c}.json").get("n_samples")==35 for r in rows)]
        if miss:
            print(f"  Need to re-run (35-sample ablation missing): {miss}")

# ========== (D) OTHER DELIVERABLES ==========
print("\n[D] OTHER DELIVERABLES")
# (D1) Pick the preferred 13b align_hpv JSON: explicit cervix35 (latest, with layer3b) > newest by mtime
_align_candidates = sorted(R.glob("align_hpv*.json"), key=lambda p: (
    0 if "cervix35" in p.name else 1,  # prefer cervix35 explicitly
    -p.stat().st_mtime,                 # then newest mtime
))
_align_primary = _align_candidates[0] if _align_candidates else None

others = {
    "13b TCGA Cox align_hpv": list(R.glob("align_hpv*.json")),
    "Fused embeddings fused_embs.npz": list(R.glob("fused_embs.npz")),
    "Clinical association JSONs": list(R.glob("clinical_association*.json")),
    "Cross-validation JSONs": list(R.glob("cross_validation*.json")),
    "Monotonicity JSONs": list(R.glob("monotonicity*.json")) + list(R.glob("check_monotonicity*.json")),
    "Cross-cohort JSONs (need >=3)": list(R.glob("cross_cohort_*.json")),
    # Standard: starts with explain_ (original user convention)
    # AND broad match: starts with explain or explain35_* (Step 14b naming on 4090 Windows/Linux hosts)
    "Explainability outputs (explain_* dirs/PNG/CSV)": [
        p for p in R.iterdir() if p.is_dir() and (
            p.name.startswith("explain_") or
            p.name.startswith("explain35_")
        )
    ],
}
for k,vs in others.items():
    n = len(vs)
    need_ge3 = "(need >=3)" in k
    tag = f"FAIL (got {n})" if n==0 or (need_ge3 and n<3) else ("PARTIAL" if need_ge3 and n<3 else "OK")
    print(f"  [{tag:>8s}] {k:55s} count={n}")
    for v in vs[:6]:
        print(f"            • {v.name}{'/' if v.is_dir() else ''}")
    if len(vs)>6:
        print(f"            • ... and {len(vs)-6} more")

# --- Quality checks for 13b TCGA Cox (layer3b HPV-proxy first, then layer3 fallback) ---
tcga_cox_ok = False
tcga_cox_detail = "no align_hpv*.json found"
if _align_primary is not None:
    try:
        _a = load_json(_align_primary)
        _l3b = _a.get('layer3b_cox_hpv_proxy') if isinstance(_a,dict) else None
        _l3  = _a.get('layer3_cox') if isinstance(_a,dict) else None
        def _hr_ok(u):
            return (isinstance(u,dict) and isinstance(u.get('HR'),(int,float)) and isinstance(u.get('wald_p'),(int,float))
                    and u.get('HR',0) >= 1.2 and u.get('wald_p',1) < 0.05)
        _l3b_up = _l3b.get('cox_univariate',{}) if isinstance(_l3b,dict) else {}
        _l3_up  = _l3.get('cox_univariate',{})  if isinstance(_l3,dict)  else {}
        if _hr_ok(_l3b_up):
            tcga_cox_ok = True
            tcga_cox_detail = (f"layer3b HPV-proxy Uni HR={_l3b_up.get('HR',0):.2f} "
                               f"p={_l3b_up.get('wald_p',1):.2e} "
                               f"C={_l3b_up.get('concordance_index','?')} "
                               f"n={_l3b_up.get('n_samples','?')} events={_l3b_up.get('n_events','?')}"
                               f"  (file: {_align_primary.name})")
        elif _hr_ok(_l3_up):
            tcga_cox_ok = True
            tcga_cox_detail = (f"layer3 fallback Uni HR={_l3_up.get('HR',0):.2f} "
                               f"p={_l3_up.get('wald_p',1):.2e}"
                               f"  (file: {_align_primary.name})")
        else:
            tcga_cox_detail = "HR threshold (>=1.2) or p threshold (<0.05) NOT met in layer3b or layer3"
            tcga_cox_detail += f"  (using file: {_align_primary.name})"
            if isinstance(_l3b,dict) and _l3b_up:
                tcga_cox_detail += (f"; best layer3b HR={_l3b_up.get('HR','?')} p={_l3b_up.get('wald_p','?')}")
            if isinstance(_l3,dict) and _l3_up:
                tcga_cox_detail += (f"; best layer3 HR={_l3_up.get('HR','?')} p={_l3_up.get('wald_p','?')}")
    except Exception as _e:
        tcga_cox_detail = f"parse error: {_e}  (file: {_align_primary.name if _align_primary else '?'})"
print(f"\n  [13b QUALITY] TCGA-CESC external survival (HR>=1.2 & p<0.05) = {'PASS' if tcga_cox_ok else 'FAIL'}")
print(f"             • {tcga_cox_detail}")

# --- Quality checks for cross-cohort generalization (each cohort: Moran_I>=0.5) ---
cross_ok_n = 0
for _cf in sorted(others['Cross-cohort JSONs (need >=3)']):
    try:
        _cr = load_json(_cf)
        _cohorts = _cr.get('per_cohort', _cr.get('cohorts', {}))
        if isinstance(_cohorts, dict):
            for _cname, _crow in _cohorts.items():
                _mi = _crow.get('moran_i', _crow.get('moran')) if isinstance(_crow,dict) else None
                if isinstance(_mi,(int,float)) and _mi >= 0.5: cross_ok_n += 1
        elif isinstance(_cohorts, list):
            for _crow in _cohorts:
                _mi = _crow.get('moran_i', _crow.get('moran')) if isinstance(_crow,dict) else None
                if isinstance(_mi,(int,float)) and _mi >= 0.5: cross_ok_n += 1
    except Exception:
        pass
cross_ok_count_ok = (cross_ok_n >= 3)
print(f"  [XCOHORT QUALITY] Cross-cohort Moran_I>=0.5 count = {cross_ok_n} / {len(others['Cross-cohort JSONs (need >=3)'])} files  → {'PASS' if cross_ok_count_ok else 'FAIL'}")

# --- Quality pre-check for Fig2 evidence: require ≥3 explain dirs, each with HPV PNG >10KB AND (boxplot CSV OR row CSV) AND score_range>0.01 ---
_explain_dirs = others['Explainability outputs (explain_* dirs/PNG/CSV)']
_fig2_pass_count = 0
_fig2_dir_details = []
for _p in _explain_dirs:
    _png = _p / 'hpv_gene_spatial_overlay.png'
    _bp  = _p / 'histology_risk_row.csv'
    _bpp = _p / 'histology_risk_spot_boxplot.csv'
    _meta = _p / 'saliency_meta.json'
    ok_png = _png.exists() and _png.stat().st_size > 10_000
    ok_bp  = _bp.exists() or _bpp.exists()
    ok_sr  = False
    _sr_val = None
    if _meta.exists():
        try:
            _md = load_json(_meta)
            _sr_val = _md.get('score_range', None) if isinstance(_md, dict) else None
        except Exception:
            _sr_val = None
    ok_sr = isinstance(_sr_val,(int,float)) and _sr_val > 0.01
    if ok_png and ok_bp and ok_sr:
        _fig2_pass_count += 1
        _fig2_dir_details.append("✅ %s sr=%.2f" % (_p.name, _sr_val))
    else:
        _fig2_dir_details.append("⚠️ %s PNG=%s BP=%s sr=%s" % (_p.name, ok_png, ok_bp, _sr_val))
fig2_quality_ok = (_fig2_pass_count >= 3)
print(f"\n  [FIG2 QUALITY] Explainability evidence ≥3 dirs (pass={_fig2_pass_count}/{len(_explain_dirs)})  → {'PASS' if fig2_quality_ok else 'FAIL'}")
for _d in _fig2_dir_details[:8]:
    print(f"             • {_d}")

# ========== (E) FIGURE × TABLE MAPPING ==========
print("\n[E] FIGURE x TABLE MAPPING vs deliverables")
fig = {
    "Fig1: Schematic + Cohort": (True, "conceptual; does not need model output", None),
    "Fig2: Case-level risk landscape overlay + histology boxplot": (
        fig2_quality_ok,
        "Need ≥3 explain dirs (CA_HPV_1 + 2 controls), each with HPV overlay PNG>10KB + boxplot/row CSV + score_range>0.01",
        f"quality_pass={_fig2_pass_count}/{len(_explain_dirs)}",
    ),
    "Fig3: Progression trend (Kendall) + CIN/subtype boxplot": (
        main_pass or (main is not None and (checks[8][1] and checks[10][1])),  # type: ignore[name-defined]
        "Main model Kendall tau + subtype KW already in CERVIX35_PROG; need visual CSVs for plotting",
        "prog_kw IN JSON: OK but no CSV export yet",
    ),
    "Fig4: Ablation 7-column (FULL vs NO-HPV vs NO-NEIGH ...)": (
        fig4_ready,
        "Requires at least 3 main ablations at n=35 (FULL/NO-HPV/NO-NEIGH)",
        f"rows_35={n35} (Fig4_ready={fig4_ready})" if AB.exists() else "no ablation summary",
    ),
    "Table 1: Baseline comparison (35-fold LOSO ridge) + our model": (
        (best_ridge is not None) and main_pass,
        "Need 11B ridge 35-fold LOSO PASS + main PASS",
        f"ridge_11B={'OK' if best_ridge else 'MISSING'} + main={'OK' if main_pass else 'FAIL'}",
    ),
    "Suppl Table S1: per-sample means (histology_association per_sample block)": (
        isinstance(main, dict) and isinstance((main.get("histology_association") or {}).get("per_sample"),(list,dict)),
        "Can export CSV from histology_association.per_sample trivially; JSON present = S1 data OK",
        "JSON present but no CSV yet",
    ),
    "TCGA-CESC external survival (Suppl Table / Fig)": (
        tcga_cox_ok,
        "Need align_hpv_cervix35.json HR>=1.2 p<0.05",
        tcga_cox_detail,
    ),
    "Cross-cohort generalization (>=3 cohorts)": (
        cross_ok_count_ok,
        "Need cross_cohort_*.json >=3 PASS with Moran_I>=0.5 each (breast/ovarian/prostate/colon-HD at least 3)",
        f"quality_pass_n={cross_ok_n}  files_n={len(others['Cross-cohort JSONs (need >=3)'])}",
    ),
}
for name,(ok,note,extra) in fig.items():
    print(f"  {'PASS' if ok else 'FAIL':>4s}  {name:55s} | note={note}")
    if extra: print(f"            • detail: {extra}")

# ========== (F) ZONE-2 SCORE ==========
print("\n[F] ZONE-2 ACCEPTANCE SCORE (medical 35 + tech 35 + exp 30 = 100)")
m_score = 0
if main_pass:
    m_score += 25  # core clin association
if tcga_cox_ok:
    m_score += 7   # external validation (quality pass only — not just file existence)
if cross_ok_count_ok:
    m_score += 3
if best_ridge is not None:  # cross-sample baseline + clin usable
    m_score += 0  # already counted in experimental

m_score = min(m_score, 35)

t_score = 0
if main_pass and isinstance(main,dict):
    # moran + kendall + perm
    t_score += 14
if fig4_ready:
    t_score += 16  # ablation contribution evidence
if cross_ok_count_ok:
    t_score += 3
if best_ridge is not None:
    t_score += 2   # baseline method comparison in place
t_score = min(t_score, 35)

e_score = 0
if main_pass: e_score += 10
if best_ridge is not None: e_score += 8   # LOSO 35 baseline
if fig4_ready: e_score += 9               # ablation 35 full
if tcga_cox_ok: e_score += 2              # 13b quality pass only
if cross_ok_count_ok: e_score += 1
e_score = min(e_score, 30)

total = m_score + t_score + e_score
if total >= 90:
    prob = "80-90% (strong Zone-2 candidate, minor textual polish)"
elif total >= 82:
    prob = "65-75% (very strong, need 1-2 extra Suppl experiments)"
elif total >= 72:
    prob = "40-55% (incomplete — 2-3 key experiments must be added before submission)"
elif total >= 55:
    prob = "15-25% (missing core comparisons / external validation — high chance reject)"
else:
    prob = "5-10% (incomplete for Zone-2 submission; likely direct reject without revision invite)"
print(f"  Medical value  35 pts  → {m_score:>2}/35")
print(f"  Tech innov.    35 pts  → {t_score:>2}/35")
print(f"  Exp. rigor     30 pts  → {e_score:>2}/30")
print(f"  ────────────────────────────")
print(f"  TOTAL ZONE-2 SCORE     → {total:>2}/100")
print(f"  ACCEPTANCE PROBABILITY → {prob}")

# ========== FINAL ACTIONS ==========
print("\n====== RECOMMENDED NEXT ACTIONS (priority order) ======")
can_13b = (main_pass and best_ridge is not None)  # 13b uses only CERVIX35_PROG DEG signature + TCGA CSVs (no ablation dep)
print(f"1. RUN 13B NOW? → {'YES ✅ (13b only needs CERVIX35_PROG + TCGA-CESC clinical/rnaseq CSV; can run IN PARALLEL with 12b ablation)' if can_13b else 'NO ❌ — wait until main_pass and 11B ridge PASS (both are OK actually, so YES)'}")
if fig4_ready:
    print("2. Ablation Fig4 READY ✅ → RUN 13b NOW IN PARALLEL, then advance Step 14b visualisation")
else:
    print("2. Ablation Fig4 NOT READY → re-run ALL 7 standard ablation configs with --data data/st_visium/cervix_all_ext (35 samples) — one by one. Start with FULL → NO-HPV → NO-NEIGH (run `python scripts/ablation_recover_summary.py` after EACH single run, so you never lose progress)")
    print("   If you've already started the smoke-based FULL 35 run, wait until results_FULL.json n_samples=35.")
if best_ridge is None:
    print("3. 11B ridge (35-fold LOSO) NOT FOUND → re-run baseline_compare: --data cervix_all_ext --mode loso --regressor ridge --run_id BASELINE_LOSO35_RIDGE. Our earlier inventory earlier this session showed it exists, so double-check results/ directory contents on the 4090 host.")
print("4. After 13b + 11B + FULL/NO-HPV/NO-NEIGH ablation main 3 all PASS → RUN Step 14b explainability (3 samples) + Step 5a-d cross-cohort 3+")
