"""Pan-African EHR -> OMOP CDM | Phase 1: review & cleaning.

Run from repo root:  python src/clean_data.py
"""
from pathlib import Path
import pandas as pd

BASE      = Path(__file__).resolve().parents[1]
RAW       = BASE / "data" / "raw" / "pan_african_ehr_10000.csv"
PROCESSED = BASE / "data" / "processed"
MAPPINGS  = BASE / "mappings"
EPOCH     = pd.Timestamp("1970-01-01")

# raw (lowercased) -> (canonical name, class, indication)
# Canonical names are what you'll search in Athena/Usagi in Phase 2.
DRUG_DICT = {
    "artesunato iv":             ("Artesunate (injectable)",                  "Antimalarial",   "Severe malaria"),
    "coartem tabs":              ("Artemether / Lumefantrine",                "Antimalarial",   "Uncomplicated malaria"),
    "sp pour cip":               ("Sulfadoxine / Pyrimethamine",              "Antimalarial",   "Malaria IPTp"),
    "የወባ መድሀኒት":               ("Antimalarial (unspecified)",               "Antimalarial",   "Malaria"),
    "rhze phase intensive":      ("Rifampicin/Isoniazid/Pyrazinamide/Ethambutol", "Anti-TB",     "TB intensive phase"),
    "tld 300/300/50":            ("Tenofovir / Lamivudine / Dolutegravir",    "Antiretroviral", "HIV first-line"),
    "ctx prophylaxis":           ("Trimethoprim / Sulfamethoxazole",          "Antibiotic",     "OI prophylaxis"),
    "unknown arvs":              ("Antiretrovirals (unspecified)",            "Antiretroviral", "HIV"),
    "amoxicilline 500mg gélule": ("Amoxicillin 500 MG Oral Capsule",          "Antibiotic",     "Bacterial infection"),
    "paracétamol 500":           ("Acetaminophen 500 MG Oral Tablet",         "Analgesic",      "Pain / fever"),
    "حبوب الباراسيتامول 500":    ("Acetaminophen 500 MG Oral Tablet",         "Analgesic",      "Pain / fever"),
    "xarope de tosse":           ("Cough preparation (unspecified)",          "Symptomatic",    "Cough"),
    "dawa ya kikohozi":          ("Cough preparation (unspecified)",          "Symptomatic",    "Cough"),
}

def detect_language(text: str) -> str:
    if any("\u0600" <= c <= "\u06ff" for c in text): return "ar"
    if any("\u1200" <= c <= "\u137f" for c in text): return "am"
    if any(w in text for w in ("gélule", "paracétamol", "pour")): return "fr"
    if any(w in text for w in ("xarope", "artesunato", "tosse")): return "pt"
    if any(w in text for w in ("dawa", "kikohozi")): return "sw"
    return "en"

def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    MAPPINGS.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(RAW, dtype=str)
    df["patient_id"] = df["patient_id"].astype(int)

    # 1. Dates: 1970-01-01 = Unix epoch = MISSING, not a real visit date
    df["sync_date"] = pd.to_datetime(df["sync_date"], errors="coerce")
    df["is_date_missing"] = df["sync_date"] == EPOCH
    df.loc[df["is_date_missing"], "sync_date"] = pd.NaT

    # 2. Strings: trim + fix known typo
    df["raw_med_string"] = (df["raw_med_string"].str.strip()
                            .str.replace("uknown", "unknown", regex=False))

    # 3. Language + canonical drug
    df["language"] = df["raw_med_string"].map(detect_language)
    canon = df["raw_med_string"].str.lower().map(DRUG_DICT)
    df["canonical_name"] = canon.map(lambda t: t[0] if t else "UNMAPPED")
    df["drug_class"]     = canon.map(lambda t: t[1] if t else "UNMAPPED")
    df["indication"]     = canon.map(lambda t: t[2] if t else "UNMAPPED")

    # 4. Keys: patient_id is NOT globally unique (same id appears in several
    #    countries) -> composite source keys for OMOP PERSON / CARE_SITE
    df["person_source_key"]    = df["country_code"] + "-" + df["patient_id"].astype(str)
    df["care_site_source_key"] = df["country_code"] + "-" + df["facility_code"]

    # 5. Outputs
    df.to_csv(PROCESSED / "cleaned_exposures.csv", index=False)
    usagi = (df.groupby(["raw_med_string", "canonical_name", "drug_class", "language"])
               .size().reset_index(name="frequency")
               .sort_values("frequency", ascending=False))
    usagi.to_csv(MAPPINGS / "usagi_input.csv", index=False)

    # 6. Review report
    dup = df.groupby("patient_id")["country_code"].nunique()
    print("=== REVIEW SUMMARY ===")
    print(f"rows                     : {len(df):,}")
    print(f"countries / facilities   : {df['country_code'].nunique()} / {df['care_site_source_key'].nunique()}")
    print(f"person_source_keys       : {df['person_source_key'].nunique():,}")
    print(f"patient_id in >1 country : {int((dup > 1).sum()):,}")
    print(f"missing sync_date (epoch): {int(df['is_date_missing'].sum()):,} ({df['is_date_missing'].mean():.1%})")
    print(f"unique raw strings       : {df['raw_med_string'].nunique()}")
    print(f"unmapped rows            : {int((df['canonical_name'] == 'UNMAPPED').sum())}")
    print("\nDrug distribution:")
    print(df["canonical_name"].value_counts().to_string())

if __name__ == "__main__":
    main()
