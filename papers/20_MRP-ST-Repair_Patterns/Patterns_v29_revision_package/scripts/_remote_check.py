import json, glob, os, re
root = "/root/autodl-tmp/project/project4_cervix_multimodal"
os.chdir(root)
js = sorted(glob.glob("results/results_SIM_group_[AC]_g*.json"))
print("n_json:", len(js))
pat = re.compile(r'"(?:n_perm|permutation_n|n_permutations)"\s*:\s*(\d+)')
for f in js:
    raw = open(f).read()
    m = pat.search(raw)
    perms = [p for p in re.findall(r'perm[a-z_]*"\s*:\s*(\d+)', raw)[:3]]
    print(os.path.basename(f), "| PERM=", (m.group(1) if m else "?"), "| extra_perm_vals=", perms)
# also report high-level keys of one file to understand schema
if js:
    d = json.load(open(js[0]))
    print("\n--- top-level keys of sample file ---")
    print(list(d.keys()))