"""Load raw NBI files into DuckDB, unchanged except for slicing into columns.

    python -m nbi.load --raw data/raw/nbi --db data/warehouse/nbi.duckdb

Writes raw.nbi_records: one row per line of every file, every field as the
original text (no trimming, casting or filtering). All cleaning happens in dbt,
so the raw table stays a faithful copy of what FHWA published and every
cleaning rule is visible and tested in one place.

The load is a full refresh per file year: rerunning replaces that year's rows.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from nbi.record_format import COLUMN_NAMES, file_year, parse_line

SCHEMA = "raw"
TABLE = "nbi_records"


def read_file(path: Path) -> pd.DataFrame:
    # latin-1 never fails to decode, and FHWA files are plain ASCII anyway.
    with path.open("r", encoding="latin-1", newline="") as fh:
        rows = [parse_line(line) for line in fh if line.strip()]
    df = pd.DataFrame(rows, columns=list(COLUMN_NAMES))
    df.insert(0, "record_year", file_year(path.name))
    df.insert(1, "source_file", path.name)
    df.insert(2, "line_number", range(1, len(df) + 1))
    return df


def load(raw_dir: Path, db_path: Path, pattern: str = "*.txt") -> dict[str, int]:
    import duckdb  # imported here so parsing tests run without duckdb

    files = sorted(raw_dir.glob(pattern))
    if not files:
        raise SystemExit(f"No files matching {pattern} in {raw_dir}. Run the download first.")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute(f"create schema if not exists {SCHEMA}")
    cols = ", ".join(f"{c} varchar" for c in COLUMN_NAMES)
    con.execute(
        f"create table if not exists {SCHEMA}.{TABLE} ("
        f"record_year integer, source_file varchar, line_number integer, {cols}, "
        f"loaded_at timestamp default current_timestamp)"
    )

    counts: dict[str, int] = {}
    for path in files:
        df = read_file(path)
        con.execute("begin")
        con.execute(f"delete from {SCHEMA}.{TABLE} where source_file = ?", [path.name])
        con.register("incoming", df)
        con.execute(
            f"insert into {SCHEMA}.{TABLE} (record_year, source_file, line_number, "
            f"{', '.join(COLUMN_NAMES)}) select * from incoming"
        )
        con.unregister("incoming")
        con.execute("commit")
        counts[path.name] = len(df)
        print(f"loaded {path.name}: {len(df):,} rows")

    total = con.execute(f"select count(*) from {SCHEMA}.{TABLE}").fetchone()[0]
    print(f"{SCHEMA}.{TABLE} now has {total:,} rows from {len(files)} files")
    con.close()
    return counts


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--raw", type=Path, default=Path("data/raw/nbi"))
    p.add_argument("--db", type=Path, default=Path("data/warehouse/nbi.duckdb"))
    p.add_argument("--pattern", default="*.txt")
    args = p.parse_args(argv)
    load(args.raw, args.db, args.pattern)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
