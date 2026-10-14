"""A real server and a fresh browser context for every E2E test."""

import os
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import uvicorn

from app.main import create_app


def pytest_addoption(parser):
    # No custom options; use PLAYWRIGHT_HEADED env var instead.
    pass


@pytest.fixture
def live_server(tmp_path: Path) -> Iterator[str]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        config = uvicorn.Config(
            create_app(tmp_path / "browser-cars.db"),
            host=host,
            port=port,
            log_level="error",
            ws="none",
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                if not thread.is_alive() or time.monotonic() > deadline:
                    raise RuntimeError("The E2E server did not start")
                time.sleep(0.02)
            yield f"http://{host}:{port}"
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError("The E2E server did not stop")


@pytest.fixture(scope="session")
def browser(pytestconfig):
    from playwright.sync_api import sync_playwright

    headed = os.environ.get("PLAYWRIGHT_HEADED") == "1"

    with sync_playwright() as playwright:
        options = {"headless": not headed}
        executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
        if executable:
            options["executable_path"] = executable
        browser = playwright.chromium.launch(**options)
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    try:
        yield page
    finally:
        context.close()