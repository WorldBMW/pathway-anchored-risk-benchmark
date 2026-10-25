"""Build the Briefings in Bioinformatics (Problem solving protocol) package
(papers/14_BiB_20261016) from verified local evidence; no external publication.

BiB changes vs csbj_build_package_v2.py:
  - main text compressed to <=5,000 words; supplementary carries clauses, model
    details, external endpoints, biology and Figures S1-S5 (old Fig5-9)
  - Tables renumbered: Table 1 grading criteria, Table 2 operating
    characteristics, Table 3 unified audit + unified readout (combined)
  - equations subset: tau_b, LDI, p_refit, tau_max, sens/fpr
  - references extended with probing / ST-methods / implementation citations
"""
from pathlib import Path
import json,re,shutil,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT

R=Path(__file__).resolve().parents[1]
O=R/'papers/14_BiB_20261016';OLD=R/'papers/12_CSBJ_audit_20261010'
E=O/'evidence';F=O/'figures';E.mkdir(parents=True,exist_ok=True);F.mkdir(parents=True,exist_ok=True)

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def package_evidence():
    old_ev = OLD/'evidence'
    if old_ev.is_dir():
        for f in old_ev.iterdir():
            if f.is_file():shutil.copy(f,E/f.name)
    for n in ['sim_power_summary.json','sim_power_summary_refit.json','sim_power_raw_refit.json','st_methods_benchmark_v2.json','v2_ctrl_full_probe.json','v2_ctrl_full_probe_refit.json','v2_ours_subset_probe.json','v2_ours_subset_probe_refit.json','unified_readout_probe.json']:
        shutil.copy(R/'results'/n,E/n)
    shutil.copy(R/'results/st_method_embeddings/st_method_embeddings_manifest.json',E/'st_method_embeddings_manifest.json')
    p=E/'Table_S1_corrected_probes.csv'
    if p.exists() and 'cohort_description' not in p.read_text(encoding='utf-8-sig').split('\n')[0]:
        ls=p.read_text(encoding='utf-8-sig').strip().split('\n')
        m={'A':'simulation: strong shared program (pre-grid scenario design)','B':'simulation: weak shared program (pre-grid scenario design)','C':'simulation: identity-confounded control (pre-grid scenario design)','cervical':'cervical demonstration cohort'}
        out=[ls[0]+',cohort_description,scale_description']
        for ln in ls[1:]:
            f=ln.split(',');sc=f[0];base=sc[:-6] if sc.endswith('_small') else sc
            sd='35 sections (cervical cohort)' if base=='cervical' else ('main scale (90 samples)' if f[2]=='90' else 'matched scale (35 samples)')
            out.append(ln+','+m[base]+','+sd)
        p.write_text('\n'.join(out)+'\n',encoding='utf-8')
    ref_path = OLD/'evidence/references_verified.json'
    refs = read(ref_path) if ref_path.exists() else (read(E/'references_verified.json') if (E/'references_verified.json').exists() else {})
    refs.update(NEW_REFS)
    (E/'references_verified.json').write_text(json.dumps(refs,indent=2,ensure_ascii=False),encoding='utf-8')

NEW_REFS={
 'spagcn':{'doi':'10.1038/s41592-021-01255-8','title':'SpaGCN: integrating gene expression, spatial location and histology to identify spatial domains and spatially variable genes by graph convolutional network','authors':['Jian Hu','Xiaoyin Li','Kyle Coleman','Angela Schroeder','Nan Ma','David J. Irwin','Edward B. Lee','Joanna E. Shin','Mingyao Li'],'journal':'Nature Methods','year':2021,'volume':'18','page':'1342-1351','url':'https://doi.org/10.1038/s41592-021-01255-8'},
 'stagate':{'doi':'10.1038/s41467-022-29439-6','title':'Deciphering spatial domains from spatially resolved transcriptomics with an adaptive graph convolutional network','authors':['Kun Dong','Shihua Zhang'],'journal':'Nature Communications','year':2022,'volume':'13','page':'1739','url':'https://doi.org/10.1038/s41467-022-29439-6'},
 'reforms':{'doi':'10.1126/sciadv.adk3452','title':'REFORMS: Consensus-based Recommendations for Machine-learning-based Science','authors':['Sayash Kapoor','Emily M. Cantrell','Kenny Peng','Thanh Hien Pham','Christopher A. Bail','Odd Erik Gundersen','Jake M. Hofman','Jessica Hullman','Michael A. Lones','Momin M. Malik','Priyanka Nanayakkara','Russell A. Poldrack','Inioluwa Deborah Raji','Michael Roberts','Matthew J. Salganik','Marta Serra-Garcia','Brandon M. Stewart','Gilles Vandewiele','Arvind Narayanan'],'journal':'Science Advances','year':2024,'volume':'10','page':'eadk3452','url':'https://doi.org/10.1126/sciadv.adk3452'},
 'dome':{'doi':'10.1038/s41592-021-01205-4','title':'DOME: recommendations for supervised machine learning validation in biology','authors':['Ian Walsh','D. Fishman','D. Garcia-Gasulla','Tiina Titma','G. Pollastri','E. Capriotti','R. Casadio','S. Capella-Gutierrez','D. Cirillo','Alessio Del Conte','Alexandros C. Dimopoulos','Victoria Dominguez del Angel','J. Dopazo','P. Fariselli','J. M. Fernandez','Florian Huber','A. Kreshuk','Tom Lenaerts','P. Martelli','A. Navarro','Pilib O. Broin','Janet Pinero','D. Piovesan','M. Reczko','F. Ronzano','Venkata P. Satagopam','Castrense Savojardo','Vojtech Spiwok','Marco Antonio Tangaro','G. Tartari','David Salgado','Alfonso Valencia','Federico Zambelli','J. Harrow','Fotis Psomopoulos','S. Tosatto'],'journal':'Nature Methods','year':2021,'volume':'18','page':'1122-1127','url':'https://doi.org/10.1038/s41592-021-01205-4'},
 'graphst':{'doi':'10.1038/s41467-023-36796-3','title':'Spatially informed clustering, integration, and deconvolution of spatial transcriptomics with GraphST','authors':['Yingxing Long','Kee Yuan Ngiam','Mingyao Li','Kok Onn Lee Chong','Rishabh Sethi','Chaokun Zhong','Hao Xu','Zhiyuan Ong','Kavitha Sachaphibulkij','Aik Choon Chen','Longping Zeng','Hongyi Fu','Mi Zhang','Lingxia Lynn Hong Chua','Liang Liu','Jing Chen'],'journal':'Nature Communications','year':2023,'volume':'14','page':'1155','url':'https://doi.org/10.1038/s41467-023-36796-3'},
 'stbench':{'doi':'10.1093/nar/gkaf303','title':'Benchmarking computational methods for detecting spatial domains and domain-specific spatially variable genes from spatial transcriptomics data','authors':['Liping Kang','Qinglong Zhang','Fan Qian','Junyao Liang','Xiaohui Wu'],'journal':'Nucleic Acids Research','year':2025,'volume':'53','page':'gkaf303','url':'https://doi.org/10.1093/nar/gkaf303'},
 'alainbengio':{'doi':'','title':'Understanding intermediate layers using linear classifier probes','authors':['Guillaume Alain','Yoshua Bengio'],'journal':'arXiv preprint arXiv:1610.01644','year':2016,'volume':'','page':'','url':'https://arxiv.org/abs/1610.01644'},
 'belinkov':{'doi':'10.1162/coli_a_00422','title':'Probing classifiers: promises, shortcomings, and advances','authors':['Yonatan Belinkov'],'journal':'Computational Linguistics','year':2022,'volume':'48','page':'207-219','url':'https://doi.org/10.1162/coli_a_00422'},
 'bayesspace':{'doi':'10.1038/s41587-021-00935-2','title':'Spatial transcriptomics at subspot resolution with BayesSpace','authors':['Edward Zhao','Matthew R. Stone','Xing Ren','Jamie Guenthoer','Kimberly S. Smythe','Thomas Pulliam','Stephen R. Williams','Cedric R. Uytingco','Sarah E. B. Taylor','Paul Nghiem','Jason H. Bielas','Raphael Gottardo'],'journal':'Nature Biotechnology','year':2021,'volume':'39','page':'1375-1384','url':'https://doi.org/10.1038/s41587-021-00935-2'},
 'banksy':{'doi':'10.1038/s41588-024-01664-3','title':'BANKSY unifies cell typing and tissue domain segmentation for scalable spatial omics data analysis','authors':['Vipul Singhal','Nigel Chou','Joseph Lee','Yifei Yue','Jinyue Liu','Wan Kee Chock','Li Lin','Yun-Ching Chang','Erica Mei Ling Teo','Jonathan Aow','Hwee Kuan Lee','Kok Hao Chen','Shyam Prabhakar'],'journal':'Nature Genetics','year':2024,'volume':'56','page':'431-441','url':'https://doi.org/10.1038/s41588-024-01664-3'},
 'scanpy':{'doi':'10.1186/s13059-017-1382-0','title':'SCANPY: large-scale single-cell gene expression data analysis','authors':['F. Alexander Wolf','Philipp Angerer','Fabian J. Theis'],'journal':'Genome Biology','year':2018,'volume':'19','page':'15','url':'https://doi.org/10.1186/s13059-017-1382-0'},
 'sklearn':{'doi':'','title':'Scikit-learn: machine learning in Python','authors':['Fabian Pedregosa','Gaël Varoquaux','Alexandre Gramfort','Vincent Michel','Bertrand Thirion','Olivier Grisel','Mathieu Blondel','Peter Prettenhofer','Ron Weiss','Vincent Dubourg','Jake Vanderplas','Alexandre Passos','David Cournapeau','Matthieu Brucher','Matthieu Perrot','Édouard Duchesnay'],'journal':'Journal of Machine Learning Research','year':2011,'volume':'12','page':'2825-2830','url':'https://www.jmlr.org/papers/v12/pedregosa11a.html'}}

package_evidence()
P=read(E/'corrected_probe.json');REG=read(E/'real_run_registry.json');N=read(R/'results/paper_v10_numbers.json')
BIO=read(R/'results/decircularization_biology.json')['variants'];G=read(E/'geomx_patient_final.json')
REF=read(E/'references_verified.json')
S=read(R/'results/sim_power_summary_refit.json');SO=read(R/'results/sim_power_summary.json')  # SO: descriptive in-sample FULL-head tau only (permutation-free)
CFP=read(R/'results/v2_ctrl_full_probe_refit.json')
OSP=read(R/'results/v2_ours_subset_probe_refit.json');BM=read(R/'results/st_methods_benchmark_v2.json')

COL=['#167D9A','#E0A038','#B74F59']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})

def tau_max(n0,n1):return math.sqrt(n0*n1*2/((n0+n1)*(n0+n1-1)))
TM_MAIN=tau_max(50,40);TM_SMALL=tau_max(31,4);TM_SUB_M=tau_max(12,9);TM_SUB_S=tau_max(19,2)

def savefig(fig,name):
    fig.savefig(F/(name+'.pdf'),bbox_inches='tight');fig.savefig(F/(name+'.svg'),bbox_inches='tight')
    fig.savefig(F/(name+'.png'),dpi=600,bbox_inches='tight',facecolor='white')
    with Image.open(F/(name+'.png')) as im:im.save(F/(name+'.tif'),compression='tiff_lzw',dpi=(600,600))
    plt.close(fig)

def roc_window(size):
    r=S['threshold_roc'][size];ws=[t for t,a,b in zip(r['threshold'],r['sensitivity'],r['one_minus_specificity']) if a==1.0 and b==0.0]
    return min(ws),max(ws)

def figures():
    print('caps: main %.4f small %.4f subset %.4f/%.4f'%(TM_MAIN,TM_SMALL,TM_SUB_M,TM_SUB_S))
    print('roc windows: main %s small %s'%(roc_window('main'),roc_window('small')))
    # Fig1 workflow (updated banner)
    fig,ax=plt.subplots(figsize=(9,5));ax.set(xlim=(0,10),ylim=(0,6));ax.axis('off')
    boxes=[(.2,4.45,2.7,1.1,'INPUT & PROVENANCE','Expression + morphology\nCoordinates and sample groups\nTarget sources and provenance'),(3.65,4.45,2.7,1.1,'SCORE DEPENDENCE','Six ablation variants\nDescriptive contrasts; all seeds'),(7.1,4.45,2.7,1.1,'REPRESENTATION','NOALL frozen embeddings\nSample-pooled features'),(7.1,2.35,2.7,1.25,'HELD-OUT PROBE','Train-only scaling and ridge\nRefit for each label permutation'),(3.65,2.35,2.7,1.25,'EXTERNAL PROFILE','Tissue separation; score direction\nSpatial organization; phenotype'),(.2,2.35,2.7,1.25,'EVIDENCE REPORT','Effect sizes and seed variation\nMeasured error rates; checksums')]
    for x,y,w,h,title,body in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.06',facecolor='#EEF5F7',edgecolor='#167D9A'))
        ax.text(x+w/2,y+h-.22,title,ha='center',va='center',weight='bold',fontsize=9)
        ax.text(x+w/2,y+.37,body,ha='center',va='center',fontsize=8.2,linespacing=1.5)
    for a,b in [((2.95,5),(3.55,5)),((6.4,5),(7,5)),((8.45,4.35),(8.45,3.7)),((7,2.95),(6.4,2.95)),((3.55,2.95),(2.95,2.95))]:ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',lw=1.6,color='#38566A'))
    ax.text(5,1.4,'SIMULATIONS: dose–response grid (nonresponder fraction 0 / 0.25 / 0.50 / 0.75) + identity-confounded control',ha='center',weight='bold',fontsize=8.6)
    ax.text(5,.8,'INFERENCE BOUNDARY: transductive in covariates; samples, not spots, are evaluation units',ha='center',fontsize=8.5)
    ax.text(5,.3,'Cervical tissue is the demonstration case. Clinical prediction is not the output.',ha='center',fontsize=8.5,color='#555555')
    savefig(fig,'Fig1_Audit_workflow')
    # Fig2 operating characteristics
    dr=S['detection_rate'];ti=S['type_i_error_control'];roc=S['threshold_roc'];LVS=['L1','L2','L3','L4']
    fig,axs=plt.subplots(1,3,figsize=(10.8,3.9))
    for size,off,mk,lb in [('main',-0.07,'o','90 samples'),('small',0.07,'s','35 samples (cervical-matched)')]:
        ms=[dr[size][lv]['mean_tau'] for lv in LVS];ss=[dr[size][lv]['sd_tau'] for lv in LVS];c=COL[0] if size=='main' else COL[1]
        axs[0].errorbar(np.arange(4)+off,ms,yerr=ss,marker=mk,color=c,capsize=3,lw=1.4,ms=5,label=lb)
        ct=ti[size]['CTRL'];axs[0].errorbar([4+off],[ct['mean_tau']],yerr=[[ct['sd_tau']]],marker=mk,mfc='none',color=c,capsize=3,lw=1.2,ms=6)
    axs[0].axhline(TM_MAIN,ls=':',color=COL[0],lw=1.1);axs[0].axhline(TM_SMALL,ls=':',color=COL[1],lw=1.1)
    axs[0].text(-0.42,TM_MAIN+.018,'τmax 0.707',fontsize=7.5,color=COL[0]);axs[0].text(-0.42,TM_SMALL+.018,'τmax 0.457',fontsize=7.5,color=COL[1])
    axs[0].axhline(0,color='#888888',lw=.8);axs[0].set_xticks(range(5),['L1\nf=0','L2\nf=0.25','L3\nf=0.50','L4\nf=0.75','CTRL'])
    axs[0].set_ylabel('Held-out probe tau-b');axs[0].set_title('A  Dose–response',loc='left',fontsize=10);axs[0].legend(fontsize=7.5,frameon=False,loc='lower left')
    w=.17
    for size,off in [('main',-w),('small',w)]:
        fr=[dr[size][lv]['frac_significant'] for lv in LVS]+[ti[size]['CTRL']['frac_significant']]
        axs[1].bar(np.arange(5)+off,fr,width=1.7*w,color=COL[0] if size=='main' else COL[1],label='90 samples' if size=='main' else '35 samples')
    axs[1].axhline(0.05,ls=':',color='#888888');axs[1].text(4.45,.075,'nominal α=0.05',fontsize=7.5,ha='right')
    axs[1].set_xticks(range(5),['L1','L2','L3','L4','CTRL']);axs[1].set_ylabel('Fraction of runs p<0.05');axs[1].set_ylim(0,1.08)
    axs[1].set_title('B  Detection and false positives',loc='left',fontsize=10);axs[1].legend(fontsize=7.5,frameon=False)
    for size,c in [('main',COL[0]),('small',COL[1])]:
        th=roc[size]['threshold']
        axs[2].plot(th,roc[size]['sensitivity'],color=c,lw=1.6,label='sensitivity (%s)'%('90' if size=='main' else '35'))
        axs[2].plot(th,roc[size]['one_minus_specificity'],color=c,ls='--',lw=1.2,label='false-positive rate (%s)'%('90' if size=='main' else '35'))
    axs[2].axvspan(*roc_window('main'),color=COL[0],alpha=.07);axs[2].axvspan(*roc_window('small'),color=COL[1],alpha=.10)
    axs[2].axvline(0.35,color='k',ls=':',lw=1);axs[2].text(0.345,1.05,'θ=0.35',ha='right',fontsize=8)
    axs[2].set_xlabel('Supported-grade threshold θ');axs[2].set_ylabel('Rate');axs[2].set_ylim(-.02,1.08)
    axs[2].set_title('C  Threshold operating characteristics',loc='left',fontsize=10);axs[2].legend(fontsize=6.5,frameon=False,loc='center right')
    fig.tight_layout();savefig(fig,'Fig2_Operating_characteristics')
    # Fig3 dissociation
    CF=['group_C_g20261006_CTRL','group_C_g20261007_CTRL','group_C_g20261008_CTRL'];CFS=[c+'_small' for c in CF]
    def q123(cohorts):
        q1=[r['full_head_insample_tau'] for c in cohorts for r in SO['per_cohort'][c]['runs']]
        q3t=[r['tau_lodo'] for c in cohorts for r in S['per_cohort'][c]['runs']]
        q3p=[r['p_refit'] for c in cohorts for r in S['per_cohort'][c]['runs']]
        q2=[t for c in cohorts for t in CFP[c]['taus']]
        return q1,q2,q3t,q3p
    fig,axs=plt.subplots(1,2,figsize=(9.8,4.2))
    for ax,cohorts,cap,title in [(axs[0],CF,TM_MAIN,'A  90 samples'),(axs[1],CFS,TM_SMALL,'B  35 samples (cervical-matched)')]:
        q1,q2,q3t,q3p=q123(cohorts);means=[np.mean(q1),np.mean(q2),np.mean(q3t)]
        ax.bar([0,1,2],means,color=['#9AB6C2','#B74F59','#167D9A'],alpha=.30,width=.55)
        jit=np.linspace(-.2,.2,len(q1))
        ax.scatter(0+jit,q1,marker='D',s=26,facecolor='none',edgecolor='#263D4A',zorder=4)
        ax.scatter(1+jit,q2,s=30,color='#B74F59',zorder=4)
        ax.scatter(2+jit,q3t,s=30,facecolor=['#167D9A' if p<0.05 else 'none' for p in q3p],edgecolor='#167D9A',zorder=4)
        for i,m in enumerate(means):ax.text(i,m+.025,'%.3f'%m,ha='center',fontsize=8)
        ax.axhline(0,color='#888888',lw=.8);ax.axhline(cap,ls='--',color='#555555',lw=1)
        ax.text(2.42,cap+.02,'τmax = %.3f'%cap,fontsize=8,ha='right')
        ax.set_xticks([0,1,2],['FULL head\n(in-sample fit)','label-trained embedding\n(“held-out” probe)','label-free embedding\n(held-out probe)'],fontsize=8)
        ax.set_title(title,loc='left',fontsize=10);ax.set_ylim(-.25,.82)
    axs[0].set_ylabel('Kendall tau-b')
    fig.text(.5,.012,'CTRL arm: labels independent of shared expression structure by construction. Diamonds: in-sample fit, no test applies. Dots: leave-one-out probes (filled p<0.05).',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.045,1,1));savefig(fig,'Fig3_Dissociation')
    # Fig4 benchmark
    main_c=['group_A_g20261006_L1','group_A_g20261006_L3','group_A_g20261006_L4']
    small_c=['group_A_g20261006_L1_small','group_A_g20261006_L3_small','group_A_g20261006_L4_small']
    mcols={'SpaGCN':'#167D9A','STAGATE':'#E0A038','GraphST':'#70AFB6'}
    fig,axs=plt.subplots(1,2,figsize=(10.4,4.2),sharey=True)
    for ax,cs,cap,title in [(axs[0],main_c,TM_SUB_M,'A  90-sample cohorts'),(axs[1],small_c,TM_SUB_S,'B  35-sample cohorts')]:
        for j,m in enumerate(['SpaGCN','STAGATE','GraphST']):
            xs=[k+(j-1.5)*.13 for k in range(3)]
            ts=[BM['groups'][c]['methods'][m]['lodo']['tau'] for c in cs]
            ps=[BM['groups'][c]['methods'][m]['lodo']['p'] for c in cs]
            ax.scatter(xs,ts,s=34,color=mcols[m],facecolor=[mcols[m] if p<0.05 else 'none' for p in ps],edgecolor=mcols[m],zorder=4,label=m)
        xs=[k+.22 for k in range(3)]
        ms=[OSP[c]['mean_tau'] for c in cs]
        rtaus=[[r['tau'] for r in OSP[c]['runs']] for c in cs]
        rps=[[r['p_refit'] for r in OSP[c]['runs']] for c in cs]
        sds=[float(np.std(t,ddof=1)) if len(set(t))>1 else 0.0 for t in rtaus]
        ax.errorbar(xs,ms,yerr=sds,fmt='none',ecolor='#B74F59',capsize=3,lw=1.2,zorder=3)
        ax.scatter(xs,ms,marker='D',s=34,color='#B74F59',facecolor=['#B74F59' if any(p<0.05 for p in ps) else 'none' for ps in rps],zorder=5,label='Reference probe (3 seeds)')
        ax.axhline(0,color='#888888',lw=.8);ax.axhline(cap,ls='--',color='#555555',lw=1)
        ax.text(2.44,cap+.025,'τmax=%.3f'%cap,fontsize=7.5,ha='right')
        ax.set_xticks(range(3),['L1','L3','L4']);ax.set_title(title,loc='left',fontsize=10)
    axs[0].set_ylabel('Kendall tau-b (21-sample subset)');axs[0].legend(fontsize=7,frameon=False,ncol=2,loc='upper right')
    fig.tight_layout();savefig(fig,'Fig4_Methods_benchmark')
    # Fig5 cervical audit (old Fig3)
    fig,axs=plt.subplots(1,2,figsize=(9,4),gridspec_kw={'width_ratios':[1.35,1]})
    for j,(v,rows) in enumerate(REG.items()):
        t=[r['tau'] for r in rows];axs[0].scatter(t,np.full(len(t),j)+np.linspace(-.1,.1,len(t)),s=24,color='#167D9A');axs[0].errorbar(np.mean(t),j,xerr=np.std(t,ddof=1),fmt='|',color='#263D4A',capsize=3)
    axs[0].set_yticks(range(7),list(REG));axs[0].invert_yaxis();axs[0].axvline(0,color='#888888',lw=.8);axs[0].set(xlabel='In-sample score–severity tau-b',title='A  Explicit ablation contrasts')
    for j,r in enumerate(P['groups']['cervical']):
        v=r['legacy_no_intercept'];axs[1].scatter(j,v['tau'],s=65,color='#167D9A');axs[1].text(j,v['tau']+.04,f"p = {v['p_refit']:.4f}",ha='center',fontsize=8)
    axs[1].axhline(0,color='#888888',lw=.8);axs[1].set(xticks=[0,1,2],xticklabels=['Seed 0','Seed 1','Seed 2'],ylim=(-.12,.57),xlim=(-.55,2.55),ylabel='Held-out probe tau-b',title='B  NOALL representation')
    fig.tight_layout();savefig(fig,'Fig5_Cervical_audit')
    # Fig6 biological orientation (old Fig4)
    keys=['CELL_tumor_epithelial','HPV_INTEGRATION_CANDIDATE','ANTIGEN_PRESENTATION','INTERFERON_ANTIVIRAL','PROLIFERATION'];labels=['Epithelial','HPV-related','Antigen presentation','Interferon / antiviral','Proliferation']
    mat=np.array([[BIO[v][k]['rho_mean'] for v in ['FULL','NOPROG','NOSUP']]+BIO['NOALL'][k]['rhos'] for k in keys])
    fig,ax=plt.subplots(figsize=(8.3,3.8));im=ax.imshow(mat,vmin=-.8,vmax=.8,cmap='RdBu_r',aspect='auto')
    ax.set_yticks(range(5),labels);ax.set_xticks(range(6),['FULL\nmean','NOPROG\nmean','NOSUP\nmean','NOALL\nseed 0','NOALL\nseed 1','NOALL\nseed 2']);ax.set_title('Orientation must be inspected before averaging biological associations',loc='left',fontsize=10)
    for i in range(5):
        for j in range(6):ax.text(j,i,f'{mat[i,j]:+.2f}',ha='center',va='center',color='white' if abs(mat[i,j])>.5 else '#222222')
    ax.axvline(2.5,color='white',lw=3);fig.colorbar(im,ax=ax,label='Spearman correlation',fraction=.035,pad=.03);fig.tight_layout();savefig(fig,'Fig6_Biological_orientation')
    # Fig7 external evidence (old Fig5)
    fig,axs=plt.subplots(1,2,figsize=(8.7,4))
    for i,r in enumerate(G['pairs']):axs[0].plot([0,1],[r['benign_mean'],r['tumor_mean']],'-o',color=plt.cm.viridis(i/6),lw=1.3,ms=4,label=r['patient'])
    axs[0].set(xticks=[0,1],xticklabels=['Benign','Tumor'],ylabel='Unbounded score',title='A  GeoMx: paired patient means');axs[0].text(.03,.07,'6 / 6 negative differences\nExact two-sided p = 0.03125',transform=axs[0].transAxes,fontsize=8);axs[0].legend(fontsize=6.5,loc='upper right',ncol=2)
    means=[N['external']['hnscc_moran_mean'],N['external']['hnscc_gse281978_moran_mean']];axs[1].bar([0,1],means,color=['#167D9A','#70AFB6'],width=.55)
    axs[1].set(xticks=[0,1],xticklabels=['GSE268014\n8 sections','GSE281978\n6 sections'],ylim=(0,1),ylabel="Mean Moran's I",title='B  Spatial organization persists')
    for j,m in enumerate(means):axs[1].text(j,m+.035,f'{m:.3f}',ha='center')
    axs[1].text(.5,.09,'HPV-status p = 0.200 / 0.133\nOrganization does not establish discrimination',transform=axs[1].transAxes,ha='center',fontsize=8)
    fig.tight_layout();savefig(fig,'Fig7_External_evidence')
    # Fig8 / Fig9 copied from the v1 package
    for src,dst in [('Fig6_LDI_calibration','Fig8_LDI_calibration'),('Fig7_Local_controls','Fig9_Local_controls')]:
        shutil.copy(OLD/'figures'/(src+'.png'),F/(dst+'.png'))
        if (OLD/'figures'/(src+'.pdf')).exists():shutil.copy(OLD/'figures'/(src+'.pdf'),F/(dst+'.pdf'))
        with Image.open(F/(dst+'.png')) as im:im.convert('RGB').save(F/(dst+'.tif'),compression='tiff_lzw',dpi=(300,300))
    # Graphical abstract
    fig,ax=plt.subplots(figsize=(9,3));ax.axis('off');ax.text(.02,.88,'MRP-ST | Audit the claim before interpreting the map',fontsize=16,weight='bold',transform=ax.transAxes)
    for j,(title,body) in enumerate([('REMOVE TARGETS','Which objectives orient\nthe scalar score?'),('PROBE REPRESENTATIONS','Does held-out information\nsurvive in the embedding?'),('SEPARATE ENDPOINTS','Do direction, organization\nand phenotype transfer?')]):
        x=.02+j*.335;ax.add_patch(FancyBboxPatch((x,.27),.29,.43,transform=ax.transAxes,boxstyle='round,pad=.02',fc='#EEF5F7',ec='#167D9A'));ax.text(x+.145,.59,title,ha='center',fontsize=10,weight='bold',transform=ax.transAxes);ax.text(x+.145,.41,body,ha='center',fontsize=10,transform=ax.transAxes)
    ax.text(.5,.1,'Known-signal grid → measured error rates → published-method audit → cervical demonstration',ha='center',fontsize=11,transform=ax.transAxes)
    savefig(fig,'Graphical_Abstract')

CAPTIONS=[
('Fig1_Audit_workflow','Figure 1. MRP-ST workflow. Separate ablation contrasts quantify scalar-score dependence; a held-out probe assesses information in frozen NOALL embeddings. Sample-label permutations refit the complete probe. A dose–response grid with an identity-confounded control measures the grading rule’s error rates, and a unified audit applies the same criteria to published embedding methods. External endpoints are evaluated separately. Encoding remains transductive in covariates; cervical disease provides a demonstration, not clinical validation.'),
('Fig2_Operating_characteristics','Figure 2. Measured operating characteristics of the C4 grading rule on the dose–response grid. A: mean held-out probe tau-b (± SD over nine runs) versus nonresponder fraction f at the 90-sample (circles) and cervical-matched 35-sample (squares) scales; the identity-confounded control is plotted at right; dotted lines mark the binary-label bound tau_max (0.707 and 0.457). B: fraction of runs with refitted p < 0.05; the dotted line marks nominal alpha = 0.05, and the control columns give the empirical false-positive rate (0/9 and 0/9). C: sensitivity (L1 cohorts) and false-positive rate (CTRL cohorts) as functions of the supported-grade threshold; shading marks the perfect-separation windows [0.20, 0.675] (main) and [0.20, 0.45] (matched); the prespecified threshold 0.35 lies inside both windows.'),
('Fig3_Dissociation','Figure 3. The control arm dissociates head memorization, encoder leakage and representation information. All panels use the identity-confounded CTRL cohorts, whose labels are independent of the shared expression structure by construction. A: 90-sample scale. B: cervical-matched 35-sample scale. Bars are means over nine runs; dots are individual runs. Three readouts per scale: FULL head in-sample tau-b (supervised fit; no test applies), FULL-embedding leave-one-out probe tau-b (label-trained transductive encoder; all p ≤ 1e-4), and NOALL-embedding leave-one-out probe tau-b (label-free frozen encoder; filled dots p < 0.05). Dashed line: binary-label bound tau_max (0.707 and 0.457). Only the label-free encoder returns the correct null (−0.030 ± 0.111 and +0.042 ± 0.102); the 0.73 and 0.41 tau-unit gaps to the label-trained embeddings are the encoder-leakage magnitude that clause C4 excludes.'),
('Fig4_Methods_benchmark','Figure 4. A unified audit grades published unsupervised embedding methods and the reference protocol on identical 21-sample subsets. A: 90-sample cohorts. B: cervical-matched 35-sample cohorts. Each panel shows Kendall tau-b of per-sample risk readouts against severity: SpaGCN, STAGATE and GraphST (single runs; cluster-max HPV-pathway readout; 2,000 label permutations; filled markers p < 0.05) and the reference protocol’s ridge probe on frozen NOALL embeddings (mean ± SD over three training seeds; refitted permutations; filled diamonds: at least one seed p < 0.05). Dashed lines: subset binary-label bounds (0.717 and 0.425). Supported grades occur only at the strongest level L1; no readout separates the weak levels from the null, and SpaGCN’s matched-scale readout returns identical tau at all three levels (readout compression).'),
('Fig5_Cervical_audit','Figure 5. Cervical score dependence and representation information. A: original NPZ scores pooled by sample and compared with severity; points show training seeds and bars mean ± sample SD. NOPROG has four seeds, other variants three. Seed sets are not fully paired. B: NOALL held-out probe correlations with one-sided p-values from 10,000 refitted label permutations. One of three seeds is significant, including after BH adjustment across 21 tests.'),
('Fig6_Biological_orientation','Figure 6. Descriptive biological associations across information removal. FULL, NOPROG and NOSUP columns show mean correlations; NOALL columns display individual seeds to expose sign instability. Colors represent stored score–program Spearman correlations. These are expression-derived associations, not independent mechanistic validation; no post hoc sign correction is applied.'),
('Fig7_External_evidence','Figure 7. External properties are not interchangeable. A: FINAL-checkpoint GeoMx scores, aggregated within each of six paired patients and tissue types. All tumor-minus-benign differences are negative; exact signed-rank p=0.03125. B: stored mean Moran’s I in two head-and-neck cohorts, accompanied by separate sample-level HPV-status tests. The axes measure different endpoints and are not combined into a validation score.'),
('Fig8_LDI_calibration','Figure 8. Label-Dependence Index calibration and gate behaviour (clause C3). A: severity-ordering distribution of the supervised score under 10,000 complete sample-label permutations, with the observed tau and the 95th-percentile gate theta marked; the observed value lies far in the upper tail. B: recovery of injected label dependence as a function of the injected fraction alpha, showing monotone calibration and the alpha at which simulated dependence matches the observed ordering. C: per-variant mean tau with seed SD across the seven variants (FULL and six ablations) on the tau scale, with the same theta line. The LDI reported in the text is this excess standardized by the null SD (LDI=3.26 against theta=1.645); the raw tau_FULL − tau_NOALL contrast is not used because the NOALL head collapses to a numerically indeterminate offset.'),
('Fig9_Local_controls','Figure 9. Local controls for label dependence, leakage and threshold choice. A: gate threshold theta as a function of alpha with the permutation-seed range shown, against the observed tau_FULL; the label-dependent verdict is stable across alpha in {0.01, 0.05, 0.10, 0.20} and five permutation seeds. B: per-variant mean score–severity tau with seed SD for the seven variants (label-free variant in red). C: leave-one-donor-out probe correlations by variant; encoders trained with donor labels return 0.42–0.46 with all seeds significant, whereas the label-free encoders return 0.270 with one of three seeds significant. Panels B and C separate the memorisation gap from the transferable signal.')]

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
def rad(inner):
    x=element('m:rad');pr=element('m:radPr');pr.append(element('m:degHide',**{'m:val':'1'}));x.append(pr)
    e=element('m:e');e.append(inner);x.append(e)
    return x

EQS=[
 [[sub('τ','b'),mr(' = '),frac('C − D','√[(C + D + Tₛ)(C + D + Tᵧ)]')]],
 [[mr('LDI = '),fraction([sub('τ̄','FULL'),mr(' − '),sub('τ','⊥')],'σ_null'),mr(' ,     θ = '),sup('Φ','−1'),mr('(1 − α)')]],
 [[sub('p','refit'),mr(' = '),fraction([mr('1 + '),summ('b=1','B','1{ τ(ŷ[πᵦ], y[πᵦ]) ≥ τ(ŷ, y) }')],'B + 1')]],
 [[sub('τ','max'),mr(' = '),rad(fraction([mr('n₀ n₁')],'C(n₀+n₁, 2)'))]],
 [[mr('sens(θ) = Pr( τ̂ ≥ θ | L1 ),      fpr(θ) = Pr( τ̂ ≥ θ | CTRL )')]]]

def setup():
    d=Document();s=d.sections[0];s.page_width=Inches(8.5);s.page_height=Inches(11);s.top_margin=s.bottom_margin=s.left_margin=s.right_margin=Inches(1);s.header_distance=s.footer_distance=Inches(.492)
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
    for w in widths:grid.append(element('w:gridCol',**{'w:w':str(w)}))
    for ri,vals in enumerate([headers]+rows):
        row=t.rows[0] if ri==0 else t.add_row();trpr=row._tr.get_or_add_trPr();trpr.append(element('w:cantSplit'))
        if ri==0:trpr.append(element('w:tblHeader'))
        for i,(c,v) in enumerate(zip(row.cells,vals)):
            c.width=Inches(widths[i]/1440);tc=c._tc.get_or_add_tcPr();tw=tc.find(qn('w:tcW'));tw.set(qn('w:w'),str(widths[i]));tw.set(qn('w:type'),'dxa');mar=element('w:tcMar')
            for side,value in [('top',80),('bottom',80),('start',120),('end',120)]:mar.append(element('w:'+side,**{'w:w':str(value),'w:type':'dxa'}))
            tc.append(mar);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER;p=c.paragraphs[0];p.paragraph_format.space_after=Pt(3);p.paragraph_format.line_spacing=1
            r=p.add_run(str(v));r.font.size=Pt(9);r.bold=ri==0
            if ri==0:tc.append(element('w:shd',**{'w:fill':'F4F6F9'}))
    return t

T1H=['Variant','Change from FULL','Retained information'];T1R=[['FULL','No removal','Ordinal + proxy + alignment; image; neighborhood'],['NOIMAGE','Zero image representation','All losses retained'],['NOHPV','lambda_hpv = 0','Ordinal and proxy targets retained'],['NONEIGH','lambda_neigh = 0','Other losses and image retained'],['NOPROG','lambda_prog = 0','Proxy and alignment retained'],['NOSUP','lambda_prog = lambda_sup = 0','Alignment retained; no explicit targets'],['NOALL','lambda_prog = lambda_sup = lambda_hpv = 0','Reconstruction, image, neighborhood, variance floor']]
T2H=['External analysis','Observed evidence','Claim boundary'];T2R=[['GeoMx, 6 paired patients','Tumor − benign mean −2.218; exact p=0.03125','Paired separation; reversed source-score direction'],['GeoMx, Silva patterns','Nonmonotone core means; 7 patients','No validated ordinal grading or calibration'],['HNSCC, 8 / 6 sections','Mean Moran’s I 0.757 / 0.667','Spatial organization; not disease discrimination'],['HNSCC, HPV status','Sample p=0.200 / 0.133','No convincing status separation in these cohorts'],['TCGA-CESC, 302 patients','11-gene screen; none significant','Gene screen only; not model-level prognosis']]
T3H=['Grade','Criterion (clause C4: mean LODO probe tau-b over seeds)','Interpretation'];T3R=[['Supported','mean τ ≥ 0.35 and ≥ 2/3 seeds p < 0.05','Replicable information in the label-free representation'],['Suggestive','neither supported nor unsupported','Weak or seed-unstable information; continuous estimates govern'],['Unsupported','|mean τ| ≤ 0.15 and 0/3 seeds p < 0.05','Insufficient evidence at this sample size, not absence of biology']]
T4H=['Level (nonresponder fraction f)','Main scale τ̄ (SD)','Sig. runs','Grade','Matched scale τ̄ (SD)','Sig. runs','Grade']
T4R=[['L1 (f = 0)','0.704 (0.009)','9/9','Supported','0.457 (0.000)','9/9','Supported'],['L2 (f = 0.25)','0.276 (0.154)','6/9','Suggestive','0.394 (0.095)','6/9','Supported'],['L3 (f = 0.50)','0.125 (0.122)','1/9','Suggestive','0.286 (0.096)','2/9','Suggestive'],['L4 (f = 0.75)','0.182 (0.104)','3/9','Suggestive','0.177 (0.148)','2/9','Suggestive'],['CTRL (identity-confounded)','−0.030 (0.111)','0/9','—','0.042 (0.102)','0/9','—']]
T4T='Table 2. Operating characteristics of the C4 held-out probe on the dose–response grid. Nine runs per cell (three generator × three training seeds). The CTRL row’s significant-run fraction is the empirical false-positive rate at α=0.05 (pooled 0/18; exact 95% CI 0–18.5%, compatible with the nominal 5%). Binary-label bounds: τ_max = 0.707 (main) and 0.457 (matched); the L1 means attain 99.6% and 100% of the bound.'
T5H=['Cohort (subset)','SpaGCN τ (p)','STAGATE τ (p)','GraphST τ (p)','STAGATE probe τ (p)†','GraphST probe τ (p)†','Reference τ̄ (seeds)']
T5R=[['L1, 90-sample','0.677 (0.0005) *','−0.173 (0.83)','0.491 (0.007) *','−0.045 (0.65)','0.707 (0.0001) *','0.717 (3/3) *'],['L3, 90-sample','0.093 (0.33)','0.173 (0.20)','0.213 (0.14)','−0.026 (0.59)','0.353 (0.0003) *','0.243 (0/3)'],['L4, 90-sample','0.080 (0.36)','−0.465 (0.99)','0.226 (0.14)','−0.005 (0.51)','0.207 (0.035) *','0.155 (0/3)'],['L1, 35-sample','0.291 (0.073)','−0.045 (0.61)','0.425 (0.005) *','0.103 (0.34)','0.457 (0.0001) *','0.425 (3/3) *'],['L3, 35-sample','0.291 (0.073)','−0.381 (0.99)','0.336 (0.050)','0.029 (0.47)','0.339 (0.015) *','−0.201 (0/3)'],['L4, 35-sample','0.291 (0.073)','−0.336 (0.96)','0.336 (0.050)','−0.022 (0.57)','0.339 (0.015) *','−0.194 (0/3)']]
T5T='Table 3. Unified audit of published embedding methods and the reference protocol. Cluster-max columns: single runs on fixed 21-sample subsets (12 + 9; 19 + 2 matched), 2,000 label permutations; subset binary-label bounds τ_max = 0.717 and 0.425. Probe columns (†): the identical LOO ridge probe with refitted permutations (B=10,000) applied to exported pooled embeddings on the full cohorts (90 and 35 samples; bounds 0.707 and 0.457); SpaGCN is excluded because its per-sample spatial domains yield no cross-sample shared continuous representation. Reference column: ridge probe on frozen NOALL embeddings on the same 21-sample subsets, three training seeds (significant seeds at α=0.05). * p < 0.05. Supported grades occur only at L1 for the subset readouts; the unified probe additionally earns supported for GraphST at L3 on the 90-sample cohort (0.353).'

def reftext(k):
    r=REF[k];a='; '.join(r['authors']);return f"{a}. {r['title']}. {r.get('journal','')}. {r.get('year','')};{r.get('volume','')}:{r.get('page','')}. {r['url']}"

def build_main(order):
    text=(O/'Manuscript_BiB.md').read_text(encoding='utf-8-sig')
    def cite(m):
        ks=[k.strip().lstrip('@') for k in m.group(1).split(';')]
        for k in ks:
            if k not in order:order.append(k)
        return '['+', '.join(str(order.index(k)+1) for k in ks)+']'
    text=re.sub(r'\[@([^\]]+)\]',cite,text);text=re.sub(r'(?m)^(#{1,3} [^\n]+)\n(?!\n)',r'\1\n\n',text);d=setup();eq=0
    for b in text.split('\n\n'):
        b=b.strip()
        if not b:continue
        if b=='[[TABLE1]]':table(d,T3H,T3R,[1300,3900,4160],'Table 1. Three-tier grading criteria for clause C4 (representation information).');continue
        if b=='[[TABLE2]]':table(d,T4H,T4R,[2050,1500,850,1150,1500,850,1460],T4T);continue
        if b=='[[TABLE3]]':table(d,T5H,T5R,[1160,1320,1280,1320,1380,1440,1460],T5T);continue
        if b=='[[REFERENCES]]':
            for i,k in enumerate(order,1):
                p=d.add_paragraph(f'[{i}] '+reftext(k));p.paragraph_format.line_spacing=1;p.paragraph_format.space_after=Pt(5)
                for r in p.runs:r.font.size=Pt(9)
            continue
        if b=='[[FIGURES]]':
            for name,cap in CAPTIONS[:4]:
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
    d.save(O/'Manuscript_BiB.docx')
    resolved=text.replace('[[REFERENCES]]','').replace('[[FIGURES]]','\n\n'.join(c for _,c in CAPTIONS[:4]))
    for marker,head,rows in [('[[TABLE1]]',T3H,T3R),('[[TABLE2]]',T4H,T4R),('[[TABLE3]]',T5H,T5R)]:resolved=resolved.replace(marker,' | '.join(head)+'\n'+'\n'.join(' | '.join(r) for r in rows))
    (O/'Manuscript_BiB_resolved.md').write_text(resolved,encoding='utf-8')
    return len(re.findall(r'\b[\w-]+\b',resolved)),eq

def build_supplementary(order):
    text=(O/'Supplementary_BiB.md').read_text(encoding='utf-8-sig')
    def cite(m):
        ks=[k.strip().lstrip('@') for k in m.group(1).split(';')]
        for k in ks:
            if k not in order:order.append(k)
        return '['+', '.join(str(order.index(k)+1) for k in ks)+']'
    text=re.sub(r'\[@([^\]]+)\]',cite,text);text=re.sub(r'(?m)^(#{1,3} [^\n]+)\n(?!\n)',r'\1\n\n',text);d=setup()
    for b in text.split('\n\n'):
        b=b.strip()
        if not b:continue
        if b=='[[STABLE1]]':table(d,T1H,T1R,[1450,2900,5010],'Table S1. Explicit ablation design. Each row contrasts with FULL.');continue
        if b=='[[STABLE2]]':table(d,T2H,T2R,[2350,3200,3810],'Table S2. External evidence and the interpretation it supports.');continue
        if b.startswith('{{FIG:'):
            spec=b[6:-2].strip();name,cap=spec.split('|',1)
            d.add_page_break();p=d.add_paragraph();p.paragraph_format.keep_with_next=True;p.add_run().add_picture(str(F/(name+'.png')),width=Inches(6.45));d.add_paragraph(cap.strip(),style='Caption')
            continue
        if b.startswith('### '):d.add_heading(b[4:],2)
        elif b.startswith('## '):d.add_heading(b[3:],1)
        elif b.startswith('# '):d.add_paragraph(b[2:],style='Title')
        else:d.add_paragraph(b)
    d.save(O/'Supplementary_BiB.docx')
    return len(re.findall(r'\b[\w-]+\b',text))

def write_refs(order):
    refs='\n\n'.join(f'[{i}] '+reftext(k) for i,k in enumerate(order,1));(O/'References_verified.txt').write_text(refs,encoding='utf-8')
    bib=[]
    for k in order:
        r=REF[k];bib.append('@article{'+k+',\n  author = {'+' and '.join(r['authors'])+'},\n  title = {'+r['title']+'},\n  journal = {'+r['journal']+'},\n  year = {'+str(r['year'])+'},\n  doi = {'+r.get('doi','')+'},\n  url = {'+r['url']+'}\n}')
    (O/'References.bib').write_text('\n\n'.join(bib),encoding='utf-8')
    return len(order)

def prescan():
    order=[]
    for f in ['Manuscript_BiB.md','Supplementary_BiB.md']:
        text=(O/f).read_text(encoding='utf-8-sig')
        for m in re.finditer(r'\[@([^\]]+)\]',text):
            for k in m.group(1).split(';'):
                k=k.strip().lstrip('@')
                if k and k not in order:order.append(k)
    return order

if __name__=='__main__':
    figures();order=prescan()
    w,eq=build_main(order);print('MAIN words=%d eqs=%d'%(w,eq))
    sw=build_supplementary(order);print('SUPP words=%d'%sw)
    nr=write_refs(order);print('REFS total=%d'%nr)
