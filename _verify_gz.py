import gzip
from pathlib import Path

d = Path('g:/project4_cervix_multimodal/data/st_visium/geo_cesc')
for s in ['N_HPV', 'HSIL_HPV', 'CA_HPV_1', 'CA_HPV_2']:
    sd = d / s
    for f in sorted(sd.glob('*.gz')):
        # test full decompression
        try:
            n = 0
            with gzip.open(f, 'rb') as g:
                while True:
                    chunk = g.read(1024 * 256)
                    if not chunk:
                        break
                    n += len(chunk)
            print('OK  ', s, f.name, round(n/1e6, 2), 'MB decompressed')
        except Exception as e:
            print('BAD ', s, f.name, type(e).__name__, str(e)[:80])
