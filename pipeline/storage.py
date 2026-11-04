"""Raw-file archive: AWS S3 when S3_BUCKET is set, otherwise a local folder.

Why an archive at all? The original BTS ZIP for every month is kept exactly as downloaded,
so any month can be reprocessed later (new cleaning rule, revised file, rebuilt database)
without depending on the BTS website. In GitHub Actions, where the database is thrown away
after each run, the archive is what lets a monthly run rebuild the full history quickly.

Both archives store files under the same keys:
    raw/bts_ontime/year=2026/month=07/On_Time_Reporting_..._2026_7.zip
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Protocol

from pipeline.bts import YearMonth, sha256_of, zip_filename

log = logging.getLogger(__name__)


def archive_key(prefix: str, ym: YearMonth) -> str:
    return f"{prefix.strip('/')}/year={ym.year}/month={ym.month:02d}/{zip_filename(ym)}"


class RawArchive(Protocol):
    def exists(self, key: str) -> bool: ...
    def put(self, local_path: Path, key: str, metadata: dict[str, str]) -> str: ...
    def get(self, key: str, local_path: Path) -> Path: ...
    def uri(self, key: str) -> str: ...


class LocalArchive:
    def __init__(self, root: Path):
        self.root = root

    def _path(self, key: str) -> Path:
        return self.root / key

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def put(self, local_path: Path, key: str, metadata: dict[str, str]) -> str:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, target)
        # keep the checksum beside the file, like S3 object metadata
        target.with_suffix(".sha256").write_text(metadata.get("sha256", sha256_of(target)))
        return self.uri(key)

    def get(self, key: str, local_path: Path) -> Path:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if self._path(key).resolve() != local_path.resolve():
            shutil.copy2(self._path(key), local_path)
        return local_path

    def uri(self, key: str) -> str:
        return self._path(key).as_uri()


class S3Archive:
    def __init__(self, bucket: str, region: str, client=None):
        import boto3

        self.bucket = bucket
        self.client = client or boto3.client("s3", region_name=region)

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as err:
            if err.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            raise  # permission problems should fail loudly, not look like "missing"

    def put(self, local_path: Path, key: str, metadata: dict[str, str]) -> str:
        self.client.upload_file(
            str(local_path),
            self.bucket,
            key,
            ExtraArgs={"Metadata": metadata, "ServerSideEncryption": "AES256"},
        )
        # verify the upload landed and carries our checksum
        head = self.client.head_object(Bucket=self.bucket, Key=key)
        if head.get("Metadata", {}).get("sha256") != metadata.get("sha256"):
            raise RuntimeError(f"S3 upload verification failed for s3://{self.bucket}/{key}")
        log.info("archived to %s", self.uri(key))
        return self.uri(key)

    def get(self, key: str, local_path: Path) -> Path:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, key, str(local_path))
        return local_path

    def uri(self, key: str) -> str:
        return f"s3://{self.bucket}/{key}"


def build_archive(settings) -> RawArchive:
    if settings.use_s3:
        log.info("raw archive: S3 bucket %s", settings.s3_bucket)
        return S3Archive(settings.s3_bucket, settings.aws_region)
    log.info("raw archive: local folder %s (set S3_BUCKET to use S3)", settings.archive_dir)
    return LocalArchive(settings.archive_dir)
