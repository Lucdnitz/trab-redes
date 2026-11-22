param(
    [string]$Server = "127.0.0.1",
    [int]$ServerPort = 8000,
    [int]$UdpPort = 5001
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ClientExe = Join-Path $ProjectRoot ".venv\Scripts\redes-client.exe"

if (-not (Test-Path -LiteralPath $ClientExe)) {
    throw "Ambiente não configurado. Execute scripts\setup.ps1 primeiro."
}

& $ClientExe --server $Server --server-port $ServerPort --udp-port $UdpPort
