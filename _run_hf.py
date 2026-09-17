import sys
from huggingface_hub import hf_hub_download

repo = sys.argv[1] if len(sys.argv) > 1 else "MahmoodLab/UNI"
short = "UNI2" if "UNI2" in repo else "UNI"
local = f"fm_cache/{short}/{short}-pytorch_model.bin"
p = hf_hub_download(
    repo_id=repo,
    filename="pytorch_model.bin",
    local_dir="fm_cache/_hf",
    local_dir_use_symlinks=False,
)
print("DOWNLOADED", p)
# move/rename into the clean path
import shutil, os
os.makedirs(f"fm_cache/{short}", exist_ok=True)
shutil.move(p, local)
print("MOVED ->", local, os.path.getsize(local), "bytes")
