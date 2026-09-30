import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("module", ["production", "staging"])
def test_deployment_settings_refuse_missing_secret(module):
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": f"config.settings.{module}"}
    env.pop("DJANGO_SECRET_KEY", None)
    result = subprocess.run(
        [sys.executable, str(ROOT / "backend/manage.py"), "check"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY is required" in result.stderr


@pytest.mark.parametrize("module", ["production", "staging"])
def test_deployment_settings_pass_security_checks_with_explicit_configuration(module):
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": f"config.settings.{module}",
        "DJANGO_SECRET_KEY": "synthetic-check-only-" + "abcdefgh12345678" * 4,
        "DATABASE_URL": "postgresql://hrm_dev@127.0.0.1:55439/hrm_dev",
        "DJANGO_ALLOWED_HOSTS": "hrm.example.test",
        "DJANGO_HSTS_INCLUDE_SUBDOMAINS": "true",
        "DJANGO_HSTS_PRELOAD": "true",
    }
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "backend/manage.py"),
            "check",
            "--deploy",
            "--fail-level",
            "WARNING",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
