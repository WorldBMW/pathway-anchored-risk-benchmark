from pathlib import Path
p=Path('scripts/jbi_final_figures.py');s=p.read_text(encoding='utf-8').replace("NUM['biology'] = bio_mean","# aggregate for the plotted marker sets").replace("key=lambda s: bio_mean[s]['rho'])","key=lambda s: bio_mean[s]['rho'], reverse=True)").replace("'In-sample distributions by section diagnosis',weight='bold'","'In-sample distributions by section diagnosis',weight='bold',pad=20")
p.write_text(s,encoding='utf-8')
p=Path('scripts/jbi_submission_build.py');s=p.read_text(encoding='utf-8').replace(" figures()\n src="," figures()\n run_source('jbi_final_figures.py')\n src=").replace("rep(doc,'标志物有效性在独立宫颈scRNA-seq'","rep(doc,'标志物有效性','标记集一致性');rep(doc,'标志物有效性在独立宫颈scRNA-seq'")
# Keep normal body figure callouts explicit.
s=s.replace(" for p in doc.paragraphs:\n  if p.style.name=='Caption':"," for p in doc.paragraphs:\n  if name=='Manuscript_JBI.docx':\n   for prefix,number in [('Mean per-spot risk rises',2),('Removing ordinal supervision reduced',3),('High-risk spots are enriched',4),('GeoMx: group separation',5)]:\n    if p.text.startswith(prefix) and f'(Figure {number})' not in p.text:settext(p,p.text+f' (Figure {number}).')\n  if p.style.name=='Caption':")
p.write_text(s,encoding='utf-8')
