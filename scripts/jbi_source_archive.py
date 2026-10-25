"""Auditable numerical supplement, preserving raw result files."""
from pathlib import Path
import json,hashlib,shutil,zipfile
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results';P=ROOT/'papers/08_JBI';O=P/'_qa_20260924/source_data';O.mkdir(exist_ok=True)
D=json.loads((R/'jbi_submission_audit/rank_perm_recomputed.json').read_text());rows=[];manifest=[]
def cp(f,rel=None):
 dst=O/(rel or f.relative_to(ROOT));dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst);manifest.append({'path':str(dst.relative_to(O)).replace('\\','/'),'original':str(f.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
for v,rr in D['variants'].items():
 for r in rr:
  fp=ROOT/r['source'];z=np.load(fp,allow_pickle=True);ids=z['sample_ids'].astype(str);scores=z['scores'].astype(float)
  dest=O/'score_arrays'/fp.name;dest.parent.mkdir(exist_ok=True);np.savez_compressed(dest,scores=scores,sample_ids=ids,coords=z['coords'])
  manifest.append({'path':str(dest.relative_to(O)).replace('\\','/'),'original':r['source'],'derived':'Only scores, sample_ids, coords; no embeddings','source_sha256':hashlib.sha256(fp.read_bytes()).hexdigest(),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
  for sid in sorted(set(ids)):
   y=2 if any(k in sid.lower() for k in ['ca_hpv','cancer','carcinoma']) else 1 if any(k in sid.lower() for k in ['hsil','cin']) else 0
   rows.append({'variant':v,'seed':r['seed'],'section':sid,'severity':y,'spots':int(sum(ids==sid)),'mean_score':float(scores[ids==sid].mean()),'within_section_moran':r['per_sample_moran'][sid]})
  cp(R/f'results_{v}_seed{r["seed"]}.json')
pd.DataFrame(rows).to_csv(O/'section_scores_and_moran.csv',index=False)
for f in (R/'jbi_submission_audit').glob('*.json'):cp(f)
names=['paper_v10_numbers.json','rank_perm_B10000.json','external_corrected_numbers.json','external_gse316098_validation_FINAL.json','gse316098_core_level.csv','gse316098_corrected_silva_labels.csv','gse316098_patient_level.csv','infer_XCOHORT_HNSCC_FINAL_summary.json','infer_XCOHORT_HNSCC_GSE281978_FINAL_summary.json','hnscc_moran_permutation_control_FINAL.json','hnscc_random_gene_moran.json','hnscc_discriminative_eval.json','downstream_spot_analysis.json','scrna_marker_validation.json','tcga_deg_cox.json','uni_embed_moran_s1.json','baseline_BASELINE_LOSO35_RIDGE.json','baseline_BASELINE_HE2ST.json','baseline_hpv_auc.json','baseline_hpv_gene_mean_vs_model.json','random_control_summary.json','results_MAIN_KEGG.json']
for n in names:cp(R/n)
for pat in ['results_RANDOM108_S*.json','results_LODOv2_*.json','results_UNSUP_LODOv2_*.json']:
 for f in R.glob(pat):cp(f)
for n in ['jbi_reaudit.py','jbi_submission_build.py','jbi_final_figures.py','gen_figures_v10.py','gen_jbi.py','gen_fig1_framework.py','gen_fig1_histology_v10.py']:cp(ROOT/'scripts'/n)
(O/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(O/'README.txt').write_text('''Numerical source data for the JBI submission, revised 25 September 2026.

Primary table: section_scores_and_moran.csv (35 sections x 22 saved runs).
score_arrays/ contains scores, section identifiers and coordinates extracted from the saved NPZ files; embeddings are omitted. No primary outputs were altered.
results/jbi_submission_audit/ contains corrected summaries, fixed-score Monte Carlo and exhaustive permutation checks. FULL seeds: 0,3,4; NO-PROG: 0,1,2,3; other arms: 0,1,2.

Moran definition: for each section, center its scores and use directed, row-standardized six-nearest-neighbor weights. Average the 35 section statistics equally. Old globally centered outputs remain in original run JSONs and are sensitivity results, not the primary estimand.
Permutation: section means, one-sided positive Kendall tau-b, scores fixed; B=10000, seed=20260924; Monte Carlo (b+1)/(B+1). All 209440 arrangements provide an exact sensitivity calculation. This does not test a label-refitted learning algorithm.

External source precedence is deliberate: external_corrected_numbers.json agrees with the current LODO fold files. external_gse316098_validation_FINAL.json agrees with corrected ROI labels and deployed scores. paper_v10_numbers.json and rank_perm_B10000.json are LEGACY inputs used only to diagnose discrepancies and reproduce the reaudit script; use jbi_submission_audit/numbers.json and rank_perm_recomputed.json for the revised manuscript. An older conflicting external_corrected_numbers_FINAL.json is not used. A FINAL filename alone does not establish provenance.

Random-panel retraining: 30 size-matched panels and a separate trained KEGG reference, not expression-matched raw-panel scores. Head-and-neck external random panels are untrained and expression matched.
LOSO morphology-only AUC concerns a within-section expression proxy, not held-out disease classification. GeoMx cores and ROIs share patients; the patient-paired analysis is primary.

Reproduction: scripts are provided with project-relative paths. The main repository supplies training code, raw-data acquisition and configuration. Raw histology, transcriptomic matrices and third-party model weights are not duplicated here. Place these files under the corresponding repository paths; score_arrays files may be placed in results/ for numerical reanalysis. Figure generation also requires public histology sources documented in the manuscript.

SHA256 provenance is in source_manifest.json. External clinical labels are public-study annotations; no new participant information is introduced.
''',encoding='utf-8')
with zipfile.ZipFile(P/'Supplementary_Source_Data_JBI.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in sorted(O.rglob('*')):
  if f.is_file():z.write(f,f.relative_to(O))
print('Source archive:',(P/'Supplementary_Source_Data_JBI.zip').stat().st_size,'bytes; section rows:',len(rows),'source entries:',len(manifest))
