"""Load BTS months into Postgres.  Run:  python -m pipeline.ingest --help

Typical use:
    python -m pipeline.ingest                    # rolling window of MONTHS_BACK months
    python -m pipeline.ingest --months-back 24   # backfill two years
    python -m pipeline.ingest --month 2026-07    # one specific month
    python -m pipeline.ingest --offline          # never call BTS; use landing/archive files

For each month the loader:
  1. finds the ZIP: local cache -> data/landing (manual downloads) -> raw archive -> BTS
  2. archives the original ZIP (S3 or data/archive) if it is not archived yet
  3. skips the month if the same file (same SHA-256) is already loaded
  4. otherwise validates the columns and replaces the month in one transaction
Exit code 0 = success or nothing new; 1 = failure (so schedulers notice).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from pipeline import bts, db
from pipeline.bts import MonthNotPublished, YearMonth
from pipeline.config import Settings, get_settings
from pipeline.logging_setup import setup_logging
from pipeline.storage import RawArchive, archive_key, build_archive

log = logging.getLogger("pipeline.ingest")

# How far back from today to look for the newest published month (BTS lags ~2 months).
MAX_PUBLICATION_LAG_MONTHS = 6


@dataclass
class RunResult:
    run_id: str
    status: str = "running"
    months_requested: list[str] = field(default_factory=list)
    months_loaded: list[str] = field(default_factory=list)
    months_skipped: list[str] = field(default_factory=list)
    rows_loaded: int = 0
    latest_month: str | None = None
    error: str | None = None


class MonthSource:
    """Finds a month's ZIP locally, in the archive, or on the BTS website."""

    def __init__(self, settings: Settings, archive: RawArchive, offline: bool):
        self.settings = settings
        self.archive = archive
        self.offline = offline

    def _landing_file(self, ym: YearMonth) -> Path | None:
        landing = self.settings.landing_dir
        if not landing.is_dir():
            return None
        exact = landing / bts.zip_filename(ym)
        if exact.is_file():
            return exact
        matches = sorted(landing.glob(f"*_{ym.year}_{ym.month}.zip"))
        return matches[0] if matches else None

    def obtain(self, ym: YearMonth) -> tuple[Path, str]:
        """Return (local zip path, archive uri). Raises MonthNotPublished if unavailable."""
        cache = self.settings.cache_dir / bts.zip_filename(ym)
        key = archive_key(self.settings.s3_prefix, ym)
        cache.parent.mkdir(parents=True, exist_ok=True)

        if not (cache.is_file() and zipfile.is_zipfile(cache)):
            landing = self._landing_file(ym)
            if landing:
                log.info("%s: using manually downloaded file %s", ym, landing.name)
                shutil.copy2(landing, cache)
            elif self.archive.exists(key):
                log.info("%s: restoring from archive %s", ym, self.archive.uri(key))
                self.archive.get(key, cache)
            elif self.offline:
                raise MonthNotPublished(f"{ym}: not in cache, landing or archive (offline mode)")
            else:
                downloaded = bts.download_month(ym, self.settings.cache_dir)
                if downloaded != cache:
                    shutil.move(downloaded, cache)

        if not self.archive.exists(key):
            metadata = {
                "sha256": bts.sha256_of(cache),
                "source_url": bts.source_url(ym),
                "archived_at": datetime.now(timezone.utc).isoformat(),
            }
            self.archive.put(cache, key, metadata)
        return cache, self.archive.uri(key)


def find_latest_month(source: MonthSource, today: date | None = None) -> YearMonth:
    """Newest month we can actually obtain, searching back from last month."""
    current = YearMonth.from_date(today or date.today())
    for lag in range(1, MAX_PUBLICATION_LAG_MONTHS + 1):
        candidate = current.add(-lag)
        try:
            source.obtain(candidate)
            log.info("latest available month: %s", candidate)
            return candidate
        except MonthNotPublished as exc:
            log.info("%s not available yet (%s)", candidate, exc)
        except OSError as exc:  # network errors (requests' exceptions are OSErrors)
            log.warning("%s could not be downloaded (%s) - trying an older month", candidate, exc)
    raise RuntimeError(
        f"no month in the last {MAX_PUBLICATION_LAG_MONTHS} months could be found - "
        "check the BTS URL, your network, or put files in data/landing/"
    )


def resolve_months(args, settings: Settings, source: MonthSource) -> tuple[list[YearMonth], bool]:
    """Return (months to load, whether this is a rolling window that may prune)."""
    if args.month:
        return [YearMonth.parse(args.month)], False
    if args.start or args.end:
        if not (args.start and args.end):
            raise SystemExit("--start and --end must be used together")
        return bts.month_range(YearMonth.parse(args.start), YearMonth.parse(args.end)), False
    latest = YearMonth.parse(args.latest) if args.latest else find_latest_month(source)
    months_back = args.months_back or settings.months_back
    return bts.rolling_window(latest, months_back), True


def write_status(settings: Settings, result: RunResult) -> None:
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result.__dict__, indent=2, default=str)
    (settings.log_dir / "last_run.json").write_text(payload)
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:  # shows up on the GitHub Actions run page
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(
                f"### Ingestion: {result.status}\n\n"
                f"- months requested: {', '.join(result.months_requested) or '-'}\n"
                f"- months loaded: {', '.join(result.months_loaded) or 'none'}\n"
                f"- months unchanged (skipped): {', '.join(result.months_skipped) or 'none'}\n"
                f"- rows loaded: {result.rows_loaded:,}\n"
                + (f"- error: `{result.error}`\n" if result.error else "")
            )


def run(args) -> RunResult:
    settings = get_settings()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:6]
    setup_logging(settings.log_dir, settings.log_level, run_id)
    result = RunResult(run_id=run_id)
    source = MonthSource(settings, build_archive(settings), offline=args.offline)

    with db.connect(settings) as conn:
        db.ensure_schema(conn)
        try:
            months, rolling = resolve_months(args, settings, source)
            result.months_requested = [str(m) for m in months]
            result.latest_month = str(months[-1])
            db.start_run(conn, run_id, months)
            already = db.loaded_months(conn)

            for ym in months:
                zip_path, archive_uri = source.obtain(ym)
                sha = bts.sha256_of(zip_path)
                if already.get(ym.key) == sha and not args.force:
                    log.info("%s: unchanged since last load, skipping", ym)
                    result.months_skipped.append(str(ym))
                    continue
                if ym.key in already:
                    log.warning("%s: source file changed (revised by BTS?) - reloading", ym)
                frame = bts.read_month(zip_path, expected=ym)
                result.rows_loaded += db.load_month(
                    conn,
                    ym,
                    frame,
                    source_file=zip_path.name,
                    source_url=bts.source_url(ym),
                    archive_uri=archive_uri,
                    sha256=sha,
                    run_id=run_id,
                )
                result.months_loaded.append(str(ym))

            if rolling and not args.no_prune:
                db.prune_months(conn, months)

            result.status = "success" if result.months_loaded else "no_new_data"
            db.finish_run(conn, run_id, result.status, [YearMonth.parse(m) for m in result.months_loaded],
                          [YearMonth.parse(m) for m in result.months_skipped], result.rows_loaded)
        except Exception as exc:  # record the failure, then re-raise for a non-zero exit
            result.status, result.error = "failed", f"{type(exc).__name__}: {exc}"
            log.exception("ingestion failed")
            try:
                db.finish_run(conn, run_id, "failed", [YearMonth.parse(m) for m in result.months_loaded],
                              [YearMonth.parse(m) for m in result.months_skipped], result.rows_loaded,
                              result.error)
            except Exception:  # pragma: no cover - the original error matters more
                log.exception("could not record the failed run")
            raise
        finally:
            write_status(settings, result)

    log.info(
        "done: status=%s loaded=%s skipped=%s rows=%s",
        result.status, result.months_loaded, result.months_skipped, f"{result.rows_loaded:,}",
    )
    return result


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Load BTS on-time data into Postgres.")
    parser.add_argument("--months-back", type=int, help="size of the rolling window (default: MONTHS_BACK)")
    parser.add_argument("--latest", help="treat this month (YYYY-MM) as the newest instead of detecting it")
    parser.add_argument("--month", help="load only this month (YYYY-MM)")
    parser.add_argument("--start", help="first month of an explicit range (YYYY-MM)")
    parser.add_argument("--end", help="last month of an explicit range (YYYY-MM)")
    parser.add_argument("--force", action="store_true", help="reload months even if unchanged")
    parser.add_argument("--offline", action="store_true", help="never download from BTS")
    parser.add_argument("--no-prune", action="store_true", help="keep months outside the window")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        run(parse_args(argv))
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
