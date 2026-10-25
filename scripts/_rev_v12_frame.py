# -*- coding: utf-8 -*-
"""v11 -> v12:
(1) reframe the novelty claim from "prior work did no measurement" to
    "design-time remedies do not cover the post-hoc case" (and credit [42] for
    naming group leakage as one of its eight types);
(2) move Proposition 1 out of Results into Experimental Procedures and compress it;
(3) consolidate tier 1 as one object (measurement + its certification);
(4) sharpen the head-and-neck 8+8 justification."""
import io, os, re

D = os.path.join('papers', '20_MRP-ST-Repair_Patterns')
SRC = os.path.join(D, 'MRP-ST-Repair_manuscript_Patterns_v11.md')
DST = os.path.join(D, 'MRP-ST-Repair_manuscript_Patterns_v12.md')

s = io.open(SRC, encoding='utf-8').read()


def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n:
        for v in (old.replace('\u2019', "'"), old.replace("'", '\u2019'),
                  old.replace('\u201c', '"'), old.replace('\u201d', '"')):
            if s.count(v) == n:
                old, c = v, n
                break
    assert c == n, 'count=%d for %r' % (c, old[:80])
    s = s.replace(old, new)


# ------------------------------------------------------------------ 1. post-hoc framing
OLD = ('What none of them supplies is a measurement. The prior work is prescriptive and preventive: it says '
       'which split to use before training,[8,40,41] or which checklist to complete,[42] and it demonstrates '
       'that the optimism is real, case by case. It does not give a practitioner a number, in units that are '
       'comparable across datasets and domains, for how much of a reported result is attributable to the '
       'shortcut; it does not give a criterion for accepting an intervention that claims to have removed the '
       'shortcut; and it is silent on the case we care about most, in which the model or the representation '
       'already exists and the split can no longer be redesigned. Those three gaps are what the instrument '
       'below is built to close, and they are the reason we quantify a known effect rather than announce it.')
NEW = ('Group leakage is not unrecognised. It is one of the eight leakage types in the cross-field taxonomy of '
       'ref [42], which documents it across 294 papers in 17 fields, and the remedies that literature offers '
       'are the right ones for the situation it addresses: construct the split so that no group straddles '
       'it,[8,40,41] and disclose what you did.[42] Both are design-time remedies, and both are instructions '
       'for someone who has not trained yet.\n\n'
       'The case this paper addresses is the one they do not cover, and in practice it is the common one: the '
       'representation already exists. A practitioner has inherited a model or an embedding that reports high '
       'held-out performance, the split that produced the number was at observation level, and neither the '
       'split nor the training run can be redone cheaply. Neither remedy answers that practitioner\'s '
       'question. Re-running with a group-disjoint split is a different experiment: it estimates what the '
       'performance would have been, not how much of the number already reported is group-driven, and it '
       'cannot be run at all on a representation that is being reused or fine-tuned downstream. A checklist '
       'returns a disclosure, not a measurement. What is needed instead is a counterfactual measurement taken '
       'on the representation as it stands: how much of its reported association survives when whole groups '
       'are held out, expressed in the units of what permutation alone would have produced, and carried out '
       'with an instrument that can itself be shown still to see something after the representation has been '
       'modified. That is a different object from a splitting protocol, and it is the object built below: the '
       'sibling-unit trap and the label-dependence index are its two components, and the acceptance protocol, '
       'the precondition test and the two decision boundaries are what make it usable.')
rep(OLD, NEW)

# ------------------------------------------------------------------ 2. one-sentence claim + tier header
rep('The contribution has two tiers. Two findings carry it, and neither of them is the repair operator. '
    'Five further findings are the diagnostics and the intervention that make the two usable:',
    '**The claim, in one sentence.** We supply the post-hoc audit that design-time remedies do not. Given a '
    'grouping variable, a label and a trained representation, and without retraining or redesigning any '
    'split, the instrument returns three things: how much of the reported association is group-driven, in '
    'units that say what permutation alone would have produced; whether an intervention that removed it left '
    'anything that transfers across groups; and whether the instrument making the measurement was itself '
    'blinded by that intervention. Group-disjoint splitting prevents the shortcut; this grades it after the '
    'fact, and the grading is what an acceptance decision has to rest on, because by then prevention is no '
    'longer available.\n\n'
    'The contribution has two tiers. Two findings carry it, and neither of them is the repair operator. '
    'Five further findings are the diagnostics and the intervention that make the two usable:\n\n'
    '**First tier: the post-hoc audit, a measurement and its certification.** These two are halves of one '
    'object rather than separate results: the first says there is something to measure, the second measures '
    'it and certifies that the measurement still works after the thing measured has been changed.')

# ------------------------------------------------------------------ 3. highlight 2
rep('2. Group-structured data let a model win by recognising the group, not the target',
    '2. Blocked splits prevent group leakage; this grades it after training, no retraining')
_h = 'Blocked splits prevent group leakage; this grades it after training, no retraining'
assert len(_h) <= 85, len(_h)

# ------------------------------------------------------------------ 4. Proposition 1 out of Results
lines = s.split('\n')
start = [i for i, l in enumerate(lines)
         if l.startswith('A repair operator is only usable with a criterion that certifies both removal')]
assert len(start) == 1, start
end = [i for i, l in enumerate(lines) if l.endswith('the protocol in Experimental Procedures keeps the two separate.')]
assert len(end) == 1, end
removed = lines[start[0]:end[0] + 1]
print('removing %d lines / %d words from Results' %
      (len(removed), len(' '.join(removed).split())))

RESULTS_POINTER = (
    '**A precondition test decides which acceptance criterion is coherent (Proposition 1).** A '
    'remove-and-preserve gate (label dependence gone, transferable signal retained) is not always '
    'satisfiable, and whether it is can be settled from the unrepaired baseline alone. Proposition 1 '
    '(stated and proved in Experimental Procedures) reduces the question to one reported number, the '
    'critical retention c_crit = 1.645 σ̂/τ_base: the dual gate is non-empty for every retention requirement '
    'c < c_crit and empty for every c ≥ c_crit. Its proof is a one-line monotonicity check and we claim no '
    'mathematical novelty for it; its value is that it is computable before any repaired model is trained. '
    'On our cohorts c_crit = 0.28 (shared-program simulation), 0.69 (cervical), 0.75 (head and neck), 0.80 '
    '(prostate), 0.12 (HAR) and 0.15 (gas drift). Read against the conventional c = 0.7 the ratio places '
    'every cohort correctly (Table 1), and the ordering of cohorts is invariant to c because only the cut '
    'point moves. Two readings have to be kept apart: what is pre-computed is the feasibility verdict, not '
    'the LDI that any particular dose will return, and σ̂ is re-estimated for every run (drifting by at '
    'most 7.6% on head and neck and 9.5% on prostate across the dose grid), which we verified changes no '
    'verdict we report (Table S14).')

METHODS_BODY = (
    'Stated here because it is used as a protocol element rather than reported as a result. Let '
    'LDI(τ) = (τ − τ_⊥)/σ̂ be the calibrated index, strictly increasing in τ, with gate value 1.645 and '
    'null floor τ_⊥ ≈ 0. The post-repair τ feasible set of the dual gate {LDI < 1.645 ∧ τ ≥ c·τ_base} is '
    'non-empty if and only if c·τ_base < τ_⊥ + 1.645·σ̂, i.e. τ_base/σ̂ < 1.645/c + τ_⊥/(c·σ̂) ≈ 2.35 for '
    'c = 0.7.\n\n'
    '*Proof.* Immediate from monotonicity: LDI < 1.645 ⟺ τ < τ_⊥ + 1.645σ̂; intersecting with '
    '[c·τ_base, τ_base] is non-empty iff c·τ_base < τ_⊥ + 1.645σ̂. ∎\n\n'
    '**How the conflict scales (Remark 1).** For any cohort with a fixed true baseline association '
    'τ_base > 0, the dual gate is structurally empty once the cohort is large enough (σ̂ → 0 as the group '
    'count grows), because the gate then demands near-zero τ while preservation demands a large fraction of '
    'τ_base. The dual gate therefore conflates "leakage removed" with "signal removed" exactly when the '
    'signal is strongest.\n\n'
    '**What the proposition is, and what c is (Remark 2).** It is an identifiability condition rather than '
    'a limit theorem or a new estimator: its proof is one line of monotonicity, and its role is to make a '
    'threshold quotable rather than to add to statistical theory. c is not a constant of nature but the '
    'fraction of the baseline association a deployer is willing to give up, so it is set by that deployer '
    '(threshold 1.645/c: c = 0.5 gives 3.29, c = 0.7 gives 2.35, c = 0.9 gives 1.83; Table S15). Because '
    'c is a normative choice, we do not ask the reader to adopt a value. Rearranged, the same condition '
    'defines a quantity that is free of it: the **critical retention** c_crit = 1.645 σ̂/τ_base, the largest '
    'retention requirement under which a feasible dose can exist. The gate is non-empty for every c < c_crit '
    'and empty for every c ≥ c_crit, so a cohort is characterised by c_crit (Table 1) rather than by a verdict '
    'taken at our c, and we display c = 0.7 only as a reading convention. The ordering of cohorts by '
    'feasibility is the same at every c; only the cut point moves. Realized retention τ_LDO/τ_base at '
    'leakage-passing cells is 0.46–0.73 on head and neck and 0.67–0.76 on prostate, which is what makes '
    'the region near c = 0.7 the informative one on these data: below 0.46 the gate would certify cells '
    'that have given up more than half the association, and above 0.76 it would certify none.\n\n'
    '**Protocol.** Fit the unrepaired baseline once and read off c_crit = 1.645 σ̂/τ_base (equivalently, form '
    'τ_base/σ̂ and read it against 1.645/c). Where the deployer requires more retention than the cohort '
    'admits, adopt the three-axis protocol instead of searching for a dose. Report c_crit and let the deployer '
    'supply c; do not tune c to obtain a preferred verdict.')

lines[start[0]:end[0] + 1] = RESULTS_POINTER.split('\n')
s = '\n'.join(lines)

rep('### Proposition 1: when is a detect-then-accept gate feasible?',
    '### A precondition test for the detect-then-accept gate')
rep('### Proposition 1', '### Proposition 1 (precondition test for the dual gate)')
rep('Stated and proved in Results. The feasibility threshold is τ_base/σ̂ < 1.645/c (≈ 2.35 for c = 0.7).',
    METHODS_BODY)

# ------------------------------------------------------------------ 5. head-and-neck subset
rep('so the subset is a choice about resolution in this arm rather than a requirement of the method.',
    'so the subset is a choice about resolution in this arm rather than a requirement of the method. Two '
    'further points about that choice should be stated plainly. The comparability claim does not depend on '
    'it: τ_base/σ̂ is dimensionless, so a cohort of different composition would still be graded on the same '
    'scale, and the 48:4 prostate cohort is direct evidence that the instrument returns a graded verdict '
    'under severe imbalance. And we did not run the full 26-sample series, and we do not extrapolate to it. '
    'The ceiling argument says τ_base would fall if it tracked the ceiling (by up to 8.9%), but σ̂ depends '
    'on the group count as well, so the argument we give does not determine the direction of the ratio; the '
    'honest statement is that the 16-patient figures are a dose-response measurement on a balanced arm, not '
    'a cohort-level estimate for GSE268014. Running the imbalanced variant is a configuration change under '
    'the released manifests.')

io.open(DST, 'w', encoding='utf-8').write(s)
print('written', DST)
print('em-dash:', s.count('\u2014'), '| literal **:', s.count('**'))
