param(
    [string]$PythonVersion = "3.12.13",
    [string]$OutputDir = "dist\Strategem-Windows"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$outputPath = Join-Path $repoRoot $OutputDir
$runtimePath = Join-Path $outputPath "runtime\python"
$appPath = Join-Path $outputPath "app"
$downloadsPath = Join-Path $repoRoot ".tmp\portable-windows"
$pythonZip = Join-Path $downloadsPath "python-$PythonVersion-embed-amd64.zip"
$getPip = Join-Path $downloadsPath "get-pip.py"
$pythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$getPipUrl = "https://bootstrap.pypa.io/get-pip.py"

Write-Host "Building Strategem portable package in $outputPath"

Remove-Item -Recurse -Force $outputPath -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $runtimePath, $appPath, $downloadsPath | Out-Null

if (-not (Test-Path $pythonZip)) {
    Write-Host "Downloading Python $PythonVersion embedded runtime..."
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonZip
}

Write-Host "Extracting Python runtime..."
Expand-Archive -Path $pythonZip -DestinationPath $runtimePath -Force

$pthFile = Get-ChildItem $runtimePath -Filter "python*._pth" | Select-Object -First 1
if ($null -ne $pthFile) {
    $pthContent = Get-Content $pthFile.FullName
    $pthContent = $pthContent | ForEach-Object {
        if ($_ -eq "#import site") { "import site" } else { $_ }
    }
    Set-Content -Path $pthFile.FullName -Value $pthContent -Encoding ASCII
}

if (-not (Test-Path $getPip)) {
    Write-Host "Downloading pip bootstrap..."
    Invoke-WebRequest -Uri $getPipUrl -OutFile $getPip
}

$pythonExe = Join-Path $runtimePath "python.exe"
Write-Host "Installing pip into embedded Python..."
& $pythonExe $getPip --no-warn-script-location

Write-Host "Installing Python dependencies..."
& $pythonExe -m pip install --no-warn-script-location -r (Join-Path $repoRoot "requirements.txt")

Write-Host "Copying application files..."
Copy-Item -Recurse -Force (Join-Path $repoRoot "backend") (Join-Path $appPath "backend")
Copy-Item -Recurse -Force (Join-Path $repoRoot "frontend") (Join-Path $appPath "frontend")
Copy-Item -Force (Join-Path $repoRoot "requirements.txt") (Join-Path $appPath "requirements.txt")
Copy-Item -Force (Join-Path $repoRoot "start-strategem.bat") (Join-Path $outputPath "start-strategem.bat")

Remove-Item -Recurse -Force (Join-Path $appPath "backend\data") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $appPath "backend\media") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $appPath "backend\staticfiles") -ErrorAction SilentlyContinue
Get-ChildItem $appPath -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem $appPath -Recurse -File |
    Where-Object { $_.Extension -in ".pyc", ".pyo" } |
    Remove-Item -Force

New-Item -ItemType Directory -Force (Join-Path $appPath "backend\data") | Out-Null
New-Item -ItemType Directory -Force (Join-Path $appPath "backend\media") | Out-Null

Write-Host "Portable package is ready: $outputPath"
Write-Host "Run start-strategem.bat from that folder."
