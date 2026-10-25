"""One-shot validator for results_CERVIX35_PROG.json or equivalent.
Prints the paper-ready checklist used for 二区 submission decisions.
Exit non-zero on critical FAIL so CI can catch it.
"""

import json
import sys
from pathlib import Path

def mark(p):
    if p is None:
        return 'NA'
    p = float(p)
    return 'SIG***' if p < 0.001 else 'SIG**' if p < 0.01 else 'SIG*' if p < 0.05 else 'NS'

def main(path: str):
    p = Path(path)
    if not p.exists():
        print(f'FATAL: {p} does not exist')
        return 2
    d = json.load(open(p, encoding='utf-8'))
    ha = d.get('histology_association') or {}

    all_ok = True

    print('\n========== A. SAMPLE SETUP ==========')
    rows = [
        ('n_samples', d.get('n_samples'), lambda v: v >= 30, '>=30'),
        ('hpv_gene_set_mode', d.get('hpv_gene_set_mode'), lambda v: v == 'kegg_hpv', 'kegg_hpv'),
        ('hpv_gene_set_size', d.get('hpv_gene_set_size'), lambda v: (v or 0) >= 50, '>=50'),
    ]
    for k, v, okfn, thr in rows:
        ok = bool(okfn(v)); chk = 'PASS' if ok else 'FAIL'
        print(f'{chk:5s}  {k:22s} = {v!s:>10s}   (threshold {thr})')
        if not ok: all_ok = False

    print('\n========== B. MEDICAL VALIDITY (35% weight) ==========')
    sub_agg = ha.get('by_histology_subtype', {})
    order = ['Normal_Ecto', 'Normal', 'HSIL', 'ADC', 'SCC']
    means = {s: (sub_agg.get(s) or {}).get('overall_mean') for s in order}
    monotonic = True
    prev = float('-inf')
    for s in order:
        m = means.get(s)
        if m is None: continue
        if m <= prev: monotonic = False
        prev = m
    sub_p = ha.get('subtype_kruskal_p')
    mwu = ha.get('mannwhitney_by_subtype_bonf5') or {}
    ecto_vs_scc = (mwu.get('Normal_Ecto_vs_SCC') or {}).get('p_bonf5')
    checks = [
        ('risk ordering (Normal_Ecto<Normal<HSIL<SCC)', monotonic, True),
        ('subtype Kruskal p<0.05', sub_p is not None and sub_p < 0.05, (sub_p, '%.2e' % (sub_p or 1))),
        ('MW Normal_Ecto vs SCC Bonf5 p<0.05 (Fig2 star)', ecto_vs_scc is not None and ecto_vs_scc < 0.05, (ecto_vs_scc, ecto_vs_scc)),
        ('HPV proxy AUC >= 0.90', (d.get('hpv_proxy_auc') or 0) >= 0.90, f"{d.get('hpv_proxy_auc'):.3f}"),
        ('HPV high-low gap >= 0.30', (d.get('hpv_gene_high_low_gap') or 0) >= 0.30, f"{d.get('hpv_gene_high_low_gap'):.3f}"),
        ('n_DEG (perm+effect) >= 10', (d.get('n_deg_perm_fdr05_effect') or 0) >= 10, d.get('n_deg_perm_fdr05_effect')),
    ]
    for name, ok, extra in checks:
        chk = 'PASS' if ok else 'FAIL'
        print(f'{chk:5s}  {name}: {extra}')
        if not ok: all_ok = False

    print('\n--- by_histology_subtype means (paper values) ---')
    for s in order:
        if s not in sub_agg: continue
        v = sub_agg[s]
        print(f"  {s:14s} n={v['n_samples']:>2d}  mean={v['overall_mean']:+.3f}")

    print('\n--- Mann-Whitney U (primary post-hoc, Bonf5) ---')
    focus = ['Normal_Ecto_vs_SCC','Normal_Ecto_vs_HSIL','Normal_Ecto_vs_ADC','Normal_vs_SCC','HSIL_vs_SCC']
    for k in focus:
        r = mwu.get(k)
        if r is None:
            print(f'  {k:28s} MISSING'); all_ok = False; continue
        bonf = r.get('p_bonf5')
        chk = mark(bonf)
        print(f"  {k:28s} n={r['n_a']}/{r['n_b']}  U={r['u']}  p_raw={r['p_raw']:.3e}  p_bonf5={bonf:.3e}  {chk}")

    sr = ha.get('spot_level_robustness') or {}
    print(f'\n--- spot-level robustness (Fig2 caption sensitivity) ---')
    print(f"  KW p = {sr.get('subtype_kruskal_p', float('nan')):.3e}")
    d_spot = sr.get('dunn_by_subtype') or {}
    for k in focus:
        r = d_spot.get(k)
        if r is None: continue
        bonf = r.get('p_bonferroni')
        print(f"  spot Dunn {k:28s} z={r.get('z',0):+.2f} p_bonf={bonf:.3e} {mark(bonf)}")

    print('\n========== C. TECHNICAL NOVELTY (35% weight) ==========')
    checks = [
        ("Moran's I >= 0.80", (d.get('moran_i') or 0) >= 0.80, f"{d.get('moran_i'):.3f}"),
        ('Kendall tau(progression) >= 0.40', ((d.get('progression_monotonicity') or {}).get('kendall_tau') or 0) >= 0.40, f"{(d.get('progression_monotonicity') or {}).get('kendall_tau'):.3f}"),
        ('progression perm p < 0.01', ((d.get('progression_monotonicity') or {}).get('permutation_p') or 1) < 0.01, f"{(d.get('progression_monotonicity') or {}).get('permutation_p'):.3e}"),
    ]
    for name, ok, extra in checks:
        chk = 'PASS' if ok else 'FAIL'
        print(f'{chk:5s}  {name}: {extra}')
        if not ok: all_ok = False

    print('\n========== CRITICAL NEW FIELDS (code v3 vs v2/v1) ==========')
    required_new_keys = ['mannwhitney_by_subtype_bonf5','spot_level_robustness','cin_kruskal_p','subtype_kruskal_p','dunn_by_subtype']
    for k in required_new_keys:
        has = k in ha
        v = ha.get(k)
        nonempty = False
        if isinstance(v, dict): nonempty = len(v) > 0
        elif isinstance(v, (int,float)): nonempty = True
        chk = 'PASS' if has and nonempty else 'FAIL'
        print(f'{chk:5s}  histology_association[{k}] present={has} nonempty={nonempty}')
        if not (has and nonempty): all_ok = False

    score = 0
    print('\n========== SUMMARY ==========')
    print(f"OVERALL: {'PASS' if all_ok else 'FAIL'}")
    if all_ok:
        print('主模型 Step 10b 达标：继续 Step 11b -> 12b -> 13b -> 14b')
    else:
        print('⚠  仍然不达标：按本打印中 FAIL 行处理，最常见情况是：')
        print('  - 先跑 scripts/patch_histology_json.py results/results_CERVIX35_PROG.json results/results_st.json')
        print('  - 如果仍缺字段：重跑 Step 10b（见 SERVER_RUN_COMMANDS_4090.md Step 10b）')
    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'results/results_CERVIX35_PROG.json'))
