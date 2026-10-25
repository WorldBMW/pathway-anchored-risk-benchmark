from pathlib import Path
import sys,shutil,json,hashlib,zipfile,ast,importlib.metadata as im
R=Path('G:/project4_cervix_multimodal');O=R/'papers/12_CSBJ_audit_20261010'
old='MRP-ST: Separating supervision-dependent scores from transferable representations in spatial transcriptomics';new='MRP-ST: Auditing supervision dependence and representation information in spatial transcriptomics'
for p in [O/'Manuscript_CSBJ.md',R/'scripts/csbj_build_package.py']:
 s=p.read_text(encoding='utf-8-sig').replace(old,new);p.write_text(s,encoding='utf-8')
sys.path.insert(0,str(R/'scripts'))
from csbj_build_package import build_main
from csbj_submission_extras import supplementary,submission_docs,archive
print('FINAL manuscript',build_main());supplementary();submission_docs();archive();A=O/'archive_staging'
for name in ['verify_evidence.py','reproduce_figures.py']:shutil.copy2(O/name,A/name)
for g in ['group_A','group_B','group_C','group_A_small','group_B_small','group_C_small']:
 for seed in range(3):
  name=f'results_SIM_{g}_FULL_seed{seed}.json';shutil.copy2(R/'results'/name,A/'evidence'/name)
for name in ['csbj_build_package.py','csbj_submission_extras.py','csbj_verify_package.py','csbj_ldi_recompute.py','csbj_recompute_heads.py']:shutil.copy2(R/'scripts'/name,A/'reference_source/scripts'/name)
r=(A/'README.md').read_text(encoding='utf-8');r+='\n## Additional reproduction\nRun python verify_evidence.py to check sample-head and GeoMx statistics. Run python reproduce_figures.py to regenerate figures and the graphical abstract from the packaged evidence (PDF/SVG/600-dpi raster outputs).\n';(A/'README.md').write_text(r,encoding='utf-8')
(A/'requirements.txt').write_text('\n'.join(p+'=='+im.version(p) for p in ['numpy','scipy','matplotlib','pillow'])+'\n',encoding='utf-8')
shutil.copy2(O/'qa/verification_report.json',A/'verification_report.json')
files=[f for f in sorted(A.rglob('*')) if f.is_file() and f.name!='SHA256SUMS.txt'];(A/'SHA256SUMS.txt').write_text('\n'.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.relative_to(A).as_posix() for f in files)+'\n',encoding='utf-8')
with zipfile.ZipFile(O/'MRPST_Zenodo_Archive_DRAFT.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
 for f in A.rglob('*'):
  if f.is_file():z.write(f,f.relative_to(A))
print('Archive',len(files)+1,'files')
