from pathlib import Path
import sys,re,shutil
from docx import Document
sys.stdout.reconfigure(encoding='utf-8')
P=Path('papers/20_MRP-ST-Repair_Patterns');f=P/'MRP-ST-Repair_manuscript_Patterns_v27.md';t=f.read_text(encoding='utf-8')
needle='## RESULTS'
context='''Earlier examples include slice-versus-subject evaluation in brain MRI,[41] while language-model contamination concerns a different route by which evaluation information can enter training.[8] Previous adversarial studies also show why suppressing a classifier need not erase encoded attributes.[29,30] Spatial-transcriptomic representation learning provides a relevant application context,[19] but the present experiments do not establish patient-level deployment benefit. Fairness outcomes require their own definitions and measurements,[20,37] and versioned public artifacts are required for FAIR reuse.[21]

'''
if context not in t:t=t.replace(needle,context+needle,1)
start=t.index('### Scope condition:');end=t.index('### Cross-domain audit:',start)
t=t[:start]+'''### Scope condition and within-cohort label control

No accepted intervention demonstrated improved downstream prediction. Head-and-neck leave-one-donor-out AUROC fell from 0.906 ± 0.063 at baseline to 0.766–0.813 under the recorded positive doses (Table S9). The cervical baseline AUROC was 0.968, with instability at λ = 2 (0.855 ± 0.107). Prostate baseline AUROC was 0.878 ± 0.044 and dosed values 0.866–0.892; four benign sections do not resolve differences of this size (Table S11). These are measured outcomes rather than evidence that a particular unit count causes benefit or harm. One section per group removes the sibling channel at the section-probe split, but does not rule out source effects, encoder-training leakage or other confounding.

The cervical resolution ladder changes section pooling from K = 1 to K = 3 or 8 blocks without changing the source spot embedding. It uses 35 section identifiers as groups, rather than resolving the main archive's 34 donor groups. At K = 1, Δ = 0 by construction; the baseline is also zero at K = 8, despite repeated units. The all-cell mean Δ is 0.0038 at K = 3 and 0.0024 at K = 8 (Table S16). Repeated units are therefore insufficient for large inflation in this dataset. The increase in LDI across resolutions is partly a change in the unit-permutation scale, not evidence of increased donor-level information.

The GeoMx control uses GSE316098,[42] whose source study reports seven specimens from six patients and 93 ROIs split into 186 epithelial/stromal compartment measurements. The archived case-level grouping has G = 7 and is not demonstrated patient-disjoint. With the feature matrix held fixed, risk, Silva pattern and cell type have baseline κ = 0.225, 0.273 and 0.000, respectively. The corresponding Δ values are +0.3736, +0.3955 and +0.0075, and τ_LOO/σ̂ is 9.34, 10.39 and 8.49 (Table S17). Identity lift is 6.55× at baseline for all three label arms. Mean retained τ_LGO under dosing is 0.806, 0.717 and 0.989, respectively. None of the twelve dosed cells per arm passes the archived unit-level dual gate. This is a descriptive matched-feature contrast; changing labels also changes the task and signal structure, and does not isolate coupling as the only cause.

'''+t[end:]
# Keep the quantitative table while removing repeated overstatements about external validation.
start=t.index('### Cross-domain audit:');table=t.index('**Table 5.',start)
t=t[:start]+'''### Cross-domain audit of two non-biological datasets

These are exploratory audits of archived representations, not complete external validation of a repair pipeline. HAR[23] comprises 10,299 windows from 30 subjects; gas drift[24] comprises 13,910 measurements from ten batches. The runner uses an MLP autoencoder with a group adversary and samples 299 HAR units and 300 gas units, preserving approximate observed group-by-label proportions. Each dataset has three training seeds and five doses. Neither carries planted control calibration or evidence of downstream benefit. The six other domain mappings in Table 4 remain untested.

At baseline, group-label κ is 0.0025 in HAR and 0.0511 in gas drift. Direct identity lift is 10.0× and 9.2× chance, while Δ is +0.0061 and +0.0494 (Table 5). Across the fifteen recorded cells per dataset, Δ ranges from +0.0010 to +0.0095 and from +0.0209 to +0.0697. This is an observed ordering, not a causal identification of coupling: data distributions, tasks, nominal-label coding and group counts differ. Seeds and doses are dependent analyses of the same datasets and do not create independent population replication.

The archived LDI uses τ_LOO and a unit-label permutation reference. Baseline τ_LOO/σ̂ is 13.8 and 11.0. No dosed cell passes the archived dual gate, which uses τ_LOO for both dependence and retention. This is consistent with the fixed-scale compatibility calculation; it does not establish impossibility of a useful repair under independent utility and identity metrics. Group-level association is reported separately and retains at least 0.98 and 0.89 of baseline. Direct identity lift decreases to 5.4× and 7.2× chance at its best recorded dose, so suppression remains partial. The in-sample versus unit-holdout gap decreases by 81% and 56% at the best dose, illustrating that these metrics need not move together.

The gas-drift result does not replicate the simulation group-count boundary: substantial retention occurs with ten groups, below the simulation placement at 16–32. No external phase grid was run. Nominal activity and gas identifiers also have no intrinsic ordinal scale; class-aware metrics, recoding sensitivity and valid group-preserving permutation are required before task-level inferential claims.

'''+t[table:]
t=t.replace('**Table 1. Proposition 1 predicts acceptance feasibility, and the prediction is made before any dose is\nchosen.**','**Table 1. Baseline fixed-scale compatibility of the recorded association gates.**')
t=t.replace('This negative result sets the design space for everything that follows and is the first of the two reasons our framework is auditable rather than merely corrective: the acceptance instrument must be able to see the difference between "the leak is gone" and "everything is gone", and it can only do so if the repair is shaped during training.', 'This negative result is specific to the tested projection and representations. It motivates separate retained-signal measurements; it does not rule out every post-hoc intervention or establish that retraining is necessary in general.')
f.write_text(t,encoding='utf-8')
# Reuse deterministic builder; this command does not repeat earlier manuscript rewrites.
exec(Path('scripts/_polish_patterns_v27.py').read_text(encoding='utf-8'))
tp=P/'TitlePage_Patterns.md';s=tp.read_text(encoding='utf-8');s+='\n**Graphical abstract file:** figures/graphical_abstract_v27.tif (1200 × 1200 pixels). Older graphical abstracts are superseded for this review version.\n';tp.write_text(s,encoding='utf-8')
from _md2docx import convert
convert(str(tp),str(P/'TitlePage_Patterns.docx'))
print('Completed scope edits and synchronized title page')
