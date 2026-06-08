from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def read_repo_file(path: str) -> str:
    return (ROOT_DIR / path).read_text(encoding="utf-8")


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

    assert "push:" in workflow
    assert "branches:" in workflow
    assert "actions/setup-python" in workflow
    assert "requirements-windows-build.txt" in workflow
    assert "Strategem.exe" in workflow
    assert "Strategem-Windows.zip" in workflow


def test_pyinstaller_launcher_sets_local_runtime_defaults() -> None:
    launcher = read_repo_file("scripts/windows/strategem_launcher.py")

    assert "DJANGO_SETTINGS_MODULE" in launcher
    assert "strategem.settings" in launcher
    assert "POSTGRES_DB" in launcher
    assert "127.0.0.1" in launcher
    assert "runserver" in launcher
