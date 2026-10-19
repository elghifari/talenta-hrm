def pytest_addoption(parser):
    parser.addoption("--run-browser", action="store_true", help="Run isolated real-browser tests")


def pytest_ignore_collect(collection_path, config):
    return collection_path.name == "browser" and not config.getoption("--run-browser")
