def pytest_addoption(parser):
    parser.addoption("--no-slow", action="store_true", default=False, help="Disable the running of slow tests")
    parser.addoption("--no-local", action="store_true", default=False, help="Disable the running of local tests")
