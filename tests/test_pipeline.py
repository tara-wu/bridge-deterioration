"""End-to-end: load fixture files into DuckDB, run dbt build, check bridge_year.

Skipped automatically when duckdb or dbt is not installed.
"""

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")
if shutil.which("dbt") is None:
    pytest.skip("dbt not installed", allow_module_level=True)

from nbi.load import load  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def built_db(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("pipeline")
    spec = importlib.util.spec_from_file_location("mk", ROOT / "tests/fixtures/make_fixtures.py")
    mk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mk)
    mk.build(tmp / "raw")

    db = tmp / "fixture.duckdb"
    load(tmp / "raw", db)
    env = {**os.environ, "NBI_DUCKDB_PATH": str(db)}
    result = subprocess.run(
        ["dbt", "build", "--profiles-dir", ".", "--target-path", str(tmp / "target")],
        cwd=ROOT / "dbt", env=env, capture_output=True, text=True,
    )
    print(result.stdout[-4000:])
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]
    con = duckdb.connect(str(db), read_only=True)
    yield con
    con.close()


def rows(con, sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def test_grain(built_db):
    n, distinct = built_db.execute(
        "select count(*), count(distinct bridge_year_id) from marts.bridge_year").fetchone()
    assert n == distinct == 15  # 5 bridges x 3 years


def test_fair_to_poor(built_db):
    r = rows(built_db, "select record_year, lowest_rating, condition_class, prev_condition_class "
                       "from marts.bridge_year where structure_id = 'F2P001' order by record_year")
    assert [x["condition_class"] for x in r] == ["Fair", "Fair", "Poor"]
    assert r[2]["prev_condition_class"] == "Fair"


def test_culvert_uses_item_62(built_db):
    r = rows(built_db, "select is_culvert, lowest_rating, condition_class, material_group "
                       "from marts.bridge_year where structure_id = 'CULV01' order by record_year")
    assert all(x["is_culvert"] for x in r)
    assert [x["lowest_rating"] for x in r] == [6, 5, 4]
    assert r[0]["material_group"] == "Concrete"


def test_padding_normalized(built_db):
    years = [r["record_year"] for r in rows(
        built_db, "select record_year from marts.bridge_year where structure_id = 'PAD01'")]
    assert sorted(years) == [2013, 2014, 2015]


def test_duplicates_and_record_type(built_db):
    r = rows(built_db, "select lines_in_year, substructure_rating from marts.bridge_year "
                       "where structure_id = 'DUPE001' and record_year = 2014")
    assert r == [{"lines_in_year": 2, "substructure_rating": 6}]  # first line kept


def test_derived_fields(built_db):
    r = rows(built_db, "select * from marts.bridge_year "
                       "where structure_id = 'GOOD001' and record_year = 2015")[0]
    assert r["years_since_work"] == 5 and r["age_years"] == 40
    assert r["condition_class"] == "Good"
    assert abs(r["latitude"] - 33.75) < 1e-6
    assert abs(r["longitude"] + 84.383333) < 1e-5
    assert r["structure_length_m"] == pytest.approx(45.6)
    assert r["inspection_year"] == 2013  # fixture default "0613"
