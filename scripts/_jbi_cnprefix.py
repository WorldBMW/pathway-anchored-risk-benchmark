from pathlib import Path
p=Path('scripts/jbi_submission_build.py');s=p.read_text(encoding='utf-8');s=s.replace(" found=[p for p in doc.paragraphs if p.text.startswith(prefix)]"," found=[p for p in doc.paragraphs if p.text.startswith(prefix)]\n if not found and prefix.startswith('图 '):found=[p for p in doc.paragraphs if p.text.startswith(prefix.replace(' ',''))]")
p.write_text(s,encoding='utf-8')
