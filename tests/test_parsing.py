"""Tests that run anywhere (no network, no DuckDB)."""

import importlib.util
from pathlib import Path

import pytest

from nbi import download
from nbi.load import read_file
from nbi.record_format import FIELDS, RECORD_LENGTH, file_year, parse_line

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def raw_dir(tmp_path_factory):
    spec = importlib.util.spec_from_file_location("mk", FIXTURES / "make_fixtures.py")
    mk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mk)
    out = tmp_path_factory.mktemp("raw")
    mk.build(out)
    return out


def test_fields_match_fhwa_spot_checks():
    # Positions copied from https://www.fhwa.dot.gov/bridge/nbi/format.cfm
    expected = {"8": (4, 18), "27": (157, 160), "43A": (202, 202), "58": (259, 259),
                "62": (263, 263), "90": (287, 290), "106": (362, 365)}
    by_item = {f.item: (f.start, f.end) for f in FIELDS}
    for item, pos in expected.items():
        assert by_item[item] == pos, item


def test_fields_do_not_overlap():
    spans = sorted((f.start, f.end, f.name) for f in FIELDS)
    for (s1, e1, n1), (s2, _, n2) in zip(spans, spans[1:]):
        assert e1 < s2, f"{n1} overlaps {n2}"
    assert all(1 <= f.start <= f.end <= RECORD_LENGTH for f in FIELDS)


def test_parse_line_handles_short_lines():
    parsed = parse_line("134" + "000000000012345" + "1")
    assert parsed["structure_number"] == "000000000012345"
    assert parsed["record_type"] == "1"
    assert parsed["deck_cond"] == " "


@pytest.mark.parametrize("name,year", [("GA92.txt", 1992), ("GA99.txt", 1999),
                                       ("GA05.txt", 2005), ("GA25.txt", 2025),
                                       ("data/raw/nbi/GA13.txt", 2013)])
def test_file_year(name, year):
    assert file_year(name) == year


def test_urls():
    assert download.file_url("ga", 2024) == "https://www.fhwa.dot.gov/bridge/nbi/2024/GA24.txt"
    assert download.file_url("GA", 1995).endswith("/1995/GA95.txt")
    assert "nbiState=GA05" in download.disclaimer_url("GA", 2005)


def test_rejects_html_and_wrong_state():
    good = b"134" + b"0" * 440 + b"\r\n"
    assert download.looks_like_nbi(good, "13")
    assert not download.looks_like_nbi(b"<!DOCTYPE html><html>...", "13")
    assert not download.looks_like_nbi(b"014" + b"0" * 440, "13")
    assert not download.looks_like_nbi(b"134 short line\n", "13")


def test_candidate_urls_end_with_disclaimer():
    urls = download.candidate_urls("GA", 2024)
    assert urls[0].endswith("/2024/GA24.txt")
    assert "disclaim.cfm" in urls[-1]


def test_unzip_if_needed():
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("GA24.txt", "134data")
    assert download.unzip_if_needed(buf.getvalue(), "GA24.txt") == b"134data"
    assert download.unzip_if_needed(b"134plain", "GA24.txt") == b"134plain"


def test_file_links_from_disclaimer_page():
    html = (b'<html><a href="/bridge/nbi/2024/GA24.txt">Accept</a>'
            b'<a href="/bridge/nbi/2024/AL24.txt">x</a><a href="/home">home</a></html>')
    links = download.file_links(html, "https://www.fhwa.dot.gov/Bridge/nbi/disclaim.cfm", "GA24.txt")
    assert links == ["https://www.fhwa.dot.gov/bridge/nbi/2024/GA24.txt"]


def test_read_file(raw_dir):
    df = read_file(raw_dir / "GA13.txt")
    assert len(df) == 6
    assert set(df.record_year) == {2013}
    assert list(df.line_number) == [1, 2, 3, 4, 5, 6]
    first = df.iloc[0]
    assert first.structure_number == "000000000F2P001"
    assert (first.deck_cond, first.superstructure_cond, first.substructure_cond) == ("6", "5", "6")
    assert first.year_built == "1975"
    assert first.latitude_raw == "33450000"
