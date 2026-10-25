# -*- coding: utf-8 -*-
"""v15: 三级证据分层约束 + Limitations 强化 + Prop1/Protocol 退化警告 + 统一措辞。"""
from pathlib import Path

D = Path(r"G:\project4_cervix_multimodal\papers\20_MRP-ST-Repair_Patterns")
SRC = D / "MRP-ST-Repair_manuscript_Patterns_v14.md"
DST = D / "MRP-ST-Repair_manuscript_Patterns_v15.md"
t = SRC.read_text(encoding="utf-8")

REPS = []


def rep(old, new, tag):
    REPS.append((old, new, tag))


# ---------------------------------------------------------------- 1. HIGHLIGHTS
rep(
    """1. Sibling units let held-out units be re-identified, so unit-level splits overstate
2. One post-hoc audit grades the leak after training, with no new split or retraining
3. The index is itself tested after repair against controls with known ground truth
4. Where each group has one unit, no accepted repair improved a downstream endpoint""",
    """1. Sibling units re-identify held-out units, so unit-level splits overstate
2. One post-hoc audit grades the leak after training; no new split, no retraining
3. A pre-computed critical retention says whether any repair dose can pay off
4. Passing the gate means leakage is below threshold, not that the group is gone
5. Validated in one domain only; two more audit predictions, no endpoints""",
    "highlights",
)

# ---------------------------------------------------------------- 2. IN BRIEF
rep(
    """Many datasets are group-structured, so a model can win by recognising the group rather than the target property. Bai and colleagues show that unit-level cross-validation hides this, and supply an auditable instrument: a calibrated index, a rule for the split, and boundaries saying in advance whether repair can pay.""",
    """Many datasets are group-structured, so a model can win by recognising the group rather than the target property. Bai and colleagues show that unit-level cross-validation hides this and supply an auditable instrument: a calibrated index, a rule for the split, and boundaries saying in advance whether repair can pay. The loop is validated end to end in spatial transcriptomics alone; two non-biological cohorts audit its predictions only, six further domains are untested mappings, and no accepted repair improved a downstream endpoint.""",
    "in-brief",
)

# ---------------------------------------------------------------- 3. SUMMARY
rep(
    """When the same person, site, or device contributes many observations, a model can score well by recognising which group an observation came from rather than the property it should predict. We call this identity leakage, and our first result is about measuring it: whenever a group contributes several units, unit-level cross-validation stays at ceiling while group-level holdout collapses, because held-out units are re-identified through their siblings. A split at the wrong level is therefore optimistic. Around it, an auditable protocol: a calibrated index grading label dependence under leave-one-group-out, itself tested after repair against controls with known ground truth; a condition deciding in advance whether any dose can both remove identity and preserve signal; and two boundaries saying which cohorts are repairable. The operator is deliberately standard. One domain is validated end to end; where a group contributes one unit it recommends against repair, and no accepted repair improved an endpoint.""",
    """When the same person, site, or device contributes many observations, a model can score well by recognising the group rather than the property it should predict. We call this identity leakage. Whenever a group contributes several units, unit-level cross-validation stays at ceiling while group-level holdout collapses: held-out units are re-identified through siblings. Around this we build an auditable instrument: a calibrated index of label dependence under leave-one-group-out, tested after repair on controls with known ground truth; a pre-computed condition saying whether any dose can remove identity and keep signal; and two boundaries saying which cohorts are repairable. The repair operator is deliberately standard and we claim no superiority for it. Validation is end-to-end in spatial transcriptomics only; two non-biological cohorts audit predictions, and the rest are untested mappings. Where each group contributes one unit, no accepted repair improved a downstream endpoint, a regime the framework predicts in advance.""",
    "summary",
)

# ---------------------------------------------------------------- 4. GRAPHICAL ABSTRACT
old_ga_start = "**Graphical abstract.** The figure has three bands"
i0 = t.index(old_ga_start)
i1 = t.index("---", i0)
old_ga = t[i0:i1].rstrip()
new_ga = """**Graphical abstract.** Three bands, and the third is part of the argument rather than decoration. *(1) The problem.* Four groups (person, site, speaker, subject, each labelled only as G) contribute several observations apiece, so the observations are not exchangeable. A model fits the training set and collapses under leave-one-group-out: it recognised the group, not the target property. Split at the unit level the collapse is invisible, because a held-out unit is re-identified through the siblings its group left in training. *(2) The auditable loop.* Split at the group level; detect with the calibrated index under leave-one-group-out; pre-compute the signal-to-null ratio and test it against the precondition 1.645/c to learn whether any dose can remove identity and preserve signal; repair at training time at dose \u03bb; re-audit on three axes. Acceptance is a verdict the instrument produces, and rejection can be predicted before a dose is chosen. The two decision boundaries sit beneath the loop because they determine its two failure modes: label\u2013identity coupling decides whether a repairable point exists at all, and group count decides whether the signal survives the dose needed to remove identity. *(3) Three levels of evidence, drawn in the band and not interchangeable.* *Validated*: the complete loop, in one domain only, spatial transcriptomics, three real cohorts plus a simulator with known ground truth. *Audited, predictions only*: two non-biological cohorts (wearable activity recognition, chemical gas-sensor drift) on which the instrument and both boundaries were run against real data but which carry no endpoint, no planted control and no domain readout, so they test whether the theory's predictions hold and not whether repair delivers utility. *Not tested*: the six remaining rows of Table 4, structural mappings only, for which we claim no transfer. The band is placed in the figure deliberately, so that the domain in which the method was developed appears next to the domains in which nothing has been shown. Every claim in the paper carries the tag of the band it belongs to."""
rep(old_ga, new_ga, "graphical-abstract")

# ---------------------------------------------------------------- 5. BIGGER PICTURE
rep(
    """This paper does not offer a better model. It offers an instrument:""",
    """This paper does not offer a better model, and it does not offer a better deconfounding operator: the repair operator used below is a standard adversarial head, chosen deliberately, and we claim no superiority for it over Group-DRO, IRM, null-space projection, contrastive or reweighting methods. What it offers is an instrument:""",
    "bigger-picture",
)

# ---------------------------------------------------------------- 6. group-count placement: Results bullet
rep(
    """On a two-dimensional phase grid, repair is infeasible below a group-count threshold that lies between 16 and 32 groups at reference signal and moves rightward as signal weakens (verified over five seeds). The consequence for practice is a precondition rather than a guarantee: repair needs a group budget, and the budget grows as the signal weakens.""",
    """On a two-dimensional phase grid, repair is infeasible below a group-count threshold that lies between 16 and 32 groups at reference signal and moves rightward as signal weakens (verified over five seeds). That interval is a placement for this configuration and not a transferable cut-off: gas drift has G = 10, below it, and still retained 0.89\u20130.93 of its group-level transfer under repair (Table 5). The consequence for practice is a precondition rather than a guarantee: repair needs a group budget, the budget grows as the signal weakens, and the budget has to be re-derived on the user's own simulator rather than quoted from ours.""",
    "results-boundaryII-bullet",
)

# ---------------------------------------------------------------- 7. group-count placement: Results detail
rep(
    """no dose in any cell dropped the cell mean below 0.86 (all cell means \u2265 0.98 at n = 64): the feasibility boundary lies between 16 and 32 groups (five-seed verification at the boundary cells in Table S6).""",
    """no dose in any cell dropped the cell mean below 0.86 (all cell means \u2265 0.98 at n = 64): the feasibility boundary lies between 16 and 32 groups in this configuration (five-seed verification at the boundary cells in Table S6). The interval is a placement, not a constant; it moves with encoder capacity, noise, program\u2013identity alignment and probe class, and it should be re-derived rather than quoted (Limitations (iii)).""",
    "results-boundaryII-detail",
)

rep(
    """shows that strong repair is seed-unstable at this group count, matching the 16\u201332 boundary;""",
    """shows that strong repair is seed-unstable at this group count, matching the group-count boundary as placed in this configuration (between 16 and 32 groups here, and not a transferable cut-off);""",
    "results-scope-boundary-mention",
)

# ---------------------------------------------------------------- 8. On baselines: instrument independence
rep(
    """The gap this leaves is real and is stated in the limitations: non-adversarial removal families were not benchmarked, and the operating characteristics of finding 1 would need re-measuring for any of them.""",
    """The gap this leaves is real and is stated in the limitations: non-adversarial removal families were not benchmarked, and the operating characteristics of finding 1 would need re-measuring for any of them. Two things about that gap should be kept straight. The instrument does not depend on the operator: LDI, the three axes and the group-level acceptance rule read a representation rather than a training objective, so the same protocol can be run on the output of any deconfounding method, including the ones not benchmarked here. And the two failure modes we report are properties of two specific methods, not a law about all of them: whether null-space projection, contrastive objectives or conditional reweighting fail in the same way is unknown.""",
    "on-baselines",
)

# ---------------------------------------------------------------- 9. partial removal in Results
rep(
    """Acceptance is then a statement about *which kind* of label dependence remains, not a demand that all label dependence vanish.""",
    """Acceptance is then a statement about *which kind* of label dependence remains, not a demand that all label dependence vanish. This is also the sense in which the word "repaired" is used throughout: passing the gate means the measured group dependence has been brought below a calibrated threshold, not that group identity has been erased. On the audited cohorts repair lowered group-identity lift from 10.0x to 5.4x chance (wearable) and from 9.2x to 7.2x (gas sensor), and it cleared only about 12% of the planted in-sample fingerprint on the identity-confounding control, so a downstream consumer must not assume the group is unrecoverable from the representation.""",
    "results-partial-removal",
)

# ---------------------------------------------------------------- 10. Discussion: instrument not operator
rep(
    """Because the failure modes are diagnosable from the sign and direction of the cross-group statistic (gap down, LDI positive; invariance claimed, LDI up), the taxonomy is usable on any method, including ones not tested here.""",
    """Because the failure modes are diagnosable from the sign and direction of the cross-group statistic (gap down, LDI positive; invariance claimed, LDI up), the taxonomy is usable on any method, including ones not tested here. What we are claiming should be stated exactly, because the comparison invites a larger reading than we intend. The two failure modes are properties of Group-DRO and IRM, and we do not generalise them: null-space projection,[32] contrastive cross-group objectives and conditional reweighting were not benchmarked, and any of them might trade fidelity against leakage differently. The deliverable of this paper is the auditing protocol, not the repair operator; LDI, the three axes and the group-level acceptance rule can be run on the output of whatever deconfounding method a practitioner already uses, because they read the representation rather than the objective that produced it. We therefore make no claim that the adversarial operator used here outperforms other deconfounding methods, and we would regard a study that ran this protocol across those families as a direct extension rather than as a competitor.""",
    "discussion-instrument-not-operator",
)

# ---------------------------------------------------------------- 11. Proposition 1: degenerate regime
rep(
    """**Protocol.** Fit the unrepaired baseline once and read off c_crit = 1.645 \u03c3\u0302/\u03c4_base (equivalently, form \u03c4_base/\u03c3\u0302 and read it against 1.645/c). Where the deployer requires more retention than the cohort admits, adopt the three-axis protocol instead of searching for a dose. Report c_crit and let the deployer supply c; do not tune c to obtain a preferred verdict. Observed ratios: shared-program simulation 5.8; cervical \u2248 2.4; head and neck 2.18; prostate \u2248 2.0 (Table 1).""",
    """**Protocol.** Fit the unrepaired baseline once and read off c_crit = 1.645 \u03c3\u0302/\u03c4_base (equivalently, form \u03c4_base/\u03c3\u0302 and read it against 1.645/c). Where the deployer requires more retention than the cohort admits, adopt the three-axis protocol instead of searching for a dose. Report c_crit and let the deployer supply c; do not tune c to obtain a preferred verdict. Observed ratios: shared-program simulation 5.8; cervical \u2248 2.4; head and neck 2.18; prostate \u2248 2.0 (Table 1).

**Degenerate regime, to be read before any accept verdict is used.** The fidelity axis is relative (\u03c4_LDO \u2265 c \u00b7 \u03c4_base), so where \u03c4_base is itself indistinguishable from the permutation null the gate is satisfied almost automatically, and an "accepted" verdict then carries no information: on the spurious simulation arm, where \u03c4_base/\u03c3\u0302 was 0.35 and 0.52 under the two backbones, 2 of 12 dosed cells passed the dual gate on each (Table S12). The proposition is not wrong there; it is a statement about the existence of a feasible operating point and not about whether that point is worth using, and the two come apart precisely at this end. The operational consequence is a rule rather than a caveat: *an accept verdict is interpretable only where the baseline association is detectably above the null scale*, and the relative gate should be paired with an absolute floor (for example \u03c4_LDO \u2265 1.645 \u03c3\u0302 computed under leave-one-group-out, or a domain-specific minimum effect size). We did not implement such a floor, so every verdict reported in this paper is conditional on the relative gate alone, and the cells accepted on the spurious arm should be read as illustrations of the degeneracy rather than as evidence that repair helped.""",
    "prop1-degenerate-regime",
)

# ---------------------------------------------------------------- 12. Practitioner's protocol
rep(
    """6. **Accept at the group level only**, and require the instrument to remain non-blind on your own controls.
7. **Read out what survived** through the decoder or its domain equivalent, and check it against external knowledge: what passes an audited repair should be recognizable, not arbitrary.""",
    """6. **Accept at the group level only**, and require the instrument to remain non-blind on your own controls.
7. **Do not read acceptance as erasure.** Passing the gate means the measured group dependence has been brought below a calibrated threshold, not that group identity is unrecoverable. Repair lowered group-identity lift from 10.0x to 5.4x chance on the wearable cohort and from 9.2x to 7.2x on gas-sensor drift, and cleared only about 12% of a planted in-sample fingerprint, so no downstream use should assume the group cannot be recovered from the representation.
8. **Check that the baseline is above the null before reading an accept verdict.** The fidelity axis is relative, so where \u03c4_base is indistinguishable from the null the gate is satisfied almost automatically (2 of 12 dosed cells on the spurious simulation arm, Table S12). Treat an accepted cell as informative only where \u03c4_base/\u03c3\u0302 is itself above 1, and pair the relative gate with an absolute floor; see the degenerate regime under Proposition 1.
9. **Read out what survived** through the decoder or its domain equivalent, and check it against external knowledge: what passes an audited repair should be recognizable, not arbitrary.""",
    "protocol-steps",
)

# ---------------------------------------------------------------- 13. Limitations (ii)
rep(
    """This is a limitation of the empirical half of the paper only.""",
    """This is a limitation of the empirical half of the paper only. Two clarifications bound how the comparison may be read. First, the instrument does not depend on the operator: LDI, the three axes and the group-level acceptance rule read a representation rather than a training objective, so the same protocol can be run on the output of any deconfounding method, including every family listed above, and a practitioner who adopts one of them loses nothing from this paper. Second, we claim no superiority for the adversarial operator over those families; the head-to-head result is a demonstration that an auditable instrument discriminates between methods that are indistinguishable in-sample, not a ranking of removal methods. Systematic benchmarking of the untested families against this protocol is the most direct next study, and we expect its outcome to change the operating characteristics rather than the theory.""",
    "limitations-ii",
)

# ---------------------------------------------------------------- 14. Limitations (vi) linear probe
rep(
    """Detecting leakage that is only recoverable by a nonlinear probe is outside what we have validated.""",
    """What this bounds is specific and worth stating plainly, because it is the constraint a referee should press hardest. LDI measures the group identity that a *linear* readout can recover from the representation. Where an encoder stores group identity in a form only a nonlinear probe can decode (a manifold that is not linearly separable in z, an interaction between latent dimensions, a code identifiable only conditionally on the label), the linear probe returns a small \u03c4, the audit reports little leakage, and a sufficiently expressive decoder still recovers the group. We did not test nonlinear probes (kernel ridge, gradient-boosted, or multilayer-perceptron probes) on any cohort, so we cannot give the size of this blind spot, only that it exists and that it is a property of the probe rather than of the argument: the sibling-unit trap, the two boundaries and Proposition 1 are statements about a channel and a coupling, and they hold whatever probe is used to read them, whereas every LDI number in this paper is a statement about linear recoverability and should be quoted as such. The practical consequence is that a low LDI is evidence, not a guarantee, and a practitioner who needs a stronger one should re-run the audit with the most expressive probe their deployment could plausibly apply and treat disagreement between probe classes as a finding rather than as noise. The permutation null carries a milder version of the same caveat: it is estimated by refitting the same probe on permuted labels, so it scales with the probe automatically, which is why the ratio is comparable across cohorts and domains at a fixed unit definition and not across unit definitions of the same data (Table S16).""",
    "limitations-vi",
)

# ---------------------------------------------------------------- 15. Limitations (vii) statistics
rep(
    """the perfect-generalization point observed in the non-hardened replication (\u03c4 at ceiling, the LDI gate exceeded only by a rebound) invites interpretation but is not resolved at this replication.""",
    """the perfect-generalization point observed in the non-hardened replication (\u03c4 at ceiling, the LDI gate exceeded only by a rebound) invites interpretation but is not resolved at this replication. The cohort sizes are fixed by what is publicly available for these modalities (16, 52 and 35 sections; 7 cases in the GeoMx control); we did not select them, and we did not add cohorts to reach a power target, so the resolution of the real-cohort results is what these data support and no more. Where a conclusion needs resolution the data cannot supply, we say so at the point of the claim rather than in aggregate: the prostate acceptance is graded as a single operating point with measured spread rather than as a replicated acceptance, and the cervical endpoint is described as seed-unstable at \u03bb = 2. The simulations supply the power the cohorts cannot: three seeds per cell over a five-by-four-by-two phase grid, and every statement about the existence and the placement of the two boundaries rests on those grids rather than on the clinical cells. We also delimit what the biological results are for: the gene-direction readouts and the HPV and tumour-provenance associations are checks that the instrument returns interpretable verdicts on real data. They are not new biological findings, they are not powered to be, and nothing in the paper should be cited as a biological result.""",
    "limitations-vii",
)

# ---------------------------------------------------------------- 16. Figure 3 legend
rep(
    """group-count-robust at \u03bb = 0, whereas the repair-damage boundary lies between 16 and 32 groups at amplitude
1.0 and between 32 and 64 at amplitude 0.3.""",
    """group-count-robust at \u03bb = 0, whereas the repair-damage boundary lies between 16 and 32 groups at amplitude
1.0 and between 32 and 64 at amplitude 0.3 (placements for this configuration, not transferable cut-offs; gas
drift has G = 10 and still retains 0.89\u20130.93 of its group-level transfer under repair, Table 5).""",
    "fig3-legend",
)

# ---------------------------------------------------------------- apply
for old, new, tag in REPS:
    n = t.count(old)
    assert n == 1, f"[{tag}] anchor count = {n}"
    t = t.replace(old, new)
    print(f"ok  {tag}")

DST.write_text(t, encoding="utf-8")
print("written:", DST)

# ---------------------------------------------------------------- checks
lines = t.split("\n")
i = lines.index("## HIGHLIGHTS")
print("\n--- highlights ---")
for l in lines[i + 1 : i + 10]:
    if l.strip().startswith(tuple("12345")):
        print(f"{len(l.strip()):3d}  {l.strip()}")
    elif l.strip().startswith("##"):
        break
j = lines.index("## IN BRIEF")
k = lines.index("## SUMMARY")
print("\nin-brief words:", len(" ".join(lines[j + 1 : k]).split()))
k2 = lines.index("## GRAPHICAL ABSTRACT")
s = " ".join(lines[k + 1 : k2]).replace("## SUMMARY", "").strip()
print("summary words:", len(s.split()))
