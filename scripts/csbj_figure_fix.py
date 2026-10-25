from pathlib import Path
p=Path('G:/project4_cervix_multimodal/scripts/csbj_build_package.py');s=p.read_text(encoding='utf-8');s=s.replace('Expression, morphology, coordinates\\nSample grouping and target sources','Expression + morphology\\nCoordinates and sample groups\\nTarget sources and provenance');p.write_text(s,encoding='utf-8')
