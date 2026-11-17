"""Build tiny synthetic NBI files that exercise every cleaning rule.

    python tests/fixtures/make_fixtures.py tests/fixtures/raw

These are invented bridges, not real data. Each one tests one rule:

  B-FAIR2POOR  Fair (5) in 2013-14, Poor (4) from 2015       -> transition
  B-CULVERT    culvert: items 58-60 'N', item 62 rated        -> is_culvert, rating from 62
  B-PADDING    zero-padded in 2013, space-padded in 2014      -> same structure_id
  B-GOOD       Good all years, reconstructed in 2010          -> years_since_work
  B-DUPE       appears twice in 2014                          -> deduped, lines_in_year = 2
  (record type 2 line for B-GOOD)                              -> excluded from the mart
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nbi.record_format import FIELDS, RECORD_LENGTH  # noqa: E402

BY_NAME = {f.name: f for f in FIELDS}


def make_line(**values: str) -> str:
    buf = [" "] * RECORD_LENGTH
    for name, value in values.items():
        f = BY_NAME[name]
        text = str(value)
        if len(text) != f.width:
            raise ValueError(f"{name}: '{text}' is not {f.width} characters")
        buf[f.start - 1 : f.end] = list(text)
    return "".join(buf)


def bridge(structure_number: str, deck: str, sup: str, sub: str, culv: str,
           year_built="1975", reconstructed="0000", material="5", insp="0613",
           record_type="1") -> str:
    return make_line(
        state_code="134",
        structure_number=structure_number,
        record_type=record_type,
        county_code="121",
        latitude_raw="33450000",     # 33 deg 45' 00" N (Atlanta area)
        longitude_raw="084230000",   # 84 deg 23' 00" W
        owner_code="01",
        year_built=year_built,
        adt="012000",
        adt_year="2012",
        material_code=material,
        design_code="02",
        main_spans="003",
        structure_length_m="000456",  # 45.6 m
        deck_width_m="0120",          # 12.0 m
        deck_cond=deck,
        superstructure_cond=sup,
        substructure_cond=sub,
        channel_cond="7",
        culvert_cond=culv,
        inspection_date=insp,
        inspection_frequency="24",
        year_reconstructed=reconstructed,
        nbis_length="Y",
    )


def build(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    years = {
        2013: [
            bridge("000000000F2P001", "6", "5", "6", "N", insp="0613"),
            bridge("000000000CULV01", "N", "N", "N", "6", material="1", insp="0513"),
            bridge("0000000000PAD01", "7", "7", "7", "N"),
            bridge("00000000GOOD001", "8", "8", "7", "N", reconstructed="2010", material="3"),
            bridge("00000000GOOD001", "8", "8", "7", "N", record_type="2"),
            bridge("00000000DUPE001", "7", "6", "6", "N"),
        ],
        2014: [
            bridge("000000000F2P001", "5", "5", "6", "N", insp="0614"),
            bridge("000000000CULV01", "N", "N", "N", "5", material="1", insp="0514"),
            bridge("     0000PAD01 ", "7", "7", "6", "N"),
            bridge("00000000GOOD001", "8", "8", "7", "N", reconstructed="2010", material="3"),
            bridge("00000000DUPE001", "7", "6", "6", "N"),
            bridge("00000000DUPE001", "7", "6", "5", "N"),
        ],
        2015: [
            bridge("000000000F2P001", "4", "5", "6", "N", insp="0715"),
            bridge("000000000CULV01", "N", "N", "N", "4", material="1", insp="0515"),
            bridge("0000000000PAD01", "7", "6", "6", "N"),
            bridge("00000000GOOD001", "8", "7", "7", "N", reconstructed="2010", material="3"),
            bridge("00000000DUPE001", "7", "6", "5", "N"),
        ],
    }
    for year, lines in years.items():
        path = out / f"GA{year % 100:02d}.txt"
        # Older NBI files are 432 characters wide; make one year short on purpose.
        width = 432 if year == 2013 else RECORD_LENGTH
        path.write_text("".join(line[:width] + "\r\n" for line in lines), encoding="ascii")
        print(f"wrote {path} ({len(lines)} lines)")


if __name__ == "__main__":
    build(Path(sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures/raw"))
