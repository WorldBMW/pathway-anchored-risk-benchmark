# -*- coding: utf-8 -*-
"""v11: cover letter (novelty increment, five results, precondition as a tool) + title page word count."""
import io, os, re

D = os.path.join('papers', '20_MRP-ST-Repair_Patterns')
CL = os.path.join(D, 'CoverLetter_Patterns.md')
TP = os.path.join(D, 'TitlePage_Patterns.md')

# ------------------------------------------------------------------ cover letter
s = io.open(CL, encoding='utf-8').read()


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, 'count=%d for %r' % (c, old[:80])
    s = s.replace(old, new)


rep('Six results, in the order we would ask a reader to weigh them. The first is the one we would want to '
    'survive if everything else were withdrawn, because it is a statement about evaluation rather than '
    'about any method.',
    'Five results, in the order we would ask a reader to weigh them. The first is the one we would want '
    'to survive if everything else were withdrawn, because it is a statement about evaluation rather '
    'than about any method.')

rep('1. **The sibling-unit trap: unit-level evaluation is optimistic whenever a group contributes more '
    'than one unit.** A held-out unit is re-identified through the siblings its group left in training, '
    'so unit-level cross-validation stays pinned at ceiling while group-level holdout collapses: the '
    'split that looks more conservative is the one that flatters the model. We produce the effect with '
    'one knob ',
    '1. **The sibling-unit trap: unit-level evaluation is optimistic whenever a group contributes more '
    'than one unit, and we give the first calibrated measure of how much.** A held-out unit is '
    're-identified through the siblings its group left in training, so unit-level cross-validation stays '
    'pinned at ceiling while group-level holdout collapses: the split that looks more conservative is '
    'the one that flatters the model. We do not claim priority for the direction of the error. Blocked '
    'cross-validation is the established prescription wherever data have spatial, temporal or '
    'hierarchical structure, re-validation with spatially disjoint blocks has collapsed apparent '
    'predictive power to quasi-null, and cross-field surveys have documented the resulting optimism '
    'across hundreds of papers. What those reports supply is a prescription and a checklist: which split '
    'to use before training. What they do not supply is a measurement. Our increment is the calibrated '
    'magnitude: a number in permutation-null units that says how much of a reported result the shortcut '
    'accounts for, is comparable across cohorts and domains, stays valid for a representation that '
    'already exists and whose split can no longer be redesigned, and remains interpretable after an '
    'intervention has been applied, which is what makes it usable as an acceptance criterion rather than '
    'as a design rule. We produce the effect with one knob ')

# drop item 5 (precondition test) from the cover-letter list and renumber 6 -> 5
lines = s.split('\n')
idx = [i for i, l in enumerate(lines) if re.match(r'^\d\. \*\*', l)]
assert len(idx) == 6, idx
del lines[idx[4]:idx[5]]
idx2 = [i for i, l in enumerate(lines) if re.match(r'^\d\. \*\*', l)]
assert len(idx2) == 5, idx2
assert lines[idx2[4]].startswith('6. **'), lines[idx2[4]][:20]
lines[idx2[4]] = '5. **' + lines[idx2[4]][len('6. **'):]
s = '\n'.join(lines)

rep('We use spatial transcriptomics as the validation domain because it is a demanding test:',
    'One further item is a tool rather than a result and is therefore not numbered above. Proposition 1 '
    'is a precondition test: from the unrepaired baseline alone it tells a practitioner which acceptance '
    'criterion is coherent for their cohort, before any repaired model is trained. We report it as a '
    'critical retention c* (the largest retention requirement under which a feasible dose can exist; '
    '0.28 on our simulation, 0.69 cervical, 0.75 head and neck, 0.80 prostate) rather than as a verdict '
    'taken at a threshold we chose, so the normative choice stays with the deployer. Its proof is a '
    'one-line monotonicity check and we count it as part of the protocol.\n\n'
    'We use spatial transcriptomics as the validation domain because it is a demanding test:')

rep('One evidentiary point is stated in the cover letter because it bounds how the operator should be '
    'read, and the same sentence appears in the Discussion: the real-data cases in which repair removed '
    'leakage the instrument had detected are confined to two small cohorts of the validation domain '
    '(head and neck, 16 patients; prostate, 52 patients, seed-fragile).',
    'One evidentiary point is stated in the cover letter because it bounds how the operator should be '
    'read, and the same statement appears in the Discussion. The instrument issued a verdict in every '
    'cohort from pre-repair quantities alone, and the verdict matched what was subsequently observed in '
    'six of six cohorts; that calibration is the positive result and it does not depend on cohort size. '
    'The accepted set on real clinical data is correspondingly small: three of eighteen dosed seed × '
    'dose cells across two cohorts of the validation domain (head and neck, 16 patients; prostate, 52 '
    'patients), which is what the framework predicts in advance for single-section-per-donor cohorts. '
    'On prostate the point estimate passes with a seed spread (SD 0.16 primary, 0.86 on an independent '
    're-run) wider than the distance from the mean to the gate, so we grade it as a single operating '
    'point with measured spread rather than as a replicated acceptance.')

io.open(CL, 'w', encoding='utf-8').write(s)
print('cover letter updated')

# ------------------------------------------------------------------ title page
t = io.open(TP, encoding='utf-8').read()
m = io.open(os.path.join(D, 'MRP-ST-Repair_manuscript_Patterns_v11.md'), encoding='utf-8').read()
a = m.index('## INTRODUCTION')
b = m.index('## EXPERIMENTAL PROCEDURES')
body = '\n'.join(l for l in m[a:b].split('\n') if not l.strip().startswith('|'))
w = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'+/-]*", body))
old = [l for l in t.split('\n') if 'Main text is approximately' in l]
assert len(old) == 1, old
new = re.sub(r'Main text is approximately [\d,]+ words[^.]*\.',
             'Main text is approximately %s words (Introduction through Limitations; tables and figure '
             'legends excluded).' % format(w, ','), old[0])
t = t.replace(old[0], new)
io.open(TP, 'w', encoding='utf-8').write(t)
print('title page word count ->', w)
