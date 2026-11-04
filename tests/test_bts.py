import io
import zipfile

import pytest

from pipeline import bts
from pipeline.bts import RAW_COLUMNS, SourceSchemaError, YearMonth


def test_year_month_arithmetic():
    assert YearMonth(2026, 1).add(-1) == YearMonth(2025, 12)
    assert YearMonth(2025, 12).add(1) == YearMonth(2026, 1)
    assert YearMonth.parse("2026-07").key == 202607
    assert str(YearMonth(2026, 7)) == "2026-07"
    with pytest.raises(ValueError):
        YearMonth(2026, 13)


def test_rolling_window_is_inclusive_and_ordered():
    window = bts.rolling_window(YearMonth(2026, 2), 3)
    assert window == [YearMonth(2025, 12), YearMonth(2026, 1), YearMonth(2026, 2)]
    assert len(bts.rolling_window(YearMonth(2026, 7), 24)) == 24


def test_source_url_uses_unpadded_month():
    url = bts.source_url(YearMonth(2026, 7))
    assert url.endswith("_2026_7.zip")
    assert url.startswith("https://transtats.bts.gov/PREZIP/")


def test_read_month_returns_raw_columns_as_text(sample_zip):
    ym, path, n_rows = sample_zip
    frame = bts.read_month(path, expected=ym)
    assert list(frame.columns) == RAW_COLUMNS
    assert len(frame) == n_rows
    import pandas as pd

    assert all(pd.api.types.is_string_dtype(dtype) for dtype in frame.dtypes)
    # blanks stay blank strings (become NULL in Postgres), never NaN or 0
    assert (frame["carrier_delay"] == "").any()


def test_read_month_rejects_wrong_month(sample_zip):
    _, path, _ = sample_zip
    with pytest.raises(SourceSchemaError, match="expected only"):
        bts.read_month(path, expected=YearMonth(2026, 6))


def test_missing_required_column_is_reported(tmp_path):
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("data.csv", "Year,Month,FlightDate\n2026,5,2026-05-01\n")
    with pytest.raises(SourceSchemaError, match="missing"):
        bts.read_month(path)


def test_zip_must_contain_exactly_one_csv(tmp_path):
    path = tmp_path / "two.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("a.csv", "x\n1\n")
        zf.writestr("b.csv", "x\n1\n")
    with pytest.raises(SourceSchemaError, match="exactly one CSV"):
        bts.read_month(path)


def test_copy_buffer_has_no_header_and_keeps_order(sample_zip):
    ym, path, n_rows = sample_zip
    frame = bts.read_month(path, expected=ym)
    lines = bts.to_copy_buffer(frame).read().splitlines()
    assert len(lines) == n_rows
    assert not lines[0].startswith("year")


def test_sha256_changes_when_file_changes(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_bytes(b"one")
    b.write_bytes(b"two")
    assert bts.sha256_of(a) != bts.sha256_of(b)
    assert len(bts.sha256_of(a)) == 64


def test_download_treats_404_as_not_published(monkeypatch, tmp_path):
    requests = pytest.importorskip("requests")

    class FakeResponse:
        status_code = 404

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(requests.Session, "get", lambda self, *a, **k: FakeResponse())
    with pytest.raises(bts.MonthNotPublished):
        bts.download_month(YearMonth(2099, 1), tmp_path)


def test_download_rejects_html_instead_of_zip(monkeypatch, tmp_path):
    requests = pytest.importorskip("requests")

    class FakeResponse:
        status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            yield b"<html>not found</html>"

    monkeypatch.setattr(requests.Session, "get", lambda self, *a, **k: FakeResponse())
    with pytest.raises(bts.MonthNotPublished, match="not a ZIP"):
        bts.download_month(YearMonth(2099, 1), tmp_path)
    assert not list(tmp_path.glob("*.zip"))  # no half-written file left behind


def test_copy_buffer_round_trips_through_csv(sample_zip):
    import pandas as pd

    ym, path, _ = sample_zip
    frame = bts.read_month(path, expected=ym)
    back = pd.read_csv(io.StringIO(bts.to_copy_buffer(frame).read()), header=None, dtype=str, keep_default_na=False)
    assert back.shape == frame.shape
