# -*- coding: utf-8 -*-
"""v12: cover letter reframed onto the post-hoc case; title page word count refreshed."""
import io, os, re

D = os.path.join('papers', '20_MRP-ST-Repair_Patterns')
CL = os.path.join(D, 'CoverLetter_Patterns.md')
TP = os.path.join(D, 'TitlePage_Patterns.md')

s = io.open(CL, encoding='utf-8').read()


def rep(old, new, n=1):
    global s
    c = s.count(old)
    assert c == n, 'count=%d for %r' % (c, old[:80])
    s = s.replace(old, new)


rep('The gap we close is between *detecting* the failure and *repairing* it.',
    'One point of positioning should be stated at the outset, because it determines how the contribution '
    'should be read. Group leakage is not an unrecognised failure mode. It is one of the eight types in the '
    'leakage taxonomy of Kapoor and Narayanan (Patterns 4, 100804, 2023), documented there across 294 '
    'papers in 17 fields, and blocked or group-disjoint cross-validation is the established prescription '
    'wherever data carry temporal, spatial or hierarchical structure. Those are design-time remedies, and '
    'they are the right ones for someone who has not trained yet. The case we address is the one they do '
    'not cover, and in practice it is the common one: the representation already exists. A practitioner has '
    'inherited a model or an embedding that reports high held-out performance, the split that produced the '
    'number was at observation level, and neither the split nor the training run can be redone cheaply. '
    'Re-running under a group-disjoint split is a different experiment, and it estimates what the '
    'performance would have been rather than how much of the number already reported is group-driven; a '
    'checklist returns a disclosure rather than a measurement. The label-dependence index is the '
    'counterfactual measurement taken on the representation as it stands, and the sibling-unit trap is the '
    'effect it exists to detect.\n\n'
    'The second gap we close is between *detecting* the failure and *repairing* it.')

rep('We do not claim priority for the direction of the error. Blocked cross-validation is the established '
    'prescription wherever data have spatial, temporal or hierarchical structure, re-validation with '
    'spatially disjoint blocks has collapsed apparent predictive power to quasi-null, and cross-field '
    'surveys have documented the resulting optimism across hundreds of papers. What those reports supply '
    'is a prescription and a checklist: which split to use before training. What they do not supply is a '
    'measurement. Our increment is the calibrated magnitude: a number in permutation-null units that says '
    'how much of a reported result the shortcut accounts for, is comparable across cohorts and domains, '
    'stays valid for a representation that already exists and whose split can no longer be redesigned, and '
    'remains interpretable after an intervention has been applied, which is what makes it usable as an '
    'acceptance criterion rather than as a design rule.',
    'Our increment is the calibrated magnitude: a number in permutation-null units that says how much of a '
    'reported result the shortcut accounts for, is comparable across cohorts and domains, stays valid for '
    'a representation whose split can no longer be redesigned, and remains interpretable after an '
    'intervention has been applied, which is what makes it usable as an acceptance criterion rather than '
    'as a design rule.')

io.open(CL, 'w', encoding='utf-8').write(s)
print('cover letter updated')

t = io.open(TP, encoding='utf-8').read()
m = io.open(os.path.join(D, 'MRP-ST-Repair_manuscript_Patterns_v12.md'), encoding='utf-8').read()
a = m.index('## INTRODUCTION')
b = m.index('## EXPERIMENTAL PROCEDURES')
body = '\n'.join(l for l in m[a:b].split('\n') if not l.strip().startswith('|'))
w = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'+/-]*", body))
old = [l for l in t.split('\n') if 'Main text is approximately' in l]
assert len(old) == 1
new = re.sub(r'Main text is approximately [\d,]+ words[^.]*\.',
             'Main text is approximately %s words (Introduction through Limitations; tables and figure '
             'legends excluded).' % format(w, ','), old[0])
io.open(TP, 'w', encoding='utf-8').write(t.replace(old[0], new))
print('main text words ->', w)
