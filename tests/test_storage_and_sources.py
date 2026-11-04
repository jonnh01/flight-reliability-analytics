import shutil
from dataclasses import replace

import pytest

from pipeline.bts import MonthNotPublished, YearMonth, zip_filename
from pipeline.config import Settings
from pipeline.ingest import MonthSource, find_latest_month
from pipeline.storage import LocalArchive, archive_key


def make_settings(tmp_path):
    return replace(
        Settings(),
        cache_dir=tmp_path / "cache",
        landing_dir=tmp_path / "landing",
        archive_dir=tmp_path / "archive",
        s3_bucket="",
    )


def test_archive_key_layout():
    key = archive_key("raw/bts_ontime", YearMonth(2026, 7))
    assert key == (
        "raw/bts_ontime/year=2026/month=07/"
        "On_Time_Reporting_Carrier_On_Time_Performance_1987_present_2026_7.zip"
    )


def test_local_archive_round_trip(tmp_path):
    archive = LocalArchive(tmp_path / "archive")
    src = tmp_path / "file.zip"
    src.write_bytes(b"data")
    key = "raw/x/file.zip"
    assert not archive.exists(key)
    archive.put(src, key, {"sha256": "abc"})
    assert archive.exists(key)
    out = archive.get(key, tmp_path / "out" / "file.zip")
    assert out.read_bytes() == b"data"


def test_landing_file_is_used_and_archived(tmp_path, sample_zip):
    ym, path, _ = sample_zip
    settings = make_settings(tmp_path)
    settings.landing_dir.mkdir(parents=True)
    shutil.copy(path, settings.landing_dir / zip_filename(ym))
    archive = LocalArchive(settings.archive_dir)
    source = MonthSource(settings, archive, offline=True)

    local, uri = source.obtain(ym)
    assert local.is_file()
    assert archive.exists(archive_key(settings.s3_prefix, ym))
    assert uri.startswith("file://")


def test_archive_restores_when_cache_is_empty(tmp_path, sample_zip):
    ym, path, _ = sample_zip
    settings = make_settings(tmp_path)
    archive = LocalArchive(settings.archive_dir)
    archive.put(path, archive_key(settings.s3_prefix, ym), {"sha256": "x"})
    local, _ = MonthSource(settings, archive, offline=True).obtain(ym)
    assert local.read_bytes() == path.read_bytes()


def test_offline_missing_month_is_not_published(tmp_path):
    settings = make_settings(tmp_path)
    source = MonthSource(settings, LocalArchive(settings.archive_dir), offline=True)
    with pytest.raises(MonthNotPublished):
        source.obtain(YearMonth(2026, 1))


def test_find_latest_month_walks_back_to_newest_available(tmp_path, sample_zip):
    from datetime import date

    ym, path, _ = sample_zip  # 2026-05
    settings = make_settings(tmp_path)
    settings.landing_dir.mkdir(parents=True)
    shutil.copy(path, settings.landing_dir / zip_filename(ym))
    source = MonthSource(settings, LocalArchive(settings.archive_dir), offline=True)
    # "today" is 2026-08-10: July and June are missing, May exists
    assert find_latest_month(source, today=date(2026, 8, 10)) == ym


def test_s3_archive_with_moto(tmp_path):
    moto = pytest.importorskip("moto")
    import boto3

    from pipeline.storage import S3Archive

    with moto.mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-bucket")
        archive = S3Archive("test-bucket", "us-east-1", client=client)
        src = tmp_path / "f.zip"
        src.write_bytes(b"zipdata")
        assert not archive.exists("raw/f.zip")
        uri = archive.put(src, "raw/f.zip", {"sha256": "deadbeef"})
        assert uri == "s3://test-bucket/raw/f.zip"
        assert archive.exists("raw/f.zip")
        assert archive.get("raw/f.zip", tmp_path / "back.zip").read_bytes() == b"zipdata"
