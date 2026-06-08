"""Windows launcher for the offline Strategem portable package."""

from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path


def bundle_root() -> Path:
    """Return the directory that contains bundled application files."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def runtime_root() -> Path:
    """Return the writable directory next to Strategem.exe."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def configure_environment() -> Path:
    """Prepare Django paths and local runtime settings."""
    app_root = bundle_root()
    writable_root = runtime_root()
    backend_dir = app_root / "backend"
    data_dir = writable_root / "data"
    media_dir = writable_root / "media"

    if not backend_dir.exists():
        raise RuntimeError(f"Cannot find bundled backend directory: {backend_dir}")

    data_dir.mkdir(exist_ok=True)
    media_dir.mkdir(exist_ok=True)
    sys.path.insert(0, str(backend_dir))
    os.chdir(backend_dir)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "strategem.settings")
    os.environ.setdefault("SECRET_KEY", "strategem-local-development-key")
    os.environ.setdefault("DEBUG", "True")
    os.environ.setdefault("ADMIN_PASSWORD", "admin123")
    os.environ.setdefault("POSTGRES_DB", "")
    os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1")
    os.environ.setdefault("STRATEGEM_DATA_DIR", str(data_dir))
    os.environ.setdefault("STRATEGEM_MEDIA_DIR", str(media_dir))

    return backend_dir


def run_management_command(command: list[str]) -> None:
    """Run a Django management command inside the packaged application."""
    from django.core.management import execute_from_command_line

    execute_from_command_line(["strategem"] + command)


def main() -> int:
    try:
        configure_environment()
        port = os.environ.get("STRATEGEM_PORT", "8000")
        address = f"127.0.0.1:{port}"
        url = f"http://{address}/"

        print("Applying local database migrations...")
        run_management_command(["migrate", "--noinput"])

        print(f"Starting Strategem at {url}")
        webbrowser.open(url)
        run_management_command(["runserver", address, "--noreload"])
        return 0
    except Exception as exc:
        print(f"Strategem failed to start: {exc}", file=sys.stderr)
        input("Press Enter to exit...")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
