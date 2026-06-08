# Windows Portable Build

This document describes how to create a Windows package that runs Strategem locally without installing Python, Node.js, PostgreSQL, or Docker on the user's machine.

## Build

Run on Windows:

```powershell
npm ci
npm run build
.\scripts\windows\build-portable.ps1
```

The build output is created at:

```text
dist\Strategem-Windows
```

The generated folder contains the embedded Python runtime, Python dependencies, application code, local static assets, and `start-strategem.bat`. Runtime frontend assets are local: Tailwind CSS is compiled, and Alpine.js/Chart.js are copied from npm into `frontend/static/vendor`.

## Run

Open:

```text
start-strategem.bat
```

The script applies SQLite migrations, starts the local Django server on `127.0.0.1:8000`, and opens the browser automatically. To use another port:

```cmd
set STRATEGEM_PORT=8010
start-strategem.bat
```

## GitHub Actions

The `Build Windows portable package` workflow can be started manually from GitHub Actions. It uploads `Strategem-Windows.zip` as an artifact.
