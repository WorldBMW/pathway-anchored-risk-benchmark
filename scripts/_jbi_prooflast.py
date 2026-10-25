from pathlib import Path
p=Path('scripts/jbi_submission_build.py');s=p.read_text(encoding='utf-8')
s=s.replace("settext(p,p.text+f' (Figure {number}).')","settext(p,p.text.rstrip('.')+(f' (Figure\\u00a0{number}; Table\\u00a02).' if number==3 else f' (Figure\\u00a0{number}).'))")
s=s.replace("for a,b in [('Z. Wang", "for a,b in [('; the axis is not a proliferation surrogate',''),('；说明该轴不是增殖替代指标',''),('at disease n=4','with four diseased sections'),('Z. Wang")
p.write_text(s,encoding='utf-8')
