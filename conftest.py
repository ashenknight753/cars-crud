def pytest_addoption(parser):
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="Show the E2E browser window",
    )