"""Re-audit journal submissions against local evidence; preserve source drafts."""
from pathlib import Path
import sys, os, ast, json, re, shutil, hashlib, copy, zipfile, math
from concurrent.futures import ThreadPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.qa/submission_deps'))
import requests
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from PIL import Image, ImageDraw
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
QA=ROOT/'.qa/submission_reaudit_20261016'
OUT=ROOT/'papers/投稿复核_20261016'
QA.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/'papers/14_BiB_20261016'
EV=SRC/'evidence'
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,s): Path(p).write_text(s,encoding='utf-8')

# Extract only pure formatting helpers and literal table/caption definitions.
# Importing the old builder would overwrite source evidence at module import.
tree=ast.parse((ROOT/'scripts/bib_build_package.py').read_text(encoding='utf-8-sig'))
names={'element','mr','sub','frac','sup','summ','fraction','rad','setup','table'}
chosen=[]
for n in tree.body:
    if isinstance(n,ast.FunctionDef) and n.name in names: chosen.append(n)
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and (t.id.startswith(('T1','T2','T3','T4','T5')) or t.id in {'EQS','CAPTIONS'}) for t in n.targets):chosen.append(n)
exec(compile(ast.Module(body=chosen,type_ignores=[]),'<formatting_helpers>','exec'),globals())

JOURNALS=[
 {'code':'BiB','folder':'14_BiB_20261016','name':'Briefings in Bioinformatics','kind':'Problem solving protocols','limit':5000,'abstract_limit':250,'guide':'https://academic.oup.com/bib/pages/msprep_submission','title':'MRP-ST for auditing supervision dependence and representation information in spatial transcriptomics','angle':'The contribution is a problem-solving protocol that specifies complementary experiments and their limits, illustrated across published spatial methods.','fit':'较匹配：计算生物信息学方法审计与问题求解协议；新颖性仍需编辑判断。'},
 {'code':'BMC','folder':'15_BMCBioinformatics_20261016','name':'BMC Bioinformatics','kind':'Research article','abstract_limit':350,'guide':'https://link.springer.com/journal/12859/submission-guidelines/research-article','title':'A reproducible audit of supervision dependence and representation information in spatial transcriptomic models','angle':'The contribution is a reproducible computational evaluation procedure with explicit units, refitted permutation inference and reusable evidence files.','fit':'较匹配：生物信息学计算评估方法；强调复现而非临床预测。'},
 {'code':'CBM','folder':'16_CBM_20261016','name':'Computers in Biology and Medicine','kind':'Full Length Article','abstract_limit':250,'guide':'https://www.sciencedirect.com/journal/computers-in-biology-and-medicine/publish/guide-for-authors','title':'Auditing supervision and validation boundaries in spatial transcriptomic disease scores','angle':'The contribution is a computational safeguard for interpreting tissue disease scores before translational follow-up; no clinical decision benefit is established.','fit':'有条件匹配：计算医学模型评估；缺乏独立患者层面的诊断验证，不能包装成临床预测突破。'},
 {'code':'CSBJ','folder':'17_CSBJ_20261016','name':'Computational and Structural Biotechnology Journal','kind':'Research article','abstract_limit':250,'guide':'https://spj.science.org/page/csbj/for-authors','title':'Auditing spatial omics representations with supervision ablations and refitted permutation probes','angle':'The contribution is a computational spatial-omics workflow that distinguishes scalar-score orientation, representation association and endpoint-specific biological interpretation.','fit':'较匹配：空间组学计算研究；按现行 SPJ 指南组织，选择 Research article，避免 Method article 的展示项限制。'},
 {'code':'GPB','folder':'18_GPB_20261016','name':'Genomics, Proteomics & Bioinformatics','kind':'Research article','limit':6000,'abstract_limit':200,'guide':'https://academic.oup.com/gpb/pages/general-instructions','title':'Separating supervision effects from representation information in spatial transcriptomic analysis','angle':'The contribution is an omics evaluation study that makes biological interpretation conditional on the information source, sample unit and external endpoint.','fit':'有条件匹配：空间组学评估研究；现有证据支持方法审计，不支持新增机制或多组学发现。'},
 {'code':'ISCLS','folder':'19_ISCLS_20261016','name':'Interdisciplinary Sciences: Computational Life Sciences','kind':'Original Research','abstract_limit':250,'guide':'https://link.springer.com/journal/12539/submission-guidelines','title':'A computational audit linking spatial transcriptomic representations to defensible biological claims','angle':'The contribution links statistical validation, representation learning and biological interpretation through a common audit of spatial transcriptomic models.','fit':'较匹配：计算与生命科学交叉方法；必须双盲，完整作者信息和声明另置标题页。'},
]

REF=read(EV/'references_verified.json')
def verify_ref(item):
    k,r=item; doi=r.get('doi',''); url='https://api.crossref.org/works/'+doi if doi else r.get('url','')
    try:
        z=requests.get(url,timeout=35,headers={'User-Agent':'ManuscriptAudit/1.0 (reference metadata verification)'})
        if z.status_code!=200:return k,{'status':z.status_code,'url':url}
        if doi:
            m=z.json()['message']; auth=[a.get('name') or (a.get('given','')+' '+a.get('family','')).strip() for a in m.get('author',[])]
            auth=[a for a in auth if a]
            upd={'doi':m.get('DOI',doi),'title':m.get('title',[r['title']])[0],'authors':auth or r['authors'],'journal':m.get('container-title',[r.get('journal','')])[0],'year':m.get('published-print',m.get('issued',m.get('published',{}))).get('date-parts',[[r['year']]])[0][0],'volume':m.get('volume',''),'page':m.get('page',m.get('article-number',r.get('page',''))),'url':'https://doi.org/'+m.get('DOI',doi)}
            return k,{'status':'verified','metadata':upd,'changed':upd!=r}
        return k,{'status':'link accessible','url':url}
    except Exception as e:return k,{'status':'unverified','error':str(e)}

def collect_sources():
    result={}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for f in as_completed([pool.submit(verify_ref,x) for x in REF.items()]):
            k,v=f.result(); result[k]=v
            if 'metadata' in v:REF[k]=v['metadata']
    write(QA/'reference_verification.json',json.dumps(result,ensure_ascii=False,indent=2))
    write(QA/'references_corrected.json',json.dumps(REF,ensure_ascii=False,indent=2))
    links={j['code']:j['guide'] for j in JOURNALS}
    links['github_release']='https://api.github.com/repos/WorldBMW/pathway-anchored-risk-benchmark/releases/tags/v1.1'
    for k,u in links.items():
        try:
            r=requests.get(u,timeout=30,headers={'User-Agent':'Mozilla/5.0'})
            result[k]={'url':u,'status':r.status_code}
            write(QA/(k+'_source.txt'),r.text)
        except Exception as e:result[k]={'url':u,'error':str(e)}
    write(QA/'source_access.json',json.dumps(result,ensure_ascii=False,indent=2))
    print('Source verification complete',flush=True)

def common_fix(text):
    # These corrections follow directly from source code/results, not new experiments.
    changes=[
      ('to our knowledge, the first measured operating characteristics for such audit rules','simulation-based operating characteristics for the audit rules'),
      ('to our knowledge the first measured operating characteristics for such audit rules','simulation-based operating characteristics for the audit rules'),
      ('Mean probe tau declines with the nonresponder fraction at both scales','Mean probe tau generally decreases with the nonresponder fraction, with a main-scale rebound at L4'),
      ('the prespecified grade threshold','the reported grade threshold'),('the prespecified threshold','the reported threshold'),
      ('rather than nulls','rather than evidence of a null association'),
      ('The label-free representation retains real but seed-unstable information','The label-free representation shows seed-unstable association'),
      ('a label-dependent ordering','an ordering associated with the training labels'),
      ('a label-dependent verdict','an association-screen verdict'),
      ('quantifies how much of the observed ordering is imposed by supervision','summarizes observed score–label association; ablations are needed to assess supervision effects'),
      ('which claims a spatial disease score supports','which claims a spatial disease score can support'),
      ('No generative AI system drafted the scientific narrative from author prompts, and no AI system is listed as an author.','AI-assisted editorial review and journal-specific restructuring were additionally performed using OpenAI Codex. No AI system is listed as an author.'),
      ('No AI system is listed as an author. A detailed usage statement appears in the Supplementary Materials.','AI-assisted editorial review and journal-specific restructuring were additionally performed using OpenAI Codex. No AI system is listed as an author. A detailed usage statement appears in the Supplementary Materials.'),
      ('Panels B and C separate the memorisation gap from the transferable signal.','Panels B and C contrast label-trained and label-free transductive representations; neither establishes fully inductive transfer.'),
      ('The most plausible source is the adaptive-graph embedding selecting an oppositely oriented dominant axis at low signal-to-noise; the single-run design cannot separate this from seed variation.','These single-run correlations do not establish the origin or reproducibility of the reversal. The pathway-expression readout has a fixed biological orientation, so a reversed ranking is not explained merely by the arbitrary sign of embedding coordinates.'),
      ('a readout ordering sections opposite to severity still reflects retained sample structure','a reversed ranking is a negative descriptive association and requires separate two-sided inference before being treated as evidence of retained severity information'),
    ]
    for a,b in changes:text=text.replace(a,b)
    return text

def replace_section(text,heading,new,next_heading):
    a=text.index(heading);b=text.index(next_heading,a)
    return text[:a]+heading+'\n'+new+'\n\n'+text[b:]

LDI_METHOD='''Score–label association is summarized by the Label-Dependence Index (LDI), retained as the name of a descriptive statistic, using sample-level Kendall tau-b with ties retained:

$$ tau-b $$

Here C and D count concordant and discordant sample pairs, respectively; Tₛ and Tᵧ count pairs tied only in score and only in annotation. Pairs tied in both variables are excluded from these counts.

The label-free NOALL scalar head is nearly constant and its ordering is precision-sensitive (Supplementary Note S2), so it is unsuitable as a counterfactual denominator or baseline. The reported standardized statistic instead uses permutations of labels against a fixed supervised score:

$$ LDI $$

Here τ⊥ and σ_null are the mean and standard deviation of tau-b under B=10,000 complete sample-label permutations; θ=Φ⁻¹(1−α) is a Gaussian reference gate. The reported cervical values are τ⊥=0.001 and σ_null=0.141. Positive affine rescaling of the scores leaves their ranks unchanged. The null calibration uses a representative FULL run, whereas τ̄_FULL summarizes three training seeds; the resulting index is descriptive rather than a calibrated inferential z-test of the seed average. The separate seed-0 stability analysis in Supplementary Note S2 uses that run's observed statistic consistently.

Because the scores were fitted using these labels, this fixed-score permutation screen does not test the entire model-training procedure and cannot distinguish genuine signal, supervision dependence, memorization or leakage. The Gaussian cutoff is an approximation to a discrete permutation distribution. We therefore report the index as an association screen; supervision-removal contrasts and the identity-confounded control address supervision effects separately. Refit training-level nulls or untouched evaluation data would be required for stronger causal or generalization claims.'''

CERVICAL_RESULT='''On the 35-section cohort the descriptive association index is 3.26, above the Gaussian reference gate 1.645, using τ⊥=0.001 and σ_null=0.141. A separate seed-0 analysis gives indices 3.25–3.30 across five permutation seeds and the same screen outcome across α ∈ {0.01, 0.05, 0.10, 0.20}; this is numerical stability of the association screen, not validation of training-level type-I error. Removing supervision channels changes the score descriptively (FULL 0.460; NOPROG 0.251; NOSUP 0.210; NOALL numerically indeterminate; Supplementary Note S2). Label-free NOALL probes have mean tau-b 0.270 (SD 0.116), with one of three seeds significant (p=0.0019), including adjustment across the 21 primary tests (Figure S1). Label-trained transductive encoders yield sample-held-out probe correlations 0.420–0.462 with three significant seeds; the encoder has already seen the held-out labels, so these are leakage-contaminated readouts rather than generalization estimates.

The supervised score has apparent in-cohort disease-versus-normal area under the receiver-operating-characteristic curve (AUC) 1.00 for four diseased and 31 normal sections. A separate stored ridge baseline reports mean within-section spot-level AUC 0.4967 (SD 0.0205) in 16 valid folds out of 35 held-out sections, using median-thresholded expression-derived pathway labels. That baseline uses a different model, target and evaluation unit; it is not a held-out disease-classification AUC and cannot demonstrate a 1.00-to-0.497 performance collapse. Its reconstruction and target construction are detailed in Supplementary Note S8. No held-out disease-classification AUC for the reference score is established here. Residual representation association could reflect disease, acquisition source or other shared structure; four diseased sections cannot establish a trajectory, biomarker or independent patient-level performance.'''

ABSTRACT_COMMON='''Spatial transcriptomic models can produce disease-associated scores in cohorts with few independently sampled tissues. We present the Minimum Reporting Protocol for Spatial Transcriptomic model audits, which separates supervision-removal contrasts, evaluation units, descriptive score–label association, label-free representation probing and external endpoints. A standardized association index is interpreted alongside ablations because fixed-score permutations after supervised fitting cannot by themselves establish label dependence. Simulations use 90-sample and 35-sample cohorts, three generator seeds and three training seeds per setting. At the reported correlation threshold, all nine strongest-signal runs were detected at each scale; none of 18 pooled control runs crossed the threshold. These are dependent-run summaries from shared generated cohorts, with limited precision. An identity-confounded control exposes label contamination in probes of supervised transductive embeddings. Published spatial embedding methods illustrate how conclusions depend on the readout. In 35 cervical sections, label-free probes show mean Kendall correlation 0.270 with one of three seeds significant. The association index is 3.26, but acquisition confounding and transductive encoding limit interpretation. No held-out disease-classification performance is established. The protocol supports traceable computational evaluation and confines biological claims to the information source, statistical unit and endpoint examined.'''

ABSTRACT_GPB='''Spatial transcriptomic representations can associate with tissue annotations without supporting transferable biological conclusions. We present an audit protocol separating supervision ablations, evaluation units, score–label association, label-free representation probes and external endpoints. A standardized association index is descriptive because permuting labels against a score fitted with those labels does not isolate supervision dependence. Simulations at two sample scales evaluate a reported correlation threshold across three generated cohorts and three training seeds per setting. All nine strongest-signal runs were detected at each scale, whereas none of 18 pooled control runs crossed the threshold; these runs share generated cohorts and do not provide independent error-rate estimates. An identity-confounded control exposes contaminated probes of supervised transductive embeddings. Analyses of published spatial embedding methods show that readout choice affects the recovered association. In 35 cervical sections, label-free probes give mean Kendall correlation 0.270, with one of three seeds significant; an association index of 3.26 does not resolve acquisition confounding. No held-out disease-classification performance is established. The audit provides a reproducible framework for matching biological claims to their information source, evaluation unit and external endpoint.'''

DISCUSSION_ADD='''The standardized association index is not a new test for causal label dependence: it is a rank association expressed in units of a fixed-score permutation null. Genuine biological signal can also produce a large value. Because the score was trained with the observed labels, its permutation screen cannot calibrate the full training-and-evaluation process. Ablation contrasts, identity-confounded controls and label-free probes provide the complementary evidence; their roles must remain distinct.

Runs sharing one generated cohort are not independent simulated datasets. The 0/18 control summary combines six generated control cohorts with three training seeds each. Clopper–Pearson intervals calculated by treating runs as independent Bernoulli trials are nominal descriptive intervals and do not incorporate this clustering; the zero of six cohort summary also spans two different sample-size regimes. Threshold sensitivity estimates concern a tau-only screening decision, whereas supported cohort grades additionally require significant seeds. Neither quantity validates the other. Threshold windows describe separation observed on this grid and do not establish robustness on new generators, artefacts or clinical populations.'''

CONCLUSION='''The proposed audit separates descriptive supervision-removal contrasts, score–label association and information recovered from label-free representations. The standardized index summarizes an association screen, while identity-confounded controls demonstrate how label-trained transductive encoders can contaminate nominally held-out probes. On the simulated grid, the strongest-signal and control runs separate at the reported correlation threshold, subject to dependence among training replicates and limited generator diversity. Published embeddings show that readout choice changes recoverable association. The cervical demonstration is seed-unstable and source-confounded; it does not establish held-out disease classification or clinical utility. The practical contribution is a traceable workflow for reporting these distinctions and their validation boundaries.'''

def revised_main(j):
    text=(SRC/'Manuscript_BiB.md').read_text(encoding='utf-8-sig')
    text=common_fix(text)
    text=replace_section(text,'### 2.2. The calibrated Label-Dependence Index',LDI_METHOD,'### 2.3.')
    text=text.replace('### 2.2. The calibrated Label-Dependence Index','### 2.2. Descriptive score–label association index')
    text=replace_section(text,'### 3.4. Cervical demonstration',CERVICAL_RESULT,'## 4.')
    text=replace_section(text,'## 5. Conclusions',CONCLUSION,'## Acknowledgments')
    # Remove unsupported novelty and circularity/transfer claims.
    text=text.replace('but none determines what information a spatial score has actually learned.','and motivate explicit task-specific experiments on spatial representations.')
    a=text.index('We present MRP-ST, a Minimum Reporting Protocol',text.index('## 1.'))
    b=text.index('\n\n## 2.',a)
    text=text[:a]+'''We present MRP-ST, a Minimum Reporting Protocol for Spatial Transcriptomic model audits, combining five clauses, a descriptive standardized score–label association index, simulations with known injected programs and an identity-confounded control, and audits of published spatial embeddings. The contribution is the explicit combination of these experiments and their reporting boundaries, rather than a new causal test of label dependence or a clinical predictor. A cervical cohort of 35 sections illustrates the protocol. Reporting frameworks provide the broader context; this study supplies worked experiments for spatial score interpretation. '''+j['angle']+text[b:]
    text=text.replace('The unified audit answers the circularity objection that a protocol authored alongside one model might calibrate its criteria to that model.','The published-method audit illustrates use beyond the reference architecture; it does not independently validate threshold selection.')
    text=text.replace('The matched-scale regime, the cervical cohort\'s own regime, is where every label-free readout in this study loses support.','At the matched scale, reference and published-method readouts lose support as the injected program weakens; this pattern is specific to the tested simulation settings.')
    text=text.replace('MRP-ST solves a practical problem: grading which biological claims a spatial disease score supports, reproducibly.','MRP-ST provides a practical workflow for relating biological claims to the experiments performed on a spatial disease score.')
    text=text.replace('measured error rates','observed simulation operating characteristics')
    text=text.replace('compatible with the nominal 5% at this run count.','a descriptive result with limited precision and shared-cohort dependence.')
    text=text.replace('With nine runs per cell the exact intervals are wide; they are part of the measured operating characteristic, not a precision claim.','With nine runs per cell, the nominal binomial intervals are wide and ignore dependence among training replicates sharing a generated cohort.')
    text=text.replace('With nine runs per cell the exact intervals are wide; they are part of the observed simulation operating characteristic, not a precision claim.','With nine runs per cell, the nominal binomial intervals are wide and ignore dependence among training replicates sharing a generated cohort.')
    text=text.replace('with exact Clopper–Pearson intervals on every reported proportion.','with nominal Clopper–Pearson intervals treating runs as independent. Training replicates reuse generated cohorts, so these intervals do not account for within-cohort dependence. The run-level threshold screen uses tau alone; cohort-level grading additionally uses seed significance and is a distinct decision rule. No preregistration or untouched threshold-validation cohort is claimed.')
    text=text.replace('the aggregation most favorable to a spatially focal program','a fixed aggregation intended to capture spatially focal expression')
    text=text.replace('a precomputed leave-one-out operator refits every permutation exactly and predictions and labels are permuted jointly','a precomputed leave-one-out operator is applied to each permuted label vector, refitting the probe and comparing its new predictions with that same vector')
    text=text.replace('Probe significance quantifies recoverable association under the fitted representation, not biological mechanism.','Pooled feature arrays retain their stored float32 precision for fold means, standard deviations and standardized Gram products; 10⁻⁸ is added to each training-fold standard deviation. The ridge solve uses a float64 identity regularizer and the leave-one-out operator is stored in float64. Probe significance quantifies recoverable association under the fitted representation, not biological mechanism.')
    text=text.replace('STAGATE\'s negative weak-level values are sign reversals of an unsupervised axis rather than evidence of a null association','negative weak-level values are reversed descriptive associations under the fixed pathway readout; their origin and significance need separate evaluation')
    text=text.replace('the sign-reversed structure its focal readout reveals is not linearly recoverable from spot means','the focal and linear readouts yield different associations')
    text=text.replace('STAGATE\'s reversal structure is invisible to a linear probe of spot means','the STAGATE linear and focal readouts differ')
    text=text.replace('The dose–response grid converts the grading vocabulary into measured error rates:','The dose–response grid illustrates the grading vocabulary:')
    text=text.replace('The dose–response grid converts the grading vocabulary into observed simulation operating characteristics:','The dose–response grid illustrates the grading vocabulary:')
    text=text.replace('so grades do not depend on fine tuning.','describing observed separation on this grid rather than independent threshold validation.')
    text=text.replace('and a positive probe of a label-trained embedding need not indicate transferable information.','and a positive probe of a label-trained embedding need not indicate transferable information.')
    text=text.replace('The practical deliverable is a traceable evidence package:',DISCUSSION_ADD+'\n\nThe practical deliverable is a traceable evidence package:')
    # explicit table references (markers alone are not textual citations)
    text=text.replace('Mean probe tau generally decreases','Table 2 summarizes the simulated grid. Mean probe tau generally decreases')
    text=text.replace('Under the cluster-max readout on 21-sample subsets','Table 3 compares the readouts. Under the cluster-max readout on 21-sample subsets')
    # Build front matter without ported BiB biography/highlights.
    body=text[text.index('## 1. Introduction'):text.index('## Acknowledgments')]
    if j['code']=='BMC':body=body.replace('## 1. Introduction','## Background').replace('## 2. Materials and methods','## Methods').replace('## 3. Results','## Results').replace('## 4. Discussion','## Discussion').replace('## 5. Conclusions','## Conclusions')
    if j['code']=='CSBJ':body=body.replace('### 2.1. Audited model, statistical unit and pooling','### 2.1. Experimental and Technical Design')
    body=body.replace('## Conclusions\n','## Conclusions\n')
    # Add correct baseline provenance with its own supplementary note.
    body=body.replace('Thirty-five','Thirty-five')
    body=body.replace('from GEO GSE208654, GSE217237 and a public 10x Genomics section.','from GEO GSE208654 [@GSE208654], GSE217237 [@GSE217237] and a public 10x Genomics section [@tenx].')
    if j['code']=='ISCLS':body=body.replace('[@alainbengio;@belinkov]','[@belinkov]')
    # Keep journal-specific implications grounded in the same underlying study.
    implications={
      'BiB':'For a problem-solving protocol, users should first identify each supervision channel, then freeze the evaluation unit, perform label-free probes and document external endpoints. The evidence package supplies worked examples and explicit negative outcomes rather than a universal pass/fail certificate.',
      'BMC':'For computational reproducibility, a reusable report must preserve sample identifiers, pooled arrays, seed definitions, label provenance and the complete refitting operator. These are distinct requirements from regenerating foundation-model features or claiming an independently validated biological endpoint.',
      'CBM':'For computational medicine, a tissue disease score must retain its target definition and patient-level evaluation boundary when moving toward translational use. The present evidence supports an audit demonstration; independent patient-held-out prediction, clinical calibration and decision-utility studies remain unperformed.',
      'CSBJ':'For spatial omics workflows, sample-pooling and readout definitions are part of the biological question. A pathway-derived score, an embedding probe and a spatial autocorrelation statistic should be reported as separate endpoints, with biological interpretation restricted to the acquisition and assay conditions examined.',
      'GPB':'For omics studies, the contribution is a transparent accounting of which data and objectives can explain an apparent disease association. These analyses offer no new molecular mechanism; source-confounded labels and expression-derived targets require independent biological and cohort validation.',
      'ISCLS':'For interdisciplinary computational life science, the workflow connects the learning objective to the statistical test and then to the biological claim. This connection depends on declaring the unit of observation and on retaining negative or unstable results alongside positive associations.'}
    body=body.replace('## 5. Conclusions',implications[j['code']]+'\n\n## 5. Conclusions') if j['code']!='BMC' else body.replace('## Conclusions',implications[j['code']]+'\n\n## Conclusions')
    front='# '+j['title']+'\n\n'
    source_front=text[:text.index('Article type:')]
    authors=source_front[source_front.index('\n\n')+2:].strip()
    if j['code']!='ISCLS':front+=authors+'\n\n'
    abstract=ABSTRACT_GPB if j['code']=='GPB' else ABSTRACT_COMMON
    if j['code']=='BMC':
        sentences=abstract.split(' A standardized association index',1)
        abstract='### Background\n'+sentences[0]+'\n\n### Results\nA standardized association index'+sentences[1].split(' The protocol supports',1)[0]+'\n\n### Conclusions\nThe protocol supports traceable computational evaluation and confines biological claims to the information source, statistical unit and endpoint examined.'
    front+='## Abstract\n'+abstract+'\n\nKeywords: spatial transcriptomics; model auditing; supervision dependence; representation probing; permutation inference; reproducibility\n\n'
    return front+body+declarations(j)+('\n\n## Key Points\n\n'+ '\n\n'.join('• '+s for s in KEYPOINTS) if j['code']=='BiB' else '')+'\n\n[[REFERENCES]]\n\n[[FIGURES]]\n'

KEYPOINTS=[
 'Supervision ablations, score–label association and label-free representation probes answer different questions.',
 'Fixed-score permutations after supervised fitting do not identify causal supervision dependence.',
 'Identity-confounded controls reveal contamination in probes of label-trained transductive encoders.',
 'Simulation threshold summaries depend on the generated cohorts and training-seed dependence.',
 'The cervical demonstration supports a limited computational audit, without held-out clinical classification claims.'
]
AI='The original study materials report use of Trae for analysis-code generation, numerical verification, figures from computed results and English editing. OpenAI Codex was additionally used for editorial review, checking source evidence, journal-specific restructuring and preparation of submission files. Authors are responsible for reviewing the final analyses, references and text; no AI system is an author.'
ETHICS='This study reanalyses publicly available human transcriptomic datasets without new recruitment or intervention. Source-study consent, ethics and data-use conditions apply. No new institutional approval number or exemption determination is asserted.'
FUNDING='This work received no specific grant from public, commercial or not-for-profit funding agencies.'
CONFLICT='Mingwei Bai and Zhiping Ni are affiliated with JiMei Technology Group Co., Ltd. The original author statement declares no known competing financial interests or personal relationships that could have influenced this work.'
CONTRIB='Mingwei Bai: conceptualization, methodology, software, formal analysis, investigation, data curation, visualization and writing—original draft. Zhengmin Gu: data curation, validation and writing—review and editing. Ye Zhang: data curation, resources and writing—review and editing. Zhiping Ni: software, validation and writing—review and editing. Lang Guo: conceptualization, methodology, supervision, project administration and writing—review and editing.'
AVAIL='Source datasets and accession identifiers are listed in the Methods and Supplementary Materials. Supplementary Data 1 (the audit evidence archive) contains pooled representations, numerical summaries, analysis source code and SHA-256 checksums. Complete model regeneration additionally requires the public source datasets and separately obtained foundation-model weights. Dataset-specific access and licensing conditions apply.'
ACK='We acknowledge the investigators and participants responsible for the public datasets. '+AI
def declarations(j):
    if j['code']=='ISCLS':return '\n\n## Statements and Declarations\nAuthor contributions, funding, acknowledgements and competing-interest disclosures are supplied on the separate title page for double-blind review.\n\n### Ethics\n'+ETHICS+'\n\n### Data availability\nSource accession identifiers are supplied in the manuscript. An anonymized audit evidence archive accompanies the submission; identifying repository details are supplied separately to the editorial office.\n\n### AI assistance\n'+AI
    parts=[('Ethics approval and consent to participate',ETHICS),('Consent for publication','Not applicable. The manuscript does not present identifiable participant details.'),('Availability of data and materials',AVAIL),('Competing interests',CONFLICT),('Funding',FUNDING),("Authors’ contributions",CONTRIB),('Acknowledgements',ACK)]
    if j['code']!='BMC':parts=[('Funding',FUNDING),('Acknowledgements',ACK),('CRediT author statement',CONTRIB),('Declaration of competing interests',CONFLICT),('Ethics',ETHICS),('Consent for publication','Not applicable. The manuscript does not present identifiable participant details.'),('Data availability',AVAIL),('Declaration of generative AI and AI-assisted technologies',AI)]
    return '\n\n## '+('Declarations' if j['code']=='BMC' else 'Statements and Declarations')+'\n\n'+'\n\n'.join('### '+h+'\n'+v for h,v in parts)

S8='''## Supplementary Note S8. Provenance and limits of the independent expression proxy baseline
The stored results/baseline_hpv_auc.json was produced by scripts/baseline_hpv_auc_eval.py. The baseline regresses expression on frozen foundation-model morphology features using RidgeCV, with input scaling fitted inside each leave-one-section-out fold. Global gene alignment and variable-gene selection precede the folds. For each held-out section, the observed mean expression of the nominal 108-gene pathway panel is median-thresholded across spots to define a binary proxy; mean predicted panel expression provides the continuous score. The stored ridge summary is 0.4967 (SD 0.0205), calculated from 16 valid within-section spot-level receiver-operating-characteristic curves among 35 attempted section folds; constant or single-class outcomes are not valid curves. The valid-fold count and missing curves must accompany the mean. This proxy is neither laboratory HPV status nor section-level histological disease. The baseline is distinct from the multimodal reference model and cannot estimate that model's held-out disease-classification performance. Consequently no paired comparison or performance collapse from an in-cohort disease AUC of 1.00 is claimed.
'''

def revised_supp(j):
    text=(SRC/'Supplementary_BiB.md').read_text(encoding='utf-8-sig')
    text=common_fix(text)
    text=text[text.index('## Supplementary Note S1'):]
    text=text.replace('C3 Label dependence. Report the mean tau, the permutation-null calibration, LDI and the θ-gate decision, together with the numeric precision used to compute the statistic.','C3 Score–label association. Report the mean tau, fixed-score permutation-null summary, descriptive standardized index and reference cutoff with numeric precision. This screen cannot identify supervision dependence or leakage after label-trained fitting; report complementary ablations and controls.')
    text=text.replace('Clauses C3 and C4 are the operative core:', 'Clauses C3 and C4 address complementary questions:')
    text=text.replace('C3 summarizes observed score–label association; ablations are needed to assess supervision effects, and C4 tests whether any disease-associated information survives in the representation once that supervision is removed.','C3 summarizes observed score–label association, whereas C4 probes the label-free representation. Both remain subject to source confounding and transductive preprocessing.')
    text=text.replace('The main text measures the C4 grading rule\'s error rates directly on known-signal cohorts.','The main text reports a tau-only run-level threshold screen and a distinct cohort-level rule that additionally uses seed significance. Nominal binomial intervals ignore shared-cohort dependence; neither operating characteristic is an independently validated clinical error rate.')
    text=text.replace('The LDI gate is stable across α ∈ {0.01, 0.05, 0.10, 0.20} and five permutation seeds (LDI 3.25–3.30, twenty combinations) (Figure S4; Figure S5).','The separate seed-0 association screen is stable across α ∈ {0.01, 0.05, 0.10, 0.20} and five permutation seeds (index 3.25–3.30, twenty combinations). Figure S4 displays these null summaries; it does not validate the model-training procedure under a null.')
    text=text.replace('Intercept sensitivity for the cervical NOALL probe','The stored float32 arithmetic is retained for the primary probe standardization and Gram products, with 10⁻⁸ added to standard deviations. Recomputing entirely in float64 changes seed-0 and seed-1 tau from 0.20736 and 0.40380 to 0.21463 and 0.39652; the three-seed mean remains 0.27041. This is a numerical sensitivity check, separate from the indeterminate scalar head. Intercept sensitivity for the cervical NOALL probe')
    text=text.replace('the same θ-gate','the same reference cutoff')
    # Drop stale mixed-definition calibration and redundant local-controls figures.
    text=re.sub(r'\n\n\{\{FIG:Fig8_LDI_calibration\|.*?\}\}', '', text, flags=re.S)
    text=re.sub(r'\n\n\{\{FIG:Fig9_Local_controls\|.*?\}\}', '', text, flags=re.S)
    text=text.replace('(Figure S4; Figure S5)','(Figure S4)').replace('Figures S4 and S5','Figure S4')
    pos=text.index('{{FIG:')
    text=text[:pos]+S8+'\n'+text[pos:]
    text+='\n\n{{FIG:FigS4_Association_screen|Figure S4. Descriptive fixed-score association screen. A: standardized indices for the representative FULL seed-0 score over five permutation seeds, with Gaussian reference cutoffs for four alpha values. B: permutation-null mean and standard deviation for each seed. The observed statistic uses the same representative run as its null. This analysis checks numerical sensitivity and does not test the fitted training procedure or identify causal supervision dependence.}}\n'
    # External endpoint plot and table are explicitly cited.
    text=text.replace('[[STABLE1]]','Table S1 defines the ablation variants.\n\n[[STABLE1]]')
    text=text.replace('main text §3.4','the main-text cervical demonstration').replace('main text §3.3','the main-text published-method audit')
    text=text.replace('GEO GSE316098 contains','GEO GSE316098 [@GSE316098] contains')
    text=text.replace('Head-and-neck mean Moran\'s I was','The head-and-neck data sources were GSE268014 [@GSE268014] and GSE281978 [@GSE281978]. Head-and-neck mean Moran\'s I was')
    front='# '+j['title']+'\n\nSupplementary Materials\n\n'
    if j['code']!='ISCLS':front+='Mingwei Bai, Zhengmin Gu, Ye Zhang, Zhiping Ni, Lang Guo\n\n'
    return front+text

def reference_text(k,code):
    r=REF[k]; authors=[]
    for full in r['authors']:
        if not full.strip():continue
        if any(w in full.lower() for w in ['consortium','network','collaboration','group','10x genomics']):authors.append(full);continue
        p=full.split(); authors.append(p[-1]+' '+''.join(x[0] for x in p[:-1] if x and x[0].isalpha()))
    if code=='BiB' and len(authors)>3:authors=authors[:3]+['et al']
    elif code=='BMC' and len(authors)>6:authors=authors[:6]+['et al']
    au=', '.join(authors)
    if r.get('dataset'):return f"[dataset] {au}. {r['title']}. {r['journal']}; {r['year']}. {r['url']} (accessed 16 October 2026)."
    if code=='ISCLS':return f"{au} ({r['year']}) {r['title']}. {r['journal']} {r.get('volume','')}:{r.get('page','')}. {r['url']}"
    return f"{au}. {r['title']}. {r['journal']}. {r['year']};{r.get('volume','')}:{r.get('page','')}. {r['url']}"

def clean_setup(line_numbers=False):
    d=setup()
    d.core_properties.author='';d.core_properties.last_modified_by='';d.core_properties.comments=''
    for st in ['Title','Heading 1','Heading 2','Heading 3']:
        d.styles[st].font.color.rgb=RGBColor(0,0,0)
    # Strip the built-in Title paragraph border (renders as a blue rule in WPS).
    for node in d.styles.element.xpath('.//w:pBdr'):
        node.getparent().remove(node)
    d.styles['Normal'].paragraph_format.line_spacing=1.5
    for s in d.sections:
        footer=s.footer.paragraphs[0];footer.clear();footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
        footer._p.append(element('w:fldSimple',**{'w:instr':'PAGE'}))
        if line_numbers:
            ln=element('w:lnNumType',**{'w:countBy':'1','w:restart':'continuous','w:distance':'180'});s._sectPr.append(ln)
    return d

def paragraph(d,b):
    if b.startswith('### '):return d.add_heading(b[4:],2)
    if b.startswith('## '):return d.add_heading(b[3:],1)
    if b.startswith('# '):return d.add_paragraph(b[2:],style='Title')
    if b.startswith('• '):return d.add_paragraph(b[2:],style='List Bullet')
    return d.add_paragraph(b)

def cite_text(text,order):
    def replace(m):
        keys=[x.strip().lstrip('@') for x in m[1].split(';')]
        for k in keys:
            if k not in order:order.append(k)
        return '['+', '.join(str(order.index(k)+1) for k in keys)+']'
    return re.sub(r'\[@([^\]]+)\]',replace,text)

def add_figure(d,path,caption):
    d.add_page_break();im=Image.open(path);w,h=im.size
    width=min(6.45,6.5*w/h)
    p=d.add_paragraph();p.paragraph_format.keep_with_next=True;p.add_run().add_picture(str(path),width=Inches(width))
    d.add_paragraph(caption,style='Caption')

def build_doc(text,path,j,order,supp=False,figdir=None):
    text=cite_text(text,order)
    text=re.sub(r'(?m)^(#{1,3} [^\n]+)\n(?!\n)',r'\1\n\n',text)
    d=clean_setup(line_numbers=path.name.startswith('Manuscript_'))
    if not path.name.startswith(('Manuscript_','Supplementary_')):
        d.styles['Normal'].paragraph_format.line_spacing=1.0
        d.styles['Normal'].paragraph_format.space_after=Pt(5)
    eq=0; resolved=[];in_abstract=False
    for b in text.split('\n\n'):
        b=b.strip()
        if not b:continue
        if b=='[[REFERENCES]]':
            d.add_heading('References',1)
            for i,k in enumerate(order,1):
                p=d.add_paragraph(f'[{i}] '+reference_text(k,j['code']));p.paragraph_format.line_spacing=1;p.paragraph_format.space_after=Pt(4)
                for r in p.runs:r.font.size=Pt(10)
            resolved.append('## References\n\n'+'\n\n'.join(f'[{i}] '+reference_text(k,j['code']) for i,k in enumerate(order,1)))
            continue
        if b=='[[FIGURES]]':
            for name,cap in CAPTIONS[:4]:add_figure(d,figdir/(name+'.png'),common_fix(cap))
            resolved.extend(common_fix(c) for _,c in CAPTIONS[:4]);continue
        tables={'[[TABLE1]]':(T3H,T3R,[1300,3900,4160],'Table 1. Cohort-level representation grading criteria. These require significance across seeds and differ from the run-level tau-only threshold screen.'),'[[TABLE2]]':(T4H,T4R,[1900,1450,700,1100,1450,700,2060],common_fix(T4T)+' The nine runs reuse three generated cohorts. Binomial intervals are nominal and do not account for shared-cohort dependence. Displayed aggregate grades summarize all nine runs; the formal per-cohort rule uses three training seeds.'),'[[TABLE3]]':(T5H,T5R,[1160,1320,1280,1320,1380,1440,1460],common_fix(T5T)),'[[STABLE1]]':(T1H,T1R,[1450,2900,5010],'Table S1. Explicit ablation design. Each row contrasts with FULL.'),'[[STABLE2]]':(T2H,T2R,[2350,3200,3810],'Table S2. External evidence and the interpretation it supports.')}
        if b in tables:
            h,r,w,cap=tables[b];table(d,h,r,w,cap);resolved.append(cap+'\n\n'+' | '.join(h)+'\n'+'\n'.join(' | '.join(x) for x in r));continue
        if b.startswith('$$'):
            p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;om=element('m:oMath')
            for part in EQS[eq][0]:om.append(copy.deepcopy(part))
            p._p.append(om);p.add_run('    ('+str(eq+1)+')');eq+=1
            formulas=['τ_b = (C − D) / √[(C + D + T_s)(C + D + T_y)]','LDI = (τ̄_FULL − τ_⊥) / σ_null; θ = Φ⁻¹(1 − α)','p_refit = [1 + Σ_b I{τ(ŷ[y_πb], y_πb) ≥ τ(ŷ[y], y)}] / (B + 1)','τ_max = √[n₀ n₁ / binom(n₀+n₁,2)]','sens(c) = Pr(τ̂ ≥ c | L1); fpr(c) = Pr(τ̂ ≥ c | CTRL)']
            resolved.append(formulas[eq-1]);continue
        if b.startswith('{{FIG:'):
            name,cap=b[6:-2].split('|',1);add_figure(d,figdir/(name+'.png'),cap);resolved.append(cap);continue
        if b=='## Abstract':in_abstract=True
        p=paragraph(d,b)
        if in_abstract and not b.startswith('Keywords:'):p.paragraph_format.keep_with_next=True
        if b.startswith('Keywords:'):in_abstract=False
        resolved.append(b)
    # Abstract and headings should not be stranded at page boundaries.
    d.save(path)
    write(path.with_suffix('.md'),'\n\n'.join(resolved)+'\n')
    return d

def prep_figures(dest):
    dest.mkdir(parents=True,exist_ok=True)
    keep=[c[0] for c in CAPTIONS[:7]]
    for n in keep:
        for ext in ['pdf','png','svg','tif']:
            f=SRC/'figures'/(n+'.'+ext)
            if f.exists():shutil.copy2(f,dest/f.name)
    # Regenerate plotted panels with larger labels for a 6.45-inch manuscript width.
    from matplotlib.patches import FancyBboxPatch
    source=(ROOT/'scripts/bib_build_package.py').read_text(encoding='utf-8-sig')
    chunk=source[source.index('    # Fig1 workflow'):source.index('    # Fig8 / Fig9')]
    chunk=re.sub(r'fontsize=([\d.]+)',lambda m:'fontsize='+str(max(12,float(m[1])*1.25)),chunk)
    chunk=chunk.replace("'Supported-grade threshold θ'","'Run-level correlation threshold c'").replace("'θ=0.35'","'c=0.35'")
    chunk=chunk.replace('Measured error rates; checksums','Simulation results; checksums')
    chunk=chunk.replace('Diamonds: in-sample fit, no test applies. Dots: leave-one-out probes (filled p<0.05).','\\nDiamonds: in-sample fit. Dots: sample-held-out probes (filled p<0.05).')
    chunk=chunk.replace("figsize=(10.8,3.9)","figsize=(10.8,5.0)").replace("figsize=(10.4,4.2)","figsize=(10.4,5.1)")
    chunk=chunk.replace("figsize=(9.8,4.2)","figsize=(9.8,5.0)").replace("rect=(0,.045,1,1)","rect=(0,.12,1,1)")
    chunk=chunk.replace('FULL head\\n(in-sample fit)','FULL head\\nIn-sample fit').replace('label-trained embedding\\n(“held-out” probe)','Label-trained\\nProbe').replace('label-free embedding\\n(held-out probe)','Label-free\\nProbe')
    chunk=re.sub(r'        for i,m in enumerate\(means\):ax.text\([^\n]+', '        # Means are represented by bars; avoid labels obscuring individual points.',chunk)
    chunk=chunk.replace("axs[0].legend(fontsize=12,frameon=False,ncol=2,loc='upper right')","fig.legend(*axs[0].get_legend_handles_labels(),fontsize=12,frameon=False,ncol=2,loc='lower center',bbox_to_anchor=(.5,.005))")
    chunk=chunk.replace("fig.tight_layout();savefig(fig,'Fig4_Methods_benchmark')","fig.tight_layout(rect=(0,.13,1,1));savefig(fig,'Fig4_Methods_benchmark')")
    chunk=re.sub(r";axs\[0\]\.legend\(fontsize=[\d.]+,loc='upper right',ncol=2\)", '',chunk)
    chunk=chunk.replace('HPV-status p = 0.200 / 0.133\\nOrganization does not establish discrimination','HPV-status p = 0.200 / 0.133\\nNot evidence of discrimination')
    chunk=chunk.replace('Orientation must be inspected before averaging biological associations','Score–program associations across ablations')
    ns={'np':np,'plt':plt,'FancyBboxPatch':FancyBboxPatch,'COL':['#167D9A','#E0A038','#B74F59'],'S':read(EV/'sim_power_summary_refit.json'),'SO':read(EV/'sim_power_summary.json'),'CFP':read(EV/'v2_ctrl_full_probe_refit.json'),'OSP':read(EV/'v2_ours_subset_probe_refit.json'),'BM':read(EV/'st_methods_benchmark_v2.json'),'REG':read(EV/'real_run_registry.json'),'P':read(EV/'corrected_probe.json'),'BIO':read(ROOT/'results/decircularization_biology.json')['variants'],'G':read(EV/'geomx_patient_final.json'),'N':read(ROOT/'results/paper_v10_numbers.json'),'TM_MAIN':math.sqrt(4000/8010),'TM_SMALL':math.sqrt(248/1190),'TM_SUB_M':math.sqrt(216/420),'TM_SUB_S':math.sqrt(76/420)}
    def roc_window(size):
        r=ns['S']['threshold_roc'][size];v=[t for t,a,b in zip(r['threshold'],r['sensitivity'],r['one_minus_specificity']) if a==1 and b==0];return min(v),max(v)
    def savefig(fig,name):
        for ext in ['pdf','svg','png']:fig.savefig(dest/(name+'.'+ext),dpi=600,bbox_inches='tight')
        with Image.open(dest/(name+'.png')) as im:im.save(dest/(name+'.tif'),compression='tiff_lzw',dpi=(600,600))
        plt.close(fig)
    ns.update(roc_window=roc_window,savefig=savefig)
    import textwrap
    plt.rcParams.update({'font.size':12,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
    exec(textwrap.dedent(chunk),ns)
    plt.rcParams.update({'font.size':10})
    # Regenerate Fig2 from its numeric source with the correct tau-only axis label.
    source=(ROOT/'scripts/bib_build_package.py').read_text(encoding='utf-8-sig')
    chunk=source[source.index('    # Fig2 operating characteristics'):source.index('    # Fig3 dissociation')]
    chunk=chunk.replace("'Supported-grade threshold θ'","'Run-level correlation threshold c'").replace("'θ=0.35'","'c=0.35'")
    ns={'S':read(EV/'sim_power_summary_refit.json'),'np':np,'plt':plt,'COL':['#167D9A','#E0A038','#B74F59'],'TM_MAIN':math.sqrt(4000/8010),'TM_SMALL':math.sqrt(248/1190)}
    def roc_window(size):
        r=ns['S']['threshold_roc'][size];v=[t for t,a,b in zip(r['threshold'],r['sensitivity'],r['one_minus_specificity']) if a==1 and b==0];return min(v),max(v)
    def savefig(fig,name):
        for ext in ['pdf','svg','png']:fig.savefig(dest/(name+'.'+ext),dpi=600,bbox_inches='tight')
        with Image.open(dest/(name+'.png')) as im:im.save(dest/(name+'.tif'),compression='tiff_lzw',dpi=(600,600))
        plt.close(fig)
    ns.update(roc_window=roc_window,savefig=savefig)
    import textwrap
    # Use stacked panels so Fig2 retains readable labels at manuscript page width.
    chunk=chunk.replace("plt.subplots(1,3,figsize=(10.8,3.9))","plt.subplots(3,1,figsize=(6.45,7.7))")
    chunk=chunk.replace("fig.tight_layout();savefig", "fig.tight_layout(h_pad=1.5);savefig")
    plt.rcParams.update({'font.size':10})
    exec(textwrap.dedent(chunk),ns)
    # Redraw the workflow with text explicitly sized to fit each box.
    from matplotlib.patches import FancyBboxPatch
    fig,ax=plt.subplots(figsize=(6.45,4.0));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    nodes=[(.02,.65,'Input provenance','Expression and images\nCoordinates and groups'),(.365,.65,'Supervision','Six ablation variants\nAll recorded seeds'),(.71,.65,'Representation','Label-free encoder\nPool within sections'),(.71,.29,'Refitted probes','Training-fold scaling\nRefit each permutation'),(.365,.29,'External endpoints','Tissue and score direction\nOrganization and phenotype'),(.02,.29,'Evidence and limits','Effects and seed variation\nSimulation summaries')]
    for x,y,h,b in nodes:
        ax.add_patch(FancyBboxPatch((x,y),.27,.24,boxstyle='round,pad=.008',facecolor='#EEF5F7',edgecolor='#167D9A'))
        ax.text(x+.135,y+.19,h,ha='center',va='center',weight='bold',fontsize=9)
        ax.text(x+.135,y+.085,b,ha='center',va='center',fontsize=8.2,linespacing=1.5)
    for a,b in [((.30,.77),(.35,.77)),((.645,.77),(.695,.77)),((.845,.635),(.845,.55)),((.695,.41),(.65,.41)),((.35,.41),(.30,.41))]:ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','lw':1.3,'color':'#38566A'})
    ax.text(.5,.16,'Known-signal simulations and identity-confounded controls',ha='center',fontsize=9)
    ax.text(.5,.075,'Sections are the evaluation unit; encoding remains transductive.\nCervical tissue illustrates the audit without establishing clinical performance.',ha='center',fontsize=8.2,linespacing=1.5)
    fig.tight_layout();savefig(fig,'Fig1_Audit_workflow')
    # Do not present the numerically indeterminate NOALL scalar head as an effect.
    registry=read(EV/'real_run_registry.json');probes=read(EV/'corrected_probe.json')['groups']['cervical']
    fig,axs=plt.subplots(1,2,figsize=(9,4),gridspec_kw={'width_ratios':[1.35,1]})
    for i,(v,rows) in enumerate(registry.items()):
        if v=='NOALL':axs[0].text(.04,i,'Indeterminate scalar ordering',va='center',fontsize=8,color='#777777');continue
        vals=[r['tau'] for r in rows];axs[0].scatter(vals,np.full(len(vals),i)+np.linspace(-.1,.1,len(vals)),s=22,color='#167D9A');axs[0].errorbar(np.mean(vals),i,xerr=np.std(vals,ddof=1),fmt='|',color='#263D4A',capsize=3)
    axs[0].set_yticks(range(len(registry)),list(registry));axs[0].invert_yaxis();axs[0].axvline(0,lw=.8,color='#888888');axs[0].set(xlabel='In-cohort score–severity tau-b',title='A  Descriptive ablation contrasts',xlim=(-.05,.51))
    for i,r in enumerate(probes):
        p=r['legacy_no_intercept'];axs[1].scatter(i,p['tau'],s=50,color='#167D9A');axs[1].text(i,p['tau']+.04,'p = %.4f'%p['p_refit'],ha='center',fontsize=8)
    axs[1].set(xticks=[0,1,2],xticklabels=['Seed 0','Seed 1','Seed 2'],ylim=(-.05,.57),xlim=(-.55,2.55),ylabel='Sample-held-out probe tau-b',title='B  Label-free representation');axs[1].axhline(0,lw=.8,color='#888888');fig.tight_layout();savefig(fig,'Fig5_Cervical_audit')
    # Recompute a consistent supplementary screen figure from one representative run.
    dat=read(ROOT/'results/csbj_local_controls.json')['theta_robustness']
    rows=dat['per_alpha']['0.05']['rows'];fig,ax=plt.subplots(1,2,figsize=(7,3.7))
    x=np.arange(len(rows));val=[r['ldi'] for r in rows]
    ax[0].plot(x,val,'o-',color='#167D9A',label='Seed-0 score index')
    for a,c in [('0.01','#9b4c55'),('0.05','#c99027'),('0.1','#55757e'),('0.2','#7e6a98')]:
        key=next(k for k in dat['per_alpha'] if float(k)==float(a));r=dat['per_alpha'][key]['rows'][0]
        ax[0].axhline(r['theta_z'],ls='--',lw=1,label='Gaussian cutoff α='+a,color=c)
    ax[0].set(xticks=x,xticklabels=[str(r['perm_seed'])[-2:] for r in rows],xlabel='Permutation seed suffix',ylabel='Standardized association index',ylim=(0,3.7));ax[0].legend(fontsize=8,loc='lower right')
    ax[1].plot(x,[r['null_sd'] for r in rows],'s-',color='#167D9A',label='Null SD')
    ax[1].plot(x,[r['null_mean'] for r in rows],'o-',color='#c99027',label='Null mean')
    ax[1].set(xticks=x,xticklabels=[str(r['perm_seed'])[-2:] for r in rows],xlabel='Permutation seed suffix',ylabel='Kendall tau-b units');ax[1].legend(fontsize=8)
    for a,label in zip(ax,['A','B']):a.spines[['top','right']].set_visible(False);a.text(-.14,1.02,label,transform=a.transAxes,fontweight='bold')
    fig.tight_layout()
    for ext in ['pdf','svg','png']:fig.savefig(dest/('FigS4_Association_screen.'+ext),dpi=600,bbox_inches='tight')
    plt.close(fig)
    with Image.open(dest/'FigS4_Association_screen.png') as im:im.save(dest/'FigS4_Association_screen.tif',compression='tiff_lzw',dpi=(600,600))
    # Original graphical abstract omits the descriptive-index and transductive limits.
    fig,ax=plt.subplots(figsize=(8.8,3));ax.axis('off')
    steps=[('Identify information sources','Supervision ablations\nSection-level pooling'),('Probe representations','Label-free frozen encoders\nRefit label permutations'),('Bound the interpretation','Readout and endpoint checks\nTransductive limits stated')]
    for i,(h,b) in enumerate(steps):
        xx=.02+i*.335;ax.text(xx+.145,.7,h,ha='center',fontsize=10,fontweight='bold',transform=ax.transAxes);ax.text(xx+.145,.47,b,ha='center',fontsize=10,linespacing=1.7,transform=ax.transAxes,bbox={'boxstyle':'round,pad=.6','fc':'#EEF5F7','ec':'#167D9A'})
    ax.text(.5,.12,'Simulation evidence and a cervical demonstration; no held-out clinical classification claim',ha='center',fontsize=9,transform=ax.transAxes)
    for ext in ['pdf','svg','png']:fig.savefig(dest/('Graphical_Abstract.'+ext),dpi=600,bbox_inches='tight')
    plt.close(fig)
    with Image.open(dest/'Graphical_Abstract.png') as im:im.save(dest/'Graphical_Abstract.tif',compression='tiff_lzw',dpi=(600,600))

def auxiliary(j,folder):
    src=(SRC/'Manuscript_BiB.md').read_text(encoding='utf-8-sig')
    authors=src[src.index('\n\n')+2:src.index('Article type:')].strip()
    title='# '+j['title']+'\n\n'+authors+'\n\nRunning title: Spatial transcriptomic model auditing\n\nArticle type: '+j['kind']+'\n\nKeywords: spatial transcriptomics; model auditing; supervision dependence; representation probing; permutation inference; reproducibility\n\n## Funding\n'+FUNDING+'\n\n## Acknowledgements\n'+ACK+'\n\n## Statements and Declarations\n\n### Competing interests\n'+CONFLICT+'\n\n### Author contributions\n'+CONTRIB+'\n\n### Ethics\n'+ETHICS+'\n\n### Data availability\n'+AVAIL
    if j['code']=='BiB':
        bios=re.search(r'Author biographies: (.*?)\n\nKey Points:',src,re.S)[1]
        title+='\n\n## Author biographies\n'+bios
    cover=f'''# Cover letter
Dear Editor,

Please consider our manuscript, “{j['title']}”, as a {j['kind']} in {j['name']}.

{j['angle']} Spatially coherent tissue scores can mix supervised ordering, representation association and acquisition effects. Our audit makes these distinctions explicit through five reporting clauses, supervision-removal experiments, label-free representation probes with refitted label permutations, and external endpoint checks.

Simulations at 90-sample and 35-sample scales combine three generator cohorts and three training seeds per setting. The reported tau threshold detects all nine strongest-signal runs at each scale and none of 18 pooled control runs. These are shared-cohort simulation summaries with limited precision, rather than independent clinical error-rate estimates. An identity-confounded control demonstrates contamination in probes of label-trained transductive encoders. Published spatial methods illustrate the influence of the readout.

The cervical demonstration comprises 35 sections, including four diseased sections. Label-free probe association is seed-unstable, and acquisition confounding and transductive encoding preclude clinical or causal conclusions. The standardized score–label index is descriptive. We do not claim a held-out disease-classification AUC or interpret an unrelated proxy baseline as a performance collapse.

The work is original and is not under consideration elsewhere. Commercial affiliations are disclosed on the title page and in the author declarations. The work reanalyses public datasets without new recruitment or intervention. An audit evidence archive accompanies the submission.

{AI}

Thank you for considering the manuscript.

Sincerely,
Lang Guo, corresponding author
School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, Shenyang 110034, China
E-mail: guolang1016@symc.edu.cn; Tel: +86 13555707001
On behalf of Mingwei Bai, Zhengmin Gu, Ye Zhang, Zhiping Ni and Lang Guo
'''
    for name,txt in [('TitlePage',title),('CoverLetter',cover)]:
        build_doc(txt,folder/(name+'_'+j['code']+'.docx'),j,[])
    if j['code']=='CBM':
        hl=['Five audit clauses separate supervision effects and representation association.','Identity-confounded controls expose contaminated transductive probes.','Refitted permutations assess probes of label-free frozen representations.','Simulation summaries distinguish generated cohorts from training replicates.','A cervical example shows seed instability and limits on biological claims.']
        assert all(len(s)<=85 for s in hl)
        txt='# Highlights\n\n'+'\n\n'.join('• '+s for s in hl)
        build_doc(txt,folder/'Highlights_CBM.docx',j,[]);write(folder/'Highlights_CBM.txt','\n'.join(hl)+'\n')
    dec='# Author declarations\n\n## Competing interests\n'+CONFLICT+'\n\n## Funding\n'+FUNDING+'\n\n## Author contributions\n'+CONTRIB+'\n\n## Ethics\n'+ETHICS+'\n\n## AI assistance\n'+AI
    build_doc(dec,folder/('Declarations_'+j['code']+'.docx'),j,[])

def evidence_bundle():
    folder=OUT/'_审查记录';folder.mkdir(exist_ok=True)
    write(folder/'references_corrected.json',json.dumps(REF,ensure_ascii=False,indent=2))
    for f in ['reference_verification.json','source_access.json']:shutil.copy2(QA/f,folder/f)
    # Actual evidence files rather than an unsupported completeness assertion.
    zpath=OUT/'Audit_evidence.zip';manifest=[]
    files=[(p,'evidence/'+p.name) for p in EV.iterdir() if p.is_file()]
    files += [(p,'evidence/st_method_embeddings/'+p.name) for p in (ROOT/'results/st_method_embeddings').glob('*.npz')]
    files += [(p,'evidence/pooled_grid/'+p.name) for p in (ROOT/'results/pooled_grid').glob('*.npz')]
    files += [(ROOT/'scripts/reproduce_submission_audit.py','reproduce_audit.py')]
    files += [(ROOT/'results'/n,'evidence/'+n) for n in ['baseline_hpv_auc.json','csbj_local_controls.json','csbj_ldi_validated.json']]
    files += [(ROOT/'scripts'/n,'scripts/'+n) for n in ['probe_lodo.py','refit_grid_audit.py','probe_unified_readout.py','baseline_hpv_auc_eval.py','csbj_local_controls.py','csbj_ldi_recompute.py','sim_power_grid.py','benchmark_st_methods.py']]
    files += [(p,p.relative_to(ROOT).as_posix()) for p in (ROOT/'src').rglob('*.py')]
    files += [(ROOT/'scripts'/n,'scripts/'+n) for n in ['train_st.py','infer_st.py','simulate_st_positive_control.py','csbj_review_verify.py']]
    files += [(ROOT/'requirements.txt','requirements.txt')]
    files += [(folder/'references_corrected.json','evidence/references_corrected.json')]
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
        for p,n in files:
            if not p.exists():continue
            raw=p.read_bytes()
            if p.name=='st_method_embeddings_manifest.json':
                m=json.loads(raw)
                for g in m['groups'].values():
                    for d in g['methods'].values():d['export']='evidence/st_method_embeddings/'+Path(d['export']).name
                raw=json.dumps(m,indent=2,ensure_ascii=False).encode()
            z.writestr(n,raw);manifest.append(hashlib.sha256(raw).hexdigest()+'  '+n)
        z.writestr('SHA256SUMS.txt','\n'.join(manifest)+'\n')
        z.writestr('README.txt','Audit evidence for journal alternatives. Original result files are preserved for traceability; their historical labels and conclusions are not endorsements. See revised manuscripts for interpretation. Three training seeds share each generated cohort. The fixed-score LDI screen is descriptive. The 0.4967 AUC is a separate within-section expression-proxy baseline (16 valid folds), not held-out disease classification.\n\nCPU reproduction: install numpy and scipy in your environment, extract this archive, and run python reproduce_audit.py --section primary --permutations 10000. Other sections: published (12 embedding arrays), grid (108 pooled arrays), all. Results are written to audit_reproduction.json. The primary section reproduces the 21 main probe tests; this subset was independently checked during manuscript revision. Model training was not rerun.\n\nHistorical scripts/ preserve original paths as source provenance; they are not a one-command end-to-end training reproduction. Complete training requires public source data and separately obtained foundation-model weights. Source modules and the project requirements are included.\n')
    return zpath

def main():
    if not (QA/'references_corrected.json').exists():collect_sources()
    else:REF.update(read(QA/'references_corrected.json'))
    # Crossref stores corporate authors in 'name', not 'family'. Repair cached metadata.
    for k in ['tcga','scipy','dome']:
        if k in REF and any(not a.strip() for a in REF[k]['authors']):
            kk,res=verify_ref((k,REF[k]))
            if 'metadata' in res:REF[kk]=res['metadata']
    write(QA/'references_corrected.json',json.dumps(REF,ensure_ascii=False,indent=2))
    # Add primary data-source entries, using locally retained GEO SOFT metadata.
    for acc in ['GSE208654','GSE217237','GSE268014','GSE281978','GSE316098']:
        meta=(EV/(acc+'_metadata.txt')).read_text(encoding='utf-8-sig')
        title=re.search(r'!Series_title = (.+)',meta)[1].strip()
        au=re.findall(r'!Series_contributor = (.+)',meta)
        if not au:au=re.findall(r'!Series_contact_name = (.+)',meta)
        au=[' '.join(p.strip() for p in a.strip().split(',') if p.strip()) for a in au]
        date=re.search(r'!Series_status = Public on (.+)',meta)
        year=int(re.search(r'\d{4}',date[1])[0]) if date else 2026
        REF[acc]={'title':title+' ['+acc+']','authors':au,'year':year,'journal':'NCBI Gene Expression Omnibus','volume':'','page':'','doi':'','url':'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc='+acc,'dataset':True}
    REF['tenx']={'title':'Visium FFPE Human Cervical Cancer, Space Ranger 1.3.0','authors':['10x Genomics'],'year':'n.d.','journal':'10x Genomics public datasets','volume':'','page':'','doi':'','url':'https://www.10xgenomics.com/datasets/human-cervical-cancer-1-standard','dataset':True}
    REF['whalen']['year']=2022
    # Correct the equations to state refitting rather than permuting predictions.
    EQS[2]=[[sub('p','refit'),mr(' = '),fraction([mr('1 + '),summ('b=1','B','I{ τ(ŷ[y_πᵦ], y_πᵦ) ≥ τ(ŷ[y], y) }')],'B + 1')]]
    EQS[4]=[[mr('sens(c) = Pr( τ̂ ≥ c | L1 ),      fpr(c) = Pr( τ̂ ≥ c | CTRL )')]]
    T4T_NEW=common_fix(T4T)
    # Shared captions must not claim independent error rates or prespecification.
    for i,(n,c) in enumerate(CAPTIONS):
        c=common_fix(c).replace('error rates','simulation operating characteristics').replace('supported-grade threshold','run-level correlation threshold')
        if i==1:c+=' Training seeds share generated cohorts; the run-level threshold screen is distinct from the cohort grade requiring seed significance.'
        if i==4:c+=' The NOALL scalar ordering is omitted because it is numerically indeterminate; its frozen representation is evaluated separately in panel B.'
        CAPTIONS[i]=(n,c)
    basefig=QA/'figures';prep_figures(basefig)
    stats=[]
    for j in JOURNALS:
        dest=OUT/j['name'].replace(':','');dest.mkdir(exist_ok=True)
        figures=dest/'figures';shutil.copytree(basefig,figures,dirs_exist_ok=True)
        m=revised_main(j);s=revised_supp(j)
        order=[]
        cite_text(m,order);cite_text(s,order)
        mainname='Manuscript_'+j['code']+('_blinded' if j['code']=='ISCLS' else '')
        suppname='Supplementary_'+j['code']+('_blinded' if j['code']=='ISCLS' else '')
        build_doc(m,dest/(mainname+'.docx'),j,order,figdir=figures)
        # Supplementary references must be self-contained for separate upload.
        build_doc(s+'\n\n[[REFERENCES]]',dest/(suppname+'.docx'),j,order,supp=True,figdir=figures)
        auxiliary(j,dest)
        write(dest/'References.txt','\n\n'.join(f'[{i}] '+reference_text(k,j['code']) for i,k in enumerate(order,1)))
        write(dest/'References.bib','\n\n'.join('@article{'+k+',\n  title = {'+REF[k]['title']+'},\n  author = {'+' and '.join(REF[k]['authors'])+'},\n  year = {'+str(REF[k]['year'])+'},\n  journal = {'+REF[k]['journal']+'},\n  doi = {'+REF[k].get('doi','')+'},\n  url = {'+REF[k]['url']+'}\n}' for k in order))
        # Abstract word count excludes headings; manuscript body count excludes endmatter.
        ab=m[m.index('## Abstract')+11:m.index('Keywords:')];aw=len(re.findall(r'\b[\w]+(?:[–-][\w]+)*\b',re.sub(r'(?m)^#+.*$','',ab)))
        assert aw<=j['abstract_limit'],(j['code'],aw)
        body=m[m.index('## Background') if j['code']=='BMC' else m.index('## 1.'):m.index('## Statements and Declarations') if j['code']!='BMC' else m.index('## Declarations')]
        wc=len(re.findall(r'\b[\w]+(?:[–-][\w]+)*\b',body))
        if 'limit' in j:assert wc<=j['limit'],(j['code'],wc)
        guide=f'''# {j['name']} 投稿文件说明

核验日期：2026-10-16。稿件类型：{j['kind']}。

期刊适配判断：{j['fit']}

官方指南：{j['guide']}

摘要 {aw} 词；正文约 {wc} 词（不含参考文献、表格及图注，具体以投稿系统计数为准）。主图 4 张、主表 3 张；补充图 4 张、补充表 2 张。Word 公式可编辑，表格为可编辑文本，图件提供独立文件。

## 上传文件

- {mainname}.docx：正文、参考文献、主表和审稿用主图。
- {suppname}.docx：完整补充方法、补充图表和参考文献。GPB 请使用同名 PDF 附录。
- TitlePage_{j['code']}.docx：作者、单位、通讯信息及作者相关声明。
- CoverLetter_{j['code']}.docx：对应期刊投稿信。
- Declarations_{j['code']}.docx：作者声明，供编辑或系统要求时上传。
- figures/：主图 Fig1–Fig4，补充图 Fig5–Fig7 和 FigS4，以及单独 Graphical_Abstract。
- 上级目录 Audit_evidence.zip：审查证据与原始计算摘要。ISCLS 使用本刊目录的匿名附件版本。
'''
        if j['code']=='ISCLS':guide+='\n双盲要求：只将带 blinded 的正文和补充材料交给审稿人；标题页、投稿信、作者声明指定为不供审稿文件。匿名证据附件只含去标识后的聚合计算与嵌入数组。作者身份和仓库地址通过编辑文件另供；勿上传共享非匿名证据包。\n'
        if j['code']=='CBM':guide+='\nHighlights_CBM.docx / .txt 为 5 条独立 highlights，每条不超过 85 字符。CBM 官方指南本次直接访问被拒，部分细则未能独立核验；摘要按不超过 250 词、独立 highlights 等保守格式准备，必须在投稿系统复核当前强制字段。\n'
        if j['code']=='CSBJ':guide+='\n按现行 SPJ 作者指南准备 Research article。未套用 Elsevier 旧版 highlights 要求；该文不是按 Method article 申报，因为现有 7 个主展示项超过其 5 项限制。作者许可/利益冲突等签署表按当前系统办理，不代签。\n'
        guide+='''
## 尚不能替作者完成的项目

1. 作者已表示没有 ORCID；BiB 官方要求投稿作者提供 ORCID，需作者注册后填写。其他期刊以当前系统字段为准，不编造编号。
2. 公开人类数据二次分析的机构伦理认定/豁免材料尚未提供。现稿只陈述现有事实；如果编辑要求机构认定或具体编号，需真实材料后补齐。
3. 本次编辑后的全文、AI 使用披露、作者贡献、商业单位利益声明和单一在审状态需全部作者最终核实。原声明不能替代对本轮新文本的实际批准。
4. 公共代码 release 的可访问性以审查记录为准；提交前确保读者确实能下载所述版本。若公开链接不可用，可先将证据包作为附件，但公开代码声明仍需修正或恢复真实可访问地址。
5. 六套是同一研究的备选版本，应选择一个期刊提交；不得同时在多刊审稿。

上述待办未落实前，本套文件是已经完成实质修订的投稿候选包，不能声称所有行政条件已满足。稿件接受与否还取决于新颖性、方法充分性及编辑判断。
'''
        write(dest/'投稿文件说明.md',guide)
        stats.append({'journal':j['name'],'code':j['code'],'folder':dest.name,'abstract_words':aw,'body_words':wc,'references':len(order),'main':mainname,'supp':suppname})
        print(j['code'],'built',aw,wc,flush=True)
    evidence_bundle()
    write(QA/'build_stats.json',json.dumps(stats,ensure_ascii=False,indent=2))
    write(OUT/'_审查记录/build_stats.json',json.dumps(stats,ensure_ascii=False,indent=2))
    print('BUILD COMPLETE',flush=True)

if __name__=='__main__':main()
