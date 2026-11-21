$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"

if (-not (Test-Path -LiteralPath $VenvPath)) {
    python -m venv $VenvPath
}

$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
& $PythonExe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao atualizar o pip."
}
& $PythonExe -m pip install -e "$ProjectRoot[client,dev]"
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao instalar as dependências do projeto."
}

Write-Host "Ambiente configurado em $VenvPath"
Write-Host "Use scripts\start-server.ps1 e scripts\start-client.ps1"
