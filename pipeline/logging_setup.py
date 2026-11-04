"""Logging to the terminal and to logs/pipeline.log (one line per event, easy to grep)."""
from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_dir: Path, level: str = "INFO", run_id: str = "-") -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = f"%(asctime)s | %(levelname)-7s | run={run_id} | %(name)s | %(message)s"
    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "pipeline.log", encoding="utf-8"),
    ]
    logging.basicConfig(level=level.upper(), format=fmt, handlers=handlers, force=True)
    # third-party libraries are noisy at INFO
    for noisy in ("botocore", "boto3", "urllib3", "s3transfer"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
