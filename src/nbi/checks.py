"""First-look checks on the finished bridge_year table.

    python -m nbi.checks

Prints four small tables that answer the questions in docs/data_notes.md:

1. Bridges per year, and the share in Fair and Poor condition
2. Bridge ID continuity: how many IDs are new each year and how many vanished
   (a year where thousands appear AND thousands vanish means renumbering)
3. Bridges that skip one or more years between records
4. A first look at the baseline: share of Fair bridges that reach Poor
   within five years, by material
"""

from __future__ import annotations

import argparse
from pathlib import Path

CHECKS = {
    "1. Bridges per year": """
        select record_year as year,
               count(*) as bridges,
               round(100 * avg((condition_class = 'Fair')::int), 1) as pct_fair,
               round(100 * avg((condition_class = 'Poor')::int), 1) as pct_poor,
               sum((condition_class = 'Unknown')::int) as unknown
        from marts.bridge_year
        group by 1 order by 1
    """,
    "2. Bridge ID continuity (new = not in the year before, gone = not in the year after)": """
        with ids as (select distinct structure_id, record_year from marts.bridge_year),
        bounds as (select min(record_year) as first_yr, max(record_year) as last_yr from ids)
        select i.record_year as year,
               count(*) as bridges,
               case when i.record_year = any_value(b.first_yr) then null
                    else count(*) filter (where p.structure_id is null) end as new_ids,
               case when i.record_year = any_value(b.last_yr) then null
                    else count(*) filter (where n.structure_id is null) end as gone_next_year
        from ids i
        cross join bounds b
        left join ids p on p.structure_id = i.structure_id and p.record_year = i.record_year - 1
        left join ids n on n.structure_id = i.structure_id and n.record_year = i.record_year + 1
        group by i.record_year order by 1
    """,
    "3. Bridges with a gap between records": """
        select record_year - prev_record_year as years_between_records,
               count(*) as times_seen
        from marts.bridge_year
        where prev_record_year is not null
        group by 1 order by 1
    """,
    "4. Fair bridges that reached Poor within 5 years (starting years 1992-2015)": """
        with fair as (
            select structure_id, record_year, material_group
            from marts.bridge_year
            where condition_class = 'Fair' and record_year <= 2015
        ),
        outcome as (
            select f.material_group,
                   coalesce(max((later.condition_class = 'Poor')::int), 0) as reached_poor
            from fair f
            left join marts.bridge_year later
              on later.structure_id = f.structure_id
             and later.record_year between f.record_year + 1 and f.record_year + 5
            group by f.structure_id, f.record_year, f.material_group
        )
        select coalesce(material_group, 'Unknown') as material,
               count(*) as fair_bridge_years,
               round(100 * avg(reached_poor), 1) as pct_reached_poor
        from outcome
        group by 1 order by 2 desc
    """,
}


def main(argv: list[str] | None = None) -> int:
    import duckdb

    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--db", type=Path, default=Path("data/warehouse/nbi.duckdb"))
    args = p.parse_args(argv)
    if not args.db.exists():
        raise SystemExit(f"No database at {args.db}. Run the load and dbt steps first.")

    con = duckdb.connect(str(args.db), read_only=True)
    for title, sql in CHECKS.items():
        print(f"\n{title}\n" + "-" * len(title))
        print(con.sql(sql).df().to_string(index=False))
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
