"""Revision v5: reposition to instrument/theory/boundaries, reconcile units, add citations."""
import io, os, re, sys

P = 'MRP-ST-Repair_manuscript_Patterns_v5.md'
txt = io.open(P, encoding='utf-8').read()

REPS = []

# ---------------- CRITICAL 1: reposition (title / highlights / in brief / summary) ----------------
REPS.append((
"# Auditable repair of identity leakage in group-structured data: theory, decision boundaries, and validation in spatial transcriptomics",
"# An auditable instrument for identity leakage in group-structured data: feasibility theory, decision boundaries, and validation in spatial transcriptomics"
))

REPS.append((
"""1. Identity leakage is a general failure mode of group-structured data, not one field
2. Post-hoc de-identification removes signal with the leak; repair must be in training
3. Proposition 1: detect-then-accept is infeasible above a pre-computable ratio
4. Two decision boundaries predict repairability, tested in two non-biological cohorts
5. Auditability, not accuracy: Group-DRO and IRM fail in diagnosable ways""",
"""1. A calibrated instrument grades leakage and stays non-blind after repair
2. Proposition 1: detect-then-accept is infeasible above a pre-computable ratio
3. Two decision boundaries predicted repairability in two non-biological cohorts
4. In our validation domain repair improved no endpoint; the audit predicted it"""
))

REPS.append((
"""Most datasets are group-structured: patients, speakers, sites or subjects each contribute many observations. A model can then win by recognising the group instead of the target property — identity leakage. We treat this as a general data-science failure mode and supply an auditable repair loop: a training-time operator, a calibrated acceptance protocol, a feasibility theory, and two decision boundaries that say in advance whether repair can work. Spatial transcriptomics is the case in which the full loop is validated; two non-biological cohorts test whether the theory's predictions hold outside it.""",
"""Many datasets are group-structured, so a model can win by recognising the group rather than the target property. Bai and colleagues provide an auditable instrument for this identity leakage: a calibrated index, a feasibility condition, and two boundaries saying in advance whether repair can pay."""
))

REPS.append((
"""When the same person, site, or device contributes many observations, a model can succeed by recognising which group an observation came from rather than predicting the property it is meant to predict. We call this identity leakage, a general failure mode of group-structured data. Detection alone leaves practitioners without a remedy: cleaning a trained model afterwards removes the transferable signal with the leak. We present an auditable training-time adversarial repair framework with a three-axis acceptance protocol, and prove that the natural "detect-then-accept" gate is feasible only below a signal-to-null ratio computable from the unrepaired model (Proposition 1). Two decision boundaries — label–identity coupling, and a group-count threshold — tell a practitioner in advance whether repair can succeed. The framework is validated end-to-end in one domain, spatial transcriptomics; its predictions are tested on two non-biological cohorts, and its applicability to further domains is structural, not demonstrated.""",
"""When the same person, site, or device contributes many observations, a model can succeed by recognising the group an observation came from rather than the property it should predict. We call this identity leakage, a general failure mode of group-structured data, and we supply an auditable instrument for it. A calibrated index measures label dependence under leave-one-group-out and is tested on controls with known ground truth after repair. A feasibility condition shows that the natural detect-then-accept gate is empty above a signal-to-null ratio computable before any repair is run, and two decision boundaries say in advance whether repair can succeed. A standard adversarial operator instantiates the repair; the instrument, the condition and the boundaries are the contribution. The framework is validated end-to-end in spatial transcriptomics, where its own audit predicts that repair will not improve endpoints. Predictions are tested on two non-biological cohorts; wider applicability is structural."""
))

# ---------------- MINOR 8 / structure: add BIGGER PICTURE (Patterns requirement) ----------------
REPS.append((
"""---

## INTRODUCTION""",
"""---

## BIGGER PICTURE

Most datasets that scientists actually analyse are not collections of independent measurements. They are collections of clusters: one patient contributes several tissue sections, one hospital contributes many scans, one speaker contributes many utterances, one monitoring station contributes thousands of readings. Standard practice treats these measurements as exchangeable and splits them at random, which quietly keeps members of the same cluster on both sides of the split. A model can then score well by recognising which cluster a measurement came from rather than predicting the property the scientist cares about, and it will report excellent held-out performance while collapsing on any cluster it has not seen. We call this identity leakage.

Three features make it worth naming. It is invisible to the metrics that are normally reported, so it is usually discovered as a reproducibility failure rather than as a mechanism. It is a property of how the data were collected rather than of any model, so no amount of model tuning removes it. And the cluster is frequently a person or an institution, so a model that reads the cluster performs unevenly across the people it was trained on, which makes the failure a fairness problem as well as an accuracy one.

This paper does not offer a better model. It offers an instrument: a calibrated statistic that asks how much of a model's reported performance survives removal of the cluster, together with a test of whether the instrument itself still works once a repair has been applied. With it come a feasibility condition and two decision boundaries that let a practitioner decide, before spending compute, whether attempting a repair is worth attempting at all, and one worked case in which the answer the instrument returns is that it is not. The instrument is deliberately cheap to run: it needs a recorded grouping variable, a label, and a linear probe.

## INTRODUCTION"""
))

# ---------------- MAJOR 4: adversarial attribute-removal literature + difference axes ----------------
REPS.append((
"""The nearest prior work each solves a neighbouring problem. Batch- and patient-robust contrastive encoders produce group-consistent representations but provide no leakage metric, no calibrated acceptance criterion, and no operating characteristics.""",
"""Adversarial removal of an attribute from a learned representation is a mature idea, and we place ourselves inside that literature rather than beside it. Censoring representations with an adversary,[27] controllable invariance through adversarial feature learning,[28] adversarially fair and transferable representations,[29] and the domain-adversarial machinery we build on[3,4] all attach a predictor to a representation and train the encoder to make that predictor fail. Our repair operator is deliberately an instance of this standard design: a group-identity classifier attached through a gradient-reversal layer. We claim no novelty for it, and we say so here because the alternative reading, that this paper proposes a new debiasing method, would misdescribe the contribution. The reason is that this literature has also established, repeatedly, that a defeated adversary is not evidence of removal: attributes that an adversary drove to chance during training remain recoverable by a post-hoc classifier trained on the same representation,[30] and the same gap has been reported for explicit bias removal in image embeddings[31] and for iterative nullspace projection.[32] What is missing is therefore not another operator but an instrument: something that asks, after any removal attempt, whether what remains still transfers across groups and whether it exceeds what permutation alone would produce. Our contributions sit at exactly that point, and they are properties of the audit rather than of the adversary. The consequence appears inside our own results below: on the simulated identity-confounding control the planted fingerprint was cleared only partially, and in the two cross-domain cohorts group identity remained five to eight times more recoverable than chance after repair. We read both as the gap of ref [30] reproduced by our own operator, which is precisely why the acceptance decision is delegated to an instrument rather than to the adversary's loss.

The nearest prior work each solves a neighbouring problem. Batch- and patient-robust contrastive encoders produce group-consistent representations but provide no leakage metric, no calibrated acceptance criterion, and no operating characteristics."""
))

REPS.append((
"""Batch-correction and alignment tools (Harmony,[12] conditional generative models,[13] spatial-alignment methods) align distributions across batches, which is orthogonal to removing label dependence nested *within* groups. Domain-adversarial training[3,4] is the closest machinery to ours, but it is used to transfer across domains, not to remove a group identity that is confounded with the label inside a single training set. Group-disjoint splitting[8] is a preventive practice, not a remediation of an already-trained model.""",
"""Batch-correction and alignment tools (Harmony,[12] conditional generative models,[13] spatial-alignment methods) align distributions across batches, which is orthogonal to removing label dependence nested *within* groups; the adversarial members of that family (iMAP,[33] SCIDRL,[34] DAVAE[35]) use the same gradient-reversal machinery as our operator but optimise cross-batch mixing and are scored by integration metrics such as batch entropy and the adjusted Rand index, not by a calibrated group-level label-dependence statistic. Domain-adversarial training[3,4] is the closest machinery to ours, but it is used to transfer across domains, not to remove a group identity that is confounded with the label inside a single training set. Group-disjoint splitting[8] is a preventive practice, not a remediation of an already-trained model. In fairness research, adversarial and constrained objectives learn representations independent of a sensitive attribute,[27–29,36,37] and the fairness–accuracy trade-offs they navigate are the same shape as the one our feasibility condition makes explicit; the surveys of that literature[21,38] document the trade-off, whereas our contribution is the pre-computable diagnosis of when it has no feasible point."""
))

REPS.append((
"""This paper contributes an **auditable repair framework for identity leakage** — an operator, an acceptance protocol, a feasibility theory, and two decision boundaries — together with its instantiation and validation in one application domain.""",
"""This paper contributes an **auditable instrument for identity leakage** — a calibrated statistic with measured operating characteristics, an acceptance protocol, a feasibility condition, and two decision boundaries — together with a repair operator that instantiates it and a validation of the whole loop in one application domain."""
))

# ---------------- CRITICAL 1: re-order contribution list ----------------
REPS.append((
"""1. **A training-time repair operator with measured operating characteristics.** A group-adversarial operator is trained jointly with the encoder through a gradient-reversal layer,[3,4] and the same calibrated instrument used for detection is repurposed as an acceptance referee. Across 75 positive-control runs the shared, group-transferable program survived every dose, while the detector remained non-blind on 45 identity-confounding runs (no false alarms).""",
"""1. **A calibrated instrument with measured operating characteristics, and a standard operator for it to grade.** The label-dependence index grades a model under leave-one-group-out against its own refit permutation null, and the instrument is itself tested on controls with known ground truth: across 75 positive-control runs the shared, group-transferable program survived every dose, while the detector remained non-blind on 45 identity-confounding runs (no false alarms). The operator being graded is deliberately standard — a group-identity classifier trained jointly with the encoder through a gradient-reversal layer[3,4] — and we claim no novelty for it. The operating characteristics above are what make any verdict below interpretable, and they are reported for the instrument rather than for the operator."""
))

REPS.append((
"""2. **A theory separating detection from acceptance (Proposition 1).** We prove that the intuitive "detect-then-accept" dual gate — require the label dependence to be gone *and* the signal to be preserved — is structurally empty once the pre-repair association exceeds an identifiable multiple of the permutation null scale.""",
"""2. **A pre-computable feasibility condition for the detect-then-accept gate (Proposition 1).** The intuitive dual gate — require the label dependence to be gone *and* the signal to be preserved — has a non-empty feasible set only below a ratio of the pre-repair association to the permutation null scale; above it, the statistic that certifies detection makes acceptance infeasible."""
))

REPS.append((
"""**Scope of the claims.** Three levels of evidence appear in this paper""",
"""**Where the novelty lies, stated plainly.** Three of the seven findings are properties of the instrument and the theory, not of the operator: the operating characteristics (finding 1), the feasibility condition (finding 2), and the two decision boundaries (findings 3 and 4). The operator itself is a standard adversarial head, chosen deliberately, because a familiar operator makes the instrument's verdict easier to audit and easier to distrust. Findings 5 to 7 are demonstrations of what the instrument does: it discriminates between methods that look alike on in-sample metrics, it returns a negative answer in the one domain where a downstream endpoint exists, and its predictions hold in two domains where nothing but the grouping structure is shared. A reader who takes the operator away keeps the instrument; a reader who takes the instrument away keeps nothing that can be checked.

**Scope of the claims.** Three levels of evidence appear in this paper"""
))

# ---------------- CRITICAL 2: units of analysis ----------------
REPS.append((
"""The quantities we use throughout are defined for any encoder and any domain: τ_in, the in-sample association between a linear probe's score and the label; τ_LOO, its leave-one-unit-out counterpart; and τ_LDO, the leave-one-*group*-out variant in which all units of a held-out group leave jointly.""",
"""The quantities we use throughout are defined for any encoder and any domain: τ_in, the in-sample association between a linear probe's score and the label; τ_LOO, its leave-one-unit-out counterpart; and τ_LDO, the leave-one-*group*-out variant in which all units of a held-out group leave jointly."""
))

REPS.append((
"""Full definitions are in Experimental Procedures.

The cheapest repair for an already-trained model""",
"""Full definitions are in Experimental Procedures.

**Two units of analysis, and why we keep them apart.** Every number in this paper belongs to one of two resolutions, and conflating them produces an apparent contradiction that we want to remove at the outset. The **representation unit** is the spot. The encoder, the reconstruction decoder and the adversarial head are all defined per spot, and there are of the order of 10^5 spots per cohort: 57,872 spots over 16 sections in the head-and-neck cohort, a mean of 3,617 per section. Repair acts here, and it is here that donor identity is present as a fingerprint shared by thousands of observations. The **consumption unit** is the section. Every statistic we report — τ_in, τ_LDO, the LDI built on it, R, and the leave-one-donor-out AUROC — is computed on section-mean embeddings, one vector per donor, because that is the resolution at which a downstream user consumes the representation. Because each donor contributes essentially one section (cervical 35 sections from 34 donors; head and neck 16 from 16; prostate 52 from 52), the consumption unit carries one observation per group, so τ_LOO and τ_LDO are the same statistic by construction and no sibling channel exists there. The same distinction explains an asymmetry between our two evidence settings: in the validation domain the audit is read at the consumption unit, whereas in the cross-domain cohorts of Table 5 the identical statistics are read at the observation level, where each group contributes hundreds of units and τ_LOO and τ_LGO separate (Figure 5B). We return to the distinction where it is load-bearing, in the scope condition.

The cheapest repair for an already-trained model"""
))

# sibling-unit k reconciliation
REPS.append((
"""and we state the resulting recommendation as a protocol rule: **whenever a group contributes more than one unit, model acceptance must be measured at the group level, never the unit level.** This rule is as much an evaluation-hygiene contribution""",
"""and we state the resulting recommendation as a protocol rule: **whenever a group contributes more than one unit, model acceptance must be measured at the group level, never the unit level.** The grid probes k ∈ {1, 2, 4, 8}, which is three orders of magnitude below the representation-level group size of our validation cohorts (about 3,617 spots per donor) and is not intended to match it: what decides whether the trap binds is the number of units a group contributes *at the resolution at which the model is consumed*. In the validation domain that number is one section per donor, so the trap is dormant and the two statistics coincide; in the cross-domain cohorts it is about 343 windows per subject and 1,391 measurements per batch, so the trap is live there (Figure 5B). A reader who compares the grid's k against a spot count is comparing the wrong pair of numbers. This rule is as much an evaluation-hygiene contribution"""
))

# scope condition rewrite
REPS.append((
"""We report this as a scope condition rather than a negative result about the operator, and — more to the point — as one the framework predicts in advance. All three cohorts have essentially one section per donor (cervical 35 sections from 34 donors; head and neck 16 from 16; prostate 52 from 52), so by the sibling-unit argument above there is no sibling-leakage channel for repair to remove; the audit already certifies the signal as group-transferable, and repair pays a pure fidelity cost. Repair's benefit is conditional on a leakage channel existing; its cost — a partial erasure of the transferable signal, the same effect that sets R = 0.38–0.60 at accepted cells — is paid regardless. Two further observations reinforce""",
"""We report this as a scope condition rather than as a negative result about the operator, and, more to the point, as one the framework yields in advance. The two units defined above explain it, and they also dissolve what would otherwise read as a contradiction: a channel demonstrably exists, yet closing it pays a cost with no return.

At the **representation unit** there is a real channel and repair attacks it. Each donor contributes thousands of spots carrying a donor-specific fingerprint, and the adversarial head measurably reduces donor identity in the embedding: group-identity lift fell by 46% in the wearable cohort and 22% in the gas-sensor cohort, and the planted in-sample fingerprint on the identity-confounding control was partly cleared. At the **consumption unit** there is no sibling channel to close. With one section per donor, the route by which leakage inflates a held-out score, re-identifying a held-out unit through the siblings its group left behind in training, does not exist, and τ_LOO and τ_LDO coincide. What repair removes at that resolution is therefore not leakage but label-associated signal, which is exactly what R = 0.38–0.60 at accepted cells records. The channel that exists is not the one the endpoint was paying for, so repair cannot improve the endpoint, while the erasure it performs costs fidelity regardless. We ran the operator on these cohorts anyway, and the reason is what makes the result informative rather than merely negative: the framework predicted in advance that repair would not pay where each group contributes a single consumption unit, and running it converts that prediction from a rationalisation into a test.

Two further observations reinforce"""
))

REPS.append((
"""Acceptance therefore cannot be delegated to a downstream metric, which is the practical reason an auditable gate exists at all.""",
"""Acceptance therefore cannot be delegated to a downstream metric, which is the practical reason an auditable gate exists at all. The framework's own recommendation for cohorts of this shape is stated in the protocol: where each group contributes a single consumption unit, the correct action is group-disjoint splitting[8] and the audit, not repair."""
))

# ---------------- MAJOR 3: head-and-neck baseline configuration ----------------
REPS.append((
"""**Real-cohort head-to-head validation.** Both external cohorts were re-run under the same encoder, dose schedule, and readout, with only the training objective changed. On the head-and-neck cohort (GSE268014, 16 patients, single-seed 100-epoch runs) the baseline already sat below the LDI gate (1.28);""",
"""**Real-cohort head-to-head validation.** Both external cohorts were re-run under the same encoder, dose schedule, and readout, with only the training objective changed. **These runs use a cheaper configuration than the primary dose–response: one seed and 100 epochs on the head-and-neck cohort, three seeds and 300 epochs on prostate, no stability hardening on either, so their baseline LDI is not the value reported in Table 1.** On the head-and-neck cohort the baseline in this configuration already sat below the LDI gate (1.28, against 2.2 in the three-seed stability runs of Table 1);"""
))

REPS.append((
"""Group-DRO (η ∈ {1, 10}) raised LDI to 1.87–2.26, and IRM (c ∈ {10, 100}) to 2.45–2.53.""",
"""Group-DRO (η ∈ {1, 10}) raised LDI to 1.87–2.26, and IRM (c ∈ {10, 100}) to 2.45–2.53. We therefore do not read these runs as evidence that repair *created* acceptance: in this configuration the cohort was already sub-gate at baseline, so what the comparison establishes is the ordering of methods at a common dose, not the size of a repair effect. The acceptance claim rests on the Table 1 and Table 2 runs, whose baseline LDI was 2.2 and which crossed the gate only under dose."""
))

REPS.append((
"""Primary runs are reported; the independent prostate re-run is noted. The last row shows a dose the
gate rejects despite carrying the numerically best endpoint.""",
"""Primary runs are reported; the independent prostate re-run is noted. The last row shows a dose the gate rejects despite carrying the numerically best endpoint. Baseline (λ = 0) LDI in this configuration is 2.2 for head and neck and 2.04 for prostate; the head-to-head comparison of Table 3 uses a cheaper configuration (single seed, 100 epochs, not stability-hardened) whose head-and-neck baseline LDI was 1.28, and the two are not interchangeable."""
))

# ---------------- MAJOR 5: why no off-the-shelf adversarial debiasing baseline ----------------
REPS.append((
"""Group-DRO leaves the leakage signal positive; IRM preserves the identity fingerprint as if it were an invariant feature (LDI rises to +3.2).

Three mechanistic findings emerge.""",
"""Group-DRO leaves the leakage signal positive; IRM preserves the identity fingerprint as if it were an invariant feature (LDI rises to +3.2).

**Why there is no off-the-shelf adversarial debiasing baseline in this table.** A natural expectation is a comparison against a published adversarial removal method. Our operator *is* that method: a gradient-reversal layer,[3,4] a cross-entropy adversary on the grouping variable, and a scalar dose λ, which is the canonical adversarial attribute-removal design.[27–29] Adding a second instance of it would compare our acceptance protocol against itself, and it would be scored on exactly the operating characteristics that the published versions do not report. What can be compared, and is compared here, are methods that pursue the same goal through a different objective, reweighting (Group-DRO) and invariance (IRM), where the question "did label dependence actually go" is the question the instrument exists to answer and the one neither method ships with. The gap this leaves is real and is stated in the limitations: we did not benchmark non-adversarial removal families, and the operating characteristics of finding 1 should be re-measured for any of them.

Three mechanistic findings emerge."""
))

# ---------------- MINOR 6: de-flate the theory packaging ----------------
REPS.append((
"""**Corollary 1.** For any cohort with a fixed true baseline association τ_base > 0,""",
"""**Remark 1 (how the conflict scales).** For any cohort with a fixed true baseline association τ_base > 0,"""
))

REPS.append((
"""*Proof.* Immediate from monotonicity: LDI < 1.645 ⟺ τ < τ_⊥ + 1.645σ̂; intersecting with [c·τ_base, τ_base] is non-empty iff c·τ_base < τ_⊥ + 1.645σ̂. ∎""",
"""*Proof of Proposition 1.* Immediate from monotonicity: LDI < 1.645 ⟺ τ < τ_⊥ + 1.645σ̂; intersecting with [c·τ_base, τ_base] is non-empty iff c·τ_base < τ_⊥ + 1.645σ̂. ∎""".replace(
    "*Proof of Proposition 1.*",
    "*Proof.*")
))

REPS.append((
"""The proposition is not a curiosity; it predicted our experimental outcomes exactly (Table 1).""",
"""**How much theory this is.** The argument above is a one-line monotonicity check. We label it a proposition only so that it can be cited, we have removed the corollary numbering that would have suggested more depth than is there, and we ask readers to judge it on its reading rather than on its derivation: the feasibility of a remove-and-preserve criterion is decided by a ratio that can be estimated from the unrepaired baseline, which turns the choice of acceptance protocol into a checkable precondition instead of a tuning decision. The proposition is not a curiosity; it predicted our experimental outcomes exactly (Table 1)."""
))

REPS.append(("and Corollary 1 says the conflict worsens as cohorts grow.",
              "and Remark 1 says the conflict worsens as cohorts grow."))
REPS.append(("Proposition 1 and Corollary 1 concern the *acceptance gate*",
              "Proposition 1 and Remark 1 concern the *acceptance gate*"))

# ---------------- MAJOR 4 (cont.): name the untested families in the limitations ----------------
REPS.append((
"""contrastive objectives with cross-group positive pairs; group-conditioned reweighting or importance sampling; explicit orthogonality or variance penalties on the group subspace; disentangled or factorised latent-variable models; and generative removal.""",
"""contrastive objectives with cross-group positive pairs; group-conditioned reweighting or importance sampling; explicit orthogonality or variance penalties on the group subspace; iterative nullspace projection;[32] disentangled or factorised latent-variable models; and generative removal. The three most informative next comparisons are the post-hoc or partly post-hoc ones, because they are cheap to run on the same grid: iterative nullspace projection,[32] contrastive cross-group objectives, and orthogonality penalties on the group subspace."""
))

REPS.append((
"""The operating characteristics, by contrast, are properties of the adversarial family: the 75/75 safety record, the dose–response shape, the seed instability at strong doses, and the retained fraction R = 0.38–0.60 at accepted cells should all be re-measured before being quoted for another operator.""",
"""The operating characteristics, by contrast, are properties of the adversarial family: the 75/75 safety record, the dose–response shape, the seed instability at strong doses, and the retained fraction R = 0.38–0.60 at accepted cells should all be re-measured before being quoted for another operator. This is a limitation of the empirical half of the paper only."""
))

# ---------------- MINOR 7: DOI placeholders ----------------
REPS.append((
"archived at Zenodo (DOI: [to be assigned before submission])",
"archived at Zenodo (DOI to be minted at submission; the GitHub repository above is the accessible interim location)"
))
REPS.append((
"Companion study; preprint available at [bioRxiv DOI to be added].",
"Companion study; preprint DOI to be added before submission (interim access: https://github.com/WorldBMW/cervix-st-multimodal)."
))

# ---------------- MAJOR 4 (cont.): new references ----------------
REPS.append((
"""26. [Dataset] Dua, D., and Graff, C. UCI Machine Learning Repository. University of California, Irvine, School of Information and Computer Science (2019).""",
"""26. [Dataset] Dua, D., and Graff, C. UCI Machine Learning Repository. University of California, Irvine, School of Information and Computer Science (2019).
27. Edwards, H., and Storkey, A. Censoring representations with an adversary. arXiv:1511.05897 (2015).
28. Xie, Q., Dai, Z., Du, Y., Hovy, E., and Neubig, G. Controllable invariance through adversarial feature learning. In Advances in Neural Information Processing Systems 30 (2017).
29. Madras, D., Creager, E., Pitassi, T., and Zemel, R. Learning adversarially fair and transferable representations. In Proceedings of the 35th International Conference on Machine Learning, 3384–3393 (2018).
30. Elazar, Y., and Goldberg, Y. Adversarial removal of demographic attributes from text data. In Proceedings of the 2018 Conference on Empirical Methods in Natural Language Processing, 11–21 (2018).
31. Alvi, M., Zisserman, A., and Nellåker, C. Turning a blind eye: explicit removal of biases and variation from deep neural network embeddings. In Proceedings of the European Conference on Computer Vision, 556–572 (2018).
32. Ravfogel, S., Elazar, Y., Gonen, H., Twiton, M., and Goldberg, Y. Null it out: guarding protected attributes by iterative nullspace projection. In Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics, 7237–7256 (2020).
33. Wang, D. et al. iMAP: integration of multiple single-cell datasets by adversarial paired transfer networks. Genome Biol. 22, 63 (2021).
34. Guo, T., Chen, Y., Shi, M., Li, X., and Zhang, M.Q. Integration of single cell data by disentangled representation learning. Nucleic Acids Res. 50, e8 (2022).
35. Hu, J., Zhong, Y., and Shang, X. A versatile and scalable single-cell data integration algorithm based on domain-adversarial and variational approximation. Brief. Bioinform., bbab400 (2021).
36. Zemel, R., Wu, Y., Swersky, K., Pitassi, T., and Dwork, C. Learning fair representations. In Proceedings of the 30th International Conference on Machine Learning, 325–333 (2013).
37. Louizos, C., Swersky, K., Li, Y., Welling, M., and Zemel, R. The variational fair autoencoder. arXiv:1511.00830 (2015).
38. Barocas, S., Hardt, M., and Narayanan, A. Fairness and Machine Learning: Limitations and Opportunities. MIT Press (2023)."""
))

for old, new in REPS:
    n = txt.count(old)
    if n != 1 and not old.startswith('archived at Zenodo'):
        print('!! count=%d for: %s' % (n, old[:90].replace('\n', ' ')))
        sys.exit(1)
    txt = txt.replace(old, new)

io.open(P, 'w', encoding='utf-8').write(txt)
print('replacements applied:', len(REPS))
