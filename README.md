# pan-african-ehr-omop

Review, cleaning, and OHDSI OMOP CDM standardization of a multi-country
Pan-African EHR medication extract (10,000 rows · 10 countries · 13 unique raw drug strings).

## Source data
`data/raw/pan_african_ehr_10000.csv`
- `patient_id`, `country_code` (AGO CIV EGY ETH KEN MOZ NGA RWA SEN ZAF), `facility_code`
- `raw_med_string` — free text in English, French, Portuguese, Arabic, Amharic, Swahili
- `sync_date` — contains `1970-01-01` Unix-epoch artifacts (= missing date)

## Pipeline
1. **Review & profiling** — pandas / OHDSI White Rabbit scan report
2. **Cleaning** — epoch dates → `NaT`, typo fix (`uknown ARVs`), duplicate key audit
3. **Vocabulary mapping** — Usagi source-to-concept mapping (RxNorm / ATC)
4. **ETL to OMOP CDM v5.4** — `PERSON`, `OBSERVATION_PERIOD`, `CARE_SITE`, `LOCATION`, `DRUG_EXPOSURE`
5. **DQA** — OHDSI DataQualityDashboard + Achilles

## Core mapping dictionary (v0.1)
| raw_med_string | Meaning | Target |
|---|---|---|
| TLD 300/300/50 | Tenofovir/Lamivudine/Dolutegravir | RxNorm combo |
| RHZE phase intensive | Rifampicin/Isoniazid/Pyrazinamide/Ethambutol | RxNorm combo |
| CTX prophylaxis | Cotrimoxazole | RxNorm |
| SP pour CIP | Sulfadoxine/Pyrimethamine | RxNorm |
| Coartem tabs | Artemether/Lumefantrine | RxNorm |
| Artesunato IV | Artesunate injectable | RxNorm |
| paracétamol 500 / حبوب الباراسيتامول 500 | Paracetamol 500 mg | RxNorm (Acetaminophen) |
| amoxicilline 500mg gélule | Amoxicillin 500 mg capsule | RxNorm |
| xarope de tosse / dawa ya kikohozi | Cough medicine | ATC class (R05) |
| የወባ መድሀኒት | "Malaria medicine" (Amharic) | ATC class (P01) |
| uknown ARVs | Unspecified antiretrovirals | ATC class (J05) |

## Rules
- `sync_date == 1970-01-01` → treated as **missing**, never loaded as a real exposure date
- Raw strings always preserved in `drug_source_value` (full traceability)

## License
Apache-2.0
