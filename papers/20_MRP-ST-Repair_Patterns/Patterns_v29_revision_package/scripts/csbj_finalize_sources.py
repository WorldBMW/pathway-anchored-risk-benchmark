from pathlib import Path
import json
R=Path('G:/project4_cervix_multimodal');O=R/'papers/12_CSBJ_audit_20261010'
p=O/'Manuscript_CSBJ.md';s=p.read_text(encoding='utf-8');s=s.replace('Nominal panel size differs from observed coverage: FULL seed 0 reports 92 prior genes.','Nominal panel size is distinguished from its observed expression intersection; the legacy n_prior_genes field counts the downstream marker union and is not HPV-panel coverage.');s=s.replace('Training repetitions reuse a generated cohort and do not estimate variation across independently simulated datasets.','Training repetitions reuse a generated cohort and do not estimate variation across independently simulated datasets. Simulation labels are binary (0/2); the matched setting matches sample count and disease prevalence, not the three-level annotation distribution of the cervical cohort.');s=s.replace('with zero observed seed variation in this rank statistic','with zero observed seed variation in this rank statistic (ties in binary labels limit the attainable tau-b for continuously ordered predictions)');p.write_text(s,encoding='utf-8')
p=R/'scripts/csbj_build_package.py';s=p.read_text(encoding='utf-8');start=s.index('EQS=[');end=s.index('\ndef setup():',start)
new='''def supers(a,b):
 x=element('m:sSup');e=element('m:e');e.append(mr(a));v=element('m:sup');v.append(mr(b));x.extend([e,v]);return x
EQS=[
 [[sub('s̄','i'),mr(' = '),frac('Σⱼ sᵢⱼ','nᵢ'),mr(' ,     '),sub('z̄','i'),mr(' = '),frac('Σⱼ zᵢⱼ','nᵢ')]],
 [[mr('ℒ = '),sub('λ','rec'),sub('ℒ','rec'),mr(' + '),sub('λ','neigh'),sub('ℒ','neigh'),mr(' + '),sub('λ','sup'),mr('('),sub('ℒ','proxy,s'),mr(' + '),sub('ℒ','proxy,z'),mr(')')],[mr('      + '),sub('λ','prog'),sub('ℒ','ordinal'),mr(' + '),sub('λ','hpv'),sub('ℒ','align'),mr(' + 0.1 '),sub('ℒ','var')]],
 [[sub('τ','b'),mr(' = '),frac('C − D','√[(C + D + Tₛ)(C + D + Tᵧ)]')]],
 [[sub('D','ordinal'),mr(' = '),sub('τ̄','FULL'),mr(' − '),sub('τ̄','NOPROG'),mr(' ,     '),sub('D','joint'),mr(' = '),sub('τ̄','FULL'),mr(' − '),sub('τ̄','NOALL')]],
 [[sub('β̂','−i'),mr(' = arg minᵦ { Σℓ≠ᵢ (yℓ − z̃ℓ,−ᵢᵀβ)² + ‖β‖₂² }')],[sub('ŷ','i'),mr(' = '),sub('z̃','i,−i'),mr('ᵀ '),sub('β̂','−i')]],
 [[sub('p','refit'),mr(' = '),frac('1 + Σᵇ₌₁ᴮ 1{ τ(ŷ[πᵦ], y[πᵦ]) ≥ τ(ŷ, y) }','B + 1')]]]
'''
s=s[:start]+new+s[end:];p.write_text(s,encoding='utf-8')
p=O/'evidence/references_verified.json';r=json.loads(p.read_text(encoding='utf-8'));r['whalen']['year']=2022;r['kegg']['year']=2025;r['moran']['page']='17–23';p.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8')
