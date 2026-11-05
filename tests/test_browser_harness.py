from pathlib import Path


def test_browser_collection_requires_explicit_opt_in(pytestconfig):
    assert pytestconfig.getoption("--run-browser") is False
    import importlib.util

    path = Path(__file__).with_name("conftest.py")
    spec = importlib.util.spec_from_file_location("root_conftest", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.pytest_ignore_collect(Path("tests/browser"), pytestconfig)
