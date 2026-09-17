from pathlib import Path
d = Path('g:/project4_cervix_multimodal/data/st_visium/geo_cesc')
for s in ['N_HPV', 'HSIL_HPV', 'CA_HPV_1', 'CA_HPV_2']:
    sd = d / s
    print(s)
    for f in ['filtered_feature_bc_matrix.h5', 'spatial/tissue_hires_image.png',
              'spatial/tissue_positions_list.csv', 'spatial/scalefactors_json.json']:
        p = sd / f
        if p.exists():
            print('   ', f, 'OK', round(p.stat().st_size/1e6, 2), 'MB')
        else:
            print('   ', f, 'MISSING')
