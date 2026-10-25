import sys,json
from pathlib import Path
import numpy,scipy,sklearn,torch,pandas
d={'python':sys.version,'numpy':numpy.__version__,'scipy':scipy.__version__,'scikit-learn':sklearn.__version__,'torch':torch.__version__,'pandas':pandas.__version__}
Path('results/runtime_versions_v29.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
print(json.dumps(d,indent=2))
