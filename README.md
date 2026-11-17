# Bridge Deterioration Forecast

**Which Georgia bridges in Fair condition are most likely to fall to Poor within the next five years?**

This project predicts when highway bridges will decline, using 34 years of
federal inspection records. It is built the way a production data science
project would be: an automated data pipeline, tested data, models that are
compared against a simple baseline, scheduled retraining, and a map of the
results that anyone can open.

> \*\*Status:\*\* In progress (December 2026 – March 2027). Month 1, the data
> pipeline, is underway. Results below will be filled in as each phase finishes.

\---

## Why this matters

Georgia has about 15,000 public highway bridges. Every one is inspected,
usually every two years, and rated on a 0–9 scale. Most are in Good or Fair
condition, but inspection and repair budgets are limited, so agencies have to
decide where to look first.

A bridge that slips from **Fair** to **Poor** usually needs costly repairs,
weight limits, or replacement. Catching that decline early, while a bridge is
still Fair, gives an agency time to plan cheaper preventive work.

This project asks a practical question a state Department of Transportation
could act on: **if Georgia could take a closer look at only 10% of its Fair
bridges next year, which ones should it choose?**

The same problem, predicting when an asset will need major work, shows up
anywhere organizations maintain physical equipment: vehicle fleets, water
pipes, power lines, and buildings.

## The data

The [National Bridge Inventory (NBI)](https://www.fhwa.dot.gov/bridge/nbi/ascii.cfm)
from the Federal Highway Administration is free and public. It has one file
per year from 1992 to 2025, covering every public highway bridge in the
country. Each record includes:

* **Condition ratings** for the deck, superstructure (the beams), substructure
(the piers and abutments), and culverts, each on a 0–9 scale
* **Age**, year built, and the year of any major reconstruction
* **Traffic**: average vehicles per day
* **Design**: material (concrete, steel, timber), structure type, length, width
* **Location**: county and latitude/longitude

Because bridges keep the same ID year after year, each one can be followed
through up to 34 years of inspections.

**What counts as Poor.** Following the federal rule (23 CFR 490), a bridge's
condition is set by its lowest component rating:

|Condition|Lowest rating|Meaning|
|-|-|-|
|Good|7–9|Minor problems at most|
|Fair|5–6|Sound structure with some wear or section loss|
|Poor|0–4|Advanced deterioration; needs major repair or replacement|

The project starts with Georgia only, which keeps the data small enough for a
laptop. Other states can be added once the pipeline works.

## Approach

The modeling builds up in steps, and each step is kept only if it beats the
one before. Knowing when a simple answer is good enough is part of the job.

1. **Baseline.** A lookup table: for each group of bridges by age and
material, what share of Fair bridges fell to Poor within five years? Every
model has to beat this.
2. **Survival analysis.** The outcome is *time until a bridge falls to Poor*.
Bridges still in Fair condition at the end of the data have not failed
*yet*; survival models count them correctly instead of throwing them out.

   * Kaplan–Meier curves show how quickly bridges of each material decline.
   * A Cox model estimates how much age, traffic, material, deck rating, and
climate region each raise or lower the risk.
   * A random survival forest is tried if the Cox model leaves room to improve.
3. **Spatial check.** The predictions are mapped, and the errors are tested
for geographic clustering. If the model is wrong in the same region again
and again, something is missing, such as freeze–thaw cycles in north
Georgia or salt exposure near the coast.

## How the model is judged

The model is trained on data through 2015 and tested on 2016–2025, so it is
always predicting a future it has never seen.

|Measure|Question it answers|
|-|-|
|Concordance index|Does the model rank riskier bridges above safer ones?|
|Calibration|When the model says 30% risk, do about 30% of those bridges actually fall to Poor?|
|Top-10% capture|Of the bridges that really fell to Poor, how many were in the model's top 10% ranking?|

The last measure is compared with a simple rule an agency might use today:
inspect the oldest bridges first.

## Results

*To be completed as the project progresses.*

|Model|Concordance|Calibration|Failures caught in top 10%|
|-|-|-|-|
|Baseline (age × material)|–|–|–|
|Cox model|–|–|–|
|Random survival forest|–|–|–|
|Oldest-first rule|–|–|–|

Key findings, the risk map, and the model card will be linked here.

## How it is built

```
FHWA yearly files ─► Python download ─► DuckDB (raw) ─► dbt (clean, tested)
                                                              │
         Map / dashboard ◄─ Risk scores ◄─ Models (MLflow) ◄──┘
                     ▲
     GitHub Actions: scheduled rerun, data tests, drift checks
```

|Step|Tool|What it does|
|-|-|-|
|Download|Python|Fetches each year's file and records its size and checksum|
|Store|DuckDB|A free database that runs on a laptop; its SQL carries over to Snowflake|
|Clean|dbt|Turns raw text into one tested table with a row per bridge per year|
|Model|lifelines, scikit-survival|Survival models, written as scripts rather than notebooks|
|Track|MLflow|Logs every model run's settings and scores so they can be compared|
|Automate|GitHub Actions|Reruns the pipeline on a schedule and fails loudly when a data test breaks or the data shifts|
|Spatial|PySAL, ArcGIS Pro|Tests whether errors cluster; makes the final map|
|Publish|ArcGIS Online or Streamlit|A map of risk scores anyone can open|

**Data quality tests** run on every build, for example: one row per bridge per
year, ratings between 0 and 9, coordinates inside Georgia, and a warning if
the number of bridges jumps more than 10% between years.

## Project roadmap

* \[ ] **Month 1 – Data pipeline:** download all years, load into DuckDB, build
and test the bridge-by-year table
* \[ ] **Month 2 – Models:** baseline, Kaplan–Meier, Cox model, MLflow tracking
* \[ ] **Month 3 – Production:** scheduled GitHub Actions runs, drift checks,
spatial error analysis
* \[ ] **Month 4 – Communication:** map, model card, and a short decision
write-up

## Run it yourself

You need Python 3.11 or newer (3.12 recommended) and about 300 MB of disk
space. 



**Windows (PowerShell), short version**

```powershell
python -m venv .venv
.venv\\Scripts\\activate
pip install -e ".\[dev]"
pytest                                   # end-to-end test on sample files
python -m nbi.download --state GA --start 1992 --end 2025
python -m nbi.load
cd dbt; dbt build --profiles-dir .; cd ..
python -m nbi.checks                     # first-look data checks
```

**Mac or Linux**

```bash
make setup \&\& source .venv/bin/activate
make test     # unit tests and an end-to-end run on small sample files
make all      # download, load, and build with tests
make profile  # first-look data checks
```

## Repository layout

```
src/nbi/          Python: download, load and check the NBI files
dbt/              Cleaning models, tests, and reference tables
tests/            Unit tests and synthetic sample files
docs/             Data notes and decisions (later: model card, write-up)
.github/          Automated tests and scheduled runs
```

## About

Built by Tara Wu, MS in Spatial Data Science (Penn State, 2026), with
Forest Service bridge inspection certification. Inspection work showed me how
much judgment goes into choosing which structures to look at first; this
project tests how much data can help with that choice.

Data: Federal Highway Administration, National Bridge Inventory, 1992–2025.
This is an independent portfolio project and is not affiliated with FHWA or
the Georgia Department of Transportation.

