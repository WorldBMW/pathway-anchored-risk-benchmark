from pathlib import Path
p=Path('G:/project4_cervix_multimodal/scripts/csbj_build_package.py');s=p.read_text(encoding='utf-8');s=s.replace("text=re.sub(r'\\[@([^\\]]+)\\]',cite,text);d=setup();eq=0", "text=re.sub(r'\\[@([^\\]]+)\\]',cite,text);text=re.sub(r'(?m)^(#{1,3} [^\\n]+)\\n(?!\\n)',r'\\1\\n\\n',text);d=setup();eq=0")
p.write_text(s,encoding='utf-8')
