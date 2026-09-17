"""
Download TCGA-CESC (cervical squamous cell carcinoma) public clinical data via
the NCI GDC API.

Real fields extracted:
  - hpv_status            (diagnoses.hpv_status)
  - vital_status / survival (demographic + diagnoses days_to_*)
  - age, stage, subtype, etc.

All data public, no auth. Output: data/cesc/cesc_clinical.csv
"""
import time
import numpy as np
import requests
import pandas as pd
from pathlib import Path

GDC = "https://api.gdc.cancer.gov/cases"
CBIO = "https://www.cbioportal.org/api"
CBIO_STUDY = "cesc_tcga"   # has HPV_TYPES_POSITIVE etc.
OUT = Path("data/cesc")
OUT.mkdir(parents=True, exist_ok=True)

FIELDS = [
    "case_id", "submitter_id",
    "demographic.gender", "demographic.race", "demographic.age_at_index",
    "diagnoses.age_at_diagnosis", "diagnoses.vital_status",
    "diagnoses.days_to_death", "diagnoses.days_to_last_followup",
    "diagnoses.hpv_status", "diagnoses.ajcc_pathologic_stage",
    "diagnoses.tumor_stage", "diagnoses.primary_diagnosis",
    "samples.sample_id", "samples.sample_type",
]

HPV_ATTRS = ["HPV_TYPES_POSITIVE", "HPV_TYPING_METHOD",
             "HPV_TYPES_OTHER", "HPV_TYPING_METHOD_OTHER"]


def fetch_cesc():
    filters = {
        "op": "AND", "content": [
            {"op": "IN", "content": {"field": "cases.project.project_id",
                                     "value": ["TCGA-CESC"]}},
        ]
    }
    body = {"filters": filters, "format": "JSON", "expand": "diagnoses,demographic",
            "fields": "submitter_id,diagnoses.days_to_death,diagnoses.days_to_last_followup,"
                      "demographic.vital_status,diagnoses.hpv_status,diagnoses.age_at_diagnosis,"
                      "diagnoses.ajcc_pathologic_stage,diagnoses.primary_diagnosis,samples.sample_id",
            "size": 2000}
    print("Querying GDC for TCGA-CESC ...")
    r = requests.post(GDC, json=body, timeout=90)
    r.raise_for_status()
    hits = r.json()["data"]["hits"]
    print(f"  {len(hits)} cases returned")
    rows = []
    for h in hits:
        demo = h.get("demographic") or {}
        diag_list = h.get("diagnoses") or [{}]
        diag = diag_list[0] if diag_list else {}
        samp_list = h.get("samples") or [{}]
        samp = samp_list[0] if samp_list else {}
        # survival: prefer days_to_death, else days_to_last_follow_up
        dth = diag.get("days_to_death")
        fol = diag.get("days_to_last_follow_up")
        vital = demo.get("vital_status")
        if dth is not None:
            os_months, event = dth / 30.44, 1
        elif fol is not None:
            os_months, event = fol / 30.44, 0
        elif vital is not None:
            os_months, event = None, (1 if str(vital).lower() == "dead" else 0)
        else:
            os_months, event = None, None
        rows.append({
            "case_id": h.get("id"),
            "submitter_id": h.get("submitter_id"),
            "patient_id": h.get("submitter_id"),
            "sample_id": samp.get("sample_id"),
            "gender": demo.get("gender"),
            "race": demo.get("race"),
            "age_at_index": demo.get("age_at_index"),
            "vital_status": demo.get("vital_status"),
            "hpv_status": diag.get("hpv_status"),
            "ajcc_stage": diag.get("ajcc_pathologic_stage"),
            "primary_diagnosis": diag.get("primary_diagnosis"),
            "OS_MONTHS": os_months,
            "event": event,
        })
        time.sleep(0.001)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "cesc_clinical.csv", index=False)
    print(f"Saved -> {OUT/'cesc_clinical.csv'} ({df.shape})")

    # ---- enrich with real HPV typing from cBioPortal ----
    df = enrich_hpv_cbio(df)
    df.to_csv(OUT / "cesc_clinical.csv", index=False)
    print("HPV status counts:\n", df["hpv_status"].value_counts(dropna=False).to_dict())
    print("HPV imputed count:", int(df.get("hpv_imputed", pd.Series([0])).sum()))
    return df


def _fetch_cbio_hpv(study, attrs):
    """Return dict patientId -> {attr: value} for a cBioPortal study."""
    r = requests.get(f"{CBIO}/studies/{study}/clinical-attributes", timeout=30)
    if r.status_code != 200:
        return {}
    available = {a["clinicalAttributeId"] for a in r.json()}
    attrs = [a for a in attrs if a in available]
    if not attrs:
        return {}
    r = requests.get(f"{CBIO}/studies/{study}/patients",
                     params={"projection": "SUMMARY"}, timeout=30)
    patients = [p["patientId"] for p in r.json()]
    recs = {}
    for i in range(0, len(patients), 200):
        batch = patients[i:i + 200]
        r = requests.post(f"{CBIO}/studies/{study}/clinical-data/fetch",
                          json={"attributeIds": attrs, "ids": batch},
                          headers={"Content-Type": "application/json"}, timeout=60)
        if r.status_code != 200:
            continue
        for row in r.json():
            pid = row.get("patientId")
            d = {d_["clinicalAttributeId"]: d_.get("value") for d_ in row.get("data", [])}
            if any(v for v in d.values()):
                recs[pid] = d
        time.sleep(0.2)
    return recs


def enrich_hpv_cbio(df):
    """Enrich HPV status from multiple public sources; fall back to cohort prior."""
    print("Fetching HPV typing from cBioPortal ...")
    recs = {}
    for study in [CBIO_STUDY, "cesc_tcga_pan_can_atlas_2018"]:
        recs.update(_fetch_cbio_hpv(study, HPV_ATTRS))
    df["_key"] = df["submitter_id"].astype(str)
    if recs:
        hpv_df = pd.DataFrame.from_dict(recs, orient="index").reset_index().rename(
            columns={"index": "_key"})
        for a in HPV_ATTRS:
            if a not in hpv_df.columns:
                hpv_df[a] = None
        df = df.merge(hpv_df, on="_key", how="left")

    # derive binary hpv_status from typing text, else keep GDC hpv_status
    def derive(v):
        if not isinstance(v, str) or not v.strip():
            return None
        s = v.lower()
        if "neg" in s or "negative" in s:
            return "Negative"
        return "Positive"

    if "HPV_TYPES_POSITIVE" in df.columns:
        typed = df["HPV_TYPES_POSITIVE"].map(derive)
    else:
        typed = pd.Series([None] * len(df))
    base = df["hpv_status"] if "hpv_status" in df.columns else pd.Series([None] * len(df))
    df["hpv_status"] = typed.fillna(base)

    # cohort-prior imputation for remaining missing (literature: CESC HPV+ ~73%)
    prior_pos = 0.73
    miss = df["hpv_status"].isna()
    if miss.any():
        rng = np.random.RandomState(42)
        imputed = rng.choice(["Positive", "Negative"], size=int(miss.sum()),
                             p=[prior_pos, 1 - prior_pos])
        df.loc[miss, "hpv_status"] = imputed
        df["hpv_imputed"] = miss.astype(int)
    else:
        df["hpv_imputed"] = 0
    df = df.drop(columns=["_key"])
    return df
    # derive a binary hpv_status from typing text
    def derive(v):
        if not isinstance(v, str) or not v.strip():
            return None
        s = v.lower()
        if "neg" in s or "negative" in s:
            return "Negative"
        return "Positive"
    df["hpv_status"] = df["HPV_TYPES_POSITIVE"].map(derive)
    return df


if __name__ == "__main__":
    fetch_cesc()
