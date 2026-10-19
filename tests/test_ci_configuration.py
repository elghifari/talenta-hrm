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


def test_ci_builds_frontend_and_runs_real_browser_acceptance():
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/backend.yml").read_text()
    for command in [
        "actions/setup-node@",
        "node-version-file: .node-version",
        "npm --prefix frontend ci",
        "npm --prefix frontend run typecheck",
        "npm --prefix frontend run lint",
        "npm --prefix frontend test -- --run",
        "npm --prefix frontend run build",
        "uv sync --frozen --group browser",
        "playwright install --with-deps chromium",
        "pytest --run-browser tests/browser -q",
    ]:
        assert command in workflow
    assert workflow.index("npm --prefix frontend run build") < workflow.index(
        "pytest --run-browser"
    )
