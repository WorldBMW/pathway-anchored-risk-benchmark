from pathlib import Path
p=Path('scripts/jbi_final_figures.py');s=p.read_text(encoding='utf-8');s=s.replace("fig.savefig(F/(name+'.pdf'))","fig.savefig(F/(name+'.pdf'),dpi=600)")
insert='''# Figure 2: spot distributions are descriptive; means explicitly separated from medians.
z=np.load(R/'fused_embs_FULL_seed0.npz',allow_pickle=True);ss=z['sample_ids'].astype(str);sc=z['scores'].astype(float)
y=np.array([2 if any(k in a.lower() for k in ['ca_hpv','cancer','carcinoma']) else 1 if any(k in a.lower() for k in ['hsil','cin']) else 0 for a in ss]);groups=[sc[y==i] for i in range(3)]
fig,ax=plt.subplots(figsize=(5.2,3.6));fig.subplots_adjust(left=.16,right=.97,bottom=.20,top=.85)
v=ax.violinplot(groups,showmedians=True,widths=.7)
for pc,c in zip(v['bodies'],['#5798C1','#D29B38','#C44E52']):pc.set_facecolor(c);pc.set_alpha(.7)
v['cmedians'].set_color('black')
for i,g in enumerate(groups):ax.text(i+1,max(g)+.11,f'Mean {g.mean():.2f}',ha='center',fontsize=8)
ax.set_xticks([1,2,3],['Normal\\n31 sections','HSIL\\n1 section','Cancer\\n3 sections']);ax.set(ylabel='Spot-level model score (FULL, seed 0)',ylim=(-.85,2.55));ax.set_title('In-sample distributions by section diagnosis',weight='bold');ax.text(.5,1.01,'Descriptive spot distributions; black lines show medians',transform=ax.transAxes,ha='center',fontsize=7)
save(fig,'Fig2_risk_violin')
# Figure 4: descriptive correlations, with accessible blue/orange colors.
bio=read('downstream_spot_analysis.json')
'''
# Reuse the verified source mapping for program names and aggregate correlations.
orig=(Path('scripts/gen_figures_v10.py')).read_text(encoding='utf-8')
start=orig.index("bio = json.load");end=orig.index('fig, ax = plt.subplots(figsize=(8.8')
pre=orig[start:end]
insert+=pre+'''fig,ax=plt.subplots(figsize=(7.2,3.8));fig.subplots_adjust(left=.35,right=.97,bottom=.17,top=.86)
ax.barh(np.arange(len(labels)),rhos,color=['#28548A' if r>=.2 else '#C77B32' if r<=-.15 else '#999999' for r in rhos]);ax.set_yticks(np.arange(len(labels)),labels);ax.invert_yaxis();ax.axvline(0,c='#555555',lw=.8);ax.set_xlim(-.60,.60)
for i,r in enumerate(rhos):ax.text(r+(.018 if r>=0 else -.018),i,f'{r:+.2f}',va='center',ha='left' if r>=0 else 'right',fontsize=8)
ax.set_xlabel('Spearman ρ (within-section z scores; mean of three seeds)');ax.set_title('Pathway / cell-state correlations with model scores',weight='bold')
save(fig,'Fig4_biology_correlation')
'''
# source names are inspected below; ensure the rho array identifier is correct.
s=s.replace('# Figure 1:',insert+'\n# Figure 1:')
p.write_text(s,encoding='utf-8')
