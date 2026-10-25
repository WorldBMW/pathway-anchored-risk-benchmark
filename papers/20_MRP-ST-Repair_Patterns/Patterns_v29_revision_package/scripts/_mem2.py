import numpy as np, time, os


def rss_mib():
    with open("/proc/self/statm") as f:
        return int(f.read().split()[1]) * 4096 / 2**20


hold = []
for i in range(1, 30):
    a = np.ones((200, 1024, 256), dtype=np.float32)  # 200 MiB, written -> resident
    hold.append(a)
    tot = sum(x.nbytes for x in hold) / 2**20
    print(f"chunk {i:2d}: held {tot:6.0f} MiB  RSS {rss_mib():7.0f} MiB", flush=True)
    time.sleep(1)
print("SURVIVED_TO", sum(x.nbytes for x in hold) / 2**20, flush=True)
