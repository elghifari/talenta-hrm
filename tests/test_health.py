import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_endpoint_confirms_database_readiness():
    response = Client().get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_reports_unavailable_database_without_exposing_connection_details():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import django; django.setup(); from django.test import Client; "
                "r=Client(raise_request_exception=False).get('/api/health/'); "
                "print(r.status_code); print(r.content.decode())"
            ),
        ],
        cwd=Path(__file__).resolve().parents[1] / "backend",
        env={
            **os.environ,
            "DJANGO_SETTINGS_MODULE": "config.settings.development",
            "DATABASE_URL": "postgresql://hrm_dev@127.0.0.1:1/unreachable?connect_timeout=1",
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == '503\n{"status": "unavailable"}'
