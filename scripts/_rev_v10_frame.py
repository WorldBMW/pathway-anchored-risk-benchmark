# -*- coding: utf-8 -*-
"""v10: 贡献重心重排 —— sibling-unit trap / evaluation hygiene 升为第一贡献，
Proposition 1 与 repair operator 降为配套诊断与干预。"""
import io, os, re, sys

SRC = 'papers/20_MRP-ST-Repair_Patterns/MRP-ST-Repair_manuscript_Patterns_v9.md'
DST = 'papers/20_MRP-ST-Repair_Patterns/MRP-ST-Repair_manuscript_Patterns_v10.md'

s = io.open(SRC, encoding='utf-8').read()
def rep(old, new, n=1):
    global s
    c = s.count(old)
    if c != n:
        for v in (old.replace('’', "'"), old.replace("'", '’'),
                  old.replace('‘', "'"), old.replace('“', '"'), old.replace('”', '"')):
            if s.count(v) == n:
                old = v
                c = n
                break
    assert c == n, 'count=%d for %r' % (c, old[:70])
    s = s.replace(old, new)

def rep_line(prefix, new):
    """replace the whole line starting with prefix"""
    global s
    lines = s.split('\n')
    idx = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    assert len(idx) == 1, 'line prefix %r -> %d' % (prefix, len(idx))
    lines[idx[0]] = new
    s = '\n'.join(lines)

# ---------------------------------------------------------------- 1. title
rep('# An auditable instrument for identity leakage in group-structured data: feasibility theory, decision boundaries, and validation in spatial transcriptomics',
    '# An auditable instrument for identity leakage in group-structured data: the sibling-unit trap, decision boundaries, and validation in spatial transcriptomics')

# ---------------------------------------------------------------- 2. highlights
HL = [
 '1. Sibling units let held-out units be re-identified, so unit-level splits overstate',
 '2. Group-structured data let a model win by recognising the group, not the target',
 '3. A calibrated index grades leakage and stays non-blind after de-identification',
 '4. Where each group has one unit, no accepted repair improved a downstream endpoint',
]
for h in HL:
    assert len(h) <= 85, 'HIGHLIGHT too long (%d): %s' % (len(h), h)
lines = s.split('\n')
i = lines.index('## HIGHLIGHTS')
j = i + 1
while not lines[j].strip():
    j += 1
assert lines[j].startswith('1. ') and lines[j + 3].startswith('4. ')
lines[j:j + 4] = HL
s = '\n'.join(lines)

# ---------------------------------------------------------------- 3. in brief
BRIEF = ('Many datasets are group-structured, so a model can win by recognising the group rather than the target property. '
         'Bai and colleagues show that unit-level cross-validation hides this, and supply an auditable instrument: '
         'a calibrated index, a rule for the split, and boundaries saying in advance whether repair can pay.')
assert len(BRIEF.split()) <= 50, len(BRIEF.split())
rep_line('Many datasets are group-structured', BRIEF)

# ---------------------------------------------------------------- 4. summary
SUMMARY = ('When the same person, site, or device contributes many observations, a model can score well by recognising '
 'which group an observation came from rather than the property it should predict. We call this identity leakage, and '
 'our first result is about measuring it: whenever a group contributes several units, unit-level cross-validation stays '
 'at ceiling while group-level holdout collapses, because held-out units are re-identified through their siblings. A split '
 'at the wrong level is therefore optimistic. Around it, an auditable protocol: a calibrated index grading label dependence '
 'under leave-one-group-out, itself tested after repair against controls with known ground truth; a condition deciding in '
 'advance whether any dose can both remove identity and preserve signal; and two boundaries saying which cohorts are repairable. '
 'The operator is deliberately standard. One domain is validated end to end; where a group contributes one unit it recommends '
 'against repair, and no accepted repair improved an endpoint.')
w = len(SUMMARY.split())
assert w <= 150, 'SUMMARY %d words' % w
print('summary words:', w)
rep_line('When the same person, site, or device contributes many observations', SUMMARY)

# ---------------------------------------------------------------- 5. graphical abstract
rep('A model trained on such data fits the training set well while collapsing under leave-one-group-out: it recognised the group, not the target property. *(2) The auditable loop.* Detect with the calibrated index under leave-one-group-out; pre-compute the signal-to-null ratio and compare it with the feasibility threshold of Proposition 1; repair at training time with a group-adversarial operator at dose λ; re-audit against three axes.',
    'A model trained on such data fits the training set well while collapsing under leave-one-group-out: it recognised the group, not the target property. Split at the unit level the collapse is invisible, because a held-out unit is re-identified through the siblings its group left in training. *(2) The auditable loop.* Split at the group level first, then detect with the calibrated index under leave-one-group-out; pre-compute the signal-to-null ratio and test it against the precondition 1.645/c to learn whether any dose can both remove identity and preserve signal; repair at training time with a group-adversarial operator at dose λ; re-audit against three axes.')

# ---------------------------------------------------------------- 6. introduction: tier the findings
i0 = s.index('Seven findings constitute the contribution:')
i1 = s.index('**Where the novelty lies, stated plainly.**')
region = s[i0:i1]
item_idx = [(m.start(), m.group(1)) for m in re.finditer(r'(?m)^(\d)\. \*\*', region)]
assert [n for _, n in item_idx] == ['1', '2', '3', '4', '5', '6', '7'], item_idx
bounds = [p for p, _ in item_idx] + [len(region)]
blocks = {}
for k in range(7):
    blocks[str(k + 1)] = region[bounds[k]:bounds[k + 1]].strip()

def retitle(block, old_start, new_start):
    assert block.startswith(old_start), block[:80]
    return new_start + block[len(old_start):]

# item 1 -> new: the sibling-unit trap (written fresh)
NEW1 = ('1. **The sibling-unit trap: unit-level evaluation is optimistic whenever a group contributes more than one unit.** '
 'This is the first of our two claims and it depends on none of the machinery below: not on the repair, not on the index, '
 'and not on the domain. When a group contributes several units, a held-out unit is re-identified through the siblings its '
 'group left in training, so unit-level cross-validation stays pinned at ceiling while group-level holdout collapses. The '
 'split that looks more conservative is the one that flatters the model. We produce the effect with a single knob (units per '
 'group k ∈ {2, 4, 8} at 16 groups, dose λ, three seeds): in 45 of 45 runs unit-level leave-one-out stayed at its class-size '
 'ceiling at every dose while the group-level statistic collapsed (0.713 → 0.230 at k = 2, λ = 5). It is not an artefact of '
 'the simulator. On the two real cross-domain cohorts audited below, where a subject contributes about 343 windows and a '
 'measurement batch about 1,391 measurements, τ_LOO − τ_LGO is positive in all 15 seed × dose cells of each cohort, and the '
 'two cohorts’ per-cell ranges do not overlap (+0.0010 to +0.0095 on HAR against +0.0209 to +0.0697 on gas drift; Table 5, '
 'Table S13). The companion study’s leave-one-donor-out AUROC collapse from 1.00 to 0.497 is the same effect in the wild.[1] '
 'The remedy is a rule rather than a method: **whenever a group contributes more than one unit, acceptance must be measured '
 'at the group level, never the unit level.** It costs nothing, it applies to any model on any group-structured dataset, and '
 'it is the part of this paper that survives if every other claim is withdrawn.')

OLD1_HEAD = '1. **A calibrated instrument with measured operating characteristics, and a standard operator for it to grade.**'
b1 = retitle(blocks['1'], OLD1_HEAD,
             '2. **An auditable instrument: a calibrated statistic with measured operating characteristics and an acceptance protocol.**')
b1 = b1.rstrip() + ' A practical corollary, established head-to-head below: in-sample criteria cannot certify acceptance, because methods that are indistinguishable on the in-sample memorization gap differ in kind on the group-level statistic.'

b3 = retitle(blocks['3'], '3. **Decision boundary I', '3. **Decision boundary I')

b4 = retitle(blocks['4'], '4. **Decision boundary II: a group-count feasibility boundary, and a sibling-unit trap.**',
             '4. **Decision boundary II: a group-count feasibility boundary.**')
rep_in_b4 = ('The same grid exposes a trap that generalises beyond our validation domain: when each group contributes several '
             'units, unit-level cross-validation stays pinned at ceiling while group-level holdout collapses, because held-out '
             'units are re-identified through their siblings. Acceptance must be measured at the group level.')
assert b4.count(rep_in_b4) == 1
b4 = b4.replace(rep_in_b4,
    'The consequence for practice is a precondition rather than a guarantee: repair needs a group budget, and the budget grows as the signal weakens.')

b2 = retitle(blocks['2'], '2. **A pre-computable feasibility condition for the detect-then-accept gate (Proposition 1).**',
             '5. **A precondition test for the detect-then-accept gate (Proposition 1).**')
b5 = retitle(blocks['5'], '5. **Auditability as a discriminator: a failure-mode taxonomy.**',
             '6. **Auditability as a discriminator: a failure-mode taxonomy.**')
b6 = retitle(blocks['6'], '6. **A scope condition, stated as such.**', '7. **A scope condition, stated as such.**')
b7 = retitle(blocks['7'], "7. **The theory's predictions are tested outside the life sciences.**",
             "8. **The predictions hold outside the life sciences, and one of them is a consistency check.**")

HEAD = ('The contribution has two tiers. Two findings carry it, and neither of them is the repair operator. Six further '
        'findings are the diagnostics and the intervention that make the two usable:')
TIER2 = ('**Second tier: diagnostics and one intervention.**')
new_region = ('\n\n' + HEAD + '\n\n' + NEW1 + '\n\n' + b1 + '\n\n' + TIER2 + '\n\n'
              + b3 + '\n\n' + b4 + '\n\n' + b2 + '\n\n' + b5 + '\n\n' + b6 + '\n\n' + b7 + '\n\n')
s = s[:i0] + new_region + s[i1:]

# ---------------------------------------------------------------- 7. where the novelty lies
rep_line('**Where the novelty lies', '**Where the novelty lies, stated plainly.** Finding 1 is the claim we would want to survive if everything else here were withdrawn: it is a statement about evaluation rather than about any method, it errs in one direction only (a unit-level split flatters a model rather than penalising it), and adopting the fix requires nothing new. Finding 2 is the instrument that makes findings 3 to 8 readable; the operator inside it is a standard adversarial head, chosen deliberately, because a familiar operator makes the verdict easier to audit and easier to distrust. Findings 3 to 8 are diagnostics and one intervention: they say when repair is worth attempting, when it is provably not, and how far the predictions travel, and they are the parts a better operator or a larger cohort would revise first. A reader who takes the operator away keeps the trap, the instrument and the boundaries; a reader who takes the instrument away still keeps the rule about the split, which costs nothing and applies everywhere.')

# ---------------------------------------------------------------- 8. Remark 2: no longer self-defeating
rep('Proposition 1 is an identifiability condition, not a limit theorem or a new estimator: its proof is one line of monotonicity and we claim no mathematical novelty for it. It is stated as a proposition so that a practitioner can cite the threshold instead of re-deriving it, and so that the threshold can be quoted as a function of c.',
    'Proposition 1 is an identifiability condition rather than a limit theorem or a new estimator: its proof is one line of monotonicity, and its role here is to make a threshold quotable rather than to add to statistical theory. It is stated as a proposition so that a practitioner can cite the threshold instead of re-deriving it, and so that the threshold can be quoted as a function of c.')

# ---------------------------------------------------------------- 9. Results: promote the trap to its own section
i = s.index('**Sibling-unit inflation: unit-level cross-validation overestimates generalization whenever groups contribute multiple units.**')
j = s.index('it costs nothing to adopt.', i) + len('it costs nothing to adopt.')
s = s[:i] + s[j:]
s = s.replace('\n\n\n### Auditability', '\n\n### Auditability')

NEWSEC = """### The sibling-unit trap: unit-level evaluation is optimistic whenever a group contributes more than one unit

We place this result immediately after the instrument because it is the most transferable finding in the paper and it does not depend on the repair. We generated a second phase grid that differs from the group-count grid of Decision boundary II in one respect: units per group k ∈ {2, 4, 8} at 16 groups, with the shared group fingerprint as the sole leakage channel and dose λ on the third axis, three seeds per cell, and we evaluated two statistics side by side: the unit-level leave-one-out τ used so far, and the group-level τ_LDO in which every unit of a held-out group is removed jointly. At λ = 0 the two coincide at the ceiling (0.713 for the 18-versus-14 unit classes): the shared program transfers across groups, as it should. After repair they separate dramatically (Figure 3C): unit-level leave-one-out stayed pinned at the ceiling in all 45 runs across k ∈ {2, 4, 8} (each k at its own class-size ceiling), while τ_LDO collapsed (at k = 2: 0.713 → 0.585 at λ = 2 and → 0.230 at λ = 5). The unit-level split is silently rescued by sibling units: the held-out unit's group remains in training through its siblings, so "generalization" is partly a re-identification match. The companion study's leave-one-donor-out AUROC collapse is exactly this effect in the wild; here it is produced and controlled with a single knob.

The effect is not confined to simulation. On the two real cross-domain cohorts audited below, a subject contributes about 343 windows and a measurement batch about 1,391 measurements, and τ_LOO − τ_LGO is positive in all 15 seed × dose cells of each cohort, with per-cell ranges that do not overlap between cohorts (HAR +0.0010 to +0.0095; gas drift +0.0209 to +0.0697; Table 5, Table S13). The trap therefore rests on three independent supports: 45 of 45 simulated runs, 30 of 30 real cross-domain cells, and a clinical cohort in the companion study.[1] None of them is one of the two small cohorts that carry the repair result, which is why we separate this claim from the question of how far the positive repair evidence extends.

Our repairability claims are therefore computed at k = 1, where the two statistics coincide by construction, and we state the resulting recommendation as a protocol rule: **whenever a group contributes more than one unit, model acceptance must be measured at the group level, never the unit level.** The grid probes k ∈ {1, 2, 4, 8}, which is three orders of magnitude below the representation-level group size of our validation cohorts (about 3,617 spots per donor) and is not intended to match it: what decides whether the trap binds is the number of units a group contributes *at the resolution at which the model is consumed*. In the validation domain that number is one section per donor, so the trap is dormant and the two statistics coincide; in the cross-domain cohorts it is about 343 windows per subject and 1,391 measurements per batch, so the trap is live there (Figure 5B). A reader who compares the grid's k against a spot count is comparing the wrong pair of numbers. The rule is a contribution about evaluation hygiene rather than about our operator: it applies to any model on any group-structured dataset, and it costs nothing to adopt.

"""
anchor = '### Proposition 1: when is a detect-then-accept gate feasible?'
assert s.count(anchor) == 1
s = s.replace(anchor, NEWSEC + anchor)

rep('### Decision boundary II: a group-count feasibility boundary, and the sibling-unit trap',
    '### Decision boundary II: a group-count feasibility boundary')

# ---------------------------------------------------------------- 10. cross-domain: falsifiable first
rep('### Cross-domain audit: do the predictions hold outside the validation domain?',
    '### Cross-domain audit: what reproduces outside the validation domain, and what does not')
rep('preserving each cohort’s natural joint distribution.',
    'preserving each cohort’s natural joint distribution. Two predictions were tested and they are not equally strong, so we '
    'report the falsifiable one first. The emptiness of the dual gate turns out to be a consistency check in these two '
    'cohorts: the fidelity axis was satisfied throughout, so the gate could only fail on the leakage axis, and prediction and '
    'observation are therefore close to the same statement. Decision boundary I is different in kind: it predicted an '
    '*ordering* between the two cohorts at comparable encoded identity, an identifiability-based account would have predicted '
    'no ordering, and the prediction could have failed.')

# move boundary I before proposition 1
i = s.index('**Decision boundary I reproduced with real data.**')
j = s.index('**Proposition 1 held out of domain.**')
assert i > j
para_b1 = s[i:s.index('**The operator transferred, and so did the three-axis reading.**')]
s = s[:i] + s[len(para_b1) + i:]
s = s.replace('**Proposition 1 held out of domain.**', para_b1.rstrip() + '\n\n**Proposition 1 held out of domain.**')
rep('The out-of-domain prediction we defend as falsifiable is decision boundary I, tested next: it predicted an ordering between cohorts, not an empty set, and it could have failed.',
    'The out-of-domain prediction we defend as falsifiable is decision boundary I, reported above: it predicted an ordering between cohorts, not an empty set, and it could have failed.')
rep('Unlike the feasibility check above, this is a prediction that could have failed:',
    'Unlike the consistency check reported next, this is a prediction that could have failed:')

# ---------------------------------------------------------------- 11. discussion: reorder
i0 = s.index('## DISCUSSION')
i1 = s.index('### Implications for fairness and evaluation integrity')
disc = s[i0:i1]
parts = disc.split('\n\n')
KEYS = ['Auditability, not accuracy', 'A feasibility theory turns', 'Two decision boundaries make',
        'Evaluation hygiene is a separate', 'Auditability discriminates', 'How far the positive repair']
found = {}
for p in parts:
    if p.startswith('**'):
        for k in KEYS:
            if p.startswith('**' + k):
                assert k not in found
                found[k] = p
assert len(found) == 6, found.keys()
drops = set(found.values())
renamed = found['A feasibility theory turns'].replace(
    '**A feasibility theory turns acceptance from tuning into a precondition.**',
    '**A precondition test turns acceptance from tuning into a check.**')
assert renamed != found['A feasibility theory turns']
renamed = renamed.replace(
    'Proposition 1 says that the intuitive dual gate is empty whenever the pre-repair association exceeds ≈ 2.35 null scales, and Remark 1 says the conflict worsens as cohorts grow.',
    'Proposition 1 says that the intuitive dual gate is empty whenever the pre-repair association exceeds ≈ 2.35 null scales, and Remark 1 says the conflict worsens as cohorts grow. It is a precondition test and not a theory of repair: it costs one baseline fit, and it tells the practitioner which acceptance criterion to adopt, not what any particular dose will return.')
found['A feasibility theory turns'] = renamed
order = ['Evaluation hygiene is a separate', 'Auditability, not accuracy', 'A feasibility theory turns',
         'Two decision boundaries make', 'Auditability discriminates', 'How far the positive repair']
lead = [p for p in parts if 'Six points follow.' in p]
assert len(lead) == 1
rest = [p for p in parts if p not in drops]
li = rest.index(lead[0])
newparts = rest[:li + 1] + [found[k] for k in order] + rest[li + 1:]
s = s[:i0] + '\n\n'.join(newparts) + s[i1:]

rep('Identity leakage is a structural property of how data are collected, not a property of any model or field, and the contribution we want to emphasise is not that we removed it in one domain but that the whole loop (detect, repair, re-audit, accept) can be made auditable and pre-computable.',
    'Identity leakage is a structural property of how data are collected, not a property of any model or field. The contribution we want to emphasise first is not that we removed it in one domain, but that the split conventionally used to measure it is wrong in a direction that flatters the model, that correcting the split is free, and that once the split is right the loop around it (detect, repair, re-audit, accept) can be made auditable.')

# ---------------------------------------------------------------- 12. LDI: reporting unit, not new test
rep('LDI should be read as a calibrated cross-validated rank statistic, and we state which parts of it are standard and which carry the claim.',
    'LDI is not offered as a new test. It is a reporting unit: a calibrated cross-validated rank statistic expressed in null-scale units, chosen because three things the protocol needs are awkward in p-value units (comparability across cohorts of different size, a threshold computable before any repair, and an acceptance record a third party can re-derive from a manifest). What follows states which parts of it are standard and which carry the claim.')

# ---------------------------------------------------------------- 13. balance is not a precondition
rep('The cost is resolution: n = 16 against 52 on the prostate cohort, which is one reason the head-and-neck acceptance result is the more fragile of the two.',
    'The cost is resolution: n = 16 against 52 on the prostate cohort, which is one reason the head-and-neck acceptance result is the more fragile of the two. Balance is not a precondition of the instrument: the prostate cohort is severely unbalanced (48 tumour sections against 4 benign) and the index still returns a graded verdict there, so the subset is a choice about resolution in this arm rather than a requirement of the method.')

# ---------------------------------------------------------------- 14. limitation wording
rep('we do not present this as a test of the feasibility theory',
    'we do not present this as a test of the feasibility condition')

io.open(DST, 'w', encoding='utf-8').write(s)
print('written', DST, len(s), 'chars')
words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'+/-]*", s))
print('approx words:', words)
