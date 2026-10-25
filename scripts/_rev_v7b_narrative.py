"""v6 -> v7 (part B): narrative contraction for a cross-domain readership.

- Highlights and Summary rewritten as neutral, domain-agnostic assertions.
- The two-unit discussion is reduced to a forward pointer where it first appears;
  the full argument stays where it is load-bearing (the scope condition).
- Defensive passages are shortened; Finding 5 is reframed as a demonstration of
  auditability rather than as a win for the operator.
- Configuration manifest schema and a pinned-release statement are added.
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


# ---------------------------------------------------------------- highlights
rep(
    "1. A calibrated instrument grades leakage and stays non-blind after repair\n"
    "2. Proposition 1: detect-then-accept is infeasible above a pre-computable ratio\n"
    "3. Two decision boundaries predicted repairability in two non-biological cohorts\n"
    "4. In our validation domain repair improved no endpoint; the audit predicted it",
    "1. Group-structured data let a model win by recognising the group, not the target\n"
    "2. A calibrated index grades leakage and stays non-blind after de-identification\n"
    "3. A pre-repair ratio decides whether any dose can satisfy remove-and-preserve\n"
    "4. Where each group has one unit, no accepted repair improved a downstream endpoint",
)

# ------------------------------------------------------------------- summary
new_sum = (
    "When the same person, site, or device contributes many observations, a model can score well "
    "by recognising which group an observation came from rather than the property it should "
    "predict. We call this identity leakage, and we contribute an auditable protocol for deciding "
    "what to do about it. A calibrated index grades label dependence under leave-one-group-out and "
    "is itself tested after repair against controls with known ground truth. A feasibility "
    "condition shows that the natural remove-and-preserve gate is empty above a ratio computable "
    "from the unrepaired baseline, and two decision boundaries say in advance whether repair can "
    "succeed. The repair operator is deliberately standard. One domain is validated end to end; "
    "where each group contributes a single unit the protocol recommends against repair, and no "
    "accepted repair improved a downstream endpoint. Two non-biological cohorts test the "
    "predictions and carry no endpoint."
)
m_sum = re.search(r'(## SUMMARY\s*\n+)(.*?)(\n\n\*\*Keywords)', t, re.S)
if m_sum is None:
    raise SystemExit('SUMMARY block not found')
t = t[:m_sum.start(2)] + new_sum + t[m_sum.end(2):]

# ------------------------------------------- two units: forward pointer only
old_units = (
    "**Two units of analysis, and why we keep them apart.** Every number in this paper belongs to "
    "one of two resolutions, and conflating them produces an apparent contradiction that we want "
    "to remove at the outset. The **representation unit** is the spot. The encoder, the "
    "reconstruction decoder and the adversarial head are all defined per spot, and there are tens "
    "of thousands of spots per cohort: 57,872 spots over 16 sections in the head-and-neck cohort, "
    "a mean of 3,617 per section. Repair acts here, and it is here that donor identity is present "
    "as a fingerprint shared by thousands of observations. The **consumption unit** is the "
    "section. Every statistic we report (τ_in, τ_LDO, the LDI built on it, R, and the "
    "leave-one-donor-out AUROC) is computed on section-mean embeddings, one vector per donor, "
    "because that is the resolution at which a downstream user consumes the representation. "
    "Because each donor contributes essentially one section (cervical 35 sections from 34 donors; "
    "head and neck 16 from 16; prostate 52 from 52), the consumption unit carries one observation "
    "per group, so τ_LOO and τ_LDO are the same statistic by construction and no sibling channel "
    "exists there. The same distinction explains an asymmetry between our two evidence settings: "
    "in the validation domain the audit is read at the consumption unit, whereas in the "
    "cross-domain cohorts of Table 5 the identical statistics are read at the observation level, "
    "where each group contributes hundreds of units and τ_LOO and τ_LGO separate (Figure 5B). We "
    "return to the distinction where it is load-bearing, in the scope condition."
)
new_units = (
    "**Two units of analysis.** Every number in this paper belongs to one of two resolutions. The "
    "**representation unit** is the spot: the encoder, the reconstruction decoder and the "
    "adversarial head are defined per spot, and repair acts there (57,872 spots over 16 sections "
    "in the head-and-neck cohort, a mean of 3,617 per section). The **consumption unit** is the "
    "section: every statistic we report is computed on section-mean embeddings, one vector per "
    "donor, because that is the resolution at which a downstream user consumes the representation. "
    "The distinction becomes load-bearing at one point only, the scope condition in which we "
    "report that no accepted repair improved a downstream endpoint, and we develop it there rather "
    "than here."
)
rep(old_units, new_units)

# ------------------------------------------------- theory packaging, trimmed
rep(
    "**How much theory this is.** The argument above is a one-line monotonicity check. We label it "
    "a proposition only so that it can be cited, we have removed the corollary numbering that "
    "would have suggested more depth than is there, and we ask readers to judge it on its reading "
    "rather than on its derivation: the feasibility of a remove-and-preserve criterion is decided "
    "by a ratio that can be estimated from the unrepaired baseline, which turns the choice of "
    "acceptance protocol into a checkable precondition instead of a tuning decision.",
    "**How much theory this is.** The argument above is a monotonicity check, stated as a "
    "proposition only so that it can be cited. What matters is its reading: the feasibility of a "
    "remove-and-preserve criterion is decided by a ratio estimable from the unrepaired baseline, "
    "which turns the choice of acceptance protocol into a checkable precondition instead of a "
    "tuning decision.",
)

# --------------------------------------------------- baseline defence, trimmed
rep(
    "**Why there is no off-the-shelf adversarial debiasing baseline in this table.** A natural "
    "expectation is a comparison against a published adversarial removal method. Our operator *is* "
    "that method: a gradient-reversal layer,[3,4] a cross-entropy adversary on the grouping "
    "variable, and a scalar dose λ, which is the canonical adversarial attribute-removal "
    "design.[27–29] Adding a second instance of it would compare our acceptance protocol against "
    "itself, and it would be scored on exactly the operating characteristics that the published "
    "versions do not report. What can be compared, and is compared here, are methods that pursue "
    "the same goal through a different objective, reweighting (Group-DRO) and invariance (IRM), "
    "where the question \"did label dependence actually go\" is the question the instrument exists "
    "to answer and the one neither method ships with. The gap this leaves is real and is stated in "
    "the limitations: we did not benchmark non-adversarial removal families, and the operating "
    "characteristics of finding 1 should be re-measured for any of them.",
    "**On baselines.** A natural expectation is a comparison against a published adversarial "
    "removal method, but our operator *is* that method: a gradient-reversal layer,[3,4] a "
    "cross-entropy adversary on the grouping variable and a scalar dose λ is the canonical "
    "design,[27–29] so a second instance of it would compare our acceptance protocol against "
    "itself. What can be compared are methods that pursue the same goal through a different "
    "objective, reweighting (Group-DRO) and invariance (IRM). The gap this leaves is real and is "
    "stated in the limitations: non-adversarial removal families were not benchmarked, and the "
    "operating characteristics of finding 1 would need re-measuring for any of them.",
)

# ------------------------------------------- finding 5 reframed as discrim.
rep(
    "Only the adversarial repair both preserves shared signal and eliminates cross-group leakage. "
    "Both patterns replicate on a second real cohort. A practical corollary: in-sample metrics are "
    "not sufficient for leakage-repair acceptance.",
    "The point of the comparison is not that our operator wins it: the operator is a standard "
    "adversarial head, and any removal method that clears the group-level statistic would score "
    "the same. It is that only an instrument graded at the group level separates these three "
    "outcomes at all, since on the in-sample gap that Group-DRO optimises the methods are "
    "indistinguishable. Both patterns replicate on a second real cohort. A practical corollary: "
    "in-sample metrics are not sufficient for leakage-repair acceptance.",
)

# --------------------------------------------------------- manifest schema
rep(
    "All instrument quantities (τ_in, τ_LOO, τ_LGO, σ̂ at B = 2,000 seed 20261010, LDI, R) are "
    "computed by the same code used for the transcriptomic cohorts.",
    "All instrument quantities (τ_in, τ_LOO, τ_LGO, σ̂ at B = 2,000 seed 20261010, LDI, R) are "
    "computed by the same code used for the transcriptomic cohorts.\n\n"
    "### Configuration manifests and reproducibility\n\n"
    "Every run reported here, simulated or real, is produced by a script that reads one JSON "
    "configuration manifest and writes one JSON result file; no analysis step accepts an "
    "interactive argument that is not recorded in the manifest. A manifest records: `cohort` "
    "(source identifier, and for simulations the full generator parameters: planted amplitude, "
    "identity offset, and whether the planted direction is shared or spurious); `split` (grouping "
    "variable, split scheme, number of groups and units per group); `label` (target and class "
    "sizes); `encoder` (backbone, layer widths, neighbourhood size); `objective` (method, dose λ "
    "or its Group-DRO or IRM equivalent, gradient-reversal schedule, warm-up); `seed` (training "
    "seed, recorded separately from the permutation seed); `probe` (probe family and "
    "regularisation); `audit` (permutation count B for σ̂, permutation count for p, null floor "
    "τ_⊥, gate value, retained fraction c); and `outputs` (paths of the result file and of any "
    "derived figure data). Manifests are archived together with the results they produced, so "
    "every number in every table is traceable to one manifest and one result file. The archive "
    "also contains a checksum index mapping each table row and figure panel to the manifest and "
    "result file from which it was computed, which is the artefact a reader needs in order to "
    "re-derive any reported value without correspondence with the authors.",
)

# --------------------------------------------------------- data availability
rep(
    "is released at https://github.com/WorldBMW/cervix-st-multimodal and archived at Zenodo "
    "(DOI to be minted at submission; the GitHub repository above is the accessible interim "
    "location). The cervical cohort is as described in the companion study.[1]",
    "is released at https://github.com/WorldBMW/cervix-st-multimodal, pinned to a tagged release "
    "at submission, and archived at Zenodo (DOI: TO BE INSERTED BEFORE SUBMISSION; the tagged "
    "GitHub release is the accessible interim location). Both the tag and the DOI are frozen "
    "before submission so that the archived state matches the reported numbers exactly. The "
    "cervical cohort is as described in the companion study.[1]",
)
rep(
    "All training, simulation, audit, aggregation, and analysis scripts, with exact seeds and "
    "configuration manifests (including the cohort simulator), are released at "
    "https://github.com/WorldBMW/cervix-st-multimodal and archived at Zenodo (DOI to be minted at "
    "submission; the GitHub repository above is the accessible interim location).",
    "All training, simulation, audit, aggregation, and analysis scripts, with exact seeds and "
    "configuration manifests (including the cohort simulator), are released at "
    "https://github.com/WorldBMW/cervix-st-multimodal under a tagged release and archived at "
    "Zenodo (DOI: TO BE INSERTED BEFORE SUBMISSION).",
)

io.open(P, 'w', encoding='utf-8').write(t)
print('part B applied; em-dash:', t.count('\u2014'))
