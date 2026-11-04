"""Data loading and calculations for the Streamlit app. Plain pandas (no Streamlit here),
so it can be unit-tested; the pages wrap these loaders in st.cache_data."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

MARTS_DIR = Path(__file__).resolve().parent.parent / "data" / "marts"

CAUSE_COLUMNS = {
    "carrier_delay_min": "Carrier",
    "late_aircraft_delay_min": "Late-arriving aircraft",
    "nas_delay_min": "Air traffic system (NAS)",
    "weather_delay_min": "Weather",
    "security_delay_min": "Security",
}


def load_table(name: str, marts_dir: Path = MARTS_DIR) -> pd.DataFrame:
    parquet = marts_dir / f"{name}.parquet"
    if parquet.exists():
        return pd.read_parquet(parquet)
    frame = pd.read_csv(marts_dir / f"{name}.csv")
    for col in frame.columns:  # psql CSV exports write booleans as t/f
        if pd.api.types.is_string_dtype(frame[col]) and set(frame[col].dropna().unique()) <= {"t", "f"}:
            frame[col] = frame[col].map({"t": True, "f": False})
    return frame


def load_manifest(marts_dir: Path = MARTS_DIR) -> dict:
    path = marts_dir / "manifest.json"
    return json.loads(path.read_text()) if path.exists() else {}


def data_available(marts_dir: Path = MARTS_DIR) -> bool:
    return (marts_dir / "manifest.json").exists()


def month_label(year_month: int) -> str:
    """202607 -> 'Jul 2026'"""
    return pd.Timestamp(year=int(year_month) // 100, month=int(year_month) % 100, day=1).strftime("%b %Y")


def month_start(year_month: pd.Series) -> pd.Series:
    return pd.to_datetime(year_month.astype(int).astype(str) + "01", format="%Y%m%d")


def network_kpis(carrier_monthly: pd.DataFrame, year_month: int | None = None) -> dict:
    """Network-wide KPIs for one month (or all months when year_month is None)."""
    df = carrier_monthly if year_month is None else carrier_monthly[carrier_monthly.year_month == year_month]
    flights = df.scheduled_flights.sum()
    completed = df.completed_flights.sum()
    cause_total = df[list(CAUSE_COLUMNS)].sum().sum()
    return {
        "flights": int(flights),
        "on_time_rate": df.on_time_flights.sum() / flights if flights else float("nan"),
        "cancellation_rate": df.cancelled_flights.sum() / flights if flights else float("nan"),
        "avg_arr_delay_min": (df.avg_arr_delay_min * df.completed_flights).sum() / completed if completed else float("nan"),
        "controllable_share": (df.carrier_delay_min.sum() + df.late_aircraft_delay_min.sum()) / cause_total
        if cause_total else float("nan"),
    }


def whatif_on_time(
    delayed: pd.DataFrame,
    total_flights: int,
    on_time_flights: int,
    reductions: dict[str, float],
    threshold: int = 15,
) -> dict:
    """HYPOTHETICAL: cut each cause's delay minutes by a share and count how many delayed
    flights would have arrived under the threshold.

    reductions maps a cause column to a share between 0 and 1 (0.2 = 20% fewer minutes).
    Simplifications (shown in the app): every flight's minutes shrink by the same share;
    no knock-on effects on later flights; cancellations unchanged.
    """
    saved = sum(delayed[col] * share for col, share in reductions.items())
    new_delay = delayed["arr_delay_min"] - saved
    recovered = int((new_delay < threshold).sum())
    return {
        "recovered_flights": recovered,
        "current_on_time_rate": on_time_flights / total_flights if total_flights else float("nan"),
        "scenario_on_time_rate": (on_time_flights + recovered) / total_flights if total_flights else float("nan"),
        "minutes_saved": float(saved.sum()),
    }
