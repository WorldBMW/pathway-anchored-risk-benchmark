from pathlib import Path
p=Path('G:/project4_cervix_multimodal/scripts/csbj_build_package.py');s=p.read_text(encoding='utf-8');start=s.index('def supers(');end=s.index('\ndef setup():',start)
s=s[:start]+'''def sup(a,b):
 x=element('m:sSup');e=element('m:e');e.append(mr(a));v=element('m:sup');v.append(mr(b));x.extend([e,v]);return x

def summ(lo,hi,body):
 x=element('m:nary');pr=element('m:naryPr');pr.append(element('m:chr',**{'m:val':'∑'}));pr.append(element('m:limLoc',**{'m:val':'undOvr'}));x.append(pr)
 for tag,txt in [('m:sub',lo),('m:sup',hi),('m:e',body)]:
  a=element(tag);a.append(mr(txt));x.append(a)
 return x

def fraction(nodes,den):
 x=element('m:f');n=element('m:num');d=element('m:den')
 for a in nodes:n.append(a)
 d.append(mr(den));x.extend([n,d]);return x

EQS=[
 [[sub('s̄','i'),mr(' = '),fraction([summ('j=1','nᵢ','sᵢⱼ')],'nᵢ'),mr(' ,     '),sub('z̄','i'),mr(' = '),fraction([summ('j=1','nᵢ','zᵢⱼ')],'nᵢ')]],
 [[mr('ℒ = '),sub('λ','rec'),sub('ℒ','rec'),mr(' + '),sub('λ','neigh'),sub('ℒ','neigh'),mr(' + '),sub('λ','sup'),mr('('),sub('ℒ','proxy,s'),mr(' + '),sub('ℒ','proxy,z'),mr(')')],[mr('      + '),sub('λ','prog'),sub('ℒ','ordinal'),mr(' + '),sub('λ','hpv'),sub('ℒ','align'),mr(' + 0.1 '),sub('ℒ','var')]],
 [[sub('τ','b'),mr(' = '),frac('C − D','√[(C + D + Tₛ)(C + D + Tᵧ)]')]],
 [[sub('D','ordinal'),mr(' = '),sub('τ̄','FULL'),mr(' − '),sub('τ̄','NOPROG'),mr(' ,     '),sub('D','joint'),mr(' = '),sub('τ̄','FULL'),mr(' − '),sub('τ̄','NOALL')]],
 [[sub('β̂','−i'),mr(' = arg minᵦ { '),summ('ℓ≠i','','(yℓ − z̃ℓ,−ᵢᵀβ)²'),mr(' + ‖β‖₂² }')],[sub('ŷ','i'),mr(' = '),sub('z̃','i,−i'),mr('ᵀ '),sub('β̂','−i')]],
 [[sub('p','refit'),mr(' = '),fraction([mr('1 + '),summ('b=1','B','1{ τ(ŷ[πᵦ], y[πᵦ]) ≥ τ(ŷ, y) }')],'B + 1')]]]
''' +s[end:];p.write_text(s,encoding='utf-8')
