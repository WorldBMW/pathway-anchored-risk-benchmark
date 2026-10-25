from pathlib import Path
p=Path('scripts/jbi_submission_build.py')
s=p.read_text(encoding='utf-8-sig')
s=s.replace('reported TCGA-CESC Cox analyses','univariate gene-level TCGA-CESC Cox analyses').replace('TCGA-CESC Cox分析','TCGA-CESC单基因单变量Cox分析')
s=s.replace(" doc.save(P/name)",""" for a,b in [('Z. Wang, W. Yang, et al., ST-Align','Z. Wang, R. Yu, ST-Align'),('arXiv:2411.16793. https://iclr.cc/virtual/2026/10014521.','https://openreview.net/forum?id=EWzPy228cM.'),('Commun. Biol. 9 (2025) 46','Commun. Biol. 9 (2026) 46'),('187–220','187–202'),('Marker validity was confirmed in independent cervical scRNA-seq','Marker-set coherence was assessed in independent cervical scRNA-seq'),('mean within-lineage score correlation','mean within-marker-set gene correlation'),('across lineages (gap','between marker sets (gap')]:rep(doc,a,b)
 doc.save(P/name)""")
p.write_text(s,encoding='utf-8')
