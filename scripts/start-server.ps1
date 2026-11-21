$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ServerExe = Join-Path $ProjectRoot ".venv\Scripts\redes-server.exe"

if (-not (Test-Path -LiteralPath $ServerExe)) {
    throw "Ambiente não configurado. Execute scripts\setup.ps1 primeiro."
}

& $ServerExe
