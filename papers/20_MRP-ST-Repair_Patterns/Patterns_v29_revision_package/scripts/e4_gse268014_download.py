"""E4 staging downloader: GSE268014, 16 balanced patients (8 HPV+ / 8 HPV-).
Downloads only expression+coords files (skips images)."""
import urllib.request, re, os, time

HPV_POS = ['GSM8283898', 'GSM8283899', 'GSM8283900', 'GSM8283901',
           'GSM8283905', 'GSM8283906', 'GSM8283909', 'GSM8283913']
HPV_NEG = ['GSM8283897', 'GSM8283902', 'GSM8283903', 'GSM8283904',
           'GSM8283907', 'GSM8283908', 'GSM8283910', 'GSM8283911']
PATIENT = {'GSM8283897': 'P5909', 'GSM8283898': 'P5903', 'GSM8283899': 'P5767',
           'GSM8283900': 'P5766', 'GSM8283901': 'P5764', 'GSM8283902': 'P5756',
           'GSM8283903': 'P5751', 'GSM8283904': 'P5736', 'GSM8283905': 'P5735',
           'GSM8283906': 'P5710', 'GSM8283907': 'P5709', 'GSM8283908': 'P5707',
           'GSM8283909': 'P5692', 'GSM8283910': 'P5684', 'GSM8283911': 'P5666',
           'GSM8283913': 'P5636'}
WANT = ['matrix.mtx.gz', 'barcodes.tsv.gz', 'features.tsv.gz',
        'tissue_positions_list.csv.gz', 'scalefactors_json.json.gz',
        'tissue_hires_image.png.gz', 'tissue_hires_image.png']

OUT = r'g:\project4_cervix_multimodal\data\e4_hnscc2_staging'
total = 0
t0 = time.time()
for gsm in HPV_POS + HPV_NEG:
    d = os.path.join(OUT, f'{gsm}_{PATIENT[gsm]}')
    os.makedirs(d, exist_ok=True)
    sub = 'GSM8283nnn' if gsm.startswith('GSM8283') else 'GSM8348nnn'
    base = f'https://ftp.ncbi.nlm.nih.gov/geo/samples/{sub}/{gsm}/suppl/'
    html = urllib.request.urlopen(base).read().decode('utf-8', 'replace')
    files = [f for f in re.findall(r'href="([^"]+)"', html) if any(f.endswith(w) for w in WANT)]
    for f in files:
        dest = os.path.join(d, f)
        if os.path.exists(dest):
            continue
        urllib.request.urlretrieve(base + f, dest)
        total += os.path.getsize(dest)
    print(f'{gsm}_{PATIENT[gsm]}: {len(files)} files, cum {total/1e6:.0f} MB, {time.time()-t0:.0f}s', flush=True)
print(f'DONE total {total/1e6:.0f} MB in {time.time()-t0:.0f}s')
