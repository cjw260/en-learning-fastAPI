import json
from dataclasses import replace
from pathlib import Path

import pytest

from en_learning.bootstrap.manifest import ECDICT_SOURCE, SourceManifest
from en_learning.bootstrap.source import SourceVerificationError, sha256_file, verify_source


def fixture_manifest(path: Path) -> SourceManifest:
    return replace(
        ECDICT_SOURCE,
        filename=path.name,
        sha256=sha256_file(path),
        size_bytes=path.stat().st_size,
    )


def test_pinned_ecdict_manifest_is_complete() -> None:
    assert ECDICT_SOURCE.repository == "https://github.com/skywind3000/ECDICT"
    assert ECDICT_SOURCE.tag == "1.0.28"
    assert ECDICT_SOURCE.commit == "8defb761f7c7ad1818ca94290a1844d7b33d6b23"
    assert ECDICT_SOURCE.sha256 == (
        "d0ce61e560b50d9905d20de3173aa3ca80950ce235bedd21c53e025cf9f38cb0"
    )
    assert ECDICT_SOURCE.size_bytes == 65_936_699
    assert ECDICT_SOURCE.license_name == "MIT"
    assert ECDICT_SOURCE.commit in ECDICT_SOURCE.download_url
    assert ECDICT_SOURCE.commit in ECDICT_SOURCE.license_url

    resource = Path(__file__).resolve().parents[1] / "resources" / "ecdict-source.json"
    recorded = json.loads(resource.read_text(encoding="utf-8"))
    assert recorded["commit"] == ECDICT_SOURCE.commit
    assert recorded["sha256"] == ECDICT_SOURCE.sha256
    assert recorded["size_bytes"] == ECDICT_SOURCE.size_bytes


def test_source_verification_records_digest_and_rejects_changes(tmp_path: Path) -> None:
    source = tmp_path / "ecdict.csv"
    source.write_bytes(b"word,phonetic\nhello,phonetic\n")
    manifest = fixture_manifest(source)

    result = verify_source(source, manifest)
    assert result["verified"] is True
    assert result["sha256"] == sha256_file(source)
    assert result["path"] == str(source.resolve())

    source.write_bytes(source.read_bytes() + b"changed")
    with pytest.raises(SourceVerificationError, match="size mismatch"):
        verify_source(source, manifest)
