"""Check if local results are updated with the fix."""
import json, os, glob

R = "results"
abl_ids = ["FULL", "NO-HPV", "NO-NEIGH", "BASELINE-CNN", "FM-UNI2", "HPV-ROBUST-A", "HPV-ROBUST-B"]

print("=== 本地消融结果检查（看是否已同步AutoDL新结果）===\n")
all_taus = set()
for aid in abl_ids:
    fp = os.path.join(R, f"results_{aid}.json")
    if not os.path.exists(fp):
        print(f"  ❌ {aid}: 文件缺失")
        continue
    d = json.load(open(fp))
    ha = d.get("histology_association") or {}
    pm = d.get("progression_monotonicity") or {}
    order_len = len(pm.get("order", []))
    tau = pm.get("kendall_tau")
    cin_p = ha.get("cin_kruskal_p")
    sub_p = ha.get("subtype_kruskal_p")
    hpa = d.get("hpv_proxy_auc") or d.get("hpv_auc")
    moran = d.get("moran_i")
    deg = d.get("n_deg_perm_fdr05_effect")
    
    all_taus.add(tau)
    ok = (order_len == 35 and cin_p is not None and sub_p is not None)
    flag = "✅" if ok else "❌"
    print(f"  {flag} {aid:15s} | order={order_len} | auc={hpa:.4f} | moran={moran:.4f} | deg={deg}")
    print(f"       tau={tau} | cin_KW_p={cin_p} | sub_KW_p={sub_p}")

print(f"\n  tau唯一值数: {len(all_taus)}/7 → {'✅ 有区分度' if len(all_taus) > 1 else '❌ 全部相同'}")

# Quick P0 check
print("\n=== P0 脚本输出 ===")
for name in ["baseline_hpv_auc.json", "gsva_vs_model.json", "independent_pathway.json", "threshold_sensitivity.json"]:
    fp = os.path.join(R, name)
    print(f"  {'✅' if os.path.exists(fp) else '❌'} {name}")
