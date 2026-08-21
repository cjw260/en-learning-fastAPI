from __future__ import annotations

import csv
import json
import os
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

import en_learning.bootstrap.cli as cli_module
from en_learning.bootstrap.ecdict import ECDICT_FIELDS
from en_learning.bootstrap.manifest import ECDICT_SOURCE
from en_learning.bootstrap.source import sha256_file
from en_learning.common.config import Settings
from tests.conftest import PROJECT_ROOT, settings_environment


def create_source(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=ECDICT_FIELDS)
        writer.writeheader()
        for index, exam in enumerate(("gk", "cet4", "gre", "ky"), start=1):
            writer.writerow(
                {
                    "word": f"p02-cli-{exam}",
                    "translation": f"fixture-{exam}",
                    "tag": exam,
                    "frq": str(index),
                }
            )


def test_one_command_bootstrap_on_empty_services_is_idempotent(
    isolated_postgres_url: str,
    minio_values: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    external_source = os.environ.get("P02_ECDICT_SOURCE")
    source = Path(external_source) if external_source else tmp_path / "ecdict.csv"
    report = tmp_path / "report.json"
    rejects = tmp_path / "rejects.jsonl"
    if external_source:
        expected_minimum_words = 700_000
    else:
        create_source(source)
        expected_minimum_words = 4
        manifest = replace(
            ECDICT_SOURCE,
            filename=source.name,
            sha256=sha256_file(source),
            size_bytes=source.stat().st_size,
        )
        monkeypatch.setattr(cli_module, "ECDICT_SOURCE", manifest)

    minio_environment = {
        "MINIO_ENDPOINT": str(minio_values["minio_endpoint"]),
        "MINIO_PORT": str(minio_values["minio_port"]),
        "MINIO_USE_SSL": "false",
        "MINIO_ACCESS_KEY": str(minio_values["minio_access_key"]),
        "MINIO_SECRET_KEY": str(minio_values["minio_secret_key"]),
        "MINIO_BUCKET": "avatar",
    }
    environment = settings_environment(
        ENVIRONMENT="test",
        DATABASE_URL=isolated_postgres_url,
        **minio_environment,
    )
    for key in (
        "ENVIRONMENT",
        "LOG_LEVEL",
        "DATABASE_URL",
        "REDIS_URL",
        "SECRET_KEY",
        "MINIO_ENDPOINT",
        "MINIO_PORT",
        "MINIO_USE_SSL",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "MINIO_BUCKET",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_API_KEY",
        "HTTP_TIMEOUT_SECONDS",
        "HEALTH_CHECK_TIMEOUT_SECONDS",
    ):
        monkeypatch.setenv(key, environment[key])

    arguments = [
        "--source",
        str(source),
        "--no-download",
        "--assets-dir",
        str(PROJECT_ROOT.parent / "server" / "prisma" / "assets"),
        "--report",
        str(report),
        "--rejects",
        str(rejects),
        "--batch-size",
        "1000",
    ]
    assert cli_module.main(arguments) == 0
    assert cli_module.main(arguments) == 0

    result = json.loads(report.read_text(encoding="utf-8"))
    assert result["status"] == "success"
    assert result["words"]["database_total"] >= expected_minimum_words
    assert result["words"]["inserted"] == 0
    assert result["words"]["updated"] == 0
    assert result["words"]["skipped"] + result["words"]["rejected"] == result["words"]["rows_read"]
    assert result["courses"]["database_total"] == 8
    assert result["courses"]["skipped"] == 8
    assert result["objects"]["skipped"] == 8
    assert result["objects"]["verified"] == 8
    assert set(result["protected_business_rows_after"].values()) == {0}


def test_command_failure_is_nonzero_and_writes_a_failure_report(
    settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = tmp_path / "failed-report.json"
    monkeypatch.setattr(cli_module, "ensure_source", lambda *_args, **_kwargs: {"verified": True})
    monkeypatch.setattr(cli_module, "validate_assets", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_module, "Settings", lambda: settings)

    def fail_migration(_backend_root: Path) -> None:
        raise RuntimeError("injected migration failure")

    monkeypatch.setattr(cli_module, "run_migrations", fail_migration)
    result_code = cli_module.main(["--report", str(report), "--no-download"])
    result = json.loads(report.read_text(encoding="utf-8"))
    assert result_code == 1
    assert result["status"] == "failed"
    assert result["error"] == {
        "type": "RuntimeError",
        "message": "injected migration failure",
    }
    serialized = report.read_text(encoding="utf-8")
    for secret in (
        settings.minio_access_key.get_secret_value(),
        settings.minio_secret_key.get_secret_value(),
        settings.deepseek_api_key.get_secret_value(),
    ):
        assert secret not in serialized


def test_production_environment_is_rejected_before_migration(
    settings: Settings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    production = settings.model_copy(update={"environment": "production"})
    migration = Mock()
    source = Mock(return_value={"verified": True})
    monkeypatch.setattr(cli_module, "ensure_source", source)
    monkeypatch.setattr(cli_module, "validate_assets", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_module, "Settings", lambda: production)
    monkeypatch.setattr(cli_module, "run_migrations", migration)

    report = tmp_path / "production-report.json"
    assert cli_module.main(["--report", str(report), "--no-download"]) == 1
    source.assert_not_called()
    migration.assert_not_called()
    result = json.loads(report.read_text(encoding="utf-8"))
    assert result["error"]["message"] == ("P02 bootstrap is disabled when ENVIRONMENT=production")
