# Data notes

Decisions made while building `bridge\\\\\\\_year`, and questions to answer once the
real Georgia files are loaded. Updated as the project progresses, it becomes the data
section of the model card.



## Decisions

1. **Fixed-width files, not the delimited ones.** The fixed-width layout is the
same for positions 1–433 in every year from 1992 to 2025, so one parser
covers all 34 years. Delimited files use single quotes as the text qualifier
and their headers are less certain to match across years.
2. **Raw stays raw.** `raw.nbi\\\\\\\_records` keeps every field as text, including
record type 2 lines and non-Georgia codes. Filtering happens in the mart so
it is visible and tested.
3. **Record type 1 only.** Type 2 lines describe routes passing *under* a
structure and would double-count bridges.
4. **'N' ratings become null.** Culverts are coded N for items 58–60 and rated
on item 62; bridges are N on item 62. `lowest\\\\\\\_rating` takes the minimum of
whatever is present, matching FHWA's CAT23 field.
5. **Duplicates keep the first line** and record `lines\\\\\\\_in\\\\\\\_year`, so the count
of dropped lines is a test result rather than a silent loss.
6. **Inspection year from MMYY.** The two-digit year takes the latest century
that is not after the file year.
7. **File year is not inspection year.** Georgia inspects most bridges every
24 months, so a rating in the 2016 file may come from a 2015 inspection.
Survival models in month 2 should measure time with `inspection\\\\\\\_year`
where it matters.

## Check on the first real load



Most answers come from `python -m nbi.checks` (python -m nbi.checks).



* \[x] Did all 34 years download? Yes, all 34 on the first try, no manual downloads.
dbt build: ERROR=0, 5 warnings. 318 raw lines with an invalid inspection month;
70 bridge-years with an unknown material code; 546 latitudes and 882 longitudes
outside Georgia's bounds (check before mapping in month 3); 7 bridge-years with
duplicate lines (first line kept).
* \[x] Does the bridge count stay near 14,300–15,100 every year? (FHWA's pages
list 14,306 in 1994 and 14,670 in 2010.)Yes: 14,249 in 1992 rising steadily to 15,090 in 2025, no sudden drops.
* \[x] Do structure IDs persist across years, or did Georgia renumber at some
point? Count IDs that appear in year *t* but not *t+1*, by year; a spike
means renumbering, not replacements. Yes. 50–250 new and disappearing IDs per year, never thousands: no renumbering.
* \[x] How many bridges skip a year (`record\\\\\\\_year - prev\\\\\\\_record\\\\\\\_year > 1`)? About 60 gaps of 2+ years out of \~479,000 transitions.
* \[x] Is `meets\\\\\\\_nbis\\\\\\\_length` coded consistently before 2000? Yes. Every year 1992–2025 is coded Y for all but 0–5 structures, with no blanks or other codes. The highway-bridge files already contain only NBIS-length structures, so no length filter is needed.
* \[x] Share of Fair bridges that reach Poor within five years, by material.
This is the baseline in month 2 and a sanity check now. Timber 31.5%, Steel 7.4%, Concrete 3.7%, Prestressed 2.2%, Other 3.8%.







## Open question for month 2

* Fair share drops from 51.6% (2019) to 24.1% (2021) while Poor barely changes:
about a quarter of bridges moved Fair to Good in two years. Find out which
component rating changed and why before training.
* \- Fair-to-Good transitions jumped from \~150/year (2015–2018) to 653 (2019), 2,407 (2020) and 1,807 (2021), then fell back. Almost none had a recorded reconstruction (item 106). Average deck, superstructure, substructure and culvert ratings all rose \~0.15–0.2 in 2020 and again in 2021, then stayed flat. Likely a statewide change in rating practice rather than physical repairs. Decide in month 2: period variable, censor unexplained upgrades, or split test results by start year.
* District check (2019–2021): the Fair-to-Good jump appears in all seven GDOT

&#x20; districts. In 2019–2020, six districts upgraded 20–22% of Fair bridges (District 6: 12.5%).

* In 2021 it ranged from 22% (District 7) to 54% (District 4). Points to a statewide

&#x20; change in rating practice, applied unevenly in 2021. Bridges outside the GDOT

&#x20; district codes show almost no upgrades.

* Cleaning fix needed: highway\_district is coded "04" in some years and "4" in

&#x20; others (2021). Standardize to two digits in stg\_nbi\_\_records before using

&#x20; district in any model.

