$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'GSRIM Python environment missing.' }
$consolePython = Join-Path $projectRoot '.venv\Scripts\python.exe'
& $consolePython -c "import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(n) is not None for n in ('numpy','scipy','cupy','PySide6')) else 1)"
if ($LASTEXITCODE -ne 0) { throw 'Install desktop dependencies first: .\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt' }
Start-Process -FilePath $pythonPath -ArgumentList '-m','gsrim.desktop' -WorkingDirectory $projectRoot -WindowStyle Hidden
