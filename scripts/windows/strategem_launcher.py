"""Windows launcher for the offline Strategem portable package."""

from __future__ import annotations

import os
import shutil
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


def is_windows() -> bool:
    """Return whether the launcher is running on Windows."""
    return sys.platform.startswith("win")


def persistent_root(fallback_root: Path) -> Path:
    """Return a stable writable directory that survives app folder replacement."""
    configured_root = os.environ.get("STRATEGEM_RUNTIME_DIR")
    if configured_root:
        return Path(configured_root)

    if is_windows():
        windows_profile_dir = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if windows_profile_dir:
            return Path(windows_profile_dir) / "Strategem"

    return fallback_root


def migrate_legacy_runtime_state(
    old_data_dir: Path,
    old_media_dir: Path,
    new_data_dir: Path,
    new_media_dir: Path,
) -> None:
    """Copy existing portable state into the stable profile directory once."""
    old_database = old_data_dir / "db.sqlite3"
    new_database = new_data_dir / "db.sqlite3"

    if old_database.exists() and not new_database.exists():
        shutil.copy2(old_database, new_database)
        print(f"Copied existing database to {new_database}")

    if old_media_dir.exists():
        shutil.copytree(old_media_dir, new_media_dir, dirs_exist_ok=True)


def configure_environment() -> Path:
    """Prepare Django paths and local runtime settings."""
    app_root = bundle_root()
    legacy_root = runtime_root()
    writable_root = persistent_root(legacy_root)
    backend_dir = app_root / "backend"
    data_dir = writable_root / "data"
    media_dir = writable_root / "media"
    legacy_data_dir = legacy_root / "data"
    legacy_media_dir = legacy_root / "media"

    if not backend_dir.exists():
        raise RuntimeError(f"Cannot find bundled backend directory: {backend_dir}")

    data_dir.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)
    if writable_root != legacy_root:
        migrate_legacy_runtime_state(legacy_data_dir, legacy_media_dir, data_dir, media_dir)

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
