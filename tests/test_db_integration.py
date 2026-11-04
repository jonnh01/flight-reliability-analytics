"""Runs against a real Postgres. Skipped unless psycopg is installed and PGHOST is set
(GitHub Actions CI sets both; locally, `make test` uses your .env).

Uses a fake month far in the past (1999-01) so it never touches real loaded months."""
import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
pytestmark = pytest.mark.skipif(not os.getenv("PGHOST"), reason="PGHOST not set")

from pipeline import bts, db  # noqa: E402
from pipeline.bts import YearMonth  # noqa: E402
from pipeline.config import get_settings  # noqa: E402

TEST_MONTH = YearMonth(1999, 1)


@pytest.fixture
def conn():
    settings = get_settings()
    with db.connect(settings) as connection:
        db.ensure_schema(connection)
        yield connection
        # clean up: keep every real month, drop only the test month
        others = [YearMonth(k // 100, k % 100) for k in db.loaded_months(connection) if k != TEST_MONTH.key]
        db.prune_months(connection, keep=others)


def test_load_is_idempotent_and_reconciles(conn, sample_zip):
    ym, path, n_rows = sample_zip
    frame = bts.read_month(path, expected=ym)
    kwargs = dict(source_file=path.name, source_url="test", archive_uri="test",
                  sha256=bts.sha256_of(path), run_id=f"test-{uuid.uuid4().hex[:6]}")

    assert db.load_month(conn, TEST_MONTH, frame, **kwargs) == n_rows
    assert db.load_month(conn, TEST_MONTH, frame, **kwargs) == n_rows  # replaces, never duplicates

    count = conn.execute(
        "select count(*) from raw.bts_flights where _year_month = %s", (TEST_MONTH.key,)
    ).fetchone()[0]
    assert count == n_rows
    assert db.loaded_months(conn)[TEST_MONTH.key] == kwargs["sha256"]


def test_run_tracking(conn):
    run_id = f"test-{uuid.uuid4().hex[:6]}"
    db.start_run(conn, run_id, [TEST_MONTH])
    db.finish_run(conn, run_id, "no_new_data", [], [TEST_MONTH], 0)
    status = conn.execute("select status from raw.pipeline_runs where run_id = %s", (run_id,)).fetchone()[0]
    assert status == "no_new_data"
    conn.execute("delete from raw.pipeline_runs where run_id = %s", (run_id,))
