# -*- coding: utf-8 -*-
"""v8 -> v9: answer review round 6 (novelty framing, Proposition 1 triviality, dual-gate consistency,
cohort provenance, negative-result framing, prostate fragility)."""
import io
import os

ROOT = r'G:\project4_cervix_multimodal'
PD = os.path.join(ROOT, 'papers', '20_MRP-ST-Repair_Patterns')
SRC = os.path.join(PD, 'MRP-ST-Repair_manuscript_Patterns_v8.md')
DST = os.path.join(PD, 'MRP-ST-Repair_manuscript_Patterns_v9.md')

t = io.open(SRC, encoding='utf-8').read()
n0 = len(t)


def rep(old, new, label):
    global t
    c = t.count(old)
    if c != 1:
        raise SystemExit('FAIL [%s]: %d occurrences\n%s' % (label, c, old[:200]))
    t = t.replace(old, new)
    print('  ok  %s' % label)


# ============================================================ A. dual-gate consistency (found in audit)
rep('| Head and neck (16 patients, GSE268014) | etiological (HPV) | 0.59 | ≈ 0.27 | 2.18 | non-empty | '
    '7/9 seed × dose cells at λ ∈ {0.5, 1, 2}; R 0.38–0.60 |',
    '| Head and neck (16 patients, GSE268014) | etiological (HPV) | 0.59 | ≈ 0.27 | 2.18 | non-empty | '
    'leakage axis 7/9 at λ ∈ {0.5, 1, 2}; both axes 1/9 (λ = 2, retention 0.73); R 0.38–0.60 |',
    'table1: HNSCC dual-gate count')

rep('| Prostate (52 patients, GSE278936) | benign vs tumour | 0.288 | ≈ 0.143 | ≈ 2.0 | narrow | '
    'λ = 1.0 only (LDI 1.51; re-run 1.46 ± 0.86; R 0.60) |',
    '| Prostate (52 patients, GSE278936) | benign vs tumour | 0.288 | ≈ 0.143 | ≈ 2.0 | narrow | '
    'λ = 1.0 only, 2 of 3 seeds on both axes (LDI 1.51; re-run 1.46 ± 0.86; R 0.60; retention 0.74–0.76); '
    'suggestive, see text |',
    'table1: prostate dual-gate count')

rep('Finally, LDI at λ = 0 and the ratio τ_base/σ̂ are different statistics',
    '"Accepted" is counted on two axes throughout: the leakage axis (LDI < 1.645) and the fidelity axis '
    '(τ_LDO ≥ 0.7 · τ_base). Where a seed count is quoted without naming the axes, the count is the leakage axis '
    'alone; counts on both axes are given alongside it. Finally, LDI at λ = 0 and the ratio τ_base/σ̂ are '
    'different statistics',
    'table1 footnote: two axes defined')

rep('Accepted operating points (LDI < 1.645) existed across λ ∈ {0.5, 1, 2}: seven of nine seed × dose cells, '
    'with all three seeds passing at λ = 0.5, and the transferable fraction at those cells spanned R = 0.38–0.60',
    'Operating points below the LDI gate existed across λ ∈ {0.5, 1, 2}: seven of nine seed × dose cells, with all '
    'three seeds passing at λ = 0.5, and the transferable fraction at those cells spanned R = 0.38–0.60. One of '
    'those nine also clears the fidelity axis (τ_LDO ≥ 0.7 · τ_base), at λ = 2 with τ_LDO = 0.434, i.e. 0.73 of '
    'the baseline association, and that single cell is what the dual gate admits; the distance between seven and '
    'one is the conflict Proposition 1 describes, now measured rather than derived',
    'results: HNSCC dual-gate count')

rep('the head-and-neck figure of 7/9 is quoted as a seed count because there all three seeds are sub-gate at '
    'λ = 0.5 with a spread of 0.25.',
    'the head-and-neck figure of 7/9 is quoted as a seed count because there all three seeds are sub-gate at '
    'λ = 0.5 with a spread of 0.25. Applying the fidelity axis in addition (τ_LDO ≥ 0.7 · τ_base, with '
    'τ_base = 0.59 on head and neck and 0.288 on prostate) leaves 1 of 9 head-and-neck cells accepted (seed 1 at '
    'λ = 2) and 2 of 9 prostate cells (both at λ = 1.0); realized retention τ_LDO/τ_base at leakage-passing cells '
    'is 0.46–0.73 on head and neck and 0.67–0.76 on prostate, which is why c = 0.7 binds rather than being '
    'vacuous here.',
    'table2 footnote: dual-gate counts')

# ============================================================ B. Proposition 1 triviality + c = 0.7
rep('*Proof.* Immediate from monotonicity: LDI < 1.645 ⟺ τ < τ_⊥ + 1.645σ̂; intersecting with '
    '[c·τ_base, τ_base] is non-empty iff c·τ_base < τ_⊥ + 1.645σ̂. ∎',
    '*Proof.* Immediate from monotonicity: LDI < 1.645 ⟺ τ < τ_⊥ + 1.645σ̂; intersecting with '
    '[c·τ_base, τ_base] is non-empty iff c·τ_base < τ_⊥ + 1.645σ̂. ∎\n\n'
    '**Remark 2 (what the proposition is, and what c is).** Proposition 1 is an identifiability condition, not a '
    'limit theorem or a new estimator: its proof is one line of monotonicity and we claim no mathematical novelty '
    'for it. It is stated as a proposition so that a practitioner can cite the threshold instead of re-deriving '
    'it, and so that the threshold can be quoted as a function of c. That dependence is explicit: the threshold is '
    '1.645/c, so c is not a constant of nature but the fraction of the baseline association a deployer is willing '
    'to give up, and it has to be set by that deployer (c = 0.5 gives 3.29, c = 0.7 gives 2.35, c = 0.9 gives '
    '1.83; Table S15). We use c = 0.7 because it is the value at which the gate binds on our own data without '
    'being empty: realized retention τ_LDO/τ_base at leakage-passing cells is 0.46–0.73 on head and neck and '
    '0.67–0.76 on prostate, so c = 0.9 would admit no cell in any real cohort we ran and c = 0.5 would certify '
    'cells that keep less than half the association. Changing c changes which cohorts are feasible (Table S15) '
    'and nothing else in the argument.',
    'prop1: Remark 2 on triviality and c')

# ============================================================ C. relation of LDI to existing calibration
rep('moved σ̂ by ≤ 4.4% and changed the gate decision in 0 of 15 external-cohort runs, all doses included '
    '(Table S4).',
    'moved σ̂ by ≤ 4.4% and changed the gate decision in 0 of 15 external-cohort runs, all doses included '
    '(Table S4).\n\n'
    '### Relation of LDI to existing calibration procedures\n\n'
    'LDI should be read as a calibrated cross-validated rank statistic, and we state which parts of it are '
    'standard and which carry the claim. The *calibration machinery* is standard: LDI is the standardized excess '
    'of a statistic over its own permutation null, and because LDI is a strictly increasing affine function of τ, '
    'it orders samples identically to the usual permutation p-value p = (1 + #{b : τ*_b ≥ τ_obs})/(1 + B), the two '
    'being related by LDI ≈ Φ⁻¹(1 − p) up to Monte-Carlo error at B = 2,000. We report the index rather than the '
    'p-value for three reasons: p saturates at 1/(1 + B) ≈ 5 × 10⁻⁴ and is therefore not comparable across '
    'cohorts of different size; LDI is expressed in null-scale units, which is exactly the quantity Proposition 1 '
    'thresholds; and a null scale, unlike a p-value, can be estimated once at baseline and reused, which is what '
    'makes the feasibility ratio pre-computable.\n\n'
    'What is *not* standard is the object being calibrated, and three choices carry the contribution. First, the '
    'statistic is a group-level association (Kendall τ under leave-one-group-out) rather than a loss or an '
    'accuracy, so it measures dependence rather than error and has a known analytic ceiling for a given class '
    'split. Second, the null is a *refit* null: the probe is refit inside every fold and again inside every '
    'permutation, because the quantity under test is produced by a fitting procedure; a null that permutes labels '
    'while reusing a fitted probe understates σ̂ and inflates significance.[39] Third, the index is paired with '
    'calibration on planted controls (75 positive-control runs, 45 identity-confounding runs), which is what '
    'licenses the non-blindness claim; a generic permutation test of association carries no such calibration and '
    'cannot separate "the leak is gone" from "the model is empty".\n\n'
    'Relative to group-aware cross-validation, standard practice is to report a held-out loss under group-disjoint '
    'splits. That practice targets the same failure but reports an uncalibrated quantity: a held-out loss has no '
    'null, so a small generalization gap cannot distinguish a model that has stopped using identity from one that '
    'has stopped working. The uncalibrated analogue of our numerator is the memorization gap τ_in − τ_LOO, which '
    'we also report; LDI is that statistic placed on its own null. We therefore claim no novelty for permutation '
    'calibration as such, and locate the contribution in the group-level, refit-calibrated target, its expression '
    'in null-scale units, and its combination with a pre-computable feasibility condition and planted-control '
    'calibration.',
    'exp proc: relation to existing calibration')

# ============================================================ D. cohort provenance
rep('The head-and-neck cohort is GSE268014[17] (Visium, HPV-positive / HPV-negative HNSCC; balanced '
    '16-patient subset, 8 + 8, 57,872 spots, mean 3,617 spots per section) from the Gene Expression Omnibus.',
    'The head-and-neck cohort is GSE268014[17] (Visium, HPV-positive / HPV-negative HNSCC): 16 sections of that '
    'series (GSM8283897–GSM8283913), selected as a balanced 8 HPV-positive and 8 HPV-negative subset, 57,872 '
    'spots, mean 3,617 spots per section, from the Gene Expression Omnibus. The published cohort reports 26 '
    'tumour samples;[17] we used the balanced subset because Kendall τ under a binary label has an analytic '
    'ceiling that falls with class imbalance (τ_max = 0.7303 for an 8-versus-8 split against 0.6656 for an '
    '8-versus-18 split, 8.9% lower) and because a rank statistic loses power under imbalance. The cost is '
    'resolution: n = 16 against 52 on the prostate cohort, which is one reason the head-and-neck acceptance '
    'result is the more fragile of the two.',
    'resource availability: cohort provenance')

# ============================================================ E. defuse the out-of-domain tautology
rep('A practitioner reading only the gate rejection would have concluded that repair failed; Proposition 1 says '
    'in advance that no dose could have succeeded.',
    'A practitioner reading only the gate rejection would have concluded that repair failed; Proposition 1 says '
    'in advance that no dose could have succeeded. One qualification belongs with this, because it bounds what '
    'the result is worth. The fidelity axis was satisfied at every dose in both cohorts (τ_LGO retained ≥ 0.89 of '
    'baseline), so the emptiness of the dual gate here is carried entirely by the leakage axis, and repair did not '
    'move τ_LOO at all: prediction and observation are therefore close to the same statement, and we present this '
    'as a consistency check rather than as an independent test of Proposition 1. What it does establish is still '
    'not empty: the operator\'s reach is bounded, because a dose that removed 46% and 22% of group-identity lift '
    'in these cohorts left the group-level label association untouched. The out-of-domain prediction we defend as '
    'falsifiable is decision boundary I, tested next: it predicted an ordering between cohorts, not an empty set, '
    'and it could have failed.',
    'cross-domain: Proposition 1 as consistency check')

rep('The discriminator is coupling, not identifiability: the conclusion the transcriptomic cohorts reached, now '
    'reproduced in a wearable and an analytical-chemistry setting.',
    'The discriminator is coupling, not identifiability: the conclusion the transcriptomic cohorts reached, now '
    'reproduced in a wearable and an analytical-chemistry setting. Unlike the feasibility check above, this is a '
    'prediction that could have failed: encoded identity is comparable in the two cohorts, so an account based on '
    'identifiability alone would have predicted similar inflation in both, and the observed inflation differs by a '
    'factor of eight with non-overlapping per-cell ranges (Table S13). Two cohorts are the minimum needed to '
    'establish an ordering and not enough to establish a functional form; we claim the ordering and nothing more.',
    'cross-domain: boundary I as the falsifiable prediction')

# ============================================================ F. negative result reframed
rep('the framework predicted in advance that repair would not pay where each group contributes a single '
    'consumption unit, and running it converts that prediction from a rationalisation into a test.',
    'the framework predicted in advance that repair would not pay where each group contributes a single '
    'consumption unit, and running it converts that prediction from a rationalisation into a test. We state the '
    'result in the direction that generalises: what transfers is not "repair fails" but "the framework correctly '
    'identifies, before an endpoint is measured, the regime in which repair must fail". That no accepted repair '
    'improved an endpoint on these cohorts is a property of the cohorts; that the protocol said so in advance is a '
    'property of the framework, and it is the second of the two that a reader in another domain can use.',
    'scope condition: negative result reframed as negative predictive power')

# ============================================================ G. prostate downgraded
rep('Real-data cases in which repair removed leakage that the instrument had detected are confined to two small '
    'cohorts of the validation domain: head and neck (16 patients; baseline LDI 2.18 falling to 1.13–1.37 at '
    'λ = 0.5, all three seeds below the gate) and prostate (52 patients; 2.04 to 1.51 at λ = 1.0, two of three '
    'seeds). Both are single-section-per-donor cohorts of modest size, and the prostate result is seed-fragile.',
    'Real-data cases in which repair removed leakage that the instrument had detected are confined to two small '
    'cohorts of the validation domain: head and neck (16 patients; baseline LDI 2.18 falling to 1.13–1.37 at '
    'λ = 0.5, all three seeds below the leakage gate, and one of nine seed × dose cells clearing the fidelity axis '
    'as well) and prostate (52 patients; 2.04 to 1.51 at λ = 1.0, two of three seeds on both axes). Both are '
    'single-section-per-donor cohorts of modest size. The prostate result we report as suggestive rather than '
    'established: the verdict is carried by the mean of three seeds whose spread (SD 0.16, and 0.86 in the '
    'independent re-run) is wider than the distance from the mean to the gate, and the cohort carries four benign '
    'donors, so the endpoint that would corroborate acceptance is unresolvable there. Establishing it requires '
    'more benign sections, not more seeds.',
    'discussion: prostate downgraded to suggestive')

# ============================================================ H. new limitation (xi)
rep('(x) **The fidelity gate degenerates when the baseline association is near zero.**',
    '(xi) **The out-of-domain test of Proposition 1 is a consistency check, not an independent test.** On both '
    'non-biological cohorts the fidelity axis was satisfied at every dose (τ_LGO retained ≥ 0.89 of baseline), so '
    'the emptiness of the dual gate there is carried entirely by the leakage axis, and repair did not move τ_LOO '
    'at all. Prediction and observation are consequently close to the same statement, and we do not present this '
    'as a test of the feasibility theory. The out-of-domain claim we do defend as falsifiable is decision '
    'boundary I, which predicted an ordering between the two cohorts and would have failed had inflation tracked '
    'identifiability rather than coupling.\n\n'
    '(x) **The fidelity gate degenerates when the baseline association is near zero.**',
    'limitations: new bullet (xi)')

# ============================================================ I. reference 39
rep('38. Barocas, S., Hardt, M., and Narayanan, A. Fairness and Machine Learning: Limitations and Opportunities. '
    'MIT Press (2023).',
    '38. Barocas, S., Hardt, M., and Narayanan, A. Fairness and Machine Learning: Limitations and Opportunities. '
    'MIT Press (2023).\n'
    '39. Ojala, M., and Garriga, G. Permutation tests for studying classifier performance. J. Mach. Learn. Res. '
    '11, 1833–1863 (2010).',
    'ref 39 added')

# ============================================================ J. SI list: S15
rep('the movement of τ_LOO alongside that of σ̂.',
    'the movement of τ_LOO alongside that of σ̂.\n\n'
    '**Table S15.** Sensitivity of the feasibility threshold to the retained fraction c: threshold 1.645/c for '
    'c ∈ {0.5, 0.6, 0.7, 0.8, 0.9}, and for each cohort whether the dual gate is predicted feasible at that '
    'value, together with the realized retention τ_LDO/τ_base observed at leakage-passing cells.',
    'si list: S15')

io.open(DST, 'w', encoding='utf-8').write(t)
print('v8 %d chars -> v9 %d chars' % (n0, len(t)))
print('wrote', DST)
