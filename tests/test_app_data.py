import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import data  # noqa: E402


def test_month_label():
    assert data.month_label(202607) == "Jul 2026"


def test_whatif_counts_only_flights_pushed_under_threshold():
    delayed = pd.DataFrame({
        "arr_delay_min":           [20, 40, 100],
        "late_aircraft_delay_min": [10, 30, 0],
        "carrier_delay_min":       [10, 10, 100],
        "nas_delay_min":           [0, 0, 0],
    })
    result = data.whatif_on_time(delayed, total_flights=10, on_time_flights=7,
                                 reductions={"late_aircraft_delay_min": 1.0})
    # flight 1: 20-10=10 (<15, recovered); flight 2: 40-30=10 (recovered); flight 3 unchanged
    assert result["recovered_flights"] == 2
    assert result["scenario_on_time_rate"] == pytest.approx(0.9)
    assert result["minutes_saved"] == 40


def test_whatif_zero_reduction_changes_nothing():
    delayed = pd.DataFrame({"arr_delay_min": [30], "late_aircraft_delay_min": [30]})
    result = data.whatif_on_time(delayed, 5, 4, {"late_aircraft_delay_min": 0.0})
    assert result["recovered_flights"] == 0
    assert result["scenario_on_time_rate"] == result["current_on_time_rate"]


def test_network_kpis_weights_by_flights():
    cm = pd.DataFrame({
        "year_month": [202607, 202607],
        "scheduled_flights": [100, 300], "completed_flights": [90, 290],
        "on_time_flights": [50, 270], "cancelled_flights": [10, 10],
        "avg_arr_delay_min": [20.0, 5.0],
        "carrier_delay_min": [10, 10], "late_aircraft_delay_min": [10, 10],
        "nas_delay_min": [10, 10], "weather_delay_min": [0, 0], "security_delay_min": [0, 0],
    })
    kpis = data.network_kpis(cm, 202607)
    assert kpis["flights"] == 400
    assert kpis["on_time_rate"] == pytest.approx(0.8)
    assert kpis["avg_arr_delay_min"] == pytest.approx((20 * 90 + 5 * 290) / 380)
    assert kpis["controllable_share"] == pytest.approx(40 / 60)
