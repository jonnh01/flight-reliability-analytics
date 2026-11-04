"""Settings read from environment variables (and the .env file, if present).

Everything configurable lives here so the rest of the code never reads os.environ directly.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # python-dotenv is optional at import time so unit tests run without it
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


@dataclass(frozen=True)
class Settings:
    pg_host: str = field(default_factory=lambda: os.getenv("PGHOST", "localhost"))
    pg_port: int = field(default_factory=lambda: int(os.getenv("PGPORT", "5432")))
    pg_database: str = field(default_factory=lambda: os.getenv("PGDATABASE", "flights"))
    pg_user: str = field(default_factory=lambda: os.getenv("PGUSER", "postgres"))
    pg_password: str = field(default_factory=lambda: os.getenv("PGPASSWORD", ""))

    months_back: int = field(default_factory=lambda: int(os.getenv("MONTHS_BACK", "3")))

    s3_bucket: str = field(default_factory=lambda: os.getenv("S3_BUCKET", "").strip())
    s3_prefix: str = field(default_factory=lambda: os.getenv("S3_PREFIX", "raw/bts_ontime").strip("/"))
    aws_region: str = field(default_factory=lambda: os.getenv("AWS_REGION", "us-west-2"))

    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    cache_dir: Path = DATA_DIR / "cache"        # downloaded ZIPs (working copies)
    landing_dir: Path = DATA_DIR / "landing"    # drop manually downloaded ZIPs here
    archive_dir: Path = DATA_DIR / "archive"    # local raw archive when S3 is off
    marts_dir: Path = DATA_DIR / "marts"        # Parquet files the app reads (committed)
    tableau_dir: Path = DATA_DIR / "tableau"    # CSV copies for Tableau Public
    analysis_dir: Path = DATA_DIR / "analysis"  # flight-level sample for the notebook
    log_dir: Path = REPO_ROOT / "logs"

    @property
    def use_s3(self) -> bool:
        return bool(self.s3_bucket)

    def pg_conninfo(self) -> str:
        parts = [
            f"host={self.pg_host}",
            f"port={self.pg_port}",
            f"dbname={self.pg_database}",
            f"user={self.pg_user}",
        ]
        if self.pg_password:
            parts.append(f"password={self.pg_password}")
        return " ".join(parts)


def get_settings() -> Settings:
    return Settings()
