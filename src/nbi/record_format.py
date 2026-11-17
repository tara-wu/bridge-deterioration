"""NBI fixed-width record layout (the subset this project uses).

Source: FHWA "NBI Record Format", https://www.fhwa.dot.gov/bridge/nbi/format.cfm
Positions are 1-based and inclusive, exactly as printed in the FHWA table, so
each entry can be checked against the spec by eye.

The layout of positions 1-433 is the same for every year 1992-2025. Positions
434-445 (CAT10, CAT23, CAT29) are download-only fields FHWA added later; older
files are shorter, so lines are right-padded before slicing.
"""

from __future__ import annotations

from dataclasses import dataclass

RECORD_LENGTH = 445


@dataclass(frozen=True)
class Field:
    item: str          # FHWA item number, e.g. "58"
    name: str          # column name used in the raw table
    start: int         # 1-based, inclusive
    end: int           # 1-based, inclusive

    @property
    def width(self) -> int:
        return self.end - self.start + 1

    def slice(self, line: str) -> str:
        return line[self.start - 1 : self.end]


FIELDS: tuple[Field, ...] = (
    Field("1", "state_code", 1, 3),
    Field("8", "structure_number", 4, 18),
    Field("5A", "record_type", 19, 19),
    Field("2", "highway_district", 28, 29),
    Field("3", "county_code", 30, 32),
    Field("16", "latitude_raw", 130, 137),
    Field("17", "longitude_raw", 138, 146),
    Field("21", "maintenance_responsibility", 151, 152),
    Field("22", "owner_code", 153, 154),
    Field("26", "functional_class", 155, 156),
    Field("27", "year_built", 157, 160),
    Field("29", "adt", 165, 170),
    Field("30", "adt_year", 171, 174),
    Field("41", "open_posted_closed", 199, 199),
    Field("42A", "service_on", 200, 200),
    Field("42B", "service_under", 201, 201),
    Field("43A", "material_code", 202, 202),
    Field("43B", "design_code", 203, 204),
    Field("45", "main_spans", 208, 210),
    Field("49", "structure_length_m", 223, 228),
    Field("52", "deck_width_m", 239, 242),
    Field("58", "deck_cond", 259, 259),
    Field("59", "superstructure_cond", 260, 260),
    Field("60", "substructure_cond", 261, 261),
    Field("61", "channel_cond", 262, 262),
    Field("62", "culvert_cond", 263, 263),
    Field("90", "inspection_date", 287, 290),
    Field("91", "inspection_frequency", 291, 292),
    Field("106", "year_reconstructed", 362, 365),
    Field("112", "nbis_length", 374, 374),
)

COLUMN_NAMES: tuple[str, ...] = tuple(f.name for f in FIELDS)


def parse_line(line: str) -> dict[str, str]:
    """Slice one fixed-width NBI record into raw string fields (no cleaning)."""
    padded = line.rstrip("\r\n").ljust(RECORD_LENGTH)
    return {f.name: f.slice(padded) for f in FIELDS}


def file_year(filename: str) -> int:
    """GA92.txt -> 1992, GA05.txt -> 2005, GA25.txt -> 2025."""
    stem = filename.rsplit("/", 1)[-1].split(".", 1)[0]
    yy = int(stem[-2:])
    return 1900 + yy if yy >= 90 else 2000 + yy
