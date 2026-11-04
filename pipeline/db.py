"""Postgres access for the loader: schema setup, idempotent month loads, run tracking."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from pipeline.bts import RAW_COLUMNS, YearMonth, to_copy_buffer

log = logging.getLogger(__name__)
SQL_DIR = Path(__file__).parent / "sql"


@contextmanager
def connect(settings):
    import psycopg

    # autocommit: each statement commits on its own, and `with conn.transaction()` blocks
    # are real all-or-nothing transactions (not savepoints inside a forgotten outer one)
    conn = psycopg.connect(settings.pg_conninfo(), autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


def ensure_schema(conn) -> None:
    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        conn.execute(sql_file.read_text())


def loaded_months(conn) -> dict[int, str]:
    """{year_month: sha256} for every month currently loaded."""
    rows = conn.execute("select year_month, source_sha256 from raw.load_log").fetchall()
    return {ym: sha for ym, sha in rows}


def load_month(
    conn,
    ym: YearMonth,
    frame: pd.DataFrame,
    *,
    source_file: str,
    source_url: str,
    archive_uri: str,
    sha256: str,
    run_id: str,
) -> int:
    """Replace one month in raw.bts_flights inside a single transaction.

    Delete-then-insert in one transaction means a crash halfway leaves the previous
    version of the month untouched, and rerunning never duplicates rows.
    """
    loaded_at = datetime.now(timezone.utc)
    frame = frame.copy()
    frame["_year_month"] = ym.key
    frame["_source_file"] = source_file
    frame["_source_sha256"] = sha256
    frame["_loaded_at"] = loaded_at.isoformat()
    columns = RAW_COLUMNS + ["_year_month", "_source_file", "_source_sha256", "_loaded_at"]
    buffer = to_copy_buffer(frame, columns)

    with conn.transaction():
        conn.execute("delete from raw.bts_flights where _year_month = %s", (ym.key,))
        copy_sql = f"copy raw.bts_flights ({', '.join(columns)}) from stdin with (format csv)"
        with conn.cursor().copy(copy_sql) as copy:
            while chunk := buffer.read(8 * 1024 * 1024):
                copy.write(chunk)

        loaded = conn.execute(
            "select count(*) from raw.bts_flights where _year_month = %s", (ym.key,)
        ).fetchone()[0]
        if loaded != len(frame):  # row-count reconciliation: file vs database
            raise RuntimeError(f"{ym}: file has {len(frame)} rows but {loaded} were loaded")

        conn.execute(
            """
            insert into raw.load_log
                (year_month, source_file, source_url, archive_uri, source_sha256,
                 row_count, loaded_at, run_id)
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (year_month) do update set
                source_file = excluded.source_file,
                source_url = excluded.source_url,
                archive_uri = excluded.archive_uri,
                source_sha256 = excluded.source_sha256,
                row_count = excluded.row_count,
                loaded_at = excluded.loaded_at,
                run_id = excluded.run_id
            """,
            (ym.key, source_file, source_url, archive_uri, sha256, loaded, loaded_at, run_id),
        )
    log.info("%s: loaded %s rows into raw.bts_flights", ym, f"{loaded:,}")
    return loaded


def prune_months(conn, keep: list[YearMonth]) -> list[int]:
    """Drop months outside the rolling window from the raw layer."""
    keep_keys = [ym.key for ym in keep]
    with conn.transaction():
        dropped = [
            r[0]
            for r in conn.execute(
                "delete from raw.load_log where not (year_month = any(%s)) returning year_month",
                (keep_keys,),
            ).fetchall()
        ]
        if dropped:
            conn.execute(
                "delete from raw.bts_flights where _year_month = any(%s)", (dropped,)
            )
    if dropped:
        log.info("pruned months outside the window: %s", dropped)
    return dropped


def start_run(conn, run_id: str, months: list[YearMonth]) -> None:
    conn.execute(
        "insert into raw.pipeline_runs (run_id, started_at, status, months_requested) "
        "values (%s, now(), 'running', %s)",
        (run_id, ",".join(map(str, months))),
    )


def finish_run(
    conn,
    run_id: str,
    status: str,
    loaded: list[YearMonth],
    skipped: list[YearMonth],
    rows: int,
    error: str | None = None,
) -> None:
    conn.execute(
        """
        update raw.pipeline_runs
        set finished_at = now(), status = %s, months_loaded = %s, months_skipped = %s,
            rows_loaded = %s, error_message = %s
        where run_id = %s
        """,
        (
            status,
            ",".join(map(str, loaded)),
            ",".join(map(str, skipped)),
            rows,
            (error or "")[:2000] or None,
            run_id,
        ),
    )
