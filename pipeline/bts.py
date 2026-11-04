"""Everything specific to the BTS 'Reporting Carrier On-Time Performance' source.

- which months to load
- where each month's ZIP lives on the BTS site
- downloading it safely (retries, timeouts, ZIP check)
- pulling the CSV out of the ZIP and checking it has the columns we need
- turning it into the exact column list our raw table expects
"""
from __future__ import annotations

import hashlib
import io
import logging
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

BTS_URL_TEMPLATE = (
    "https://transtats.bts.gov/PREZIP/"
    "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
)

# Source column name -> raw table column name.
# We only keep what the project uses; the BTS file has ~110 columns.
COLUMN_MAP: dict[str, str] = {
    "Year": "year",
    "Month": "month",
    "FlightDate": "flight_date",
    "Reporting_Airline": "reporting_airline",
    "Tail_Number": "tail_number",
    "Flight_Number_Reporting_Airline": "flight_number",
    "Origin": "origin",
    "OriginCityName": "origin_city_name",
    "OriginState": "origin_state",
    "Dest": "dest",
    "DestCityName": "dest_city_name",
    "DestState": "dest_state",
    "CRSDepTime": "crs_dep_time",
    "DepTime": "dep_time",
    "DepDelay": "dep_delay",
    "CRSArrTime": "crs_arr_time",
    "ArrTime": "arr_time",
    "ArrDelay": "arr_delay",
    "ArrDel15": "arr_del15",
    "Cancelled": "cancelled",
    "CancellationCode": "cancellation_code",
    "Diverted": "diverted",
    "CRSElapsedTime": "crs_elapsed_time",
    "ActualElapsedTime": "actual_elapsed_time",
    "Distance": "distance",
    "CarrierDelay": "carrier_delay",
    "WeatherDelay": "weather_delay",
    "NASDelay": "nas_delay",
    "SecurityDelay": "security_delay",
    "LateAircraftDelay": "late_aircraft_delay",
}
REQUIRED_SOURCE_COLUMNS = list(COLUMN_MAP)
RAW_COLUMNS = list(COLUMN_MAP.values())


class SourceSchemaError(ValueError):
    """The downloaded file does not have the columns we depend on."""


class MonthNotPublished(Exception):
    """BTS has not published this month yet (HTTP 404 or a non-ZIP response)."""


@dataclass(frozen=True, order=True)
class YearMonth:
    year: int
    month: int

    def __post_init__(self) -> None:
        if not 1 <= self.month <= 12:
            raise ValueError(f"month must be 1-12, got {self.month}")

    @classmethod
    def parse(cls, text: str) -> "YearMonth":
        """'2026-07' -> YearMonth(2026, 7)"""
        year, month = text.strip().split("-")
        return cls(int(year), int(month))

    @classmethod
    def from_date(cls, d: date) -> "YearMonth":
        return cls(d.year, d.month)

    def add(self, months: int) -> "YearMonth":
        index = self.year * 12 + (self.month - 1) + months
        return YearMonth(index // 12, index % 12 + 1)

    @property
    def key(self) -> int:
        """202607 - the year_month integer used across the warehouse."""
        return self.year * 100 + self.month

    def __str__(self) -> str:
        return f"{self.year}-{self.month:02d}"


def month_range(start: YearMonth, end: YearMonth) -> list[YearMonth]:
    """Inclusive list of months from start to end."""
    if end < start:
        raise ValueError(f"end {end} is before start {start}")
    months, current = [], start
    while current <= end:
        months.append(current)
        current = current.add(1)
    return months


def rolling_window(latest: YearMonth, months_back: int) -> list[YearMonth]:
    """The `months_back` months ending at `latest` (inclusive)."""
    if months_back < 1:
        raise ValueError("months_back must be at least 1")
    return month_range(latest.add(-(months_back - 1)), latest)


def source_url(ym: YearMonth) -> str:
    # BTS uses an un-padded month number in the file name (…_2026_7.zip)
    return BTS_URL_TEMPLATE.format(year=ym.year, month=ym.month)


def zip_filename(ym: YearMonth) -> str:
    return source_url(ym).rsplit("/", 1)[1]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_month(ym: YearMonth, dest_dir: Path, timeout: int = 300) -> Path:
    """Download one month's ZIP from BTS with retries. Returns the local path.

    Raises MonthNotPublished when BTS answers 404 or returns something that is not a ZIP
    (BTS serves an HTML page for months that do not exist yet).
    """
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / zip_filename(ym)
    partial = target.with_suffix(".zip.part")
    url = source_url(ym)

    session = requests.Session()
    retry = Retry(
        total=4,
        backoff_factor=5,  # waits 5s, 10s, 20s, 40s between attempts
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    headers = {"User-Agent": "flight-reliability-analytics/1.0 (portfolio data pipeline)"}

    log.info("downloading %s", url)
    with session.get(url, stream=True, timeout=timeout, headers=headers) as response:
        if response.status_code == 404:
            raise MonthNotPublished(f"{ym}: BTS returned 404 for {url}")
        response.raise_for_status()
        with open(partial, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                handle.write(chunk)

    if not zipfile.is_zipfile(partial):
        partial.unlink(missing_ok=True)
        raise MonthNotPublished(f"{ym}: response from {url} was not a ZIP file")
    partial.replace(target)  # only a complete, valid file ever gets the final name
    log.info("downloaded %s (%.1f MB)", target.name, target.stat().st_size / 1e6)
    return target


def find_csv_member(zf: zipfile.ZipFile) -> str:
    """The BTS ZIP holds one CSV plus a readme.html; return the CSV's name."""
    csvs = [name for name in zf.namelist() if name.lower().endswith(".csv")]
    if len(csvs) != 1:
        raise SourceSchemaError(f"expected exactly one CSV in the ZIP, found {csvs}")
    return csvs[0]


def validate_header(columns: list[str]) -> None:
    missing = [c for c in REQUIRED_SOURCE_COLUMNS if c not in columns]
    if missing:
        raise SourceSchemaError(
            f"BTS file is missing {len(missing)} required column(s): {missing}. "
            "The source layout may have changed - check the BTS site before loading."
        )


def read_month(zip_path: Path, expected: YearMonth | None = None) -> pd.DataFrame:
    """Read one month's ZIP into a DataFrame with exactly RAW_COLUMNS, all as text.

    Everything stays text on purpose: the raw layer must never reject a row because of a
    surprising value. Typing and cleaning happen in dbt staging, where it is tested.
    """
    with zipfile.ZipFile(zip_path) as zf:
        member = find_csv_member(zf)
        with zf.open(member) as raw:
            header = pd.read_csv(raw, nrows=0).columns.str.strip().tolist()
        validate_header(header)
        with zf.open(member) as raw:
            frame = pd.read_csv(
                raw,
                usecols=REQUIRED_SOURCE_COLUMNS,
                dtype=str,
                keep_default_na=False,  # keep blanks as '' so nothing is silently guessed
                encoding="latin-1",
            )

    frame = frame[REQUIRED_SOURCE_COLUMNS].rename(columns=COLUMN_MAP)
    frame = frame.apply(lambda col: col.str.strip())

    if expected is not None and len(frame):
        months_in_file = set(zip(frame["year"].astype(int), frame["month"].astype(int)))
        if months_in_file != {(expected.year, expected.month)}:
            raise SourceSchemaError(
                f"{zip_path.name}: expected only {expected} but found {sorted(months_in_file)}"
            )
    return frame


def to_copy_buffer(frame: pd.DataFrame, columns: list[str] | None = None) -> io.StringIO:
    """CSV text in a fixed column order, ready for Postgres COPY ... FROM STDIN."""
    buffer = io.StringIO()
    frame[columns or RAW_COLUMNS].to_csv(buffer, index=False, header=False)
    buffer.seek(0)
    return buffer
