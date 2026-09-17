import sys
import download_fm_weights as d

repo = sys.argv[1] if len(sys.argv) > 1 else "MahmoodLab/UNI"
short = "UNI2" if "UNI2" in repo else "UNI"
out = d.OUT / short / f"{short}-pytorch_model.bin"
d.download(d.BASE.format(repo=repo), out)
print("DONE", out)
