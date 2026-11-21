$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Ambiente não configurado. Execute scripts\setup.ps1 primeiro."
}

Push-Location $ProjectRoot
try {
    & $PythonExe -m ruff check .
    if ($LASTEXITCODE -ne 0) {
        throw "O lint encontrou problemas."
    }
    & $PythonExe -m pytest
    if ($LASTEXITCODE -ne 0) {
        throw "A suíte de testes falhou."
    }
}
finally {
    Pop-Location
}
