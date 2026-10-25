# -*- coding: utf-8 -*-
"""v10 配套：TitlePage 与 CoverLetter 随贡献重排同步更新。"""
import io, re

D = 'papers/20_MRP-ST-Repair_Patterns/'
OLD_T = 'An auditable instrument for identity leakage in group-structured data: feasibility theory, decision boundaries, and validation in spatial transcriptomics'
NEW_T = 'An auditable instrument for identity leakage in group-structured data: the sibling-unit trap, decision boundaries, and validation in spatial transcriptomics'

# ------------------------------------------------------------------ TitlePage
p = D + 'TitlePage_Patterns.md'
s = io.open(p, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n:
        for v in (old.replace('\u2019', "'"), old.replace("'", '\u2019')):
            if s.count(v) == n:
                old, c = v, n
                break
    assert c == n, 'count=%d for %r' % (c, old[:60])
    s = s.replace(old, new)

rep(OLD_T, NEW_T)
rep('**Teaser (TOC, ≤120 characters):** An auditable instrument measures identity leakage and predicts in advance whether repair can succeed.',
    '**Teaser (TOC, ≤120 characters):** Unit-level splits flatter models on group-structured data; an auditable index grades the leak and the repair.')
assert len('Unit-level splits flatter models on group-structured data; an auditable index grades the leak and the repair.') <= 120

rep('**Manuscript statistics:** In brief, 45 words (limit 50); Summary, 141 words (limit 150); 4 highlights (all ≤85 characters, Cell Press maximum); bigger picture box, 299 words (limit 300); 1 graphical abstract; 5 main figures; 5 main tables; 14 supplemental tables (S1–S14; S13 carries the per-seed cross-domain inflation values behind the uncertainty interval reported in the text, and S14 carries the per-cell dose-grid σ̂ drift and gate-robustness check behind the pre-computability scope condition, and S15 carries the sensitivity of the feasibility threshold to the retained fraction c); 38 references.',
    '**Manuscript statistics:** In brief, 49 words (limit 50); Summary, 150 words (limit 150); 4 highlights (all ≤85 characters, Cell Press maximum); bigger picture box, 299 words (limit 300); 1 graphical abstract; 5 main figures; 5 main tables; 15 supplemental tables (S1–S15; S13 carries the per-seed cross-domain inflation values behind the uncertainty interval reported in the text, S14 carries the per-cell dose-grid σ̂ drift and gate-robustness check behind the pre-computability scope condition, and S15 carries the sensitivity of the feasibility threshold to the retained fraction c); 39 references.')

rep('Three bands: the failure mode; the auditable loop with its two decision boundaries;',
    'Three bands: the failure mode and the split that hides it; the auditable loop, entered at the group level, with its two decision boundaries;')
io.open(p, 'w', encoding='utf-8').write(s)
print('TitlePage ok')

# ------------------------------------------------------------------ CoverLetter
p = D + 'CoverLetter_Patterns.md'
s = io.open(p, encoding='utf-8').read()
def rep2(old, new, n=1):
    global s
    c = s.count(old)
    if c != n:
        for v in (old.replace('\u2019', "'"), old.replace("'", '\u2019')):
            if s.count(v) == n:
                old, c = v, n
                break
    assert c == n, 'count=%d for %r' % (c, old[:60])
    s = s.replace(old, new)

rep2(OLD_T, NEW_T)

rep2('Our contributions are a calibrated index with operating characteristics measured on controls with known ground truth, a feasibility condition for the natural detect-then-accept gate, and two decision boundaries that say in advance whether repair is even coherent for a given cohort. The operator is what those objects are demonstrated on, and a reader who takes it away still keeps everything that can be checked.',
     'Our contributions are ordered, and the order is the point. The first is a rule about evaluation, not a method: whenever a group contributes more than one unit, unit-level cross-validation overstates generalization, because a held-out unit is re-identified through the siblings its group left in training, and acceptance must be measured at the group level. That rule is independent of everything else in the paper and costs nothing to adopt. The second is the instrument itself: a calibrated index with operating characteristics measured on controls with known ground truth, an acceptance protocol, and two decision boundaries that say in advance whether repair is even coherent for a given cohort. The third is a precondition test (Proposition 1) that makes the choice of acceptance criterion a check rather than a tuning exercise. The operator is what those objects are demonstrated on, and a reader who takes it away keeps the rule about the split, the instrument and the boundaries.')

rep2('Five results, in the order we would ask a reader to weigh them. We note at the outset that the last of them is a negative result about the operator, and that we consider it a feature of the instrument rather than a defect of the method:',
     'Six results, in the order we would ask a reader to weigh them. The first is the one we would want to survive if everything else were withdrawn, because it is a statement about evaluation rather than about any method. We note at the outset that the last of them tests predictions rather than validating utility, and that we consider the scope condition reported in the manuscript a feature of the instrument rather than a defect of the method:')

TRAP = ('1. **The sibling-unit trap: unit-level evaluation is optimistic whenever a group contributes more than one unit.** '
        'A held-out unit is re-identified through the siblings its group left in training, so unit-level cross-validation stays '
        'pinned at ceiling while group-level holdout collapses: the split that looks more conservative is the one that flatters '
        'the model. We produce the effect with one knob (units per group k ∈ {2, 4, 8} at 16 groups): in 45 of 45 runs the '
        'unit-level statistic stayed at ceiling at every dose while the group-level statistic fell to 0.230 at k = 2 and λ = 5. '
        'It is not an artefact of simulation: on the two real cross-domain cohorts below, where a subject contributes about 343 '
        'windows and a batch about 1,391 measurements, τ_LOO − τ_LGO is positive in all 15 seed × dose cells of each, with '
        'per-cohort ranges that do not overlap. The remedy is a rule, not a method: measure acceptance at the group level.')

old1 = ('1. **A feasibility theory that is computable before you repair (Proposition 1).** The intuitive dual gate (require the '
        'label dependence to be gone *and* the signal preserved) is structurally empty once the pre-repair association exceeds '
        '≈ 2.35 permutation-null scales, and the conflict worsens as cohorts grow. Both inputs are estimated from the unrepaired '
        'baseline, so the choice of acceptance criterion becomes a precondition rather than a tuning exercise. We replace the '
        'dual gate with a three-axis protocol (safety, leakage reduction, instrument non-blindness).')
new1 = ('5. **A precondition test that is computable before you repair (Proposition 1).** The intuitive dual gate (require the '
        'label dependence to be gone *and* the signal preserved) is structurally empty once the pre-repair association exceeds '
        '≈ 2.35 permutation-null scales, and the conflict worsens as cohorts grow. Both inputs are estimated from the unrepaired '
        'baseline, so the choice of acceptance criterion becomes a check rather than a tuning exercise. We replace the dual '
        'gate with a three-axis protocol (safety, leakage reduction, instrument non-blindness). The proposition is an '
        'identifiability condition with a one-line monotonicity proof; it is stated so that the threshold can be quoted as a '
        'function of the retained fraction c, and we treat it as part of the protocol rather than as the theory the paper is '
        'built on.')
rep2(old1, new1)

# renumber remaining items and append trap as item 1
for old, new in [
    ('2. **Auditability as the deliverable.**', 'ZZ2. **Auditability as the deliverable.**'),
    ('3. **Two decision boundaries, both estimable in advance.**', 'ZZ3. **Two decision boundaries, both estimable in advance.**'),
    ('4. **A failure-mode taxonomy that discriminates between methods that look alike on standard metrics.**',
     'ZZ4. **A failure-mode taxonomy that discriminates between methods that look alike on standard metrics.**'),
    ('5. **The predictions are tested outside the life sciences, not merely asserted to transfer.**',
     'ZZ6. **The predictions are tested outside the life sciences, not merely asserted to transfer.**')]:
    rep2(old, new)
for old, new in [('ZZ2.', '2.'), ('ZZ3.', '3.'), ('ZZ4.', '4.'), ('ZZ6.', '6.')]:
    rep2(old, new)
assert s.count('\n5. **A precondition test') == 1
s = s.replace('\n2. **Auditability as the deliverable.**', '\n' + TRAP + '\n\n2. **Auditability as the deliverable.**')

io.open(p, 'w', encoding='utf-8').write(s)
print('CoverLetter ok')
