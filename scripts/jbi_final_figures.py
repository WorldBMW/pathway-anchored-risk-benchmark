"""Publication-size vector figures and source-based histology; no synthetic images."""
from pathlib import Path
import json,io,importlib.util
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch,Rectangle
from PIL import Image
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'results';P=ROOT/'papers/08_JBI';F=P/'Figures'
read=lambda f:json.loads((R/f).read_text(encoding='utf-8'))
N=read('jbi_submission_audit/numbers.json');D=read('jbi_submission_audit/rank_perm_recomputed.json')
plt.rcParams.update({'font.family':'Arial','font.size':8,'axes.titlesize':9,'axes.labelsize':8,'xtick.labelsize':8,'ytick.labelsize':8,'pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})
manifest={}
def save(fig,name):
 fig.savefig(F/(name+'.pdf'),dpi=600)
 fig.savefig(F/(name+'.png'),dpi=600)
 fig.savefig(F/(name+'.tiff'),dpi=600,pil_kwargs={'compression':'tiff_lzw'})
 manifest[name]={'inches':list(fig.get_size_inches()),'dpi':600,'pdf':'embedded TrueType fonts; vector text and plots'}
 plt.close(fig)
# Figure 3: estimates, optimization seeds, and fixed-score alignment diagnostics.
vs=list(D['variants']);labs=['FULL','NO-IMAGE','NO-HPV','NO-NEIGH','NO-PROG','NO-SUP','NO-ALL'];colors=['#28548A','#5798C1','#459C8C','#D29B38','#C44E52','#8863A5','#555555']
fig,axs=plt.subplots(1,2,figsize=(7.2,3.6));fig.subplots_adjust(left=.085,right=.985,bottom=.25,top=.83,wspace=.32)
for ax,field in zip(axs,['moran_within_mean','tau']):
 for i,v in enumerate(vs):
  vals=np.array([r[field] for r in D['variants'][v]])
  ax.bar(i,vals.mean(),color=colors[i],width=.65,yerr=vals.std(ddof=1),capsize=2,error_kw={'lw':.8})
  ax.scatter(i+np.linspace(-.13,.13,len(vals)),vals,s=9,c='black',zorder=3)
 ax.set_xticks(range(7),labs,rotation=45,ha='right');ax.axhline(0,c='#555555',lw=.6)
axs[0].set(ylabel="Mean within-section Moran's I",ylim=(0,1));axs[0].set_title('A  Within-section structure',loc='left',weight='bold')
axs[1].set(ylabel='Section-level Kendall τ-b',ylim=(-.28,.64));axs[1].set_title('B  Disease ordering',loc='left',weight='bold')
fig.text(.08,.955,'Bars: mean ± SD across seeds; dots: individual seeds',fontsize=8)
fig.text(.52,.91,'Nominal p < 0.05: 3/3, 3/3, 3/3, 3/3, 3/4, 1/3, 0/3',fontsize=7)
fig.text(.52,.035,'Fixed-score, one-sided permutation; not a refitted null',fontsize=7)
save(fig,'Fig3_ablation_multiseed')
# Figure 5: original external outputs, explicit section/core/fold units.
ex=read('external_corrected_numbers.json');gx=ex['geomx_gse316098_corrected'];core=pd.read_csv(R/'gse316098_core_level.csv')
rg=read('hnscc_random_gene_moran.json')
# Reuse verified aggregation definitions from the existing source, without its plots.
base=(ROOT/'scripts/gen_figures_v10.py').read_text(encoding='utf-8')
part=base[base.index("hnscc = json.load"):base.index("disc = json.load")]
ns={'json':json,'np':np};exec(part,ns)
fig,axs=plt.subplots(2,2,figsize=(7.2,6.0));fig.subplots_adjust(left=.095,right=.985,bottom=.10,top=.93,wspace=.30,hspace=.50)
rng=np.random.default_rng(20260924);ax=axs[0,0];x=np.arange(2);w=.20
series=[('Model',[ns['hm'],ns['g28']],'#28548A'),('KEGG',[ns['rg268']['kegg_per_slide'],ns['rg281']['kegg_per_slide']],'#5798C1'),('Random',[ns['rg268']['random_HVG_union_exprMatched']['per_slide'],ns['rg281']['random_HVG_union_exprMatched']['per_slide']],'#999999')]
for j,(lab,arrs,c) in enumerate(series):
 pos=x+(j-1)*w;ax.bar(pos,[np.mean(a) for a in arrs],w*.9,label=lab,color=c)
 for px,arr in zip(pos,arrs):ax.scatter(px+rng.uniform(-.04,.04,len(arr)),arr,s=7,c='black',alpha=.55)
ax.set_xticks(x,['GSE268014\n8 sections','GSE281978\n6 sections']);ax.set(ylabel="Within-section Moran's I",ylim=(-.06,1.15));ax.axhline(0,c='#666666',lw=.8,ls='--');ax.legend(frameon=False,ncol=3,fontsize=7,loc='upper center',handlelength=.9,columnspacing=.8)
ax.set_title('A  Head-and-neck spatial structure',loc='left',weight='bold')
ax=axs[0,1];groups=[core.loc[~core.silva.isin(['A','B','C']),'score'].to_numpy(),core.loc[core.silva.isin(['A','B','C']),'score'].to_numpy()]
v=ax.violinplot(groups,showmedians=True)
for body,c in zip(v['bodies'],['#5798C1','#C44E52']):body.set_facecolor(c);body.set_alpha(.65)
for i,a in enumerate(groups):ax.scatter(i+1+rng.uniform(-.065,.065,len(a)),a,s=6,c='black',alpha=.45)
ax.set_xticks([1,2],[f'Benign\n{len(groups[0])} cores',f'Tumor\n{len(groups[1])} cores']);ax.set_ylabel('Expression-only model score');ax.set_title('B  GeoMx core scores',loc='left',weight='bold',pad=20);ax.text(.5,1.015,'Six paired patients: p = 0.03125',transform=ax.transAxes,ha='center',fontsize=8)
ax=axs[1,0];cs=gx['core_level']['silva'];means=[cs[k]['mean'] for k in 'ABC']
ax.scatter(range(3),means,s=38,c=['#D29B38','#459C8C','#28548A']);ax.set_xticks(range(3),[f'Silva {k}\n{cs[k]["n"]} cores' for k in 'ABC']);ax.set(xlim=(-.45,2.45),ylim=(-15.2,-11.3),ylabel='Mean core score');ax.set_title('C  Descriptive invasion patterns',loc='left',weight='bold',pad=20)
for i,v in enumerate(means):ax.text(i,v+.16,f'{v:.2f}',ha='center',fontsize=8)
ax.text(.5,1.015,'Cores are clustered within patients',transform=ax.transAxes,ha='center',fontsize=8)
ax=axs[1,1];names=['HSIL_HPV','CA_HPV_1','CA_HPV_2','cervical_cancer_1'];x=np.arange(4)
for j,(key,lab,c) in enumerate([('lodo_v2','Ordinal + proxy','#28548A'),('unsup_lodo_v2','Targets off','#D29B38')]):
 dd={r['holdout']:r['percentile_vs_normal'] for r in ex[key]['folds']};vals=[dd[n] for n in names];pos=x+(j-.5)*.36;ax.bar(pos,vals,.34,label=lab,color=c)
 for px,v in zip(pos,vals):ax.text(px,v+.025,f'{v:.2f}',ha='center',fontsize=7)
ax.axhline(.5,c='#555555',lw=.8,ls='--');ax.set_xticks(x,['HSIL','SCC 1','ADC','SCC 2']);ax.set(ylabel='Percentile vs 31 training normals',ylim=(0,1.28));ax.legend(frameon=False,fontsize=7,loc='upper center',ncol=2,handlelength=.8,columnspacing=.7);ax.set_title('D  Held-out disease sections',loc='left',weight='bold')
save(fig,'Fig5_external_transfer')
# Figure 2: spot distributions are descriptive; means explicitly separated from medians.
z=np.load(R/'fused_embs_FULL_seed0.npz',allow_pickle=True);ss=z['sample_ids'].astype(str);sc=z['scores'].astype(float)
y=np.array([2 if any(k in a.lower() for k in ['ca_hpv','cancer','carcinoma']) else 1 if any(k in a.lower() for k in ['hsil','cin']) else 0 for a in ss]);groups=[sc[y==i] for i in range(3)]
fig,ax=plt.subplots(figsize=(5.2,3.6));fig.subplots_adjust(left=.16,right=.97,bottom=.20,top=.85)
v=ax.violinplot(groups,showmedians=True,widths=.7)
for pc,c in zip(v['bodies'],['#5798C1','#D29B38','#C44E52']):pc.set_facecolor(c);pc.set_alpha(.7)
v['cmedians'].set_color('black')
for i,g in enumerate(groups):ax.text(i+1,max(g)+.11,f'Mean {g.mean():.2f}',ha='center',fontsize=8)
ax.set_xticks([1,2,3],['Normal\n31 sections','HSIL\n1 section','Cancer\n3 sections']);ax.set(ylabel='Spot-level model score (FULL, seed 0)',ylim=(-.85,2.55));ax.set_title('In-sample distributions by section diagnosis',weight='bold',pad=20);ax.text(.5,1.01,'Descriptive spot distributions; black lines show medians',transform=ax.transAxes,ha='center',fontsize=7)
save(fig,'Fig2_risk_violin')
# Figure 4: descriptive correlations, with accessible blue/orange colors.
bio=read('downstream_spot_analysis.json')
bio = json.load(open('results/downstream_spot_analysis.json', encoding='utf-8'))
sets = [c['set'] for c in bio[0]['pathway_cell_corr']]
bio_mean = {}
for s in sets:
    rhos = [next(c['spearman_rho'] for c in r['pathway_cell_corr'] if c['set'] == s) for r in bio]
    qs = [next(c['BH_q'] for c in r['pathway_cell_corr'] if c['set'] == s) for r in bio]
    bio_mean[s] = {'rho': float(np.mean(rhos)), 'rho_sd': float(np.std(rhos, ddof=1) if len(rhos) > 1 else 0),
                   'q_max': float(max(qs))}
# aggregate for the plotted marker sets
order = sorted(sets, key=lambda s: bio_mean[s]['rho'], reverse=True)
labels = [s.replace('CELL_', '').replace('_', ' ').replace('ANTIVIRAL', 'antiviral') for s in order]
rhos = [bio_mean[s]['rho'] for s in order]
bcols = ['#C00000' if r < -0.15 else ('#70AD47' if r > 0.15 else '#BFBFBF') for r in rhos]
fig,ax=plt.subplots(figsize=(7.2,3.8));fig.subplots_adjust(left=.35,right=.97,bottom=.17,top=.86)
ax.barh(np.arange(len(labels)),rhos,color=['#28548A' if r>=.2 else '#C77B32' if r<=-.15 else '#999999' for r in rhos]);ax.set_yticks(np.arange(len(labels)),labels);ax.invert_yaxis();ax.axvline(0,c='#555555',lw=.8);ax.set_xlim(-.60,.60)
for i,r in enumerate(rhos):ax.text(r+(.018 if r>=0 else -.018),i,f'{r:+.2f}',va='center',ha='left' if r>=0 else 'right',fontsize=8)
ax.set_xlabel('Spearman ρ (within-section z scores; mean of three seeds)');ax.set_title('Pathway / cell-state correlations with model scores',weight='bold')
save(fig,'Fig4_biology_correlation')

# Figure 1: original H&E pixels with vector labels and a concise architecture diagram.
spec=importlib.util.spec_from_file_location('hist',ROOT/'scripts/gen_fig1_histology_v10.py');hist=importlib.util.module_from_spec(spec);spec.loader.exec_module(hist)
fig=plt.figure(figsize=(7.2,6.4));gs=fig.add_gridspec(2,4,left=.035,right=.985,bottom=.64,top=.955,hspace=.10,wspace=.07,height_ratios=[1.35,1])
for i,(key,path,title,src,box,wb) in enumerate(hist.CASES):
 a=hist.load_rgb(path);bb=hist.tissue_bbox(a)
 for j,cropbox in enumerate([bb,box]):
  ax=fig.add_subplot(gs[j,i]);h,w=a.shape[:2];x0,y0,x1,y1=cropbox;crop=a[int(y0*h):int(y1*h),int(x0*w):int(x1*w)]
  ax.imshow(crop);ax.axis('off')
  if j==0:
   ax.set_title(['Normal','HSIL','Invasive SCC','Invasive ADC'][i]+'\n'+['P020','HSIL_HPV','cervical_cancer_1','CA_HPV_2'][i],fontsize=8,pad=4)
   bx0,by0,bx1,by1=box;ax.add_patch(Rectangle(((bx0-x0)*w,(by0-y0)*h),(bx1-bx0)*w,(by1-by0)*h,fill=False,ec='black',lw=.8))
fig.text(.008,.986,'A',weight='bold',fontsize=11,va='top')
ax=fig.add_axes([.015,.015,.97,.60]);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off');ax.text(0,.98,'B',weight='bold',fontsize=11,va='top')
def box(x,y,w,h,title,text,color):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.008',fc=color,ec='#666666',lw=.8));ax.text(x+w/2,y+h*.72,title,ha='center',va='center',fontsize=9,weight='bold');ax.text(x+w/2,y+h*.32,text,ha='center',va='center',fontsize=8,linespacing=1.4)
def arrow(p,q):ax.add_patch(FancyArrowPatch(p,q,arrowstyle='-|>',mutation_scale=10,color='#555555',lw=1))
box(.035,.64,.22,.22,'Expression','4,991 genes per spot\nMLP → 128 dimensions','#EAF2F7')
box(.035,.32,.22,.22,'Morphology','224 × 224-pixel patches\nFrozen UNI → 128 dimensions','#EAF2F7')
box(.34,.39,.24,.39,'Fusion','Four-head attention\n+ residual normalization\n128 dimensions','#FFF7DD')
box(.69,.70,.28,.18,'Score head','128 → 64 → 1 MLP','#F7ECDC')
box(.69,.47,.28,.18,'Proxy probe','Expression-derived target','#F7ECDC')
box(.69,.24,.28,.18,'Reconstruction','128 → 256 → 4,991 MLP','#F7ECDC')
for y in [.75,.43]:arrow((.26,y),(.33,y if y>.5 else .48))
for y in [.79,.56,.33]:arrow((.585,.59),(.68,y))
box(.04,.015,.93,.16,'Training objective','Reconstruction + score variance + pathway consistency + proxy + ordinal + neighborhood','#F2F2F2')
ax.text(.16,.26,'NO-IMAGE: image input set to zero',ha='center',fontsize=7)
save(fig,'Fig1_Framework')
# Other statistical plots remain vector PDF; derive matching TIFFs at 600 dpi.
for name in ['Fig2_risk_violin','Fig4_biology_correlation']:
 d=fitz.open(F/(name+'.pdf'));page=d[0];pix=page.get_pixmap(dpi=600);im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples);im.save(F/(name+'.tiff'),compression='tiff_lzw',dpi=(600,600));manifest[name]={'pdf':'original vector plot','tiff_dpi':600,'pixels':list(im.size)}
# Graphical abstract: large text designed for the publisher's reduced display.
plt.rcParams['font.size']=20
fig,ax=plt.subplots(figsize=(13.28,5.31));fig.subplots_adjust(0,0,1,1);ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
ax.text(.5,.93,'Label dependence in small-sample spatial transcriptomics',ha='center',fontsize=25,weight='bold',color='#203864')
for x,c in [(.025,'#EAF2F7'),(.36,'#F3EFF8'),(.695,'#EDF4EE')]:ax.add_patch(FancyBboxPatch((x,.17),.28,.64,boxstyle='round,pad=.012',fc=c,ec='#203864',lw=1.5))
ax.text(.165,.73,'35 cervical sections',ha='center',fontsize=23,weight='bold')
ax.text(.165,.54,'31 normal\n4 diseased',ha='center',fontsize=25,linespacing=1.4)
ax.text(.165,.27,'46,820 correlated spots',ha='center',fontsize=19)
ax.text(.50,.73,'Seven-variant audit',ha='center',fontsize=23,weight='bold')
ax.text(.50,.51,'Ordinal targets off\n↓  Proxy targets off\n↓  Pathway term off',ha='center',fontsize=21,linespacing=1.35)
ax.text(.50,.27,'Section-level evaluation',ha='center',fontsize=19)
ax.text(.835,.73,'Disease ordering falls',ha='center',fontsize=22,weight='bold')
ax.text(.835,.57,'Kendall τ\n0.46 → 0.25 → 0.21 → −0.11',ha='center',fontsize=19,linespacing=1.3)
ax.text(.835,.36,'Spatial structure persists\nClinical utility not established',ha='center',fontsize=18,linespacing=1.5)
for x in [.32,.655]:ax.add_patch(FancyArrowPatch((x,.5),(x+.028,.5),arrowstyle='-|>',mutation_scale=22,lw=2,color='#203864'))
ax.text(.5,.072,'Dependence on training targets does not prove memorization.',ha='center',fontsize=22,color='#444444')
for ext in ['pdf','png','tiff']:
 kw={'pil_kwargs':{'compression':'tiff_lzw'}} if ext=='tiff' else {}
 fig.savefig(P/('GraphicalAbstract_JBI.'+ext),dpi=300,**kw)
plt.close(fig)
manifest['GraphicalAbstract_JBI']={'pixels':[3984,1593],'dpi':300,'font':'Arial','formats':['PDF','TIFF','PNG']}
(P/'_qa_20260924/artwork_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Final vector PDF and TIFF figures exported.')
