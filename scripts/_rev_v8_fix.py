# -*- coding: utf-8 -*-
"""v7 -> v8: fix the number-alignment and self-consistency issues raised in review round 5."""
import io
import json
import os
import sys

ROOT = r'G:\project4_cervix_multimodal'
PD = os.path.join(ROOT, 'papers', '20_MRP-ST-Repair_Patterns')
SRC = os.path.join(PD, 'MRP-ST-Repair_manuscript_Patterns_v7.md')
DST = os.path.join(PD, 'MRP-ST-Repair_manuscript_Patterns_v8.md')

with io.open(SRC, encoding='utf-8') as f:
    t = f.read()

orig_len = len(t)


def rep(old, new, label):
    global t
    n = t.count(old)
    if n != 1:
        raise SystemExit('FAIL [%s]: found %d occurrences\n%s' % (label, n, old[:160]))
    t = t.replace(old, new)
    print('  ok  %s' % label)


# ---------------------------------------------------------------- 1 / 6. sigma-hat drift vs pre-computable
rep(
    '**How much theory this is.** The argument above is a monotonicity check, stated as a proposition only so that it can be cited. '
    'What matters is its reading: the feasibility of a remove-and-preserve criterion is decided by a ratio estimable from the '
    'unrepaired baseline, which turns the choice of acceptance protocol into a checkable precondition instead of a tuning decision. '
    'The proposition is not a curiosity; it predicted our experimental outcomes exactly (Table 1). The shared-program simulation has '
    'τ_base/σ̂ = 5.8 and the cervical cohort ≈ 2.4: both above the ≈ 2.35 threshold, and indeed no dose of repair ever passed the dual '
    'gate there, by construction rather than by failure. The external head-and-neck cohort sits at τ_base/σ̂ ≈ 2.2, just below threshold, '
    'and is the first of the real cohorts in which an acceptance window exists, and where accepted operating points were in fact '
    'observed; the prostate cohort sits at ≈ 2.0 and yields a single accepted dose. A method designer who did not know this algebra '
    'would have concluded, wrongly, that repair "failed" on every strong-signal cohort.',

    '**How the proposition is used.** The argument above is a monotonicity check, stated as a proposition only so that it can be cited; '
    'what matters is its use as a precondition test. Fit the unrepaired baseline once, form τ_base/σ̂, and read it against 2.35: above '
    'the threshold no dose can satisfy a remove-and-preserve dual gate, so the practitioner should adopt the three-axis protocol rather '
    'than search for a dose; below it a feasible dose may exist and is worth searching for. The ratio places every cohort in this paper '
    'correctly (Table 1): the shared-program simulation (5.8) and the cervical cohort (≈ 2.4) sit above the threshold and produced no '
    'accepted operating point, while head and neck (2.18) and prostate (≈ 2.0) sit below it and produced accepted cells. The test costs '
    'one baseline fit and no repaired run.',

    'prop1: how-to-use paragraph')

rep(
    'This converts acceptance from a hand-tuned threshold into a checkable precondition.',

    'This converts acceptance from a hand-tuned threshold into a checkable precondition. One scope condition comes with it. What is '
    'pre-computed is the *feasibility verdict*: a statement about the existence of a feasible dose set under the baseline null scale. It '
    'is not a prediction of the LDI that any particular dose will return. σ̂ is re-estimated for every run, because an audit has to grade '
    'the representation as it stands after dosing, and across the dose grid it deviates from its baseline value by at most 7.6% (head and '
    'neck) and 9.5% (prostate). We verified that this does not move any verdict we report: recomputing every external-cohort cell with '
    'the baseline σ̂ in place of the run\'s own σ̂ flips no gate decision, the tightest surviving margin being 0.05 on head and neck '
    '(1.59 against the 1.645 gate) and 0.10 on prostate (1.54) (Table S14). The verdict is pre-computable; the grade is not, and the '
    'protocol in Experimental Procedures keeps the two separate.',

    'prop1: pre-computable scope condition')

# ---------------------------------------------------------------- 1. Table 1 footnote: separate the two sigma perturbations
rep(
    'The LDI values reported in Table 2 are computed per cell against that cell\'s own σ̂, because an audit has to grade the '
    'representation as it stands after dosing; σ̂ drifts by at most 7.6% (head and neck) and 9.5% (prostate) across the whole dose '
    'grid, so the baseline estimate used here is representative of the grid.',

    'Two different perturbations of σ̂ appear in this paper and should not be confused. (i) *Dose-grid drift*: the LDI values reported '
    'in Table 2 are computed per cell against that cell\'s own σ̂, because an audit has to grade the representation as it stands after '
    'dosing; across the dose grid σ̂ deviates from its baseline value by at most 7.6% (head and neck) and 9.5% (prostate), and because '
    'LDI is inversely proportional to σ̂, a drift of that size moves LDI by the same percentage. (ii) *Permutation-depth sensitivity*: '
    'recomputing the null at B = 10,000 instead of 2,000 moved σ̂ by ≤ 4.4% and flipped no gate decision (Table S4); the 4.4% is an '
    'upper bound on the second quantity only and is not the grid drift of (i). Neither perturbation changes a verdict we report. '
    'Substituting the baseline σ̂ for the per-run σ̂ in all 30 external-cohort cells flips no gate decision, the smallest distance from '
    'any recomputed LDI to the gate being 0.05 (head and neck) and 0.10 (prostate), and at every accepted cell the movement of τ_LOO '
    'exceeds the movement of σ̂, so no acceptance verdict is carried by the null scale (Table S14).',

    'table1 footnote: two sigma perturbations')

rep(
    'so cervical reads 2.4 as an LDI and 2.4 as a ratio, and head and neck reads 2.18 either way. The ratio governs whether a feasible '
    'dose exists; the LDI grades whether a given run is acceptable.',

    'so cervical reads 2.4 as an LDI and 2.4 as a ratio, and head and neck reads 2.18 either way (2.2 when rounded to two digits; we '
    'quote 2.18 throughout). The ratio governs whether a feasible dose exists; the LDI grades whether a given run is acceptable.',

    'table1 footnote: 2.18 rounding note')

# ---------------------------------------------------------------- 1. Statistical analysis: same separation
rep(
    'Gate decisions on the external cohorts were rechecked at B = 10,000 with no flips (Table S4); all other gate decisions use '
    'B = 2,000, and under the largest σ̂ perturbation observed in the recheck (4.4% on σ̂; LDI rescales reciprocally, at most +4.6% in '
    'the worst direction) no reported decision changes: the closest-to-gate value outside those directly rechecked runs '
    '(identity-confounding maximum LDI = 1.55) would move to at most ≈ 1.62, still under the gate.',

    'Two σ̂ perturbations are reported and are different quantities. *Permutation depth:* gate decisions on the external cohorts were '
    'rechecked at B = 10,000 with no flips (Table S4); all other gate decisions use B = 2,000, and under the largest σ̂ perturbation '
    'observed in that recheck (4.4% on σ̂; LDI rescales reciprocally, at most +4.6% in the worst direction) no reported decision '
    'changes: the closest-to-gate value outside the directly rechecked runs (identity-confounding maximum LDI = 1.55) would move to at '
    'most ≈ 1.62, still under the gate. *Dose-grid drift:* σ̂ is re-estimated for every run, and across the dose grid of the two '
    'external cohorts it deviates from its baseline value by at most 7.6% (head and neck) and 9.5% (prostate); because LDI is inversely '
    'proportional to σ̂, replacing a run\'s own σ̂ by the baseline σ̂ would move its LDI by the same percentage. Recomputing all 30 '
    'external-cohort cells that way flips no gate decision, and the smallest distance from a recomputed LDI to the 1.645 gate is 0.05 '
    '(head and neck, λ = 2: 1.59 recomputed against 1.60 observed) and 0.10 (prostate, λ = 1: 1.54 recomputed against 1.44 observed) '
    '(Table S14). At every accepted cell the change in τ_LOO exceeds the change in σ̂, so no acceptance verdict is carried by the null '
    'scale rather than by the association. The drift statistic is defined so that it can be recomputed: max over cells of '
    '|σ̂(λ) − σ̂(0)| / σ̂(0), with σ̂(0) the mean baseline σ̂ of Table 1 (0.2717 on head and neck, 0.1406 on prostate).',

    'stat analysis: two sigma perturbations')

# ---------------------------------------------------------------- 2. prostate re-run R
rep(
    '| | 1.0 | 1.51 | mean below gate | 0.229 | 0.60 (0.56–0.67) | accepted; re-run 1.46 ± 0.86 |',

    '| | 1.0 | 1.51 | 2/3 | 0.229 | 0.60 (0.56–0.67) | accepted; re-run 1.46 ± 0.86 (R = 0.58) |',

    'table2: prostate re-run R + seed count')

# ---------------------------------------------------------------- 5. accepted definition differs across cohorts
rep(
    'the figure quoted in the text. Primary runs are reported; the independent prostate re-run is noted.',

    'the figure quoted in the text. Primary runs are reported; the independent prostate re-run is noted. "Gate passes" is a per-seed '
    'count on both cohorts: at λ = 1.0 on prostate the three seeds give LDI 1.41, 1.44 and 1.70, i.e. two of three below the gate, for a '
    'mean of 1.51. We nonetheless carry the prostate verdict on the mean rather than on the seed count, because the spread between seeds '
    'at that dose (SD 0.16, and 0.86 in the independent re-run) is wider than the distance from the mean to the gate; the head-and-neck '
    'figure of 7/9 is quoted as a seed count because there all three seeds are sub-gate at λ = 0.5 with a spread of 0.25.',

    'table2 footnote: accepted definition')

# ---------------------------------------------------------------- 3. 2.2 -> 2.18
rep('against 2.2 in the three-seed stability runs of Table 1',
    'against 2.18 in the three-seed stability runs of Table 1', 'text: 2.2 -> 2.18 (a)')
rep('whose baseline LDI was 2.2 and which crossed the gate only under dose',
    'whose baseline LDI was 2.18 and which crossed the gate only under dose', 'text: 2.2 -> 2.18 (b)')
rep('| Head and neck (16 patients, GSE268014) | etiological (HPV) | 0.59 | ≈ 0.27 | ≈ 2.2 | non-empty |',
    '| Head and neck (16 patients, GSE268014) | etiological (HPV) | 0.59 | ≈ 0.27 | 2.18 | non-empty |', 'table1: 2.2 -> 2.18')

# ---------------------------------------------------------------- 4. 0/12 vs 0/15
rep('the two differ only because λ = 0 is not a repair point',
    'the two counts differ only because λ = 0 is not a repair point', 'finding7: "the two counts differ"')
rep('0 of 15 seed × dose cells passed the dual gate in either domain',
    '0 of 12 dosed seed × dose cells passed the dual gate in either domain (0 of 15 counting the three undosed baselines)',
    'cross-domain results: 0/12')
rep('column is the prediction made from τ_base/σ̂ before any dose was chosen, and “accepted cells” is what was\nobserved out of 15 seed × dose cells.',
    'column is the prediction made from τ_base/σ̂ before any dose was chosen, and “accepted cells” is what was\nobserved out of the 12 dosed seed × dose cells (λ > 0); λ = 0 is the unrepaired baseline, not a repair point,\nand is excluded from the count.',
    'table5 legend: 12 dosed cells')

# ---------------------------------------------------------------- 8. Five -> Six
rep('can be made auditable and pre-computable. Five points follow.',
    'can be made auditable and pre-computable. Six points follow.', 'discussion: five -> six')

# ---------------------------------------------------------------- 9. two units: defer numbers
rep('defined per spot, and repair acts there (57,872 spots over 16 sections in the head-and-neck cohort, a mean of 3,617 per section).',
    'defined per spot, and repair acts there (thousands of spots per section; the counts are given where the scope condition is '
    'developed).', 'two units: defer spot counts')

# ---------------------------------------------------------------- copy-editing
rep('the spread across seeds within a run is wider than the difference between runs. every other dose left',
    'the spread across seeds within a run is wider than the difference between runs. Every other dose left',
    'grammar: every -> Every')

rep('**Table S4.** External cohort: independent non-hardened replication and permutation-depth recheck (B = 2,000 → 10,000; 0/15 gate flips; σ̂ change ≤ 4.4%).',
    '**Table S4.** External cohort: independent non-hardened replication and permutation-depth recheck (B = 2,000 → 10,000; 0 of 15 '
    'external-cohort runs changed gate decision; σ̂ change ≤ 4.4%). This recheck concerns permutation depth only; dose-grid drift of σ̂ '
    'is a separate quantity and is checked in Table S14.',
    'table s4 caption: disambiguate')

# ---------------------------------------------------------------- SI list: add S13 / S14
rep(
    '"Accepted cells" counts dosed (λ > 0) seed × dose cells passing both gates: leakage (LDI < 1.645) and fidelity (τ_LDO ≥ 0.7 · τ_base); '
    'λ = 0 is the unrepaired baseline and is not a repair point. The two backbones agree on the prediction and on the outcome in both arms.',

    '"Accepted cells" counts dosed (λ > 0) seed × dose cells passing both gates: leakage (LDI < 1.645) and fidelity (τ_LDO ≥ 0.7 · τ_base); '
    'λ = 0 is the unrepaired baseline and is not a repair point. The two backbones agree on the prediction and on the outcome in both arms.\n\n'
    '**Table S13.** Cross-domain sibling-unit inflation, per seed and per dose: τ_LOO, τ_LGO, their difference Δ, LDI, and the dual-gate '
    'verdict for all 30 seed × dose cells of the two non-biological cohorts.\n\n'
    '**Table S14.** Dose-grid drift of σ̂ and the gate-robustness check that supports the pre-computability claim: for every external-cohort '
    'cell, the run\'s own σ̂, the LDI computed against it, the LDI recomputed against the baseline σ̂, whether the gate decision changes, and '
    'the movement of τ_LOO alongside that of σ̂.',

    'si list: add S13/S14')

# ---------------------------------------------------------------- ref 17: add verified DOI
rep('17. [Dataset] Simkin, D. et al. Spatial analysis of head and neck cancer identifies two ecosystems with distinct modes of '
    'epithelial-to-mesenchymal transition. Nat. Genet. 58, 2240–2253 (2026). GSE268014.',
    '17. [Dataset] Simkin, D. et al. Spatial analysis of head and neck cancer identifies two ecosystems with distinct modes of '
    'epithelial-to-mesenchymal transition. Nat. Genet. 58, 2240–2253 (2026). https://doi.org/10.1038/s41588-026-02723-7. GSE268014.',
    'ref17: add DOI')

with io.open(DST, 'w', encoding='utf-8') as f:
    f.write(t)

print('v7 %d chars -> v8 %d chars' % (orig_len, len(t)))
print('wrote', DST)
