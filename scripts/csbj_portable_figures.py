from pathlib import Path
import ast
R=Path('G:/project4_cervix_multimodal');O=R/'papers/12_CSBJ_audit_20261010';s=(R/'scripts/csbj_build_package.py').read_text(encoding='utf-8');tree=ast.parse(s)
parts=[ast.get_source_segment(s,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['savefig','figures']]
prefix='''from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image
R=Path(__file__).resolve().parent;E=R/'evidence';F=R/'reproduced_figures';F.mkdir(exist_ok=True)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
P=read(E/'corrected_probe.json');REG=read(E/'real_run_registry.json');N=read(E/'paper_v10_numbers.json');BIO=read(E/'decircularization_biology.json')['variants'];G=read(E/'geomx_patient_final.json')
COL=['#167D9A','#E0A038','#B74F59'];plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
'''
code=prefix+'\n\n'.join(parts).replace("R/f'results/results_SIM_", "E/f'results_SIM_")+"\n\nif __name__=='__main__':figures()\n"
(O/'reproduce_figures.py').write_text(code,encoding='utf-8')
# Source-level publication report is user-facing; no fabricated release metadata.
