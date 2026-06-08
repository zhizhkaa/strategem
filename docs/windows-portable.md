# Windows Portable Build

This document describes how to create a Windows package that runs Strategem locally from a flash drive without installing Python, Node.js, PostgreSQL, Docker, or npm on the user's machine.

## Build

Run on a Windows build machine:

```powershell
npm ci
npm run build
.\scripts\windows\build-portable.ps1
```

The build output is created at:

```text
dist\Strategem-Windows
```

The generated folder contains `Strategem.exe`, packaged Python dependencies, application code, local static assets, and writable `data`/`media` directories. Runtime frontend assets are local: Tailwind CSS is compiled, and Alpine.js/Chart.js are copied from npm into `frontend/static/vendor`.

`npm` is needed only on the build machine. It is not needed on the user's PC.

## Run

Open:

```text
Strategem.exe
```

The executable applies SQLite migrations, starts the local Django server on `127.0.0.1:8000`, and opens the browser automatically. To use another port:

```cmd
set STRATEGEM_PORT=8010
Strategem.exe
```

The local SQLite database is stored in `data\db.sqlite3` next to `Strategem.exe`. Uploaded files are stored in `media`.

## GitHub Releases

The `Build Windows portable package` workflow publishes `Strategem-Windows.zip` to GitHub Releases. It can be started manually with a release tag such as:

```text
windows-portable-2026-06-08
```

It also runs for pushed tags matching `v*` or `windows-*`.
