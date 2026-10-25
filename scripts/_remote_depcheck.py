import importlib, sys
mods = ["SpaGCN", "STAGATE", "stgatenmf", "GraphST", "scanpy", "harmonypy",
        "torch_geometric", "anndata", "sklearn", "torch"]
print("python:", sys.version.split()[0])
for m in mods:
    try:
        mod = importlib.import_module(m)
        v = getattr(mod, "__version__", None)
        print(f"{m:18s} OK  {v}")
    except Exception as e:
        print(f"{m:18s} MISSING ({type(e).__name__})")