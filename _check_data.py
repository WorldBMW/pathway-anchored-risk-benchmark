import os
root = "data/st_visium"
print("=== data/st_visium 当前内容 ===")
for d in sorted(os.listdir(root)):
    p = os.path.join(root, d)
    if os.path.isdir(p):
        sz = 0
        for dp, dn, fn in os.walk(p):
            for f in fn:
                sz += os.path.getsize(os.path.join(dp, f))
        print("  %-28s dir  %8.1f MB" % (d, sz / 1e6))
    else:
        print("  %-28s file %8.1f MB" % (d, os.path.getsize(p) / 1e6))
