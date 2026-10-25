import os, time
d = "data/st_visium/geo_prostate_GSE278936"
def total():
    s = 0
    for r, _, fs in os.walk(d):
        for f in fs:
            try:
                s += os.path.getsize(os.path.join(r, f))
            except OSError:
                pass
    return s
b = total()
time.sleep(30)
a = total()
sp = round((a - b) / 1024 / 1024 / 30, 3)
print("speed:", sp, "MB/s, total:", round(a / 1024 / 1024 / 1024, 3), "GB")
