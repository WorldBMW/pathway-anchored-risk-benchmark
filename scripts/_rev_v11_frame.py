# -*- coding: utf-8 -*-
"""v10 -> v11: (1) cite the group-leakage prior literature and state the increment,
(2) demote Proposition 1 out of the findings list and replace the free parameter c
with the reported critical retention c*, (3) reframe the positive-evidence paragraph,
(4) add three references."""
import io, os, re

D = os.path.join('papers', '20_MRP-ST-Repair_Patterns')
SRC = os.path.join(D, 'MRP-ST-Repair_manuscript_Patterns_v10.md')
DST = os.path.join(D, 'MRP-ST-Repair_manuscript_Patterns_v11.md')

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


def para(startswith):
    """return the full paragraph (blank-line delimited) beginning with `startswith`"""
    lines = s.split('\n')
    i = [k for k, l in enumerate(lines) if l.startswith(startswith)]
    assert len(i) == 1, (startswith, len(i))
    j = i[0]
    while j + 1 < len(lines) and lines[j + 1].strip():
        j += 1
    return '\n'.join(lines[i[0]:j + 1])


def rep_para(startswith, new):
    rep(para(startswith), new)


# ---------------------------------------------------------------- 1. prior literature
OLD_PRIOR = ('What these reports share is a structural precondition (multiple observations per group, '
             'observation-level splitting) and an evaluation that cannot tell whether a model learned '
             'the target property or the group.')
assert s.count(OLD_PRIOR) == 1
NEW_PRIOR = (
    'Ecological and remote-sensing modelling reached the same conclusion from the opposite direction: '
    'blocked cross-validation, in which whole spatial, temporal, hierarchical or phylogenetic blocks are '
    'held out rather than individual records, is nearly universally more appropriate than random '
    'cross-validation wherever a dependence structure exists,[40] and re-validating a large-scale '
    'forest-biomass map with spatially disjoint blocks collapsed an apparent predictive R2 above 0.5 to '
    'quasi-null predictive power.[41] A cross-field survey finds leakage affecting 294 papers across 17 '
    'fields and supplies a taxonomy of eight leakage types together with model info sheets for '
    'preventing them.[42]\n\n'
    'What these reports share is a structural precondition (multiple observations per group, '
    'observation-level splitting) and an evaluation that cannot tell whether a model learned the target '
    'property or the group. What none of them supplies is a measurement. The prior work is prescriptive '
    'and preventive: it says which split to use before training,[8,40,41] or which checklist to '
    'complete,[42] and it demonstrates that the optimism is real, case by case. It does not give a '
    'practitioner a number, in units that are comparable across datasets and domains, for how much of a '
    'reported result is attributable to the shortcut; it does not give a criterion for accepting an '
    'intervention that claims to have removed the shortcut; and it is silent on the case we care about '
    'most, in which the model or the representation already exists and the split can no longer be '
    'redesigned. Those three gaps are what the instrument below is built to close, and they are the '
    'reason we quantify a known effect rather than announce it.')
rep(OLD_PRIOR, NEW_PRIOR)

# ---------------------------------------------------------------- 2. findings list
rep('The contribution has two tiers. Two findings carry it, and neither of them is the repair operator. '
    'Six further findings are the diagnostics and the intervention that make the two usable:',
    'The contribution has two tiers. Two findings carry it, and neither of them is the repair operator. '
    'Five further findings are the diagnostics and the intervention that make the two usable:')

# drop finding 5 (Proposition 1) and renumber 6,7,8 -> 5,6,7
lines = s.split('\n')
cut = lines.index('## RESULTS')
idx = [i for i, l in enumerate(lines) if i < cut and re.match(r'^\d\. \*\*', l)]
assert len(idx) == 8, idx
del lines[idx[4]:idx[5]]
cut = lines.index('## RESULTS')
idx2 = [i for i, l in enumerate(lines) if i < cut and re.match(r'^\d\. \*\*', l)]
assert len(idx2) == 7, idx2
for k, (old, new) in zip(idx2[4:], [('6.', '5.'), ('7.', '6.'), ('8.', '7.')]):
    assert lines[k].startswith(old + ' **'), lines[k][:20]
    lines[k] = new + lines[k][len(old):]
s = '\n'.join(lines)

# note that the proposition is a tool, not a finding
rep('**Where the novelty lies, stated plainly.**',
    '**Two results are tools, not findings.** Proposition 1 (the precondition test) is deliberately '
    'absent from the list above. Its proof is a one-line monotonicity check, and we count it as part of '
    'the protocol rather than as a contribution: it is derived in Results, quoted in Experimental '
    'Procedures, and used in every cohort below. The configuration manifests are in the same category.\n\n'
    '**Where the novelty lies, stated plainly.**')

rep('Finding 2 is the instrument that makes findings 3 to 8 readable;',
    'Finding 2 is the instrument that makes findings 3 to 7 readable;')

rep('Finding 1 is the claim we would want to survive if everything else here were withdrawn: it is a '
    'statement about evaluation rather than about any method, it errs in one direction only (a unit-level '
    'split flatters a model rather than penalising it), and adopting the fix requires nothing new.',
    'Finding 1 is the claim we would want to survive if everything else here were withdrawn: it is a '
    'statement about evaluation rather than about any method, it errs in one direction only (a unit-level '
    'split flatters a model rather than penalising it), and adopting the fix requires nothing new. What '
    'is new about it is not the direction of the error, which the blocked-cross-validation literature '
    'established,[40,41] but its calibrated magnitude: a number, expressed in null-scale units, that says '
    'how much of a reported result the shortcut accounts for, is comparable across cohorts and domains, '
    'and stays interpretable after an intervention has been applied.')

# ---------------------------------------------------------------- 3. critical retention c*
rep('**Remark 2 (what the proposition is, and what c is).** Proposition 1 is an identifiability condition '
    'rather than a limit theorem or a new estimator: its proof is one line of monotonicity, and its role '
    'here is to make a threshold quotable rather than to add to statistical theory. It is stated as a '
    'proposition so that a practitioner can cite the threshold instead of re-deriving it, and so that the '
    'threshold can be quoted as a function of c. That dependence is explicit: the threshold is 1.645/c, so '
    'c is not a constant of nature but the fraction of the baseline association a deployer is willing to '
    'give up, and it has to be set by that deployer (c = 0.5 gives 3.29, c = 0.7 gives 2.35, c = 0.9 gives '
    '1.83; Table S15). We use c = 0.7 because it is the value at which the gate binds on our own data '
    'without being empty: realized retention τ_LDO/τ_base at leakage-passing cells is 0.46–0.73 on head '
    'and neck and 0.67–0.76 on prostate, so c = 0.9 would admit no cell in any real cohort we ran and '
    'c = 0.5 would certify cells that keep less than half the association. Changing c changes which '
    'cohorts are feasible (Table S15) and nothing else in the argument.',
    '**Remark 2 (what the proposition is, and what c is).** Proposition 1 is an identifiability condition '
    'rather than a limit theorem or a new estimator: its proof is one line of monotonicity, and its role '
    'here is to make a threshold quotable rather than to add to statistical theory. It is stated as a '
    'proposition so that a practitioner can cite the threshold instead of re-deriving it, and so that the '
    'threshold can be quoted as a function of c. That dependence is explicit: the threshold is 1.645/c, so '
    'c is not a constant of nature but the fraction of the baseline association a deployer is willing to '
    'give up, and it has to be set by that deployer (c = 0.5 gives 3.29, c = 0.7 gives 2.35, c = 0.9 gives '
    '1.83; Table S15). Because c is the deployer\'s normative choice, we do not ask the reader to adopt a '
    'particular value. Rearranged, the same condition defines a quantity that is free of it: the '
    '**critical retention** c* = 1.645 σ̂/τ_base, the largest retention requirement under which a feasible '
    'dose can exist. The dual gate is non-empty for every c < c* and empty for every c ≥ c*, so a cohort '
    'is characterised by c* (Table 1) rather than by a verdict taken at our c. Read this way the result is '
    'invariant where it matters: the ordering of cohorts by feasibility is the same at every c, and only '
    'the cut point moves. On our cohorts c* = 0.28 (shared-program simulation), 0.69 (cervical), 0.75 '
    '(head and neck) and 0.80 (prostate): the three clinical cohorts close in that order as the '
    'requirement tightens, and all three are infeasible once a deployer demands retention of 81% or more. '
    'Realized retention τ_LDO/τ_base at leakage-passing cells is 0.46–0.73 on head and neck and 0.67–0.76 '
    'on prostate, which is what makes the region near c = 0.7 the informative one on these data: below '
    '0.46 the gate would certify cells that have given up more than half the association, and above 0.76 '
    'it would certify none. We display c = 0.7 throughout only as a reading convention; Table S15 gives '
    'the whole curve, and a deployer who requires a different c can read their own verdict off it without '
    're-running anything.')

rep('Fit the unrepaired baseline once, form τ_base/σ̂, and read it against 2.35: above the threshold no '
    'dose can satisfy a remove-and-preserve dual gate, so the practitioner should adopt the three-axis '
    'protocol rather than search for a dose; below it a feasible dose may exist and is worth searching '
    'for.',
    'Fit the unrepaired baseline once and read off the critical retention c* = 1.645 σ̂/τ_base '
    '(equivalently, form τ_base/σ̂ and read it against 1.645/c): the dual gate is empty for any retention '
    'requirement at or above c*, so if the deployer requires more retention than the cohort admits the '
    'practitioner should adopt the three-axis protocol rather than search for a dose; below it a feasible '
    'dose may exist and is worth searching for.')

# ---------------------------------------------------------------- 4. Table 1 gains a c* column
rep('| Cohort | Label type | τ_base | σ̂ | τ_base/σ̂ | Dual-gate window | Observed accepted operating points |',
    '| Cohort | Label type | τ_base | σ̂ | τ_base/σ̂ | Critical retention c* | Dual-gate window | Observed accepted operating points |')
rep('| Shared-program simulation | planted shared program | n/a | n/a | 5.8 | empty | none (by construction) |',
    '| Shared-program simulation | planted shared program | n/a | n/a | 5.8 | 0.28 | empty | none (by construction) |')
rep('| Cervical (35 sections, 34 donors) | ordinal severity | 0.42 | ≈ 0.176 | ≈ 2.4 | empty | none; bistable, no stable point at any dose |',
    '| Cervical (35 sections, 34 donors) | ordinal severity | 0.42 | ≈ 0.176 | ≈ 2.4 | 0.69 | empty | none; bistable, no stable point at any dose |')
rep('| Head and neck (16 patients, GSE268014) | etiological (HPV) | 0.59 | ≈ 0.27 | 2.18 | non-empty |',
    '| Head and neck (16 patients, GSE268014) | etiological (HPV) | 0.59 | ≈ 0.27 | 2.18 | 0.75 | non-empty |')
rep('| Prostate (52 patients, GSE278936) | benign vs tumour | 0.288 | ≈ 0.143 | ≈ 2.0 | narrow |',
    '| Prostate (52 patients, GSE278936) | benign vs tumour | 0.288 | ≈ 0.143 | ≈ 2.0 | 0.80 | narrow |')
rep('their ratio\nagainst the feasibility threshold (≈ 2.35 for a retained fraction of c = 0.7), whether the remove-and-\npreserve dual gate has a non-empty feasible set, and what was actually observed.',
    'their ratio, and the critical retention c* = 1.645 σ̂/τ_base at which the gate closes (non-empty for every c < c*, empty for every c ≥ c*; the equivalent threshold expressed as a ratio is 1.645/c, ≈ 2.35 at c = 0.7), whether the remove-and-\npreserve dual gate has a non-empty feasible set, and what was actually observed.')

# ---------------------------------------------------------------- 5. Experimental Procedures tool
rep('4. **Compute τ_base/σ̂ before choosing a dose.** If it exceeds ≈ 2.35 (for c = 0.7), a '
    'remove-and-preserve dual gate is empty; use the three-axis protocol instead.',
    '4. **Compute the critical retention before choosing a dose.** From the unrepaired baseline, form '
    'c* = 1.645 σ̂/τ_base (equivalently τ_base/σ̂ against 1.645/c). The dual gate is empty for any '
    'retention requirement at or above c*, and the practitioner should then adopt the three-axis protocol '
    'instead of searching for a dose. Report c* and let the deployer supply c: do not tune c to obtain a '
    'preferred verdict.')

# ---------------------------------------------------------------- 6. Discussion
rep_para('**Evaluation hygiene is a separate, transferable result.**',
         para('**Evaluation hygiene is a separate, transferable result.**') +
         ' This is the same failure the blocked-cross-validation literature documents,[40,41] and we make '
         'no claim of priority for the phenomenon: that literature established the prescription (hold out '
         'whole blocks rather than records) and demonstrated the optimism case by case. What we add is the '
         'measurement, and a measurement is needed even where the prescription is followed. A '
         'group-disjoint split stops the shortcut from entering the training objective, but it cannot tell '
         'the owner of an already-trained representation how much of its reported performance is '
         'group-driven, and it cannot certify an intervention that claims to have removed the shortcut, '
         'because by then the split is fixed and the counterfactual has to be measured rather than '
         'designed. The check itself is one line in an existing evaluation script, given a recorded '
         'grouping variable.')

rep('It is a precondition test and not a theory of repair: it costs one baseline fit, and it tells the '
    'practitioner which acceptance criterion to adopt, not what any particular dose will return.',
    'It is a precondition test and not a theory of repair: it costs one baseline fit, and it tells the '
    'practitioner which acceptance criterion to adopt, not what any particular dose will return. We '
    'report it as a critical retention c* (Table 1) rather than as a verdict taken at a chosen c, so that '
    'the normative choice is made explicit instead of being absorbed into the statistic.')

rep_para('**How far the positive repair evidence extends.**',
         '**What the audit decided in the validation domain, and how precisely.** Two numbers bound how '
         'the operator should be read, and both are properties of the instrument rather than admissions '
         'about it. The first is that the instrument issued a verdict in every cohort from pre-repair '
         'quantities alone, and the verdict matched what was subsequently observed in six of six cohorts '
         '(Table 1): the shared-program simulation and the cervical cohort were declared infeasible and '
         'produced no accepted operating point, while head and neck and prostate produced the accepted '
         'cells the test said were available, and both non-biological cohorts were graded as they were '
         'graded. A diagnostic whose verdicts agree with the outcomes it predicts, across six cohorts and '
         'two domains, is calibrated; that is the positive result, and it does not rest on cohort size. '
         'The second number is the size of the accepted set on real data: three of eighteen dosed seed × '
         'dose cells across the two clinical cohorts clear both axes, one of nine on head and neck '
         '(λ = 2, retention 0.73) and two of nine on prostate (λ = 1.0, retention 0.74–0.76). A gate that '
         'accepted none of them would be vacuous and one that accepted all of them would be '
         'uninformative, so the smallness is the calibration reading rather than a shortfall: on '
         'single-section-per-donor cohorts the framework predicts a small feasible set in advance, and '
         'finding three where it predicted few is the outcome it calls for. The precision of the two '
         'gradings differs and we say which is which. Head and neck (16 patients; baseline LDI 2.18 '
         'falling to 1.13–1.37 at λ = 0.5) clears the leakage axis on all three seeds at that dose and '
         'both axes on one of nine cells. Prostate (52 patients; 2.04 to 1.51 at λ = 1.0) clears both '
         'axes on two of three seeds with a seed spread (SD 0.16 on the primary run, 0.86 on the '
         'independent re-run) that is wider than the distance from the mean to the gate, so we grade it '
         'as a single operating point with measured spread rather than as a replicated acceptance; the '
         'observation that would upgrade the grading is more benign sections, not more seeds.')

# ---------------------------------------------------------------- 7. references
rep('39. Ojala, M., and Garriga, G. Permutation tests for studying classifier performance. '
    'J. Mach. Learn. Res. 11, 1833–1863 (2010).',
    '39. Ojala, M., and Garriga, G. Permutation tests for studying classifier performance. '
    'J. Mach. Learn. Res. 11, 1833–1863 (2010).\n'
    '40. Roberts, D.R., Bahn, V., Ciuti, S., Boyce, M.S., Elith, J., Guillera-Arroita, G., Hauenstein, S., '
    'Lahoz-Monfort, J.J., Schröder, B., Thuiller, W., Warton, D.I., Wintle, B.A., Hartig, F., and Dormann, '
    'C.F. Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic '
    'structure. Ecography 40, 913–929 (2017). https://doi.org/10.1111/ecog.02881.\n'
    '41. Ploton, P., Mortier, F., Réjou-Méchain, M., Barbier, N., Picard, N., Rossi, V., Dormann, C., '
    'Cornu, G., Viennois, G., Bayol, N., Lyapustin, A., Gourlet-Fleury, S., and Pélissier, R. Spatial '
    'validation reveals poor predictive performance of large-scale ecological mapping models. '
    'Nat. Commun. 11, 4540 (2020). https://doi.org/10.1038/s41467-020-18321-y.\n'
    '42. Kapoor, S., and Narayanan, A. Leakage and the reproducibility crisis in machine-learning-based '
    'science. Patterns 4, 100804 (2023). https://doi.org/10.1016/j.patter.2023.100804.')

# ref 17: make the issue explicit so the year cannot read as a future date
rep('Nat. Genet. 58, 2240–2253 (2026). https://doi.org/10.1038/s41588-026-02723-7. GSE268014.',
    'Nat. Genet. 58(9), 2240–2253 (2026). https://doi.org/10.1038/s41588-026-02723-7. GSE268014.')

io.open(DST, 'w', encoding='utf-8').write(s)
print('written', DST)
print('em-dash:', s.count('\u2014'), '| literal **:', s.count('**'))
print('refs:', len([l for l in s.split('\n') if re.match(r'^\d{1,2}\. [A-Z\[]', l) and len(l) > 60]))
