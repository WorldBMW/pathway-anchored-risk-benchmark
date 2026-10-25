from csbj_build_package import *
import importlib.metadata as im

def doc(name,title,sections):
 d=setup();d.add_paragraph(title,style='Title')
 for h,body in sections:
  if h:d.add_heading(h,1)
  for p in body.split('\n\n'):d.add_paragraph(p)
 d.save(O/name);return d

def supplementary():
 d=setup();d.add_paragraph('Supplementary Materials',style='Title');d.add_paragraph(TITLE);d.add_paragraph('Mingwei Bai, Zhengmin Gu, Ye Zhang and Lang Guo')
 d.add_heading('Supplementary Methods',1)
 methods=[('S1. Units and provenance','Every primary disease statistic uses one row per sample identifier, not per spot. Patient independence is not assumed beyond available metadata. The cervical cohort contains 31 normal, one HSIL and three cancer sections, with 46,820 spots. Source and disease annotation are partly confounded. GEO metadata snapshots accompany the archive. GeoMx FINAL scores are grouped within patient and tissue type; the stale positive-score patient CSV and pre-FINAL checkpoint were excluded.'),
 ('S2. Reference training','The real-data launcher rerun_2026-09-15_regfix.sh specifies 40 epochs, no global spot cap, KEGG HPV mode and weights rec=0.2, neigh=0.3, sup=5.0, prog=1.5 and hpv=1.0. Learning rate and batch size inherit current train_st.py defaults of 0.001 and 256. Weight decay is 0.0001; gradient clipping defaults to 1.0. The per-sample batch sampler prevents cross-section neighborhood targets. Neighborhoods are batch-local, not a fixed complete-section graph. Proxy-supervised runs may stop using their diagnostic criterion; target-free runs do not use that diagnostic for stopping. The included source is a current snapshot, not a recovered training-time commit.'),
 ('S3. Synthetic data and actual training cap','Generator defaults are 1,500 spots per sample and 3,000 genes. Actual stored outputs have 30,000 pooled training spots in every simulation run because run_sim_one.sh retains the trainer global cap. Generated and fitted spot counts must not be conflated. A uses shared signal amplitude 2.5 and batch amplitude 0.3. B uses signal 0.20, batch 1.5, response range 0.15-0.95, nonresponder fraction 0.35 and program-gene presence probability 0.5. C uses fingerprint amplitude 1.2 and batch amplitude 0.5. Shared scenarios affect 60% of panel genes. Generator seed is 20261006. One generated dataset is reused across three training seeds; these are not independent simulation replications.'),
 ('S4. Simulation versus real model','Synthetic FULL uses fm=none, a CNN on placeholder images, and rec=1.0, neigh=0.3, sup=2.0, prog=1.0, hpv=0.5. All seven main variants were run; matched scenarios include only FULL and NOALL. Cervical FULL uses different weights and frozen UNI features. These experiments test audit logic, not realistic histology or clinical performance.'),
 ('S5. Exact algebraic refitting','For each held-out sample, standardize X on the remaining samples, form Z and held-out vector z, and compute training-label weights h=(ZZ^T+I)^(-1)Zz. Insert h into row i of H and set Hii=0. Predictions are Hy. The intercept sensitivity replaces h by h-mean(h)+1/(n-1). Generate 10,000 complete sample-label permutations with default_rng(20261010), calculate H y_perm and compare its tau-b with the permuted labels. This refits the probe algebraically. It does not merely permute the labels against fixed predictions. P-values include ties and use (count+1)/(B+1). Encoder/preprocessing remain fixed and label-independent, so inference is conditional and transductive in X.'),
 ('S6. Multiple testing','Table S1 provides raw p-values, BH q-values across 21 primary tests and intercept sensitivity. Table S2 reports exploratory grades using both raw p and adjusted q. Correlated seed tests do not increase biological sample size. No average p-value is used for inference. Supported means mean tau >=0.35 and at least two significant seeds; unsupported means absolute mean tau <=0.15 with none significant; otherwise suggestive. These rules are retrospective, not preregistered.'),
 ('S7. Numerical discrepancies','The historical summary reported NOALL head taus -0.076394, -0.200079 and -0.040016 (mean -0.105496). Current original NPZ scores give -0.030270, -0.201589 and -0.043690 (mean -0.091850, SD 0.095274). This revision uses the current NPZ values throughout, giving D_joint=0.551426. Historical summaries are retained only for provenance. Quarantined contaminated files, GLOBALCONFOUND_DO_NOT_USE results, partial .filepart transfers and smoke runs are excluded. Real ablation seeds are not fully paired, so there is no paired component decomposition.'),
 ('S8. Biological and external endpoints','Score-program correlations reuse model-input expression and are descriptive. NOSUP retains alignment; NOALL can reverse orientation. Neither association persistence nor removal establishes causation. GeoMx uses FINAL expression-only scores with log1p aligned raw counts and zero filling (4,788 of 4,991 genes matched). Platform normalization and missingness may contribute to score reversal. Core-level Silva tests ignore patient clustering and are not confirmatory. HNSCC organization and phenotype are separate endpoints. The TCGA 11-gene screen is not application of the frozen spatial predictor.'),
 ('S9. Reproduction','The staged archive includes pooled X/y/sample-name arrays for 21 probes, corrected outputs, raw-derived head summaries, source extracts and SHA256 checksums. Run python reproduce_probes.py --self-test, then python reproduce_probes.py --permutations 10000 --output reproduced_probe.json. This requires no GPU. Full encoder retraining requires source datasets and separately obtained model weights. Environment versions describe this revision, not an inferred historical environment. DOI assignment and public release remain pending.')]
 for h,p in methods:d.add_heading(h,2);d.add_paragraph(p)
 d.add_heading('Supplementary tables',1);rows=[]
 for g,rr in P['groups'].items():
  for r in rr:
   a=r['legacy_no_intercept'];b=r['intercept_sensitivity'];rows.append([g.replace('group_',''),r['seed'],r['n_samples'],f"{a['tau']:.6f}",f"{a['p_refit']:.6f}",f"{a['q_BH_21']:.6f}",f"{b['tau']:.6f}",f"{b['p_refit']:.6f}"])
 table(d,['Scenario','Seed','n','tau','p refit','q BH','tau + int.','p + int.'],rows,[1750,450,450,1350,1350,1350,1350,1310],'Table S1. Corrected probes; 10,000 permutations per test.')
 with (E/'Table_S1_corrected_probes.csv').open('w',newline='',encoding='utf-8') as f:w=csv.writer(f);w.writerow(['scenario','seed','n','tau','p_refit','q_BH_21','tau_intercept','p_intercept']);w.writerows(rows)
 def grade(ts,ps):
  if np.mean(ts)>=.35 and sum(x<.05 for x in ps)>=2:return 'supported'
  if abs(np.mean(ts))<=.15 and sum(x<.05 for x in ps)==0:return 'unsupported'
  return 'suggestive'
 rows=[];summ={}
 for g,rr in P['groups'].items():
  ts=[r['legacy_no_intercept']['tau'] for r in rr];ps=[r['legacy_no_intercept']['p_refit'] for r in rr];qs=[r['legacy_no_intercept']['q_BH_21'] for r in rr]
  rows.append([g,f'{np.mean(ts):.3f} +/- {np.std(ts,ddof=1):.3f}',f'{sum(p<.05 for p in ps)}/3',grade(ts,ps),grade(ts,qs)]);summ[g]={'mean':float(np.mean(ts)),'sd':float(np.std(ts,ddof=1)),'grade_p':grade(ts,ps),'grade_q':grade(ts,qs)}
 table(d,['Scenario','Mean +/- seed SD','p<0.05','Grade (p)','Grade (q)'],rows,[2300,2100,900,2030,2030],'Table S2. Exploratory grades; variation is across seeds.')
 (E/'corrected_summary.json').write_text(json.dumps(summ,indent=2),encoding='utf-8')
 rows=[]
 for v,rr in REG.items():
  for r in rr:rows.append([v,r['seed'],f"{r['tau']:.6f}",f"{r['moran']:.6f}",r['score_source']])
 table(d,['Variant','Seed','Score tau','Moran I','NPZ source'],rows,[1400,500,1200,1300,4960],'Table S3. Score audit recomputed from current NPZ files.')
 table(d,['Patient','Benign','Tumor','Difference'],[[r['patient'],f"{r['benign_mean']:.6f}",f"{r['tumor_mean']:.6f}",f"{r['difference']:.6f}"] for r in G['pairs']],[2100,2420,2420,2420],'Table S4. GeoMx patient pairs from FINAL scores.')
 rows=[]
 for a,role in [('GSE208654','Cervical lesions and HPV-positive normal'),('GSE217237','Normal ectocervix'),('GSE316098','External cervical GeoMx'),('GSE268014','External HNSCC'),('GSE281978','External HNSCC'),('GSE308792','Contextual single-cell markers')]:rows.append([a,role,'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc='+a])
 rows.append(['TCGA-CESC','Contextual 11-gene survival screen','https://portal.gdc.cancer.gov/projects/TCGA-CESC'])
 table(d,['Accession','Role','Source'],rows,[1450,3200,4710],'Table S5. Public accessions; metadata snapshots accompany the archive.')
 d.save(O/'Supplementary_Materials_CSBJ.docx')

def submission_docs():
 cover=[('', 'Dear Editors,\n\nPlease consider our Research Article, '+TITLE+', for the General section of Computational and Structural Biotechnology Journal.'),('', 'The manuscript presents a computational audit method for interpreting spatial transcriptomic representations. The central question is whether an apparently disease-related spatial score reflects imposed supervision, recoverable expression structure or sample identity. Cervical tissue is the demonstration case; the paper does not propose a cervical diagnostic system.'),('', 'MRP-ST introduces two nameable contributions. The first is a five-clause Minimum Reporting Protocol that specifies the minimal experiment set which can falsify each type of biological claim (ablation completeness, evaluation unit, label dependence, held-out representation probing, endpoint-specific external checks). The second is the Label-Dependence Index (LDI), a precision-stable statistic that standardizes a score\u2019s severity ordering against a 10,000-draw label-permutation null and decides label dependence with a 95th-percentile gate. On the cervical cohort LDI is 3.26 against a gate of 1.645. A strong-signal simulation shows that an unoriented scalar can lose disease ordering while its representation retains recoverable information; identity-confounded and scale-matched weak-signal scenarios supply complementary failure cases. The same sections separate at AUC 1.00 in-cohort but only 0.497 under leave-one-sample-out evaluation, which is the leakage the protocol is built to report.'),('', 'The contribution addresses computational biological inference from spatial gene-expression data. We separate expression-derived associations from independent biological evidence and disclose transductive encoding, acquisition confounding and limited lesion diversity. The submission offers an executable audit protocol with named, reusable outputs and demonstrated utility, rather than a new foundation model or a clinically validated biomarker.'),('', 'The package contains the manuscript, six figures, three main tables, Supplementary Materials and an executable evidence archive. OpenAI Codex assisted code generation, statistical checking, drafting, English editing and figure preparation, as disclosed in the acknowledgments. The authors retain full scientific responsibility.'),('', 'The corresponding author will confirm author approval, exclusive submission, funding and conflicts before submission. The evidence archive is staged locally; its public release identifier and Zenodo DOI will be inserted after deposition. This letter does not claim those pending actions have already occurred.'),('', 'Sincerely,\nLang Guo, on behalf of the author team\nSchool of Pharmacy, Shenyang Medical College\nShenyang 110034, China\nEmail: guolang1016@symc.edu.cn')]
 doc('Cover_Letter_CSBJ.docx','Cover letter - CSBJ',cover)
 doc('Title_Page_CSBJ.docx','Title page',[('',TITLE),('', 'Mingwei Bai (1), Zhengmin Gu (2), Ye Zhang (2), Lang Guo (3)*\n\n(1) JiMei Technology Group Co., Ltd., Shenyang 110002, China\n(2) Medical Record Management Center, The First Hospital of China Medical University, Shenyang 110002, China\n(3) School of Pharmacy, Shenyang Medical College, 146 Huanghe North Avenue, Shenyang 110034, China\n\n* Corresponding author: Lang Guo; guolang1016@symc.edu.cn; +86 13555707001'),('', 'Article type: Research Article\nProposed section: General\nDisplay items: six figures and three main tables\nSupplement: methods and five tables\nRunning title: Auditing spatial transcriptomic representations')])
 h=['MRP-ST: a five-clause audit protocol for spatial transcriptomic models.','A Label-Dependence Index scores orderings against a permutation null with a gate.','Cervical LDI 3.26 vs the 1.645 gate: label-dependent ordering, informative probes.','In-cohort AUC 1.00 falls to 0.497 under leave-one-sample-out evaluation.','Known-signal simulations calibrate the protocol and expose head-only failure.']
 doc('Highlights_CSBJ.docx','Highlights',[('', '\n\n'.join(h))]);(O/'Highlights_CSBJ.txt').write_text('\n'.join(h),encoding='utf-8')
 doc('Author_Declarations_for_Confirmation.docx','Author declarations - confirmation required',[('Authorship','The author list, affiliations and CRediT roles are carried forward from the previous project manuscript. All authors must confirm accuracy, accountability and approval. No signature or approval is generated on their behalf.'),('Funding and interests','The previous record states no specific grant and no known competing interests. The commercial affiliation of Mingwei Bai is disclosed. Confirm whether employment, ownership, intellectual property or other support needs further disclosure.'),('Ethics','Only public datasets are reanalyzed without new recruitment or intervention. Source-study conditions apply. Confirm any institutional requirement for a secondary-analysis determination; no approval or exemption number has been invented.'),('Submission status','Confirm that the paper is not under review elsewhere, all authors approve submission and relevant related manuscripts/preprints have been disclosed. An earlier rejection does not establish current exclusive-submission status.'),('Archive and licensing','Review the staged release, select a code/data license and confirm redistribution conditions for derived sample representations. Publish the release and Zenodo record, then insert the issued identifiers. Raw images, raw count matrices and foundation-model weights are not bundled.'),('AI assistance','The manuscript and letter disclose Codex assistance. Authors must review and approve the final results, reference list and wording and accept responsibility for the submitted version.')])

def archive():
 A=O/'archive_staging';(A/'evidence').mkdir(parents=True,exist_ok=True);(A/'reference_source/scripts').mkdir(parents=True,exist_ok=True)
 for f in E.iterdir():
  if f.is_file():shutil.copy2(f,A/'evidence'/f.name)
 for name in ['paper_v10_numbers.json','sim_audit_summary.json','sim_lodo_summary.json','sim_lodo_summary_small.json','threshold_robustness.json','threshold_robustness_small.json','decircularization_biology.json','external_corrected_numbers.json','external_gse316098_validation_FINAL.json','gse316098_corrected_silva_labels.csv','hnscc_discriminative_eval.json','infer_XCOHORT_HNSCC_FINAL_summary.json','infer_XCOHORT_HNSCC_GSE281978_FINAL_summary.json','tcga_deg_cox.json','csbj_ldi_validated.json','baseline_hpv_auc.json','baseline_BASELINE_LOSO35_RIDGE.json','baseline_hpv_gene_mean_vs_model.json']:
  if (R/'results'/name).exists():shutil.copy2(R/'results'/name,A/'evidence'/name)
 for name in ['train_st.py','simulate_st_positive_control.py','run_sim_one.sh','run_sim_small.sh','rerun_2026-09-15_regfix.sh','rerun_2026-09-23_nosup.sh','rerun_2026-09-24_noall.sh','probe_lodo.py','csbj_corrected_audit.py','csbj_recompute_heads.py','downstream_spot_analysis.py','decircularization_biology.py']:
  shutil.copy2(R/'scripts'/name,A/'reference_source/scripts'/name)
 for f in (R/'src').glob('*.py'):
  (A/'reference_source/src').mkdir(exist_ok=True);shutil.copy2(f,A/'reference_source/src'/f.name)
 if (O/'reproduce_probes.py').exists():shutil.copy2(O/'reproduce_probes.py',A/'reproduce_probes.py')
 v={'python':sys.version,'platform':platform.platform(),'packages':{p:im.version(p) for p in ['numpy','scipy','matplotlib','python-docx','pandas','pillow']},'note':'Revision environment, not a recovered historical training environment.'}
 (A/'environment_versions.json').write_text(json.dumps(v,indent=2),encoding='utf-8');(A/'requirements.txt').write_text('numpy=='+im.version('numpy')+'\nscipy=='+im.version('scipy')+'\n',encoding='utf-8')
 readme='''# MRP-ST audit evidence - CSBJ revision 2026-10-10

Status: locally staged, not a public release; no Zenodo DOI has been issued.

## Reproduce
Install requirements.txt in a Python environment, then run:
    python reproduce_probes.py --self-test
    python reproduce_probes.py --permutations 10000 --output reproduced_probe.json

The portable script uses evidence/pooled_*.npz and refits the sample-level probe under every label permutation. It does not retrain the encoder. Encoding is transductive in covariates. The reference_source snapshot requires the original project and data layout for training and is not a recovered training-time commit.

## Authoritative revision results
corrected_probe.json contains 21 corrected probe tests and intercept sensitivities. real_run_registry.json contains current NPZ-derived head values (float64) and source checksums. csbj_ldi_validated.json contains the Label-Dependence Index calibration: LDI = (tau_FULL - tau_perp) / sigma_null = 3.258 against theta = Phi^-1(0.95) = 1.6449, with tau_FULL = 0.4596 (sd 0.0042), tau_perp = 0.0007 and sigma_null = 0.1408. The NOALL head collapses to a near-constant per-sample offset, so its tau is numerically indeterminate: float64 gives -0.1055 (sd 0.0839) and float32 gives -0.0919 from the same npz file. The raw tau_FULL - tau_NOALL contrast is therefore NOT the index and is retained only for transparency. Historical paper_v10_numbers.json is provenance only and must not be reused.

## Data and limits
No raw images, raw count matrices, foundation weights or credentials are included. Pooled derived representations are supplied for review/reproduction; source-data redistribution conditions require author confirmation before public deposition. This is not a clinical prediction product.

## Publish
1. Confirm author declarations, release contents and code/data license.
2. Publish a versioned release in the existing repository.
3. Create a Zenodo draft, upload this archive, reserve a DOI and cross-link identifiers.
4. Review metadata/license, publish, and verify access and checksums.
5. Insert the real version DOI into manuscript and cover letter.

Project: https://github.com/WorldBMW/pathway-anchored-risk-benchmark
Zenodo DOI help: https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/
'''
 (A/'README.md').write_text(readme,encoding='utf-8')
 m={'title':TITLE+' - computational audit evidence','version':'csbj-audit-2026.10.10','upload_type':'software','description':'Reproducible conditional probe audits, score summaries and provenance for MRP-ST. Cervical tissue is a demonstration; no clinical validity is claimed. LOCAL DRAFT: complete license and release metadata before upload.','creators':[{'name':'Bai, Mingwei','affiliation':'JiMei Technology Group Co., Ltd.'},{'name':'Gu, Zhengmin','affiliation':'The First Hospital of China Medical University'},{'name':'Zhang, Ye','affiliation':'The First Hospital of China Medical University'},{'name':'Guo, Lang','affiliation':'Shenyang Medical College'}],'keywords':['spatial transcriptomics','model audit','permutation testing','reproducibility'],'notes':'No DOI assigned; license requires confirmation.'}
 (A/'zenodo_metadata_DRAFT.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
 (A/'LICENSE_STATUS.txt').write_text('No license is asserted. The existing repository API reported no license. Authors must select a code license and verify source-data terms before publication. Third-party weights are excluded.\n',encoding='utf-8')
 files=[f for f in sorted(A.rglob('*')) if f.is_file() and f.name!='SHA256SUMS.txt'];(A/'SHA256SUMS.txt').write_text('\n'.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.relative_to(A).as_posix() for f in files)+'\n',encoding='utf-8')
 with zipfile.ZipFile(O/'MRPST_Zenodo_Archive_DRAFT.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
  for f in A.rglob('*'):
   if f.is_file():z.write(f,f.relative_to(A))

if __name__=='__main__':supplementary();submission_docs();archive();print('Supplement, submission documents and staged archive built.')
