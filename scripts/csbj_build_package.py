"""Build the CSBJ revision from verified local evidence; no external publication."""
from pathlib import Path
import json,re,csv,shutil,hashlib,zipfile,sys,platform
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image,ImageOps,ImageDraw
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT

R=Path(__file__).resolve().parents[1];O=R/'papers/12_CSBJ_audit_20261010';E=O/'evidence';F=O/'figures';F.mkdir(exist_ok=True)
LDI_FIG=O/'figures'/'Fig_LDI_validation.png'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
P=read(E/'corrected_probe.json');REG=read(E/'real_run_registry.json');N=read(R/'results/paper_v10_numbers.json');BIO=read(R/'results/decircularization_biology.json')['variants'];G=read(E/'geomx_patient_final.json');REF=read(E/'references_verified.json')
COL=['#167D9A','#E0A038','#B74F59'];plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
def savefig(fig,name):
 fig.savefig(F/(name+'.pdf'),bbox_inches='tight');fig.savefig(F/(name+'.svg'),bbox_inches='tight');fig.savefig(F/(name+'.png'),dpi=600,bbox_inches='tight',facecolor='white')
 with Image.open(F/(name+'.png')) as im:im.save(F/(name+'.tif'),compression='tiff_lzw',dpi=(600,600))
 plt.close(fig)

def figures():
 fig,ax=plt.subplots(figsize=(9,5));ax.set(xlim=(0,10),ylim=(0,6));ax.axis('off')
 boxes=[(.2,4.45,2.7,1.1,'INPUT & PROVENANCE','Expression + morphology\nCoordinates and sample groups\nTarget sources and provenance'),(3.65,4.45,2.7,1.1,'SCORE DEPENDENCE','Seven explicit ablation variants\nDescriptive contrasts; all seeds'),(7.1,4.45,2.7,1.1,'REPRESENTATION','NOALL frozen embeddings\nSample-pooled features'),(7.1,2.35,2.7,1.25,'HELD-OUT PROBE','Train-only scaling and ridge\nRefit for each label permutation'),(3.65,2.35,2.7,1.25,'EXTERNAL PROFILE','Tissue separation; score direction\nSpatial organization; phenotype'),(.2,2.35,2.7,1.25,'EVIDENCE REPORT','Effect sizes and seed variation\nSource files and checksums')]
 for x,y,w,h,title,body in boxes:
  ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.06',facecolor='#EEF5F7',edgecolor='#167D9A'))
  ax.text(x+w/2,y+h-.22,title,ha='center',va='center',weight='bold',fontsize=9)
  ax.text(x+w/2,y+.37,body,ha='center',va='center',fontsize=8.2,linespacing=1.5)
 for a,b in [((2.95,5),(3.55,5)),((6.4,5),(7,5)),((8.45,4.35),(8.45,3.7)),((7,2.95),(6.4,2.95)),((3.55,2.95),(2.95,2.95))]:ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',lw=1.6,color='#38566A'))
 ax.text(5,1.4,'SIMULATIONS: shared strong signal | weak heterogeneous signal | sample identity',ha='center',weight='bold',fontsize=9)
 ax.text(5,.8,'INFERENCE BOUNDARY: transductive in covariates; samples, not spots, are evaluation units',ha='center',fontsize=8.5)
 ax.text(5,.3,'Cervical tissue is the demonstration case. Clinical prediction is not the output.',ha='center',fontsize=8.5,color='#555555')
 savefig(fig,'Fig1_Audit_workflow')
 fig,axs=plt.subplots(1,2,figsize=(8.8,3.9),sharey=True)
 for ax,suf,title in zip(axs,['','_small'],['A  90 samples (50 normal / 40 diseased)','B  35 samples (31 normal / 4 diseased)']):
  for j,g in enumerate(['group_A','group_B','group_C']):
   rows=P['groups'][g+suf];ts=[r['legacy_no_intercept']['tau'] for r in rows];full=[read(R/f'results/results_SIM_{g+suf}_FULL_seed{k}.json')['progression_monotonicity']['kendall_tau'] for k in range(3)]
   ax.scatter(np.array([j-.07,j,j+.07]),ts,color=COL[j],s=42,zorder=4);ax.errorbar(j,np.mean(ts),yerr=np.std(ts,ddof=1),color=COL[j],capsize=5,fmt='_',ms=22,lw=1.5)
   ax.scatter(j+.24,np.mean(full),marker='D',s=33,facecolor='none',edgecolor='#555555')
  ax.axhline(0,color='#888888',lw=.8);ax.set_xticks(range(3),['Strong\nshared','Weak\nshared','Identity\nconfounded']);ax.set_title(title,loc='left',fontsize=10);ax.set_ylim(-.4,.9)
 axs[0].set_ylabel('Kendall tau-b');fig.text(.5,.015,'Colored dots: NOALL held-out probes (three seeds). Open diamonds: FULL in-sample score means.',ha='center',fontsize=8);fig.tight_layout(rect=(0,.05,1,1));savefig(fig,'Fig2_Simulation_probes')
 fig,axs=plt.subplots(1,2,figsize=(9,4),gridspec_kw={'width_ratios':[1.35,1]})
 for j,(v,rows) in enumerate(REG.items()):
  t=[r['tau'] for r in rows];axs[0].scatter(t,np.full(len(t),j)+np.linspace(-.1,.1,len(t)),s=24,color='#167D9A');axs[0].errorbar(np.mean(t),j,xerr=np.std(t,ddof=1),fmt='|',color='#263D4A',capsize=3)
 axs[0].set_yticks(range(7),list(REG));axs[0].invert_yaxis();axs[0].axvline(0,color='#888888',lw=.8);axs[0].set(xlabel='In-sample score–severity tau-b',title='A  Explicit ablation contrasts')
 for j,r in enumerate(P['groups']['cervical']):
  v=r['legacy_no_intercept'];axs[1].scatter(j,v['tau'],s=65,color='#167D9A');axs[1].text(j,v['tau']+.04,f"p = {v['p_refit']:.4f}",ha='center',fontsize=8)
 axs[1].axhline(0,color='#888888',lw=.8);axs[1].set(xticks=[0,1,2],xticklabels=['Seed 0','Seed 1','Seed 2'],ylim=(-.12,.57),xlim=(-.55,2.55),ylabel='Held-out probe tau-b',title='B  NOALL representation');fig.tight_layout();savefig(fig,'Fig3_Cervical_audit')
 keys=['CELL_tumor_epithelial','HPV_INTEGRATION_CANDIDATE','ANTIGEN_PRESENTATION','INTERFERON_ANTIVIRAL','PROLIFERATION'];labels=['Epithelial','HPV-related','Antigen presentation','Interferon / antiviral','Proliferation']
 mat=np.array([[BIO[v][k]['rho_mean'] for v in ['FULL','NOPROG','NOSUP']]+BIO['NOALL'][k]['rhos'] for k in keys])
 fig,ax=plt.subplots(figsize=(8.3,3.8));im=ax.imshow(mat,vmin=-.8,vmax=.8,cmap='RdBu_r',aspect='auto')
 ax.set_yticks(range(5),labels);ax.set_xticks(range(6),['FULL\nmean','NOPROG\nmean','NOSUP\nmean','NOALL\nseed 0','NOALL\nseed 1','NOALL\nseed 2']);ax.set_title('Orientation must be inspected before averaging biological associations',loc='left',fontsize=10)
 for i in range(5):
  for j in range(6):ax.text(j,i,f'{mat[i,j]:+.2f}',ha='center',va='center',color='white' if abs(mat[i,j])>.5 else '#222222')
 ax.axvline(2.5,color='white',lw=3);fig.colorbar(im,ax=ax,label='Spearman correlation',fraction=.035,pad=.03);fig.tight_layout();savefig(fig,'Fig4_Biological_orientation')
 fig,axs=plt.subplots(1,2,figsize=(8.7,4))
 for i,r in enumerate(G['pairs']):axs[0].plot([0,1],[r['benign_mean'],r['tumor_mean']],'-o',color=plt.cm.viridis(i/6),lw=1.3,ms=4,label=r['patient'])
 axs[0].set(xticks=[0,1],xticklabels=['Benign','Tumor'],ylabel='Unbounded score',title='A  GeoMx: paired patient means');axs[0].text(.03,.07,'6 / 6 negative differences\nExact two-sided p = 0.03125',transform=axs[0].transAxes,fontsize=8);axs[0].legend(fontsize=6.5,loc='upper right',ncol=2)
 means=[N['external']['hnscc_moran_mean'],N['external']['hnscc_gse281978_moran_mean']];axs[1].bar([0,1],means,color=['#167D9A','#70AFB6'],width=.55)
 axs[1].set(xticks=[0,1],xticklabels=['GSE268014\n8 sections','GSE281978\n6 sections'],ylim=(0,1),ylabel="Mean Moran's I",title='B  Spatial organization persists')
 for j,m in enumerate(means):axs[1].text(j,m+.035,f'{m:.3f}',ha='center')
 axs[1].text(.5,.09,'HPV-status p = 0.200 / 0.133\nOrganization does not establish discrimination',transform=axs[1].transAxes,ha='center',fontsize=8)
 fig.tight_layout();savefig(fig,'Fig5_External_evidence')
 # A vector graphical abstract is optional, not counted as a main figure.
 fig,ax=plt.subplots(figsize=(9,3));ax.axis('off');ax.text(.02,.88,'MRP-ST | Audit the claim before interpreting the map',fontsize=16,weight='bold',transform=ax.transAxes)
 for j,(title,body) in enumerate([('REMOVE TARGETS','Which objectives orient\nthe scalar score?'),('PROBE REPRESENTATIONS','Does held-out information\nsurvive in the embedding?'),('SEPARATE ENDPOINTS','Do direction, organization\nand phenotype transfer?')]):
  x=.02+j*.335;ax.add_patch(FancyBboxPatch((x,.27),.29,.43,transform=ax.transAxes,boxstyle='round,pad=.02',fc='#EEF5F7',ec='#167D9A'));ax.text(x+.145,.59,title,ha='center',fontsize=10,weight='bold',transform=ax.transAxes);ax.text(x+.145,.41,body,ha='center',fontsize=10,transform=ax.transAxes)
 ax.text(.5,.1,'Known-signal simulations → cervical demonstration → traceable evidence package',ha='center',fontsize=11,transform=ax.transAxes);savefig(fig,'Graphical_Abstract')
 src=LDI_FIG
 if src.exists():
  shutil.copy(src,F/'Fig6_LDI_calibration.png')
  with Image.open(src) as im:
   im.convert('RGB').save(F/'Fig6_LDI_calibration.tif',compression='tiff_lzw',dpi=(300,300))
   im.convert('RGB').save(F/'Fig6_LDI_calibration.pdf')

TITLE='MRP-ST: Auditing supervision dependence and representation information in spatial transcriptomics'
CAPTIONS=[
('Fig1_Audit_workflow','Figure 1. MRP-ST workflow. Separate ablation contrasts quantify scalar-score dependence; a held-out probe assesses information in frozen NOALL embeddings. Sample-label permutations refit the complete probe. External endpoints are evaluated separately. Encoding remains transductive in covariates; cervical disease provides a demonstration, not clinical validation.'),
('Fig2_Simulation_probes','Figure 2. Synthetic expression programs and identity confounding. A: 90-sample scenarios. B: matched 35-sample scenarios. Dots are NOALL probe tau-b for individual training seeds; bars indicate mean ± sample SD. Open diamonds show mean FULL in-sample head correlation. Training seeds reuse one generated cohort per scenario; bars are not biological confidence intervals. All refitted permutation results appear in Table S1.'),
('Fig3_Cervical_audit','Figure 3. Cervical score dependence and representation information. A: original NPZ scores pooled by sample and compared with severity; points show training seeds and bars mean ± sample SD. NOPROG has four seeds, other variants three. Seed sets are not fully paired. B: NOALL held-out probe correlations with one-sided p-values from 10,000 refitted label permutations. One of three seeds is significant, including after BH adjustment across 21 tests.'),
('Fig4_Biological_orientation','Figure 4. Descriptive biological associations across information removal. FULL, NOPROG and NOSUP columns show mean correlations; NOALL columns display individual seeds to expose sign instability. Colors represent stored score–program Spearman correlations. These are expression-derived associations, not independent mechanistic validation; no post hoc sign correction is applied.'),
('Fig5_External_evidence','Figure 5. External properties are not interchangeable. A: FINAL-checkpoint GeoMx scores, aggregated within each of six paired patients and tissue types. All tumor-minus-benign differences are negative; exact signed-rank p=0.03125. B: stored mean Moran’s I in two head-and-neck cohorts, accompanied by separate sample-level HPV-status tests. The axes measure different endpoints and are not combined into a validation score.'),
('Fig6_LDI_calibration','Figure 6. Label-Dependence Index calibration and gate behaviour (clause C3). A: severity-ordering distribution of the supervised score under 10,000 complete sample-label permutations, with the observed tau and the 95th-percentile gate theta marked; the observed value lies far in the upper tail. B: recovery of injected label dependence as a function of the injected fraction alpha, showing monotone calibration and the alpha at which simulated dependence matches the observed ordering. C: per-variant mean tau with seed SD across the seven supervision-removal variants on the tau scale, with the same theta line. The LDI reported in the text is this excess standardized by the null SD (LDI=3.26 against theta=1.645); the raw tau_FULL − tau_NOALL contrast is not used because the NOALL head collapses to a numerically indeterminate offset.'),
('Fig7_Local_controls','Figure 7. Local controls for label dependence, leakage and threshold choice. A: gate threshold theta as a function of alpha with the permutation-seed range shown, against the observed tau_FULL; the label-dependent verdict is stable across alpha in {0.01, 0.05, 0.10, 0.20} and five permutation seeds. B: per-variant mean score–severity tau with seed SD for the seven supervision-removal variants (label-free variant in red). C: leave-one-donor-out probe correlations by variant; encoders trained with donor labels return 0.42–0.46 with all seeds significant, whereas the label-free encoders return 0.270 with one of three seeds significant. Panels B and C separate the memorisation gap from the transferable signal.')]

def element(tag,**attrs):
 x=OxmlElement(tag)
 for k,v in attrs.items():x.set(qn(k),str(v))
 return x
def mr(t):x=element('m:r');y=element('m:t');y.text=t;x.append(y);return x
def sub(a,b):
 x=element('m:sSub');e=element('m:e');e.append(mr(a));s=element('m:sub');s.append(mr(b));x.extend([e,s]);return x
def frac(a,b):
 x=element('m:f');n=element('m:num');n.append(mr(a));d=element('m:den');d.append(mr(b));x.extend([n,d]);return x
def sup(a,b):
 x=element('m:sSup');e=element('m:e');e.append(mr(a));v=element('m:sup');v.append(mr(b));x.extend([e,v]);return x

def summ(lo,hi,body):
 x=element('m:nary');pr=element('m:naryPr');pr.append(element('m:chr',**{'m:val':'∑'}));pr.append(element('m:limLoc',**{'m:val':'undOvr'}));x.append(pr)
 for tag,txt in [('m:sub',lo),('m:sup',hi),('m:e',body)]:
  a=element(tag);a.append(mr(txt));x.append(a)
 return x

def fraction(nodes,den):
 x=element('m:f');n=element('m:num');d=element('m:den')
 for a in nodes:n.append(a)
 d.append(mr(den));x.extend([n,d]);return x

EQS=[
 [[sub('s̄','i'),mr(' = '),fraction([summ('j=1','nᵢ','sᵢⱼ')],'nᵢ'),mr(' ,     '),sub('z̄','i'),mr(' = '),fraction([summ('j=1','nᵢ','zᵢⱼ')],'nᵢ')]],
 [[mr('ℒ = '),sub('λ','rec'),sub('ℒ','rec'),mr(' + '),sub('λ','neigh'),sub('ℒ','neigh'),mr(' + '),sub('λ','sup'),mr('('),sub('ℒ','proxy,s'),mr(' + '),sub('ℒ','proxy,z'),mr(')')],[mr('      + '),sub('λ','prog'),sub('ℒ','ordinal'),mr(' + '),sub('λ','hpv'),sub('ℒ','align'),mr(' + 0.1 '),sub('ℒ','var')]],
 [[sub('τ','b'),mr(' = '),frac('C − D','√[(C + D + Tₛ)(C + D + Tᵧ)]')]],
 [[sub('D','ordinal'),mr(' = '),sub('τ̄','FULL'),mr(' − '),sub('τ̄','NOPROG')]],
 [[mr('LDI = '),fraction([sub('τ̄','FULL'),mr(' − '),sub('τ','⊥')],'σ_null'),mr(' ,     θ = '),sup('Φ','−1'),mr('(1 − α)')]],
 [[sub('β̂','−i'),mr(' = arg minᵦ { '),summ('ℓ≠i','','(yℓ − z̃ℓ,−ᵢᵀβ)²'),mr(' + ‖β‖₂² }')],[sub('ŷ','i'),mr(' = '),sub('z̃','i,−i'),mr('ᵀ '),sub('β̂','−i')]],
 [[sub('p','refit'),mr(' = '),fraction([mr('1 + '),summ('b=1','B','1{ τ(ŷ[πᵦ], y[πᵦ]) ≥ τ(ŷ, y) }')],'B + 1')]]]

def setup():
 d=Document();s=d.sections[0];s.page_width=Inches(8.5);s.page_height=Inches(11);s.top_margin=s.bottom_margin=s.left_margin=s.right_margin=Inches(1);s.header_distance=s.footer_distance=Inches(.492)
 # narrative_proposal preset with a named journal-manuscript override:
 # Times New Roman, black hierarchy, left aligned, 1.25 line spacing.
 for name,size,bef,aft in [('Normal',11,0,6),('Title',17,0,12),('Heading 1',14,16,8),('Heading 2',12,12,6),('Heading 3',11,8,4),('Caption',9,4,6)]:
  st=d.styles[name];st.font.name='Times New Roman';st.font.size=Pt(size);st.font.color.rgb=RGBColor(0,0,0);st.font.bold=name.startswith('Heading') or name=='Title';st.paragraph_format.space_before=Pt(bef);st.paragraph_format.space_after=Pt(aft);st.paragraph_format.line_spacing=1.25 if name=='Normal' else 1.0
  st.paragraph_format.widow_control=True
  if name.startswith('Heading'):st.paragraph_format.keep_with_next=True
 footer=s.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
 footer.add_run('MRP-ST  |  ');fld=element('w:fldSimple',**{'w:instr':'PAGE'});footer._p.append(fld)
 return d

def table(d,headers,rows,widths,title):
 d.add_paragraph(title,style='Caption').paragraph_format.keep_with_next=True
 t=d.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.LEFT;t.autofit=False
 pr=t._tbl.tblPr;w=pr.find(qn('w:tblW'));w.set(qn('w:w'),'9360');w.set(qn('w:type'),'dxa');pr.append(element('w:tblInd',**{'w:w':'120','w:type':'dxa'}));pr.append(element('w:tblLayout',**{'w:type':'fixed'}))
 borders=element('w:tblBorders')
 for side in ['top','bottom','insideH']:borders.append(element('w:'+side,**{'w:val':'single','w:sz':'4','w:color':'AAAAAA'}))
 for side in ['left','right','insideV']:borders.append(element('w:'+side,**{'w:val':'nil'}))
 pr.append(borders);grid=t._tbl.tblGrid
 for c in list(grid):grid.remove(c)
 for w in widths:grid.append(element('w:gridCol',**{'w:w':w}))
 for ri,vals in enumerate([headers]+rows):
  row=t.rows[0] if ri==0 else t.add_row();trpr=row._tr.get_or_add_trPr();trpr.append(element('w:cantSplit'))
  if ri==0:trpr.append(element('w:tblHeader'))
  for i,(c,v) in enumerate(zip(row.cells,vals)):
   c.width=Inches(widths[i]/1440);tc=c._tc.get_or_add_tcPr();tw=tc.find(qn('w:tcW'));tw.set(qn('w:w'),str(widths[i]));tw.set(qn('w:type'),'dxa');mar=element('w:tcMar')
   for side,value in [('top',80),('bottom',80),('start',120),('end',120)]:mar.append(element('w:'+side,**{'w:w':value,'w:type':'dxa'}))
   tc.append(mar);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER;p=c.paragraphs[0];p.paragraph_format.space_after=Pt(3);p.paragraph_format.line_spacing=1
   r=p.add_run(str(v));r.font.size=Pt(9);r.bold=ri==0
   if ri==0:tc.append(element('w:shd',**{'w:fill':'F4F6F9'}))
 return t

T1H=['Variant','Change from FULL','Retained information'];T1R=[['FULL','No removal','Ordinal + proxy + alignment; image; neighborhood'],['NOIMAGE','Zero image representation','All losses retained'],['NOHPV','lambda_hpv = 0','Ordinal and proxy targets retained'],['NONEIGH','lambda_neigh = 0','Other losses and image retained'],['NOPROG','lambda_prog = 0','Proxy and alignment retained'],['NOSUP','lambda_prog = lambda_sup = 0','Alignment retained; no explicit targets'],['NOALL','lambda_prog = lambda_sup = lambda_hpv = 0','Reconstruction, image, neighborhood, variance floor']]
T2H=['External analysis','Observed evidence','Claim boundary'];T2R=[['GeoMx, 6 paired patients','Tumor − benign mean −2.218; exact p=0.03125','Paired separation; reversed source-score direction'],['GeoMx, Silva patterns','Nonmonotone core means; 7 patients','No validated ordinal grading or calibration'],['HNSCC, 8 / 6 sections','Mean Moran’s I 0.757 / 0.667','Spatial organization; not disease discrimination'],['HNSCC, HPV status','Sample p=0.200 / 0.133','No convincing status separation in these cohorts'],['TCGA-CESC, 302 patients','11-gene screen; none significant','Gene screen only; not model-level prognosis']]
T3H=['Grade','Criterion (clause C4: mean LODO probe tau-b over seeds)','Interpretation'];T3R=[['Supported','mean τ ≥ 0.35 and ≥ 2/3 seeds p < 0.05','Replicable information in the label-free representation'],['Suggestive','neither supported nor unsupported','Weak or seed-unstable information; continuous estimates govern'],['Unsupported','|mean τ| ≤ 0.15 and 0/3 seeds p < 0.05','Insufficient evidence at this sample size, not absence of biology']]

def reftext(k):
 r=REF[k];a='; '.join(r['authors']);return f"{a}. {r['title']}. {r.get('journal','')}. {r.get('year','')};{r.get('volume','')}:{r.get('page','')}. {r['url']}"

def build_main():
 text=(O/'Manuscript_CSBJ.md').read_text(encoding='utf-8-sig');order=[]
 def cite(m):
  ks=[k.strip().lstrip('@') for k in m.group(1).split(';')]
  for k in ks:
   if k not in order:order.append(k)
  return '['+', '.join(str(order.index(k)+1) for k in ks)+']'
 text=re.sub(r'\[@([^\]]+)\]',cite,text);text=re.sub(r'(?m)^(#{1,3} [^\n]+)\n(?!\n)',r'\1\n\n',text);d=setup();eq=0
 for b in text.split('\n\n'):
  b=b.strip()
  if not b:continue
  if b=='[[TABLE1]]':table(d,T1H,T1R,[1450,2900,5010],'Table 1. Explicit ablation design. Each row contrasts with FULL.');continue
  if b=='[[TABLE2]]':table(d,T2H,T2R,[2350,3200,3810],'Table 2. External evidence and the interpretation it supports.');continue
  if b=='[[TABLE3]]':table(d,T3H,T3R,[1300,3900,4160],'Table 3. Three-tier grading criteria for clause C4 (representation information).');continue
  if b=='[[REFERENCES]]':
   for i,k in enumerate(order,1):
    p=d.add_paragraph(f'[{i}] '+reftext(k));p.paragraph_format.line_spacing=1;p.paragraph_format.space_after=Pt(5)
    for r in p.runs:r.font.size=Pt(9)
   continue
  if b=='[[FIGURES]]':
   for name,cap in CAPTIONS:
    d.add_page_break();p=d.add_paragraph();p.paragraph_format.keep_with_next=True;p.add_run().add_picture(str(F/(name+'.png')),width=Inches(6.45));d.add_paragraph(cap,style='Caption')
   continue
  if b.startswith('$$'):
   for j,parts in enumerate(EQS[eq]):
    p=d.add_paragraph();p.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_after=Pt(6);om=element('m:oMath')
    for part in parts:om.append(part)
    p._p.append(om)
    if j==len(EQS[eq])-1:p.add_run(f'    ({eq+1})').font.size=Pt(10)
   eq+=1;continue
  if b.startswith('### '):d.add_heading(b[4:],2)
  elif b.startswith('## '):d.add_heading(b[3:],1)
  elif b.startswith('# '):d.add_paragraph(b[2:],style='Title')
  else:d.add_paragraph(b)
 d.save(O/'Manuscript_CSBJ.docx')
 refs='\n\n'.join(f'[{i}] '+reftext(k) for i,k in enumerate(order,1));(O/'References_verified.txt').write_text(refs,encoding='utf-8')
 bib=[]
 for k in order:
  r=REF[k];bib.append('@article{'+k+',\n  author = {'+' and '.join(r['authors'])+'},\n  title = {'+r['title']+'},\n  journal = {'+r['journal']+'},\n  year = {'+str(r['year'])+'},\n  doi = {'+r.get('doi','')+'},\n  url = {'+r['url']+'}\n}')
 (O/'References.bib').write_text('\n\n'.join(bib),encoding='utf-8')
 resolved=text.replace('[[REFERENCES]]',refs).replace('[[FIGURES]]','\n\n'.join(c for _,c in CAPTIONS))
 for marker,head,rows in [('[[TABLE1]]',T1H,T1R),('[[TABLE2]]',T2H,T2R),('[[TABLE3]]',T3H,T3R)]:resolved=resolved.replace(marker,' | '.join(head)+'\n'+'\n'.join(' | '.join(r) for r in rows))
 (O/'Manuscript_CSBJ_resolved.md').write_text(resolved,encoding='utf-8')
 return len(re.findall(r'\b[\w-]+\b',resolved)),len(order)

if __name__=='__main__':
 figures();print('MAIN',build_main())
