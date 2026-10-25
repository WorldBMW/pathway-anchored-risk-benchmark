from pathlib import Path
p=Path('scripts/jbi_final_figures.py');s=p.read_text(encoding='utf-8-sig').replace('pad=20,pad=20','pad=20');p.write_text(s,encoding='utf-8')
exec(compile(s[:s.index('# Figure 1:')],str(p),'exec'),{'__file__':str(p.resolve())})
import sys;sys.path.insert(0,str(Path.cwd()))
import scripts.jbi_submission_build as b
b.figures=lambda:None
b.main()
