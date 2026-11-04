"""Create SYNTHETIC BTS-shaped ZIP files for testing without internet access.

    python scripts/make_sample_data.py --start 2026-05 --end 2026-07 --rows 20000

The files copy the real BTS layout (same ~110 columns, same file names, same quirks:
hhmm times, blank cause columns for on-time flights, no arrival for cancellations), so the
whole pipeline can run in CI and on a laptop before real data is downloaded.

THE NUMBERS ARE MADE UP. Never publish dashboards or findings built from this data.
Output goes to data/landing/, which `pipeline.ingest --offline` picks up.
"""
from __future__ import annotations

import argparse
import csv
import io
import random
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.bts import YearMonth, month_range, zip_filename  # noqa: E402

DIV_FIELDS = ["Airport", "AirportID", "AirportSeqID", "WheelsOn", "TotalGTime", "LongestGTime", "WheelsOff", "TailNum"]
BTS_HEADER = [
    "Year", "Quarter", "Month", "DayofMonth", "DayOfWeek", "FlightDate", "Reporting_Airline",
    "DOT_ID_Reporting_Airline", "IATA_CODE_Reporting_Airline", "Tail_Number",
    "Flight_Number_Reporting_Airline", "OriginAirportID", "OriginAirportSeqID", "OriginCityMarketID",
    "Origin", "OriginCityName", "OriginState", "OriginStateFips", "OriginStateName", "OriginWac",
    "DestAirportID", "DestAirportSeqID", "DestCityMarketID", "Dest", "DestCityName", "DestState",
    "DestStateFips", "DestStateName", "DestWac", "CRSDepTime", "DepTime", "DepDelay", "DepDelayMinutes",
    "DepDel15", "DepartureDelayGroups", "DepTimeBlk", "TaxiOut", "WheelsOff", "WheelsOn", "TaxiIn",
    "CRSArrTime", "ArrTime", "ArrDelay", "ArrDelayMinutes", "ArrDel15", "ArrivalDelayGroups",
    "ArrTimeBlk", "Cancelled", "CancellationCode", "Diverted", "CRSElapsedTime", "ActualElapsedTime",
    "AirTime", "Flights", "Distance", "DistanceGroup", "CarrierDelay", "WeatherDelay", "NASDelay",
    "SecurityDelay", "LateAircraftDelay", "FirstDepTime", "TotalAddGTime", "LongestAddGTime",
    "DivAirportLandings", "DivReachedDest", "DivActualElapsedTime", "DivArrDelay", "DivDistance",
] + [f"Div{i}{f}" for i in range(1, 6) for f in DIV_FIELDS]

# code: (city, state, size weight, weather risk)
AIRPORTS = {
    "ATL": ("Atlanta, GA", "GA", 10, 1.0), "DFW": ("Dallas/Fort Worth, TX", "TX", 9, 1.1),
    "DEN": ("Denver, CO", "CO", 9, 1.3), "ORD": ("Chicago, IL", "IL", 9, 1.4),
    "LAX": ("Los Angeles, CA", "CA", 8, 0.7), "CLT": ("Charlotte, NC", "NC", 7, 1.0),
    "LAS": ("Las Vegas, NV", "NV", 6, 0.6), "PHX": ("Phoenix, AZ", "AZ", 6, 0.6),
    "MCO": ("Orlando, FL", "FL", 6, 1.2), "SEA": ("Seattle, WA", "WA", 6, 0.9),
    "MIA": ("Miami, FL", "FL", 5, 1.2), "IAH": ("Houston, TX", "TX", 6, 1.2),
    "JFK": ("New York, NY", "NY", 6, 1.3), "EWR": ("Newark, NJ", "NJ", 6, 1.5),
    "SFO": ("San Francisco, CA", "CA", 6, 1.1), "BOS": ("Boston, MA", "MA", 5, 1.2),
    "MSP": ("Minneapolis, MN", "MN", 5, 1.2), "DTW": ("Detroit, MI", "MI", 5, 1.1),
    "LGA": ("New York, NY", "NY", 5, 1.5), "SLC": ("Salt Lake City, UT", "UT", 4, 0.9),
    "BWI": ("Baltimore, MD", "MD", 4, 1.0), "DCA": ("Washington, DC", "VA", 4, 1.0),
    "SAN": ("San Diego, CA", "CA", 3, 0.6), "TPA": ("Tampa, FL", "FL", 3, 1.1),
    "AUS": ("Austin, TX", "TX", 3, 1.0), "BNA": ("Nashville, TN", "TN", 3, 1.0),
    "PDX": ("Portland, OR", "OR", 2, 0.9), "STL": ("St. Louis, MO", "MO", 2, 1.0),
    "MCI": ("Kansas City, MO", "MO", 2, 1.0), "RDU": ("Raleigh/Durham, NC", "NC", 2, 1.0),
    "BOI": ("Boise, ID", "ID", 1, 0.8), "ABQ": ("Albuquerque, NM", "NM", 1, 0.7),
}
# code: (hubs, base controllable-delay propensity)
CARRIERS = {
    "WN": (["DEN", "LAS", "PHX", "BWI", "MCO"], 1.1),
    "DL": (["ATL", "MSP", "DTW", "SLC"], 0.7),
    "AA": (["DFW", "CLT", "MIA", "PHX"], 1.0),
    "UA": (["ORD", "DEN", "IAH", "EWR", "SFO"], 0.95),
    "B6": (["JFK", "BOS", "MCO"], 1.35),
    "AS": (["SEA", "PDX", "SFO"], 0.8),
    "NK": (["MCO", "LAS", "DTW"], 1.4),
    "F9": (["DEN", "MCO", "LAS"], 1.5),
    "OO": (["DEN", "ORD", "SLC", "MSP"], 1.05),
}
STATE_FIPS = "01"
RNG = random.Random(42)


def hhmm(minutes: int) -> str:
    minutes %= 1440
    value = (minutes // 60) * 100 + minutes % 60
    return f"{value:04d}" if value else "2400"


def make_rows(ym: YearMonth, n_rows: int, iso_dates: bool) -> list[dict]:
    rows: list[dict] = []
    days = (date(*(ym.add(1).year, ym.add(1).month, 1)) - timedelta(days=1)).day
    codes = list(AIRPORTS)
    weights = [AIRPORTS[c][2] for c in codes]
    legs_per_day = 4
    tails_per_day = max(1, n_rows // (days * legs_per_day))
    flight_counter = 100
    for day in range(1, days + 1):
        d = date(ym.year, ym.month, day)
        weather_day = RNG.random() < 0.08  # some bad-weather days
        for t in range(tails_per_day):
            carrier = RNG.choice(list(CARRIERS))
            hubs, propensity = CARRIERS[carrier]
            hubs = [h for h in hubs if h in AIRPORTS]
            tail = f"N{t + 100:04d}{carrier}"
            here = RNG.choice(hubs)
            clock = RNG.randint(5 * 60, 9 * 60)
            carried_delay = 0
            for leg in range(legs_per_day):
                dest = RNG.choices(codes, weights)[0]
                while dest == here:
                    dest = RNG.choices(codes, weights)[0]
                distance = RNG.randint(150, 2500)
                block = 30 + distance // 8
                crs_dep, crs_arr = clock, clock + block
                cancelled = RNG.random() < (0.035 if weather_day else 0.012)
                cancel_code = RNG.choices("ABCD", [45, 40, 14, 1])[0] if cancelled else ""
                diverted = (not cancelled) and RNG.random() < 0.002
                row = {h: "" for h in BTS_HEADER}
                flight_counter += 1
                row.update({
                    "Year": ym.year, "Quarter": (ym.month - 1) // 3 + 1, "Month": ym.month,
                    "DayofMonth": day, "DayOfWeek": d.isoweekday(),
                    "FlightDate": d.isoformat() if iso_dates else f"{d.month}/{d.day}/{d.year} 12:00:00 AM",
                    "Reporting_Airline": carrier, "IATA_CODE_Reporting_Airline": carrier,
                    "DOT_ID_Reporting_Airline": "19393", "Tail_Number": "" if RNG.random() < 0.003 else tail,
                    "Flight_Number_Reporting_Airline": flight_counter % 9000 + 1,
                    "Origin": here, "OriginCityName": AIRPORTS[here][0], "OriginState": AIRPORTS[here][1],
                    "OriginStateFips": STATE_FIPS, "Dest": dest, "DestCityName": AIRPORTS[dest][0],
                    "DestState": AIRPORTS[dest][1], "DestStateFips": STATE_FIPS,
                    "CRSDepTime": hhmm(crs_dep), "CRSArrTime": hhmm(crs_arr),
                    "Cancelled": "1.00" if cancelled else "0.00", "CancellationCode": cancel_code,
                    "Diverted": "1.00" if diverted else "0.00", "Flights": "1.00",
                    "CRSElapsedTime": f"{block}.00", "Distance": f"{distance}.00",
                    "DistanceGroup": min(11, distance // 250 + 1),
                })
                if not cancelled:
                    hour_factor = 1 + max(0, (crs_dep - 12 * 60)) / 600  # later = worse
                    own = max(-10.0, RNG.gauss(-3, 9) + (RNG.random() < 0.10 * propensity * hour_factor) * RNG.expovariate(1 / 45))
                    weather = (RNG.random() < (0.25 if weather_day else 0.01) * AIRPORTS[here][3]) * RNG.expovariate(1 / 60)
                    nas = (RNG.random() < 0.05 * AIRPORTS[dest][3]) * RNG.expovariate(1 / 25)
                    security = (RNG.random() < 0.002) * RNG.randint(5, 30)
                    late = max(0, carried_delay - RNG.randint(20, 45))  # turn buffer absorbs some
                    dep_delay = round(own + weather + late + security)
                    arr_delay = round(dep_delay + nas + RNG.gauss(-4, 6))
                    row.update({
                        "DepTime": hhmm(crs_dep + dep_delay), "DepDelay": f"{dep_delay}.00",
                        "DepDelayMinutes": f"{max(0, dep_delay)}.00", "DepDel15": "1.00" if dep_delay >= 15 else "0.00",
                    })
                    if not diverted:
                        row.update({
                            "ArrTime": hhmm(crs_arr + arr_delay), "ArrDelay": f"{arr_delay}.00",
                            "ArrDelayMinutes": f"{max(0, arr_delay)}.00",
                            "ArrDel15": "1.00" if arr_delay >= 15 else "0.00",
                            "ActualElapsedTime": f"{block + arr_delay - dep_delay}.00",
                        })
                        if arr_delay >= 15:  # BTS only fills causes for 15+ minute arrival delays
                            parts = {"WeatherDelay": round(weather), "NASDelay": round(nas),
                                     "SecurityDelay": round(security), "LateAircraftDelay": round(late)}
                            parts["CarrierDelay"] = max(0, arr_delay - sum(parts.values()))
                            excess = sum(parts.values()) - arr_delay
                            for k in ("NASDelay", "WeatherDelay", "LateAircraftDelay", "SecurityDelay"):
                                take = min(parts[k], max(0, excess))
                                parts[k] -= take
                                excess -= take
                            row.update({k: f"{v}.00" for k, v in parts.items()})
                    carried_delay = max(0, arr_delay if not diverted else 0)
                else:
                    carried_delay = 0
                rows.append(row)
                here = dest if not cancelled else here
                clock = crs_arr + RNG.randint(35, 70)
    return rows


def write_zip(ym: YearMonth, rows: list[dict], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    text = io.StringIO()
    writer = csv.writer(text, quoting=csv.QUOTE_NONNUMERIC, lineterminator="\n")
    writer.writerow(BTS_HEADER + [""])  # real files end each line with a trailing comma
    for row in rows:
        writer.writerow([row[h] for h in BTS_HEADER] + [""])
    target = out_dir / zip_filename(ym)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"On_Time_Reporting_Carrier_On_Time_Performance_(1987_present)_{ym.year}_{ym.month}.csv", text.getvalue())
        zf.writestr("readme.html", "<html><body>SYNTHETIC SAMPLE - not real BTS data</body></html>")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--start", required=True, help="first month, YYYY-MM")
    parser.add_argument("--end", required=True, help="last month, YYYY-MM")
    parser.add_argument("--rows", type=int, default=20000, help="approximate rows per month")
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data" / "landing"))
    args = parser.parse_args()
    for i, ym in enumerate(month_range(YearMonth.parse(args.start), YearMonth.parse(args.end))):
        rows = make_rows(ym, args.rows, iso_dates=(i % 2 == 0))  # mix both date formats BTS has used
        path = write_zip(ym, rows, Path(args.out))
        print(f"{ym}: {len(rows):,} synthetic rows -> {path}")


if __name__ == "__main__":
    main()
