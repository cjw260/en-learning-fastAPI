from __future__ import annotations

import hashlib
import os
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import BinaryIO

from en_learning.bootstrap.manifest import SourceManifest

CHUNK_SIZE = 1024 * 1024


class SourceVerificationError(RuntimeError):
    """The configured source is absent or differs from the pinned manifest."""


def sha256_stream(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    while chunk := stream.read(CHUNK_SIZE):
        digest.update(chunk)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    with path.open("rb") as source:
        return sha256_stream(source)


def verify_source(path: Path, manifest: SourceManifest) -> dict[str, object]:
    if not path.is_file():
        raise SourceVerificationError(f"ECDICT source does not exist: {path}")
    size_bytes = path.stat().st_size
    if size_bytes != manifest.size_bytes:
        raise SourceVerificationError(
            f"ECDICT source size mismatch: expected {manifest.size_bytes}, got {size_bytes}"
        )
    actual_sha256 = sha256_file(path)
    if actual_sha256 != manifest.sha256:
        raise SourceVerificationError(
            f"ECDICT source SHA-256 mismatch: expected {manifest.sha256}, got {actual_sha256}"
        )
    return {**asdict(manifest), "path": str(path.resolve()), "verified": True}


def download_and_verify_source(path: Path, manifest: SourceManifest) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.download")
    request = urllib.request.Request(
        manifest.download_url,
        headers={"User-Agent": "en-learning-bootstrap/0.1"},
    )
    try:
        with (
            urllib.request.urlopen(request, timeout=60) as response,
            temporary.open("wb") as target,
        ):
            content_length = response.headers.get("Content-Length")
            if content_length is not None and int(content_length) != manifest.size_bytes:
                raise SourceVerificationError(
                    "ECDICT download Content-Length differs from the pinned manifest"
                )
            downloaded_bytes = 0
            while chunk := response.read(CHUNK_SIZE):
                downloaded_bytes += len(chunk)
                if downloaded_bytes > manifest.size_bytes:
                    raise SourceVerificationError("ECDICT download exceeds the pinned byte size")
                target.write(chunk)
        verification = verify_source(temporary, manifest)
        os.replace(temporary, path)
        return {**verification, "path": str(path.resolve()), "downloaded": True}
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def ensure_source(
    path: Path,
    manifest: SourceManifest,
    *,
    download_missing: bool,
) -> dict[str, object]:
    if path.exists() or not download_missing:
        return {**verify_source(path, manifest), "downloaded": False}
    return download_and_verify_source(path, manifest)
