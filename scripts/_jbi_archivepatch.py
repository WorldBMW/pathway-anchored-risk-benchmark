from pathlib import Path
p=Path('scripts/jbi_source_archive.py');s=p.read_text(encoding='utf-8-sig').replace("names=['external_corrected_numbers.json'","names=['paper_v10_numbers.json','rank_perm_B10000.json','external_corrected_numbers.json'")
s=s.replace("An older conflicting external_corrected_numbers_FINAL.json is not used.","paper_v10_numbers.json and rank_perm_B10000.json are LEGACY inputs used only to diagnose discrepancies and reproduce the reaudit script; use jbi_submission_audit/numbers.json and rank_perm_recomputed.json for the revised manuscript. An older conflicting external_corrected_numbers_FINAL.json is not used.")
p.write_text(s,encoding='utf-8')
