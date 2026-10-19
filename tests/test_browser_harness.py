from pathlib import Path


def test_browser_collection_requires_explicit_opt_in(pytestconfig):
    assert pytestconfig.getoption("--run-browser") is False
    from conftest import pytest_ignore_collect

    assert pytest_ignore_collect(Path("tests/browser"), pytestconfig)
