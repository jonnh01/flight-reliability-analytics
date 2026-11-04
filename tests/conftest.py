import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture
def sample_zip(tmp_path):
    """One small synthetic BTS month written in the real file layout."""
    import make_sample_data as msd
    from pipeline.bts import YearMonth

    ym = YearMonth(2026, 5)
    rows = msd.make_rows(ym, 600, iso_dates=False)
    return ym, msd.write_zip(ym, rows, tmp_path), len(rows)
