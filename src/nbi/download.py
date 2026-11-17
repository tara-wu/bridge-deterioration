"""Download yearly NBI fixed-width files for one state.

    python -m nbi.download --state GA --start 1992 --end 2025

Files land in data/raw/nbi/<STATE><YY>.txt (for example GA24.txt). Files you
already have are skipped, so the script is safe to rerun. A manifest
(manifest.csv) records the address, size and SHA-256 checksum of each file,
which later drift checks compare against.

FHWA has served these files from a few different addresses over the years, so
each year tries them in order and keeps the first one that returns a real NBI
file. If none works, the script prints the FHWA page to download from by hand.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

DISCLAIMER = "https://www.fhwa.dot.gov/Bridge/nbi/disclaim.cfm?nbiYear={year}&nbiState={st}{yy}"
USER_AGENT = "bridge-deterioration-portfolio/0.1 (research; python-requests)"
DEFAULT_OUT = Path("data/raw/nbi")
STATE_FIPS = {"GA": "13"}  # add states here as the project expands


def file_name(state: str, year: int) -> str:
    return f"{state.upper()}{year % 100:02d}.txt"


def file_url(state: str, year: int) -> str:
    return f"https://www.fhwa.dot.gov/bridge/nbi/{year}/{file_name(state, year)}"


def disclaimer_url(state: str, year: int) -> str:
    return DISCLAIMER.format(year=year, st=state.upper(), yy=f"{year % 100:02d}")


def candidate_urls(state: str, year: int) -> list[str]:
    name = file_name(state, year)
    return [
        file_url(state, year),
        f"https://www.fhwa.dot.gov/Bridge/nbi/{year}/{name}",
        disclaimer_url(state, year),
    ]


def looks_like_nbi(content: bytes, state_fips: str | None = None) -> bool:
    """True for a fixed-width NBI file; False for HTML pages and other files."""
    head = content[:2000].lstrip().lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html"):
        return False
    first = content.split(b"\n", 1)[0]
    if len(first.rstrip(b"\r")) < 400:      # fixed-width records are 432-445 characters
        return False
    if state_fips and not first.startswith(state_fips.encode()):
        return False
    return True


def unzip_if_needed(content: bytes, name: str) -> bytes:
    """Some FHWA links return a .zip holding the .txt file."""
    if not content.startswith(b"PK"):
        return content
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        members = [m for m in zf.namelist() if m.lower().endswith(".txt")]
        exact = [m for m in members if m.rsplit("/", 1)[-1].lower() == name.lower()]
        pick = (exact or members or [None])[0]
        return zf.read(pick) if pick else b""


def file_links(html: bytes, base_url: str, name: str) -> list[str]:
    """Links on an HTML page (like FHWA's disclaimer) that point at the file."""
    text = html.decode("latin-1")
    hrefs = re.findall(r"""href\s*=\s*["']([^"']+)["']""", text, flags=re.IGNORECASE)
    stem = name.rsplit(".", 1)[0].lower()
    return [urljoin(base_url, h) for h in hrefs
            if stem in h.lower() and (h.lower().endswith((".txt", ".zip")) or "nbistate" in h.lower())]


def fetch(session: requests.Session, url: str, retries: int = 3) -> requests.Response | None:
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=120)
        except requests.RequestException as exc:
            print(f"      retry {url}: {exc}")
            time.sleep(2 * attempt)
            continue
        if resp.status_code in (429, 500, 502, 503, 504):
            time.sleep(5 * attempt)
            continue
        return resp
    return None


def try_url(session: requests.Session, url: str, name: str, fips: str | None,
            follow_links: bool = True) -> bytes | None:
    resp = fetch(session, url)
    if resp is None or resp.status_code != 200:
        return None
    content = unzip_if_needed(resp.content, name)
    if looks_like_nbi(content, fips):
        return content
    if follow_links and resp.content.lstrip()[:1] == b"<":
        for link in file_links(resp.content, resp.url, name):
            found = try_url(session, link, name, fips, follow_links=False)
            if found:
                return found
    return None


def download_one(session: requests.Session, state: str, year: int, out_dir: Path,
                 fips: str | None) -> dict | None:
    name = file_name(state, year)
    dest = out_dir / name
    if dest.exists() and looks_like_nbi(dest.read_bytes()[:5000], fips):
        print(f"skip  {name} (already downloaded)")
        return _manifest_row(state, year, "already on disk", dest)

    for url in candidate_urls(state, year):
        content = try_url(session, url, name, fips)
        if content:
            tmp = dest.with_suffix(".part")
            tmp.write_bytes(content)
            tmp.replace(dest)
            print(f"ok    {name} ({len(content) / 1e6:.1f} MB)")
            return _manifest_row(state, year, url, dest)

    print(f"FAIL  {name}: open {disclaimer_url(state, year)} in your browser, "
          f"accept the disclaimer, and save the file as {dest}", file=sys.stderr)
    return None


def _manifest_row(state: str, year: int, url: str, path: Path) -> dict:
    data = path.read_bytes()
    return {
        "state": state.upper(),
        "year": year,
        "file": path.name,
        "url": url,
        "bytes": len(data),
        "lines": data.count(b"\n"),
        "sha256": hashlib.sha256(data).hexdigest(),
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--state", default="GA")
    p.add_argument("--start", type=int, default=1992)
    p.add_argument("--end", type=int, default=2025)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = p.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    # Item 1 is 3 characters: the 2-digit state FIPS code plus the FHWA region
    # digit (Georgia = "134"), so only the first two are checked.
    fips = STATE_FIPS.get(args.state.upper())

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    rows, failed = [], []
    for year in range(args.start, args.end + 1):
        row = download_one(session, args.state, year, args.out, fips)
        if row:
            rows.append(row)
        else:
            failed.append(year)
        time.sleep(1)  # be polite to FHWA's server

    manifest = args.out / "manifest.csv"
    with manifest.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["file"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n{len(rows)} files ready, {len(failed)} failed. Manifest: {manifest}")
    if failed:
        print("Failed years:", ", ".join(map(str, failed)), file=sys.stderr)
        print("Download those by hand (see the FAIL lines above), then run this "
              "command again to finish the manifest.", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
