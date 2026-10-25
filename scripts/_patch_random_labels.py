"""Patch probe_lodo.py: add random-label mode for cervical cohort control experiment."""
import re

with open('scripts/probe_lodo.py') as f:
    s = f.read()

# Add the random label mapping at module level (after imports, before severity_of)
mapping_code = '''
# --- RANDOM-LABEL CONTROL EXPERIMENT (seed=42) ---
# Same label distribution as real cervical cohort (0:31, 1:1, 2:3) but shuffled
# across samples, breaking label-identity coupling.
_CERVICAL_RANDOM_LABELS = {
    "CA_HPV_1": 0, "CA_HPV_2": 0, "HSIL_HPV": 0, "N_HPV": 0,
    "CERVICAL_CANCER_1": 0,
    "ECTO_P001": 0, "ECTO_P004": 0, "ECTO_P007": 0, "ECTO_P008": 0, "ECTO_P014": 0,
    "ECTO_P016": 0, "ECTO_P018": 0, "ECTO_P020": 0, "ECTO_P021": 0, "ECTO_P023": 0,
    "ECTO_P024": 0, "ECTO_P026": 0, "ECTO_P028": 0, "ECTO_P031": 0, "ECTO_P044": 2,
    "ECTO_P045": 0, "ECTO_P047": 0, "ECTO_P050": 0, "ECTO_P057": 1, "ECTO_P067": 0,
    "ECTO_P080": 0, "ECTO_P081": 0, "ECTO_P087": 0, "ECTO_P097": 0, "ECTO_P105": 2,
    "ECTO_P107": 0, "ECTO_P108": 0, "ECTO_P114": 0, "ECTO_P117": 2, "ECTO_P118": 0,
}
'''

# Insert mapping right before 'def severity_of'
s = s.replace('def severity_of(sample_name: str):', mapping_code + '\ndef severity_of(sample_name: str):', 1)

# Add random-label check at the start of severity_of body
old_body = '''def severity_of(sample_name: str):
    n = str(sample_name).upper()'''
new_body = '''def severity_of(sample_name: str):
    n = str(sample_name).upper()
    # Random-label control: use shuffled labels for cervical cohort
    if n in _CERVICAL_RANDOM_LABELS:
        return _CERVICAL_RANDOM_LABELS[n]'''
s = s.replace(old_body, new_body, 1)

with open('scripts/probe_lodo.py', 'w') as f:
    f.write(s)
print('patched probe_lodo.py with random-label mode')
