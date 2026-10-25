"""Route the BiB MRP-ST manuscript to three target journals, one directory each.

Reuses bib_build_package.py's compiled data (tables / equations / captions /
references already loaded at import) and its build_main / build_supplementary /
write_refs / prescan functions, monkeypatching the module globals ``O`` (output
dir) and ``F`` (figures dir) per journal.

Journals:
  15_BMCBioinformatics_20261016  -> BMC Bioinformatics  (Research article)
  16_CBM_20261016                -> Computers in Biology and Medicine (Elsevier)
  17_CSBJ_20261016               -> Computational and Structural Biotechnology
                                    Journal (Elsevier)

Wrapper adaptations per journal:
  - article type line corrected away from BiB's "Problem solving protocols";
  - BiB "Key Points:" rewired to each journal's convention (none for BMC,
    "Highlights:" for the two Elsevier titles);
  - a tailored cover letter.
The scientific body (abstract/methods/results/discussion/conclusions and the
five figures) is unchanged across the three versions.
"""
from pathlib import Path
import re, shutil, sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bib_build_package as B  # noqa: E402

R = Path(__file__).resolve().parents[1]
SRC = R / 'papers/14_BiB_20261016'

ARTICLE_TYPE_BIB = 'Article type: Problem solving protocols.'

HIGHLIGHTS_ELS = (
    "Highlights:\n\n"
    "\u2022 A five-clause protocol audits what a spatial disease score has learned.\n\n"
    "\u2022 First measured error rates: sensitivity 1.00, 0/18 false positives.\n\n"
    "\u2022 Identity-confounded control separates leakage from true information.\n\n"
    "\u2022 Identical probe transfers to SpaGCN, STAGATE and GraphST.\n\n"
    "\u2022 Cervical LDI 3.26 with leave-one-out AUC collapse 1.00 to 0.497.\n\n"
)

# CBM-only body framing: reframe the protocol as a leakage gate for
# translational pipelines (honest; does not claim clinical validation).
CBM_BODY = [
    (
        "MRP-ST converts an interpretive question into a reproducible measurement with interval-bounded error rates.",
        "MRP-ST converts an interpretive question into a reproducible measurement with interval-bounded error rates. For translational disease-modelling pipelines, the protocol acts as a leakage gate: the cervical demonstration returns an in-cohort AUC of 1.00 that a routine readout would report as predictive, yet it collapses to chance (0.497) under leave-one-out evaluation, quantifying the false-discovery risk the audit intercepts before a score reaches clinical decision-making.",
    ),
    (
        "and spatial organization persisted without convincing phenotype discrimination.",
        "and spatial organization persisted without convincing phenotype discrimination. For translational pipelines, this is a reporting-level safeguard rather than a clinical claim: by mandating label-free probes and leave-one-out evaluation, MRP-ST surfaces the leakage-driven in-cohort separation (AUC 1.00) that collapses under held-out evaluation (0.497) before such a score propagates into a candidate disease model.",
    ),
]

# Per-journal Abstract scope statements (one sentence each). The scientific
# body is shared; only the closing orientation of the Abstract differs, tuned
# to each journal's scope. CBM_BODY covers CBM's clinical-translation angle.
_ABSTRACT_SCOPE = "MRP-ST converts an interpretive question into a reproducible measurement with interval-bounded error rates"

BMC_BODY = [
    (_ABSTRACT_SCOPE + ".",
     _ABSTRACT_SCOPE + ". Delivered as a reproducibility-first evaluation protocol for spatial-omics analyses."),
]

CSBJ_BODY = [
    (_ABSTRACT_SCOPE + ".",
     _ABSTRACT_SCOPE + ". The protocol is packaged as a computable audit framework transferable across spatial assay modalities."),
]

GPB_BODY = [
    (_ABSTRACT_SCOPE + ".",
     _ABSTRACT_SCOPE + ". It extends omics-scale benchmarking conventions to spatial transcriptomic model audits."),
]

ISCLS_BODY = [
    (_ABSTRACT_SCOPE + ".",
     _ABSTRACT_SCOPE + ". It serves as a reusable measurement protocol for interdisciplinary computational life-science studies."),
]

COVER_BMC = """# Cover Letter \u2014 BMC Bioinformatics

Dear Editor,

We are pleased to submit our manuscript, "MRP-ST: calibrated label-dependence indexing and measured operating characteristics for auditing spatial transcriptomic models," for consideration as a Research article in BMC Bioinformatics.

**The problem.** Spatial transcriptomic models routinely emit spatially coherent disease scores. In cohorts where thousands of spots derive from a few independently sampled lesions, in-cohort agreement is unreliable evidence that a score has learned anything transferable. Existing reporting and validation frameworks (TRIPOD+AI, REFORMS, DOME) prescribe what to document, but none determines what information a spatial score has actually learned. MRP-ST fills this gap and, we believe, fits the journal's scope for reproducible method evaluation on real experimental data.

**What the protocol delivers.** MRP-ST is a five-clause audit protocol with three methodological components, each measured rather than asserted:

1. A calibrated Label-Dependence Index (LDI): a permutation-null-standardized statistic with an explicit gate, invariant to score rescaling, that turns "is this ordering label-dependent?" into a threshold decision.
2. To our knowledge, the first measured operating characteristics for such audit rules: on a dose\u2013response grid with an identity-confounded control, the grading rule detects injected programs with sensitivity 1.00 (9/9; exact 95% CI 0.66\u20131.00), zero threshold false positives (0/18; exact 95% CI 0\u201318.5%) and wide perfect-separation windows; an exact finite-sample bound on the tau statistic separates saturation from estimation.
3. A unified audit transferring the identical probe, refitted permutation inference and grading criteria to three published unsupervised embedding methods (SpaGCN, STAGATE, GraphST) together with a unified readout that separates representation content from readout choice.

A 35-section cervical cohort demonstrates the protocol on real data: label dependence (LDI 3.26) coexists with seed-unstable representation information (0.270) and in-cohort separation (AUC 1.00) that collapses to chance (0.497) under leave-one-out evaluation.

**Reproducibility.** All analysis code, model configurations and the complete audit evidence package (pooled representations, including exported published-method embeddings and unified-readout results, SHA-256 checksums) are openly available at https://github.com/WorldBMW/pathway-anchored-risk-benchmark (release v1.1). Corrected probe calculations reproduce without a GPU.

**AI usage disclosure.** In preparing this manuscript the authors used AI-assisted coding tools (Trae) for analysis-code generation, numerical verification, figure generation from computed results and English language editing. The study was designed, and all analyses were selected, performed, interpreted and written up, by the authors, who take full responsibility for the content. No AI system is listed as an author.

**Declarations.** This manuscript is original, has not been published previously and is not under consideration elsewhere. All authors have approved the submission and declare no competing interests. The work reanalyzes public datasets without new recruitment or intervention.

Thank you for your consideration.

Sincerely,

Lang Guo (corresponding author)
School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, Shenyang 110034, China
Tel: +86 13555707001; E-mail: guolang1016@symc.edu.cn

On behalf of all authors: Mingwei Bai, Zhengmin Gu, Ye Zhang, Zhiping Ni, Lang Guo
"""

COVER_CBM = """# Cover Letter \u2014 Computers in Biology and Medicine

Dear Editor,

We are pleased to submit our manuscript, "MRP-ST: calibrated label-dependence indexing and measured operating characteristics for auditing spatial transcriptomic models," for consideration as a Research article in Computers in Biology and Medicine.

**The problem.** Disease-scoring models built on spatial transcriptomics are increasingly used in translational cancer research, but spatially smooth scalar outputs can appear to summarize a disease process without actually encoding a transferable disease axis. In small clinical cohorts, where thousands of spots derive from a few independently sampled lesions, in-cohort agreement is unreliable evidence of learned biology, and label leakage can masquerade as predictive performance. For a translational pipeline, this is a patient-safety issue: a leaked score that collapses under held-out evaluation can drive false discovery and wasted follow-up.

**What the protocol delivers.** MRP-ST is a five-clause audit protocol that converts the interpretive question "what has this spatial disease score learned?" into a reproducible measurement with interval-bounded error rates. On a dose\u2013response grid with an identity-confounded control, the grading rule detects injected programs with sensitivity 1.00 (9/9; exact 95% CI 0.66\u20131.00) and zero threshold false positives (0/18; exact 95% CI 0\u201318.5%); a calibrated Label-Dependence Index (LDI) turns label dependence into a null-derived gate; and the identical probe, inference and grading criteria transfer unchanged to three published embedding methods (SpaGCN, STAGATE, GraphST).

**Clinical demonstration.** A 35-section cervical cohort (31 normal, 1 HSIL, 3 cancer) demonstrates the protocol on real data. The label-dependence gate fires (LDI 3.26), yet the frozen label-free representation retains only seed-unstable information (0.270, one of three seeds), and in-cohort separation (AUC 1.00) collapses to chance (0.497) under leave-one-out evaluation. We present this 1.00-to-0.497 collapse as the leakage baseline, not as a validated predictor; the cervical cohort demonstrates what the protocol exposes, and we do not overstate clinical readiness.

**Reproducibility.** All analysis code, model configurations and the complete audit evidence package are openly available at https://github.com/WorldBMW/pathway-anchored-risk-benchmark (release v1.1), with SHA-256 checksums; corrected probe calculations reproduce without a GPU.

**AI usage disclosure.** In preparing this manuscript the authors used AI-assisted coding tools (Trae) for analysis-code generation, numerical verification, figure generation and English language editing. All analyses were selected, performed, interpreted and written up by the authors, who take full responsibility for the content. No AI system is listed as an author.

**Declarations.** This manuscript is original, has not been published previously and is not under consideration elsewhere. All authors have approved the submission and declare no competing interests. The work reanalyzes public datasets without new recruitment or intervention.

Thank you for your consideration.

Sincerely,

Lang Guo (corresponding author)
School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, Shenyang 110034, China
Tel: +86 13555707001; E-mail: guolang1016@symc.edu.cn

On behalf of all authors: Mingwei Bai, Zhengmin Gu, Ye Zhang, Zhiping Ni, Lang Guo
"""

COVER_CSBJ = """# Cover Letter \u2014 Computational and Structural Biotechnology Journal

Dear Editor,

We are pleased to submit our manuscript, "MRP-ST: calibrated label-dependence indexing and measured operating characteristics for auditing spatial transcriptomic models," for consideration as a Research article in Computational and Structural Biotechnology Journal.

**The problem.** Spatial transcriptomic models emit spatially coherent disease scores, but existing reporting and validation frameworks prescribe documentation rather than the decision experiments that determine what a score has learned. MRP-ST supplies the missing layer: a reusable protocol plus a calibrated index and measured error rates.

**The methodological contribution.** Three components, each measured rather than asserted:

1. A calibrated Label-Dependence Index (LDI), standardized against a permutation null with an explicit gate and invariant to score rescaling.
2. To our knowledge, the first measured operating characteristics for spatial-model audit rules, on a dose\u2013response grid with an identity-confounded control (sensitivity 1.00, 9/9; zero threshold false positives, 0/18; exact Clopper\u2013Pearson intervals), with an exact finite-sample bound separating saturation from estimation.
3. A unified audit that transfers the identical probe, refitted permutation inference and grading criteria to three published embedding methods (SpaGCN, STAGATE, GraphST), plus a unified readout separating representation content from readout choice.

The protocol is a deliverable in its own right: clauses, definitions, an evidence package with SHA-256 checksums, and results that reproduce without a GPU. A 35-section cervical cohort demonstrates it on real data (LDI 3.26; leave-one-out AUC collapse 1.00 to 0.497).

**Reproducibility.** All analysis code, model configurations and the complete audit evidence package are openly available at https://github.com/WorldBMW/pathway-anchored-risk-benchmark (release v1.1).

**AI usage disclosure.** In preparing this manuscript the authors used AI-assisted coding tools (Trae) for analysis-code generation, numerical verification, figure generation and English language editing. All analyses were selected, performed, interpreted and written up by the authors, who take full responsibility for the content. No AI system is listed as an author.

**Declarations.** This manuscript is original, has not been published previously and is not under consideration elsewhere. All authors have approved the submission and declare no competing interests. The work reanalyzes public datasets without new recruitment or intervention.

Thank you for your consideration.

Sincerely,

Lang Guo (corresponding author)
School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, Shenyang 110034, China
Tel: +86 13555707001; E-mail: guolang1016@symc.edu.cn

On behalf of all authors: Mingwei Bai, Zhengmin Gu, Ye Zhang, Zhiping Ni, Lang Guo
"""

COVER_GPB = """# Cover Letter \u2014 Genomics, Proteomics & Bioinformatics (GPB)

Dear Editor,

We are pleased to submit our manuscript, "MRP-ST: calibrated label-dependence indexing and measured operating characteristics for auditing spatial transcriptomic models," for consideration as a Research article in Genomics, Proteomics & Bioinformatics.

**The problem.** Spatially resolved transcriptomic models emit spatially coherent disease scores, but in cohorts where thousands of spots derive from a few independently sampled lesions, in-cohort agreement is unreliable evidence that a score has learned a transferable biological program. Existing reporting and validation frameworks prescribe documentation rather than the decision experiments that determine what a score has learned. MRP-ST supplies that missing layer for omics-scale model auditing.

**The methodological contribution.** Three components, each measured rather than asserted:

1. A calibrated Label-Dependence Index (LDI), standardized against a permutation null with an explicit gate and invariant to score rescaling.
2. To our knowledge, the first measured operating characteristics for spatial-model audit rules, on a dose\u2013response grid with an identity-confounded control (sensitivity 1.00, 9/9; zero threshold false positives, 0/18; exact Clopper\u2013Pearson intervals), with an exact finite-sample bound separating saturation from estimation.
3. A unified audit transferring the identical probe, refitted permutation inference and grading criteria to three published unsupervised embedding methods (SpaGCN, STAGATE, GraphST), plus a unified readout separating representation content from readout choice.

The protocol is a package in its own right: clauses, explicit formulas, an evidence bundle with SHA-256 checksums, and results that reproduce without a GPU. A 35-section cervical demonstration cohort applies it to real data (LDI 3.26; leave-one-out AUC collapse 1.00 to 0.497).

**Reproducibility.** Analysis code, model configurations and the complete evidence package are openly available at https://github.com/WorldBMW/pathway-anchored-risk-benchmark (release v1.1).

**AI usage disclosure.** The authors used AI-assisted coding tools (Trae) for analysis-code generation, numerical verification, figure generation and language editing. All analyses were selected, performed, interpreted and written up by the authors, who take full responsibility. No AI system is listed as an author.

**Declarations.** This manuscript is original, has not been published previously and is not under consideration elsewhere. All authors have approved the submission and declare no competing interests. The work reanalyzes public datasets without new recruitment or intervention.

Thank you for your consideration.

Sincerely,

Lang Guo (corresponding author)
School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, Shenyang 110034, China
Tel: +86 13555707001; E-mail: guolang1016@symc.edu.cn

On behalf of all authors: Mingwei Bai, Zhengmin Gu, Ye Zhang, Zhiping Ni, Lang Guo
"""

COVER_ISCLS = """# Cover Letter \u2014 Interdisciplinary Sciences: Computational Life Sciences

Dear Editor,

We are pleased to submit our manuscript, "MRP-ST: calibrated label-dependence indexing and measured operating characteristics for auditing spatial transcriptomic models," for consideration as an Original Research article in Interdisciplinary Sciences: Computational Life Sciences.

**The problem.** Spatial transcriptomic models emit spatially coherent disease scores, but in cohorts where thousands of spots derive from a few independently sampled lesions, in-cohort agreement is unreliable evidence that a score has learned a transferable biological program. Existing reporting and validation frameworks prescribe documentation rather than the decision experiments that determine what a score has learned. MRP-ST supplies that missing layer for computational life-science model auditing.

**The methodological contribution.** Three components, each measured rather than asserted:

1. A calibrated Label-Dependence Index (LDI), standardized against a permutation null with an explicit gate and invariant to score rescaling.
2. To our knowledge, the first measured operating characteristics for spatial-model audit rules, on a dose\u2013response grid with an identity-confounded control (sensitivity 1.00, 9/9; zero threshold false positives, 0/18; exact Clopper\u2013Pearson intervals), with an exact finite-sample bound separating saturation from estimation.
3. A unified audit transferring the identical probe, refitted permutation inference and grading criteria to three published unsupervised embedding methods (SpaGCN, STAGATE, GraphST), plus a unified readout separating representation content from readout choice.

The protocol is a package in its own right: clauses, explicit formulas, an evidence bundle with SHA-256 checksums, and results that reproduce without a GPU. A 35-section cervical demonstration cohort applies it to real data (LDI 3.26; leave-one-out AUC collapse 1.00 to 0.497).

**Reproducibility.** Analysis code, model configurations and the complete evidence package are openly available at https://github.com/WorldBMW/pathway-anchored-risk-benchmark (release v1.1).

**AI usage disclosure.** The authors used AI-assisted coding tools (Trae) for analysis-code generation, numerical verification, figure generation and language editing. All analyses were selected, performed, interpreted and written up by the authors, who take full responsibility. No AI system is listed as an author.

**Declarations.** This manuscript is original, has not been published previously and is not under consideration elsewhere. All authors have approved the submission and declare no competing interests. The work reanalyzes public datasets without new recruitment or intervention.

Thank you for your consideration.

Sincerely,

Lang Guo (corresponding author)
School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, Shenyang 110034, China
Tel: +86 13555707001; E-mail: guolang1016@symc.edu.cn

On behalf of all authors: Mingwei Bai, Zhengmin Gu, Ye Zhang, Zhiping Ni, Lang Guo
"""


def copy_figures(dst_dir):
    dst = dst_dir / 'figures'
    dst.mkdir(parents=True, exist_ok=True)
    for f in (SRC / 'figures').glob('*'):
        if f.is_file():
            shutil.copy2(f, dst / f.name)
    return dst


def rewrite_main(text, article_type, highlights_text):
    text = text.replace(ARTICLE_TYPE_BIB, article_type)
    kp = text.find('Key Points:')
    ab = text.find('## Abstract')
    if kp != -1 and ab != -1 and kp < ab:
        text = text[:kp] + highlights_text + text[ab:]
    return text


def build_journal(profile):
    J = profile['dir']
    J.mkdir(parents=True, exist_ok=True)
    # clear stale generated files from a prior naming scheme (keep figures/)
    for f in J.iterdir():
        if f.name != 'figures' and f.is_file():
            f.unlink()
    Fdst = copy_figures(J)

    main_src = (SRC / 'Manuscript_BiB.md').read_text(encoding='utf-8-sig')
    main = rewrite_main(main_src, profile['article_type'], profile['highlights'])
    for old, new in profile.get('main_replacements', []):
        main = main.replace(old, new)
    (J / 'Manuscript_BiB.md').write_text(main, encoding='utf-8')

    supp = (SRC / 'Supplementary_BiB.md').read_text(encoding='utf-8-sig')
    (J / 'Supplementary_BiB.md').write_text(supp, encoding='utf-8')

    (J / 'CoverLetter.md').write_text(profile['cover'], encoding='utf-8')

    # monkeypatch module globals and reuse the compiled build pipeline
    B.O = J
    B.F = Fdst

    order = B.prescan()
    words_main, eqs = B.build_main(order)
    words_supp = B.build_supplementary(order)
    n_refs = B.write_refs(order)

    # normalise output filenames to the target journal (drop BiB-internal names)
    tag = profile['tag']
    for src_name, dst_name in [
        ('Manuscript_BiB.docx', f'Manuscript_{tag}.docx'),
        ('Supplementary_BiB.docx', f'Supplementary_{tag}.docx'),
        ('Manuscript_BiB_resolved.md', f'Manuscript_{tag}_resolved.md'),
        ('Manuscript_BiB.md', f'Manuscript_{tag}.md'),
        ('Supplementary_BiB.md', f'Supplementary_{tag}.md'),
        ('References.bib', f'References_{tag}.bib'),
        ('References_verified.txt', f'References_{tag}_verified.txt'),
        ('CoverLetter.md', f'CoverLetter_{tag}.md'),
    ]:
        src = J / src_name
        if src.exists():
            src.replace(J / dst_name)

    # residual-placeholder check on the rendered resolved markdown only
    residual = []
    resolved = J / f'Manuscript_{tag}_resolved.md'
    if resolved.exists():
        t = resolved.read_text(encoding='utf-8-sig')
        for pat in [r'\[\[', r'\]\]', r'\{\{FIG:', r'\[@', r'Key Points:']:
            if re.search(pat, t):
                residual.append((resolved.name, pat))

    return {
        'dir': str(J),
        'main_words': words_main,
        'eqs': eqs,
        'supp_words': words_supp,
        'refs': n_refs,
        'residual': residual,
    }


def main():
    profiles = [
        {
            'key': 'BMCBioinformatics',
            'tag': 'BMC',
            'dir': R / 'papers/15_BMCBioinformatics_20261016',
            'article_type': 'Article type: Research article.',
            'highlights': '',
            'main_replacements': BMC_BODY,
            'cover': COVER_BMC,
        },
        {
            'key': 'CBM',
            'tag': 'CBM',
            'dir': R / 'papers/16_CBM_20261016',
            'article_type': 'Article type: Research article.',
            'highlights': HIGHLIGHTS_ELS,
            'main_replacements': CBM_BODY,
            'cover': COVER_CBM,
        },
        {
            'key': 'CSBJ',
            'tag': 'CSBJ',
            'dir': R / 'papers/17_CSBJ_20261016',
            'article_type': 'Article type: Research article.',
            'highlights': HIGHLIGHTS_ELS,
            'main_replacements': CSBJ_BODY,
            'cover': COVER_CSBJ,
        },
        {
            'key': 'GPB',
            'tag': 'GPB',
            'dir': R / 'papers/18_GPB_20261016',
            'article_type': 'Article type: Research article.',
            'highlights': HIGHLIGHTS_ELS,
            'main_replacements': GPB_BODY,
            'cover': COVER_GPB,
        },
        {
            'key': 'ISCLS',
            'tag': 'ISCLS',
            'dir': R / 'papers/19_ISCLS_20261016',
            'article_type': 'Article type: Original Research article.',
            'highlights': '',
            'main_replacements': ISCLS_BODY,
            'cover': COVER_ISCLS,
        },
    ]

    for p in profiles:
        print('\n==================================================')
        print('BUILD', p['key'], '->', p['dir'].name)
        r = build_journal(p)
        print('  main words = %d, eqs = %d, supp words = %d, refs = %d'
              % (r['main_words'], r['eqs'], r['supp_words'], r['refs']))
        if r['residual']:
            print('  RESIDUAL PLACEHOLDERS:', r['residual'])
        else:
            print('  residual check: clean')


if __name__ == '__main__':
    main()