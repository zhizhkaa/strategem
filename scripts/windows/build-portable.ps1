param(
    [string]$OutputDir = "dist\Strategem-Windows",
    [string]$WorkDir = ".tmp\pyinstaller-windows"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$outputPath = Join-Path $repoRoot $OutputDir
$workPath = Join-Path $repoRoot $WorkDir
$stagingPath = Join-Path $workPath "app"
$venvPath = Join-Path $workPath "venv"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"
$pyinstallerDistPath = Join-Path $workPath "dist"
$pyinstallerOutputPath = Join-Path $pyinstallerDistPath "Strategem.exe"
$appExe = Join-Path $outputPath "Strategem.exe"

Write-Host "Building Strategem executable package in $outputPath"

$requiredAssets = @(
    "frontend\static\css\tailwind.css",
    "frontend\static\vendor\alpinejs\alpine.min.js",
    "frontend\static\vendor\chartjs\chart.umd.min.js"
)

foreach ($asset in $requiredAssets) {
    $assetPath = Join-Path $repoRoot $asset
    if (-not (Test-Path $assetPath)) {
        throw "Missing frontend asset: $asset. Run npm ci and npm run build in frontend before packaging."
    }
}

Remove-Item -Recurse -Force $outputPath -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $workPath -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $workPath | Out-Null

Write-Host "Preparing clean application staging directory..."
New-Item -ItemType Directory -Force $stagingPath | Out-Null
Copy-Item -Recurse -Force (Join-Path $repoRoot "backend") (Join-Path $stagingPath "backend")
Copy-Item -Recurse -Force (Join-Path $repoRoot "frontend") (Join-Path $stagingPath "frontend")
Remove-Item -Recurse -Force (Join-Path $stagingPath "backend\data") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $stagingPath "backend\media") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $stagingPath "backend\staticfiles") -ErrorAction SilentlyContinue
Get-ChildItem $stagingPath -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem $stagingPath -Recurse -File |
    Where-Object { $_.Extension -in ".pyc", ".pyo" } |
    Remove-Item -Force

Write-Host "Creating isolated build virtual environment..."
python -m venv $venvPath

Write-Host "Installing application and packaging dependencies..."
& $pythonExe -m pip install --upgrade pip
& $pythonExe -m pip install -r (Join-Path $repoRoot "requirements.txt")
& $pythonExe -m pip install -r (Join-Path $repoRoot "scripts\windows\requirements-build.txt")

Write-Host "Running PyInstaller..."
& $pythonExe -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --console `
    --name Strategem `
    --distpath $pyinstallerDistPath `
    --workpath (Join-Path $workPath "build") `
    --specpath (Join-Path $workPath "spec") `
    --paths (Join-Path $stagingPath "backend") `
    --add-data "$stagingPath\backend;backend" `
    --add-data "$stagingPath\frontend;frontend" `
    --collect-all django `
    --collect-all rest_framework `
    --collect-all drf_spectacular `
    --collect-all corsheaders `
    --collect-all decouple `
    --collect-all simpleeval `
    --collect-all ratelimit `
    --collect-all psycopg `
    --hidden-import strategem.settings `
    --hidden-import strategem.urls `
    --hidden-import strategem.wsgi `
    --hidden-import apps.game `
    --hidden-import apps.management `
    (Join-Path $repoRoot "scripts\windows\strategem_launcher.py")

if (-not (Test-Path $pyinstallerOutputPath)) {
    throw "PyInstaller did not create executable at $pyinstallerOutputPath"
}

New-Item -ItemType Directory -Force (Split-Path -Parent $outputPath) | Out-Null
New-Item -ItemType Directory -Force $outputPath | Out-Null
Move-Item -Force $pyinstallerOutputPath $appExe

if (-not (Test-Path $appExe)) {
    throw "PyInstaller did not create Strategem.exe at $appExe"
}

Write-Host "Portable executable is ready: $appExe"
