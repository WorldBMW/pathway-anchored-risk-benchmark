from pathlib import Path
from docx import Document
P=Path('papers/20_MRP-ST-Repair_Patterns')
f=P/'Supplemental_Information_Patterns_v29.docx';d=Document(f)
for p in d.paragraphs:
 if p.text.startswith('Table S18.'):
  p.text='Table S18. Unrestricted versus within-group label-permutation sensitivity on the reanalysis subset. Both schemes use B = 2,000 refits of the same unit-holdout ridge probe. The restricted scheme shuffles labels within recorded groups, not whole independent groups, and preserves group-by-label counts. The archived LDI_group divides tau_LOO minus 0.001 by sigma_group; it is not centered on the restricted-null mean. Empirical p_group addresses the conditional randomization scheme only when within-group exchangeability is defensible. Group-constant labels make that scheme degenerate; this does not establish impossibility of other group-level inference. Identity summaries use the separate archived nearest-neighbour ratio and distance AUROC, not the classifier lift in Figure 5. Source: results/regate_v28.json and scripts/exp_regate_v28.py.'
 if p.text.startswith('Table S19. Nominal multiclass'):
  p.text='Table S19. Nominal multiclass readouts, recoding sensitivity and the archived encoder-refit comparison. Panels A–C contain one-versus-rest recorded-group holdout probes and R = 20 class-code recodings. Panel D is the original v28 HAR experiment: the encoder and probe were refitted by subject, but clipping and input standardization were fitted globally before the folds. Its reported tau is the mean of within-subject fold correlations, not pooled out-of-fold tau. The fold SD is not an equivalence bound. The corrected train-only preprocessing analysis with both estimands is reported separately below. Original sources: results/regate_v28.json and results/outer_refit_v28.json.'
 if p.text.startswith('Table S19, panel D.'):
  p.text='Table S19, panel D. Archived v28 encoder-refit comparison with global input preprocessing and mean-within-fold tau; retain as historical results, not fully nested validation.'
 if p.text=='Corrected HAR outer-refit check':p.paragraph_format.page_break_before=True
d.save(f)
print('Corrected supplemental captions and kept corrected HAR table together')
