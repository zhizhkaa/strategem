import importlib.util
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def read_repo_file(path: str) -> str:
    return (ROOT_DIR / path).read_text(encoding="utf-8")


def load_windows_launcher():
    launcher_path = ROOT_DIR / "scripts/windows/strategem_launcher.py"
    spec = importlib.util.spec_from_file_location("strategem_launcher", launcher_path)
    assert spec is not None
    assert spec.loader is not None
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    return launcher


def test_windows_build_creates_pyinstaller_exe_package() -> None:
    script = read_repo_file("scripts/windows/build-portable.ps1")

    assert "PyInstaller" in script
    assert "--onedir" in script
    assert "--name" in script
    assert "Strategem" in script
    assert "Strategem.exe" in script


def test_windows_build_does_not_package_embedded_python_launcher() -> None:
    script = read_repo_file("scripts/windows/build-portable.ps1")

    assert "python-embed-amd64.zip" not in script
    assert "get-pip.py" not in script
    assert "start-strategem.bat" not in script


def test_windows_build_excludes_local_runtime_state_from_bundle() -> None:
    script = read_repo_file("scripts/windows/build-portable.ps1")

    assert "backend\\data" in script
    assert "backend\\media" in script
    assert "backend\\staticfiles" in script
    assert "__pycache__" in script


def test_windows_workflow_builds_exe_artifact() -> None:
    workflow = read_repo_file(".github/workflows/windows-portable.yml")

    assert "workflow_dispatch:" in workflow
    assert "tags:" in workflow
    assert "runs-on: windows-2025-vs2026" in workflow
    assert "actions/checkout@v5" in workflow
    assert "actions/setup-node@v5" in workflow
    assert "actions/setup-python@v6" in workflow
    assert "actions/checkout@v4" not in workflow
    assert "actions/setup-node@v4" not in workflow
    assert "actions/setup-python@v5" not in workflow
    assert "actions/setup-python" in workflow
    assert "requirements-windows-build.txt" in workflow
    assert "Strategem.exe" in workflow
    assert "Strategem-Windows.zip" not in workflow
    assert "changelog:" in workflow
    assert "release_title:" in workflow
    assert "RELEASE_TITLE" in workflow
    assert "--notes-file" in workflow
    assert "gh release upload" in workflow
    assert "actions/upload-artifact" not in workflow


def test_deploy_workflow_ignores_windows_packaging_changes() -> None:
    workflow = read_repo_file(".github/workflows/deploy.yml")

    assert "paths-ignore:" in workflow
    assert "scripts/windows/**" in workflow
    assert "requirements-windows-build.txt" in workflow
    assert ".github/workflows/windows-portable.yml" in workflow
    assert "git sparse-checkout init --no-cone" in workflow
    assert "/backend/" in workflow
    assert "/frontend/" in workflow
    assert "/Dockerfile" in workflow


def test_pyinstaller_launcher_sets_local_runtime_defaults() -> None:
    launcher = read_repo_file("scripts/windows/strategem_launcher.py")

    assert "DJANGO_SETTINGS_MODULE" in launcher
    assert "strategem.settings" in launcher
    assert "POSTGRES_DB" in launcher
    assert "127.0.0.1" in launcher
    assert "runserver" in launcher


def test_pyinstaller_launcher_uses_stable_windows_profile_dir(monkeypatch, tmp_path) -> None:
    launcher = load_windows_launcher()
    fallback_root = tmp_path / "Strategem-Windows"
    local_app_data = tmp_path / "LocalAppData"

    monkeypatch.delenv("STRATEGEM_RUNTIME_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.setattr(launcher, "is_windows", lambda: True)

    assert launcher.persistent_root(fallback_root) == local_app_data / "Strategem"


def test_pyinstaller_launcher_allows_runtime_dir_override(monkeypatch, tmp_path) -> None:
    launcher = load_windows_launcher()
    fallback_root = tmp_path / "Strategem-Windows"
    configured_root = tmp_path / "strategem-runtime"

    monkeypatch.setenv("STRATEGEM_RUNTIME_DIR", str(configured_root))

    assert launcher.persistent_root(fallback_root) == configured_root


def test_pyinstaller_launcher_migrates_legacy_portable_state(tmp_path) -> None:
    launcher = load_windows_launcher()
    old_data_dir = tmp_path / "old" / "data"
    old_media_dir = tmp_path / "old" / "media"
    new_data_dir = tmp_path / "profile" / "data"
    new_media_dir = tmp_path / "profile" / "media"

    old_data_dir.mkdir(parents=True)
    old_media_dir.mkdir(parents=True)
    new_data_dir.mkdir(parents=True)
    new_media_dir.mkdir(parents=True)
    (old_data_dir / "db.sqlite3").write_bytes(b"legacy database")
    (old_media_dir / "upload.txt").write_text("legacy media", encoding="utf-8")

    launcher.migrate_legacy_runtime_state(
        old_data_dir,
        old_media_dir,
        new_data_dir,
        new_media_dir,
    )

    assert (new_data_dir / "db.sqlite3").read_bytes() == b"legacy database"
    assert (new_media_dir / "upload.txt").read_text(encoding="utf-8") == "legacy media"


def test_pyinstaller_launcher_does_not_overwrite_existing_profile_database(tmp_path) -> None:
    launcher = load_windows_launcher()
    old_data_dir = tmp_path / "old" / "data"
    old_media_dir = tmp_path / "old" / "media"
    new_data_dir = tmp_path / "profile" / "data"
    new_media_dir = tmp_path / "profile" / "media"

    old_data_dir.mkdir(parents=True)
    old_media_dir.mkdir(parents=True)
    new_data_dir.mkdir(parents=True)
    new_media_dir.mkdir(parents=True)
    (old_data_dir / "db.sqlite3").write_bytes(b"legacy database")
    (new_data_dir / "db.sqlite3").write_bytes(b"profile database")

    launcher.migrate_legacy_runtime_state(
        old_data_dir,
        old_media_dir,
        new_data_dir,
        new_media_dir,
    )

    assert (new_data_dir / "db.sqlite3").read_bytes() == b"profile database"
