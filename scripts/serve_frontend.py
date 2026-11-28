
"""Serve only approved portfolio files during local development."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


HOST = "127.0.0.1"
PORT = 8000

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PUBLIC_FILES = frozenset({
    "index.html",
    "style.css",
    "script.js",
    "analytics.js",
    "images/android-chrome-192x192.png",
    "images/myimg-removebg.png",
    "images/about_me.png",
    "images/inference.png",
    "images/agentic.png",
    "images/pqc-pharma.png",
    "images/emotion-to-art.png",
    "images/reddit-nlp.png",
    "images/fer-project.png",
    "resume/SaeeDesai_Resume_AIML.pdf",
    "papers/PQC_Technical_Paper.pdf",
})


def resolve_public_file(root: Path, request_target: str) -> Path | None:
    """Resolve an approved URL to a regular, non-symlink public file."""

    try:
        parsed = urlsplit(request_target)

        if parsed.scheme or parsed.netloc or parsed.fragment:
            return None

        path = unquote(parsed.path, errors="strict")

        if not path.startswith("/") or path.startswith("//"):
            return None

        if "\\" in path or "\x00" in path or "%" in path:
            return None

        if any(part in {".", ".."} for part in path.split("/")):
            return None

        relative_path = "index.html" if path == "/" else path[1:]

        if relative_path not in PUBLIC_FILES:
            return None

        root = root.resolve(strict=True)
        candidate = root / relative_path

        # Reject symlinks in both files and parent directories.
        current = root
        for part in Path(relative_path).parts:
            current = current / part
            if current.is_symlink():
                return None

        resolved = candidate.resolve(strict=True)

        if not resolved.is_relative_to(root):
            return None

        if not resolved.is_file():
            return None

        return resolved

    except (ValueError, OSError, RuntimeError):
        return None


class FrontendHandler(SimpleHTTPRequestHandler):
    """HTTP handler restricted to the explicit frontend allowlist."""

    def __init__(self, *args, root: Path = PROJECT_ROOT, **kwargs):
        self.root = root
        super().__init__(*args, directory=str(root), **kwargs)

    def send_head(self):
        public_file = resolve_public_file(self.root, self.path)

        if public_file is None:
            self.send_error(404, "Not found")
            return None

        try:
            file = public_file.open("rb")
        except OSError:
            self.send_error(404, "Not found")
            return None

        try:
            size = public_file.stat().st_size

            self.send_response(200)
            self.send_header(
                "Content-Type",
                self.guess_type(str(public_file)),
            )
            self.send_header("Content-Length", str(size))
            self.end_headers()
            return file

        except Exception:
            file.close()
            raise

    def list_directory(self, path):
        self.send_error(404, "Not found")
        return None

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main():
    handler = partial(FrontendHandler, root=PROJECT_ROOT)

    with ThreadingHTTPServer((HOST, PORT), handler) as server:
        print(f"Portfolio frontend: http://localhost:{PORT}")
        print("Serving approved public files only.")
        print("Press Ctrl+C to stop.")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nFrontend server stopped.")


if __name__ == "__main__":
    main()
