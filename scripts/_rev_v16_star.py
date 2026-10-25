"""v16: STAR-Methods framework (Key Resources Table, Resource Availability,
Quantification and Statistical Analysis) plus the scientific-wording fixes.

Reads  MRP-ST-Repair_manuscript_Patterns_v15.md
Writes MRP-ST-Repair_manuscript_Patterns_v16.md

Every replacement is asserted to match exactly once, so a rewrap of the
markdown cannot silently drop an edit.
"""
from __future__ import annotations

from pathlib import Path

PAPERS = Path(r"G:\project4_cervix_multimodal\papers\20_MRP-ST-Repair_Patterns")
SRC = PAPERS / "MRP-ST-Repair_manuscript_Patterns_v15.md"
DST = PAPERS / "MRP-ST-Repair_manuscript_Patterns_v16.md"

t = SRC.read_text(encoding="utf-8")
edits: list[tuple[str, str]] = []


def rep(old: str, new: str) -> None:
    assert t.count(old) == 1, f"anchor count {t.count(old)}: {old[:70]!r}"
    edits.append((old, new))


# ---------------------------------------------------------------- 1. Highlights
rep(
    """1. Sibling units re-identify held-out units, so unit-level splits overstate
2. One post-hoc audit grades the leak after training; no new split, no retraining
3. A pre-computed critical retention says whether any repair dose can pay off
4. Passing the gate means leakage is below threshold, not that the group is gone
5. Validated in one domain; two further cohorts test predictions, not utility""",
    """1. Sibling units re-identify held-out units, so unit splits overstate skill
2. One post-hoc audit grades the leak after training; no retraining needed
3. A pre-computed retention bound says if any repair dose can pay off
4. Passing the gate means leakage is below threshold, not that group is gone
5. Validated in one domain; two cohorts test predictions, not repair utility""",
)

# ------------------------------------------- 2. Resource availability subsections
rep(
    "### Resource availability\n\n**Data.** The head-and-neck cohort",
    "### Resource availability\n\n"
    "**Lead contact.** Requests for further information, resources, or code should be "
    "directed to, and will be fulfilled by, the lead contact, Ming Bai (contactable "
    "through the corresponding-author address on the title page).\n\n"
    "**Materials availability.** This study did not generate new unique reagents, cell "
    "lines, or biological materials. Every result derives from previously published "
    "public datasets or from data produced by the released simulator, and no physical "
    "material is available for distribution.\n\n"
    "**Data.** The head-and-neck cohort",
)

rep(
    "released at https://github.com/WorldBMW/cervix-st-multimodal under a tagged "
    "release and archived at Zenodo",
    "released at https://github.com/WorldBMW/cervix-st-multimodal, pinned at "
    "submission to the tagged release "
    "https://github.com/WorldBMW/cervix-st-multimodal/releases/tag/v1.0.0, and "
    "archived at Zenodo",
)

# ------------------------------------------------------- 3. Key Resources Table
KRT = """### Key resources table

**Table 6. Key resources table (STAR Methods).** Every dataset, package and script used to produce the reported numbers, with the version actually run. Accessions are given as deposited; the two UCI cohorts are re-downloaded by the released scripts rather than redistributed.

| Category | Resource | Source | Identifier |
|---|---|---|---|
| Deposited data | Head-and-neck Visium, HPV status (16 sections, 8 versus 8) | Gene Expression Omnibus | GSE268014 (GSM8283897 to GSM8283913) |
| Deposited data | Prostate Visium, tumour versus benign (52 sections, 48 versus 4) | Gene Expression Omnibus | GSE278936 |
| Deposited data | Cervical Visium, ordinal severity (35 sections, 34 donors) | companion study [1]; 10x Genomics public data; GEO | GSE217237 |
| Deposited data | Cervical GeoMx DSP control, per-ROI pathology (186 ROIs, 7 cases) | Gene Expression Omnibus | GSE316098 [44] |
| Deposited data | UCI Human Activity Recognition (grouping variable: subject, G = 30) | UCI Machine Learning Repository | HAR [24,26] |
| Deposited data | UCI Gas Sensor Array Drift (grouping variable: batch, G = 10) | UCI Machine Learning Repository | Gas Sensor Array Drift [25,26] |
| Deposited data | Simulated cohorts (shared-program, identity-confounding, spurious, weak-signal arms) | this paper; released generator, fixed seeds | simulator in the tagged release |
| Software | Python | Python Software Foundation | 3.13.5 |
| Software | numpy | Harris et al. | 2.4.4 |
| Software | pandas | pandas development team | 3.0.6 |
| Software | scipy | Virtanen et al. | 1.15.3 |
| Software | scikit-learn (ridge probe, logistic probe, splits) | Pedregosa et al. | 1.6.1 |
| Software | PyTorch (GAT, GCN, MLP autoencoder, gradient reversal) | Paszke et al. | 2.13 |
| Software | matplotlib (all figures) | Hunter | as pinned in requirements-patterns.txt |
| Software | Audit engine (tau_in, tau_LOO, tau_LGO, sigma_hat, LDI, R) | this paper | scripts/refit_grid_audit.py |
| Software | Cross-domain runner | this paper | scripts/exp_crossdomain_audit.py |
| Software | Unit-resolution ladder | this paper | scripts/exp_unit_ladder_cervical.py |
| Software | Within-group-label control | this paper | scripts/exp_within_group_label_geomx.py |
| Software | Domain-agnostic cohort simulator | this paper | released with the tagged release |
| Software | Manifest-to-result pipeline (one JSON manifest per run) | this paper | released with the tagged release |
| Software | Figure and table build scripts | this paper | scripts/make_figures_patterns.py and companions |
| Other | Compute | AutoDL cloud instance | single NVIDIA GeForce RTX 4080 SUPER, 32 GB |

"""
rep("### Notation, probes, and the instrument", KRT + "### Notation, probes, and the instrument")

# ------------------------------- 4. Quantification and statistical analysis block
rep("### Statistical analysis", "### Quantification and statistical analysis")

rep(
    "we report the series descriptively and draw no inference.",
    "we report the series descriptively and draw no inference.\n\n"
    "**What each n counts.** The letter n denotes two different quantities in this "
    "paper and the two are never pooled. In the real cohorts n counts *groups*, that "
    "is independent donors, patients, or cases, not units: head and neck, n = 16 "
    "sections from 16 patients (8 HPV-positive, 8 HPV-negative); prostate, n = 52 "
    "sections from 52 patients (48 tumour, 4 benign); cervix, n = 35 sections from 34 "
    "donors; GeoMx control, 186 ROIs from n = 7 cases. Each of those cohorts "
    "contributes approximately one unit per group, which is the structural fact the "
    "sibling-unit trap turns on. In simulations n counts *simulated groups* "
    "(4, 8, 16, 32, 64) at a stated number of units per group (1, 2, 4, 8); simulation "
    "n is a design parameter rather than a sample size, and no simulation n is "
    "combined with a cohort n in any reported statistic. In the two non-biological "
    "cohorts the group is a subject (HAR, G = 30) or a measurement batch (gas drift, "
    "G = 10) while the unit is an observation window or a single measurement, with 300 "
    "audited observations per cohort, so group counts and unit counts differ by two "
    "orders of magnitude and are reported separately (Table 5).\n\n"
    "**Seeds.** Two seed families are fixed and recorded separately in every manifest. "
    "Training seeds index model initialisation: three per dose-by-cohort cell "
    "(0, 1, 2; seeds 3 and 4 added at boundary cells, Table S6). The permutation seed "
    "fixes the null: 20261010 throughout, chosen independently of the training seed so "
    "that no null is correlated with a particular fit.\n\n"
    "**Permutation depth.** σ̂ is estimated at B = 2,000 refit permutations, and the "
    "null behind the reported p-value uses the same B. Depth sensitivity was measured "
    "by recomputing the external-cohort nulls at B = 10,000 (Table S4): σ̂ moved by at "
    "most 4.4% and no gate decision changed in 15 external-cohort runs.\n\n"
    "**Definition of σ̂ and of the gate.** σ̂ is the standard deviation, across the B "
    "permutations, of the leave-one-group-out (equivalently leave-one-donor-out) "
    "Kendall τ recomputed with the probe refit inside every permutation. The gate "
    "value 1.645 is the one-sided 5% quantile of the standard normal distribution, "
    "applied to LDI = (τ_LGO − 0.001)/σ̂. The feasibility threshold 2.35 in Proposition "
    "1 is 1.645/c at the reading convention c = 0.7 and is not a calibrated constant of "
    "nature (Table S15).\n\n"
    "**Dispersion.** Every spread reported here is a standard deviation (SD) across "
    "training seeds, with the seed count stated at the point of report. We do not "
    "report standard errors of the mean, because at three seeds an SEM would understate "
    "exactly the spread we are trying to convey. Where a standard error is quoted "
    "(prostate AUROC, SE approximately 0.11 at four positive donors) it is quoted only "
    "to show that the observed difference is not resolvable at that n, and no inference "
    "is drawn from it.\n\n"
    "**Multiplicity.** The dose grid (λ in {0, 0.5, 1, 2, 5}) is a descriptive "
    "operating-characteristics curve, not a family of hypothesis tests. We apply no "
    "multiplicity correction across doses and we report no dose optimum: where a cohort "
    "admits an accepted region we describe it as an operating-point interval carrying "
    "its measured seed spread (prostate: a single operating point).\n\n"
    "**Software.** Python 3.13.5, numpy 2.4.4, pandas 3.0.6, scipy 1.15.3, "
    "scikit-learn 1.6.1, PyTorch 2.13, matplotlib for figures, python-docx for "
    "submission files; versions are pinned in requirements-patterns.txt in the tagged "
    "release.",
)

# ------------------------------------------- 5. Protocol: probe step + null floor
rep(
    "8. **Check that the baseline is above the null before reading an accept verdict.**"
    " The fidelity axis is relative, so where τ_base is indistinguishable from the null"
    " the gate is satisfied almost automatically (2 of 12 dosed cells on the spurious"
    " simulation arm, Table S12). Treat an accepted cell as informative only where"
    " τ_base/σ̂ is itself above 1, and pair the relative gate with an absolute floor;"
    " see the degenerate regime under Proposition 1.\n9. **Read out what survived**",
    "8. **Re-audit with a more expressive probe wherever the deployment is "
    "high-stakes.** LDI quantifies the group identity a *linear* ridge probe can "
    "recover, so a low LDI is evidence of reduced linearly-recoverable leakage and not "
    "a guarantee that no decoder can recover the group. Where a false clean bill of "
    "health is costly, repeat the audit with a kernel-ridge, gradient-boosted, or "
    "multilayer-perceptron probe and report the most permissive reading: disagreement "
    "between a linear and a nonlinear probe is itself a warning flag and should be "
    "reported as such rather than averaged away.\n"
    "9. **Check that the baseline is above the null before reading an accept verdict, "
    "and pair the relative gate with an absolute floor.** The fidelity axis is "
    "relative (τ_LDO ≥ c · τ_base), so where τ_base is indistinguishable from the null "
    "the gate is satisfied almost automatically (2 of 12 dosed cells on the spurious "
    "simulation arm, Table S12). Treat an accepted cell as informative only where "
    "τ_base/σ̂ is itself above 1, and pair the relative condition with an absolute "
    "magnitude floor, τ_LDO ≥ 1.645 σ̂ computed under leave-one-group-out, or a "
    "domain-specific minimum effect size. **Do not trust an accept output obtained "
    "while the baseline association is near null: it is an artifact of the relative "
    "form of the gate, not a finding.** See the degenerate regime under Proposition "
    "1.\n"
    "10. **Read out what survived**",
)

# -------------------------------- 6. Proposition 1: absolute floor, stated firmly
rep(
    "The operational consequence is a rule rather than a caveat:",
    "The operational consequence is a rule rather than a caveat, and we recommend "
    "τ_LDO ≥ 1.645 σ̂ computed under leave-one-group-out as the default absolute floor:",
)
rep(
    "We did not implement such a floor, so every verdict reported in this paper is "
    "conditional on the relative gate alone",
    "We did not implement such a floor, so every verdict reported in this paper is "
    "conditional on the relative gate alone (Protocol step 9)",
)

# ------------------------------------------------ 7. Limitations (ii): two claims
rep(
    "Systematic benchmarking of the untested families against this protocol is the "
    "most direct next study, and we expect its outcome to change the operating "
    "characteristics rather than the theory.",
    "Systematic benchmarking of the untested families against this protocol is the "
    "most direct next study, and we expect its outcome to change the operating "
    "characteristics rather than the theory. Stated as two separate claims so that "
    "neither is over-read: (1) the two failure modes reported above (Group-DRO reduces "
    "the in-sample gap while preserving cross-group leakage; IRM amplifies the group "
    "fingerprint) are empirical observations about those two algorithms on these "
    "cohorts and should not be generalised to deconfounding methods we did not run; "
    "(2) the auditing instrument (LDI, the three-axis acceptance protocol, the "
    "group-level acceptance rule) is operator-agnostic and evaluates the output of "
    "null-space projection, contrastive learning, conditional re-weighting, or any "
    "other paradigm without modification, so systematic benchmarking across those "
    "families is a future extension rather than a requirement for the present "
    "manuscript. We make no claim that the adversarial operator used here outperforms "
    "any other deconfounding approach.",
)

# --------------------------------------------- 8. Limitations (vi): probe boundary
rep(
    "treat disagreement between probe classes as a finding rather than as noise.",
    "treat disagreement between probe classes as a finding rather than as noise. The "
    "two claims should be separated cleanly. The sibling-unit trap, Proposition 1, and "
    "both decision boundaries are structural statements about a channel and a coupling, "
    "and they hold under any probe class. The LDI numbers are statements about linear "
    "recoverability only, and they are the part of the paper that a change of probe "
    "would move. LDI is reported as a measure of linearly recoverable group leakage; it "
    "is not a detector of every form in which group identity can be encoded, and "
    "nothing in the Highlights, the In Brief, or the Summary should be read as claiming "
    "otherwise.",
)

# --------------------------------------- 9. Limitations (vii): reporting discipline
rep(
    "nothing in the paper should be cited as a biological result.",
    "nothing in the paper should be cited as a biological result. Three consequences "
    "follow for how the numbers may be quoted. First, we report no optimal λ anywhere "
    "in this paper: doses are described as an acceptable operating-point interval "
    "carrying its seed spread, and the prostate acceptance is a single operating point "
    "with measured spread rather than a tightly replicated result. Second, the "
    "structural claims of the paper (the sibling-unit trap, Proposition 1, both "
    "decision boundaries) rest on the simulation phase grids, where three seeds per "
    "cell over a 5 by 4 by 2 design supply the resolution the cohorts cannot; the real "
    "cohorts check the instrument on real data and do not power those claims. Third, "
    "the prostate cohort has four benign donors and the head-and-neck cohort sixteen "
    "patients, so no subgroup comparison within either cohort is powered, and none is "
    "reported.",
)

# ------------------------- 10. Cross-domain Results: standing qualifier, stated once
rep(
    "### Cross-domain audit: what reproduces outside the validation domain, and what "
    "does not\n\nThe claim that identity leakage is a data-science problem",
    "### Cross-domain audit: what reproduces outside the validation domain, and what "
    "does not\n\n**Standing qualifier for this section.** Every statement below about "
    "the two non-biological cohorts is read under one qualifier, stated once here so "
    "that it need not be repeated at each mention: both were audited for theoretical "
    "predictions only. Neither has a downstream endpoint, a planted ground truth, or a "
    "domain readout, and neither demonstrates that repair confers practical utility. "
    "What they test is whether the instrument, Proposition 1, and the two decision "
    "boundaries behave outside the validation domain as the theory says they "
    "should.\n\nThe claim that identity leakage is a data-science problem",
)

# ---------------------------------- 11. Discussion transfer: standing qualifier too
rep(
    "### Transferring the framework beyond the validation domain\n\n",
    "### Transferring the framework beyond the validation domain\n\n**Standing "
    "qualifier.** The two audited rows of Table 4 are audited for predictions only: no "
    "downstream endpoint, no planted ground truth, and no demonstration of utility. The "
    "remaining rows are structural mappings and are untested.\n\n",
)

# ----------------------- 12. Three-axis acceptance: the unified non-erasure wording
rep(
    "so a downstream consumer must not assume the group is unrecoverable from the "
    "representation.",
    "so a downstream consumer must not assume the group is unrecoverable from the "
    "representation. Stated in the form used everywhere in this paper: passing the "
    "audit gate means group-dependent leakage has been reduced below a calibrated "
    "threshold; it does not mean group identity is fully unrecoverable, and in our own "
    "experiments group-identity lift remains several-fold above chance after accepted "
    "repair.",
)

# ------------------------------------------ 13. Data availability: tag URL explicit
rep(
    "is released at https://github.com/WorldBMW/cervix-st-multimodal, pinned to a "
    "tagged release at submission",
    "is released at https://github.com/WorldBMW/cervix-st-multimodal, pinned to the "
    "tagged release https://github.com/WorldBMW/cervix-st-multimodal/releases/tag/"
    "v1.0.0",
)

for old, new in edits:
    t = t.replace(old, new)

DST.write_text(t, encoding="utf-8")
print(f"v16 written: {len(edits)} edits, {len(t.split())} words")
