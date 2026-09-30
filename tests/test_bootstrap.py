import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_django_project_passes_system_checks():
    result = subprocess.run(
        [sys.executable, str(ROOT / "backend" / "manage.py"), "check"],
        capture_output=True,
        text=True,
        env={**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings.development"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "System check identified no issues" in result.stdout
