
"""Regression tests for the restricted local frontend server."""

from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread

import pytest

from scripts.serve_frontend import (
    FrontendHandler,
    PUBLIC_FILES,
    PROJECT_ROOT,
)


@pytest.fixture
def frontend_server(tmp_path):
    root = tmp_path / "portfolio"
    root.mkdir()

    # Create synthetic versions of all approved public files.
    for relative_path in PUBLIC_FILES:
        file = root / relative_path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("public test content", encoding="utf-8")

    # Fake private files. Never use real credentials in tests.
    private_files = [
        ".env",
        ".env.production",
        ".git/config",
        "backend/main.py",
        "images/.DS_Store",
        "resume/.DS_Store",
        "images/private-notes.txt",
    ]

    for relative_path in private_files:
        file = root / relative_path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("synthetic private content", encoding="utf-8")

    outside_file = tmp_path / "outside-secret.txt"
    outside_file.write_text(
        "synthetic outside content",
        encoding="utf-8",
    )

    handler = partial(FrontendHandler, root=root)

    # Port 0 asks the OS for an available temporary port.
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield root, outside_file, server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def request(port, path, method="GET"):
    connection = HTTPConnection("127.0.0.1", port, timeout=5)

    try:
        connection.request(method, path)
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


@pytest.mark.parametrize("path", [
    "/",
    "/?utm_source=linkedin&utm_campaign=portfolio_test",
    "/?c=pp_example",
    *sorted(f"/{file}" for file in PUBLIC_FILES),
])
def test_approved_files_are_served(frontend_server, path):
    _, _, port = frontend_server

    status, body = request(port, path)

    assert status == 200
    assert body == b"public test content"


@pytest.mark.parametrize("path", [
    "/.env",
    "/.env.production",
    "/.git/config",
    "/backend/main.py",
    "/images/.DS_Store",
    "/resume/.DS_Store",
    "/images/private-notes.txt",
    "/missing.txt",
    "/images/",
    "/resume/",
    "/papers/",
    "/backend/",
    "/.git/",
    "/images",
    "/resume",
    "/../.env",
    "/images/../.env",
    "/images/../index.html",
    "/%2e%2e/.env",
    "/images/%2e%2e/.env",
    "/images/%2E%2E/index.html",
    "/images%2f..%2f.env",
    "/images/%252e%252e/.env",
    "/%2eenv",
    "/images/..%5c.env",
    "/index.html%00",
    "/images//inference.png",
])
def test_unapproved_paths_are_rejected(frontend_server, path):
    _, _, port = frontend_server

    status, body = request(port, path)

    assert status == 404
    assert b"synthetic private content" not in body
    assert b"Directory listing" not in body


def test_approved_filename_cannot_escape_via_symlink(frontend_server):
    root, outside_file, port = frontend_server

    approved_file = root / "index.html"
    approved_file.unlink()
    approved_file.symlink_to(outside_file)

    status, body = request(port, "/index.html")

    assert status == 404
    assert b"synthetic outside content" not in body


def test_parent_directory_cannot_escape_via_symlink(frontend_server):
    root, outside_file, port = frontend_server

    images = root / "images"
    images.rename(root / "original-images")

    outside_directory = outside_file.parent / "external-images"
    outside_directory.mkdir()

    (outside_directory / "inference.png").write_text(
        "synthetic outside content",
        encoding="utf-8",
    )

    images.symlink_to(outside_directory, target_is_directory=True)

    status, body = request(port, "/images/inference.png")

    assert status == 404
    assert b"synthetic outside content" not in body


def test_head_request_respects_allowlist(frontend_server):
    _, _, port = frontend_server

    status, body = request(port, "/index.html", method="HEAD")
    assert status == 200
    assert body == b""

    status, body = request(port, "/.env", method="HEAD")
    assert status == 404
    assert body == b""


def test_approved_assets_exist_in_repository():
    for relative_path in PUBLIC_FILES:
        assert (PROJECT_ROOT / relative_path).is_file()
