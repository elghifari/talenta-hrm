from pathlib import Path


def test_ci_workflow_runs_the_postgres_backend_checks():
    path = Path(__file__).resolve().parents[1] / ".github/workflows/backend.yml"
    assert path.exists(), "The backend CI workflow is missing"
    workflow = path.read_text(encoding="utf-8")
    for required in [
        "postgres:15",
        "uv sync --frozen",
        "uv run pytest -q",
        "makemigrations --check --dry-run",
        "uv run ruff check .",
    ]:
        assert required in workflow
