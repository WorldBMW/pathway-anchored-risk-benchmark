"""v6 -> v7 (part A): numeric provenance and cross-domain uncertainty.

Every change here is backed by a value read out of the result files in results/.
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, '..', 'papers', '20_MRP-ST-Repair_Patterns',
                 'MRP-ST-Repair_manuscript_Patterns_v7.md')

t = io.open(P, encoding='utf-8').read()


def rep(old, new, expect=1):
    global t
    n = t.count(old)
    if n != expect:
        raise SystemExit('EXPECT %d GOT %d :: %s' % (expect, n, old[:110]))
    t = t.replace(old, new)


# ---------------------------------------------------------------- 1. Table 1
# Provenance of sigma_hat, and the LDI vs feasibility-ratio distinction.
rep(
    "and what was actually observed.",
    "and what was actually observed. "
    "Every entry in the τ_base and σ̂ columns is estimated at λ = 0, from the unrepaired baseline "
    "model alone, before any dose is chosen; no repaired run contributes to any number in this "
    "table. σ̂ is the scale of the refit permutation null (B = 2,000 permutations, seed 20261010). "
    "The LDI values reported in Table 2 are computed per cell against that cell's own σ̂, because "
    "an audit has to grade the representation as it stands after dosing; σ̂ drifts by at most "
    "7.6% (head and neck) and 9.5% (prostate) across the whole dose grid, so the baseline estimate "
    "used here is representative of the grid. Finally, LDI at λ = 0 and the ratio τ_base/σ̂ are "
    "different statistics that happen to agree numerically here: they differ by the null-floor term "
    "τ_⊥ ≈ 0.001, which is negligible against these τ values, so cervical reads 2.4 as an LDI and "
    "2.4 as a ratio, and head and neck reads 2.18 either way. The ratio governs whether a feasible "
    "dose exists; the LDI grades whether a given run is acceptable.",
)

# ------------------------------------------------- 2. cross-domain uncertainty
rep(
    "the pre-repair ratio correctly predicted an empty dual gate in both "
    "(0 of 15 seed × dose cells accepted in each), and boundary I reproduced: sibling-unit "
    "inflation was eight-fold larger where group–label coupling was twenty-fold larger, despite "
    "comparable identity identifiability (Table 5, Figure 5).",
    "the pre-repair ratio correctly predicted an empty dual gate in both "
    "(0 of 12 dosed cells accepted in each; counting the three undosed baselines the figure is "
    "0 of 15, and the two differ only because λ = 0 is not a repair point), and boundary I "
    "reproduced: sibling-unit inflation, τ_LOO − τ_LGO at λ = 0, was +0.0061 on HAR "
    "(per-seed +0.0036 to +0.0095) against +0.0494 on the gas-sensor cohort (per-seed "
    "+0.0294 to +0.0697), the cohort whose group–label coupling κ is twenty times larger, despite "
    "comparable identity identifiability (10.4× versus 9.1× chance). The gap is not sampling "
    "variation. Across all 15 seed × dose cells of each cohort the two distributions do not "
    "overlap at all (HAR +0.0010 to +0.0095, gas +0.0209 to +0.0697), and a bootstrap 95% "
    "interval on the difference of means is +0.024 to +0.063 using baseline cells and "
    "+0.032 to +0.047 using all 15 cells, neither interval containing zero. We quote the "
    "factor of eight from the baseline means because it is the more conservative of the two "
    "ratios; over all cells the ratio is twelve (Table 5, Figure 5; Table S13).",
)

rep(
    "Accepted cells | τ_LOO − τ_LGO at λ = 0 | Identity lift | τ_LGO retained | Gap reduction |",
    "Accepted cells (λ > 0) | τ_LOO − τ_LGO at λ = 0 (per-seed range) | Identity lift | "
    "τ_LGO retained | Gap reduction |",
)
rep("| empty | 0/15 | +0.0061 | 10.0 → 5.4 | 0.98 | −81% |",
    "| empty | 0/12 | +0.0061 (+0.0036 to +0.0095) | 10.0 → 5.4 | 0.98 | −81% |")
rep("| empty | 0/15 | +0.0494 | 9.2 → 7.2 | 0.89 | −56% |",
    "| empty | 0/12 | +0.0494 (+0.0294 to +0.0697) | 9.2 → 7.2 | 0.89 | −56% |")

# --------------------------------------------------- 3. prostate R provenance
rep(
    "with τ_LDO 0.219–0.229 (R = 0.58–0.60);",
    "with τ_LDO = 0.229 in the primary run (R = 0.60, per-seed 0.56–0.67) and 0.219 in the "
    "independent re-run (R = 0.58); the two runs agree, and the spread across seeds within a run "
    "is wider than the difference between runs.",
)

# ------------------------------------------------- 4. non-blindness 45 runs
rep(
    "repaired models were correctly graded unsupported in 45 of 45 runs across configurations "
    "(GAT, GCN, and the stability-hardened variant; Figure 2B): LDI never crossed the 1.645 gate.",
    "repaired models were correctly graded unsupported in 45 of 45 runs (three configurations × "
    "three seeds × five doses; 36 of them carry λ > 0, and the nine undosed baselines are graded "
    "unsupported on the same criterion). The largest LDI seen in any configuration, including "
    "λ = 0, is 1.554, so the result does not depend on counting baselines: restricting to dosed "
    "cells leaves 36 of 36 (Table S2; Figure 2B).",
)
# (the legend version is wrapped across lines, so use a regex)
old_leg = re.search(
    r"on an identity-confounding control the LDI stays below the 1\.645 gate in 45 of 45 "
    r"repaired runs \(no false\s+alarms\),", t)
if old_leg is None:
    raise SystemExit('legend 45/45 not found')
t = t[:old_leg.start()] + (
    "on an identity-confounding control the LDI stays below the 1.645 gate in 45 of 45 runs "
    "(36 of 36 among dosed runs, no false alarms),") + t[old_leg.end():]
rep(
    "while the detector remained non-blind on 45 identity-confounding runs (no false alarms)",
    "while the detector remained non-blind on 45 identity-confounding runs (36 of them dosed; "
    "no false alarms)",
)

# ------------------------------------------- 5. honest-note wording, softened
rep(
    "This is a useful calibration of axis (ii): in-sample τ is a memorization-capacity bound, "
    "not a calibrated leakage measure, which is precisely why the group-level LDI, not τ_in, "
    "is the referee.",
    "In-sample τ is therefore a memorization-capacity bound rather than a calibrated leakage "
    "measure, which is why the group-level LDI, not τ_in, is the referee.",
)

io.open(P, 'w', encoding='utf-8').write(t)
print('part A applied; em-dash:', t.count('\u2014'))
