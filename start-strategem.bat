@echo off
setlocal

set "ROOT=%~dp0"
set "APP_DIR=%ROOT%app"
if not exist "%APP_DIR%\backend\manage.py" set "APP_DIR=%ROOT%"

set "PYTHON_CMD="%ROOT%runtime\python\python.exe""
if not exist "%ROOT%runtime\python\python.exe" set "PYTHON_CMD="%ROOT%.venv\Scripts\python.exe""
if not exist "%ROOT%.venv\Scripts\python.exe" if not exist "%ROOT%runtime\python\python.exe" set "PYTHON_CMD=py -3"

set "SECRET_KEY=strategem-local-development-key"
set "DEBUG=True"
set "ADMIN_PASSWORD=admin123"
set "POSTGRES_DB="
set "ALLOWED_HOSTS=localhost,127.0.0.1"
if "%STRATEGEM_PORT%"=="" set "STRATEGEM_PORT=8000"

cd /d "%APP_DIR%\backend"
if errorlevel 1 (
    echo Failed to open app directory: "%APP_DIR%\backend"
    pause
    exit /b 1
)

if not exist "data" mkdir "data"

echo Applying local database migrations...
%PYTHON_CMD% manage.py migrate --noinput
if errorlevel 1 (
    echo Failed to apply migrations.
    pause
    exit /b 1
)

set "STRATEGEM_URL=http://127.0.0.1:%STRATEGEM_PORT%/"
echo Starting Strategem at %STRATEGEM_URL%
start "" "%STRATEGEM_URL%"
%PYTHON_CMD% manage.py runserver 127.0.0.1:%STRATEGEM_PORT% --noreload

pause
