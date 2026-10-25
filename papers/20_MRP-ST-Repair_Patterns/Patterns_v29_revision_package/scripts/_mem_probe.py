import numpy as np, os
for mb in (256, 512, 768, 1024, 1280, 1536, 1792):
    try:
        a = np.zeros((mb, 1024, 256), dtype=np.float32)  # mb * 1 MiB
        print(f"ok {mb} MiB  nbytes={a.nbytes/2**20:.0f} MiB", flush=True)
        del a
    except MemoryError as e:
        print(f"MemoryError at {mb} MiB: {e}", flush=True)
        break
