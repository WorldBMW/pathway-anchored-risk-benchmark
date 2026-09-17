import json, os, glob

R = "results"

def j(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def fmt(v, d=4):
    if v is None: return None
    if isinstance(v, float): return round(v, d)
    return v

out = {}

# 1. main model
d = j(f"{R}/results_CERVIX35_PROG.json")
ha = d.get("histology_association") or {}
pm = d.get("progression_monotonicity") or {}
out["main"] = {
    "n_samples": d.get("n_samples"),
    "hpv_proxy_auc": fmt(d.get("hpv_proxy_auc")),
    "hpv_auc": fmt(d.get("hpv_auc")),
    "moran_i": fmt(d.get("moran_i")),
    "recon_mse_proxy": fmt(d.get("recon_mse_proxy")),
    "recon_mse": fmt(d.get("recon_mse")),
    "n_deg_perm_fdr05_effect": d.get("n_deg_perm_fdr05_effect"),
    "n_deg_naive": d.get("n_deg_naive"),
    "n_prior_genes": d.get("n_prior_genes"),
    "high_risk_ratio": fmt(d.get("high_risk_ratio")),
    "hpv_gene_set_size": d.get("hpv_gene_set_size"),
    "hpv_gene_set_mode": d.get("hpv_gene_set_mode"),
    "kendall_tau": fmt(pm.get("kendall_tau")),
    "kendall_p": fmt(pm.get("kendall_p")),
    "permutation_p": fmt(pm.get("permutation_p")),
    "permutation_n": pm.get("permutation_n"),
    "n_up": pm.get("n_up"),
    "n_pairs": pm.get("n_pairs"),
    "cin_kruskal_stat": fmt(ha.get("cin_kruskal_stat")),
    "cin_kruskal_p": fmt(ha.get("cin_kruskal_p")),
    "subtype_kruskal_stat": fmt(ha.get("subtype_kruskal_stat")),
    "subtype_kruskal_p": fmt(ha.get("subtype_kruskal_p")),
    "label_source": ha.get("label_source"),
    "by_cin_grade": ha.get("by_cin_grade"),
    "by_histology_subtype": ha.get("by_histology_subtype"),
    "dunn_by_grade": ha.get("dunn_by_grade"),
    "dunn_by_subtype": ha.get("dunn_by_subtype"),
    "mannwhitney_by_subtype_bonf5": ha.get("mannwhitney_by_subtype_bonf5"),
    "order": pm.get("order"),
    "top_deg": (d.get("deg_perm_sorted") or d.get("deg_analysis", {}).get("perm_sorted", []))[:15],
}

# 2. ablation
abl_ids = ["FULL", "NO-HPV", "NO-NEIGH", "BASELINE-CNN", "FM-UNI2", "HPV-ROBUST-A", "HPV-ROBUST-B"]
out["ablation"] = {}
for aid in abl_ids:
    fp = f"{R}/results_{aid}.json"
    if not os.path.exists(fp): continue
    dd = j(fp)
    haa = dd.get("histology_association") or {}
    pmm = dd.get("progression_monotonicity") or {}
    out["ablation"][aid] = {
        "n_samples": dd.get("n_samples"),
        "hpv_proxy_auc": fmt(dd.get("hpv_proxy_auc")),
        "hpv_high_low_gap": fmt(dd.get("hpv_high_low_gap")),
        "moran_i": fmt(dd.get("moran_i")),
        "recon_mse_proxy": fmt(dd.get("recon_mse_proxy")),
        "recon_mse": fmt(dd.get("recon_mse")),
        "n_deg_perm": dd.get("n_deg_perm_fdr05_effect"),
        "hpv_gene_set_mode": dd.get("hpv_gene_set_mode"),
        "hpv_gene_set_size": dd.get("hpv_gene_set_size"),
        "kendall_tau": fmt(pmm.get("kendall_tau")),
        "perm_p": fmt(pmm.get("permutation_p")),
        "cin_kruskal_p": fmt(haa.get("cin_kruskal_p")),
        "subtype_kruskal_p": fmt(haa.get("subtype_kruskal_p")),
        "order_len": len(pmm.get("order", [])),
    }

# 3. baseline ridge
b = j(f"{R}/baseline_BASELINE_LOSO35_RIDGE.json")
out["baseline_ridge"] = b.get("per_regressor", [])

# 4. baseline hpv auc
bh = j(f"{R}/baseline_hpv_auc.json")
out["baseline_hpv_auc"] = bh.get("per_regressor", [])

# 5. TCGA cox
a = j(f"{R}/align_hpv_cervix35.json")
out["align_keys"] = list(a.keys())
l3b = a.get("layer3b_cox_hpv_proxy", {})
out["tcga_layer3b"] = {
    "univariate": l3b.get("cox_univariate"),
    "age_adj": l3b.get("cox_multivariate_age"),
}
l3 = a.get("layer3_cox", {}) or a.get("layer3_visium_deg", {})
out["tcga_layer3"] = {"univariate": l3.get("cox_univariate")}

# 6. cross cohort
out["cross_cohort"] = {}
for fp in glob.glob(f"{R}/cross_cohort_XCOHORT_*.json"):
    dd = j(fp)
    name = os.path.basename(fp).replace("cross_cohort_XCOHORT_","").replace(".json","")
    out["cross_cohort"][name] = dd.get("rows", [])

# 7. cohort HPV auc
out["E_cohort"] = {}
for fp in glob.glob(f"{R}/results_E_*.json"):
    dd = j(fp)
    name = os.path.basename(fp).replace("results_E_","").replace(".json","")
    out["E_cohort"][name] = {
        "hpv_auc": fmt(dd.get("hpv_auc")),
        "hpv_proxy_auc": fmt(dd.get("hpv_proxy_auc")),
        "moran_i": fmt(dd.get("moran_i")),
        "n_samples": dd.get("n_samples"),
    }

tnbc = j(f"{R}/results_BREAST_TNBC_42.json")
out["tnbc"] = {
    "hpv_auc": fmt(tnbc.get("hpv_auc")),
    "hpv_proxy_auc": fmt(tnbc.get("hpv_proxy_auc")),
    "moran_i": fmt(tnbc.get("moran_i")),
    "n_samples": tnbc.get("n_samples"),
    "keys": [k for k in tnbc.keys() if "auc" in k.lower() or "hpv" in k.lower() or "moran" in k.lower()],
}

# 8. P0 scripts
out["gsva"] = j(f"{R}/gsva_vs_model.json").get("summary", {})
out["independent_pathway"] = j(f"{R}/independent_pathway.json").get("per_pathway", [])
ts = j(f"{R}/threshold_sensitivity.json")
out["threshold"] = {
    "recommended_threshold_eval": ts.get("recommended_threshold_eval"),
    "single_metric_sweeps": ts.get("single_metric_sweeps"),
}

with open("_paper_numbers.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, default=str)

print(json.dumps(out, ensure_ascii=False, indent=1, default=str))