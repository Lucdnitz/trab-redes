$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$ToolsDir = Join-Path $ProjectRoot ".venv-tools"

function Test-SupportedPython {
    param(
        [string]$Exe,
        [string[]]$ExtraArgs = @()
    )
    try {
        & $Exe @ExtraArgs -c "import sys; v = sys.version_info; raise SystemExit(0 if (v.major == 3 and v.minor in (11, 12) and v.releaselevel == 'final') else 1)" 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

$NeedCreate = $true
if (Test-Path -LiteralPath $VenvPython) {
    if (Test-SupportedPython -Exe $VenvPython) {
        $NeedCreate = $false
    }
    else {
        Write-Warning "Ambiente existente em .venv usa versão incompatível de Python e será recriado."
    }
}

$UsedUv = $false
if ($NeedCreate) {
    $SelectedExe = $null
    $SelectedArgs = @()

    if ($env:PYTHON) {
        if (Test-SupportedPython -Exe $env:PYTHON) {
            $SelectedExe = $env:PYTHON
        }
        else {
            throw "PYTHON='$($env:PYTHON)' não é Python 3.11 ou 3.12 estável."
        }
    }

    if (-not $SelectedExe -and (Get-Command py -ErrorAction SilentlyContinue)) {
        foreach ($tag in @("-3.12", "-3.11")) {
            if (Test-SupportedPython -Exe "py" -ExtraArgs @($tag)) {
                $SelectedExe = "py"
                $SelectedArgs = @($tag)
                break
            }
        }
    }

    if (-not $SelectedExe -and (Get-Command python -ErrorAction SilentlyContinue)) {
        if (Test-SupportedPython -Exe "python") {
            $SelectedExe = "python"
        }
    }

    if ($SelectedExe) {
        if (Test-Path -LiteralPath $VenvPath) {
            Remove-Item -Recurse -Force -LiteralPath $VenvPath
        }
        & $SelectedExe @SelectedArgs -m venv $VenvPath
        if ($LASTEXITCODE -ne 0) {
            throw "Falha ao criar o ambiente virtual em $VenvPath."
        }
    }
    else {
        Write-Host "Python 3.11/3.12 não encontrado no Windows; baixando Python 3.11 portátil isolado em .venv-tools..."
        $UvExe = Join-Path $ToolsDir "uv.exe"
        if (-not (Test-Path -LiteralPath $UvExe)) {
            $UvCmd = Get-Command uv -ErrorAction SilentlyContinue
            if ($UvCmd) {
                $UvExe = $UvCmd.Source
            }
            else {
                New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null
                $env:UV_UNMANAGED_INSTALL = $ToolsDir
                $env:INSTALLER_NO_MODIFY_PATH = "1"
                Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
            }
        }
        if (-not (Test-Path -LiteralPath $UvExe)) {
            throw "Não foi possível instalar o uv em $ToolsDir."
        }

        $env:UV_PYTHON_INSTALL_DIR = Join-Path $ToolsDir "python"
        New-Item -ItemType Directory -Force -Path $env:UV_PYTHON_INSTALL_DIR | Out-Null
        & $UvExe venv --python 3.11 --seed --clear $VenvPath
        if ($LASTEXITCODE -ne 0) {
            throw "Falha ao criar .venv com Python 3.11 via uv."
        }
        & $UvExe pip install --python $VenvPython -e "$ProjectRoot[client,ai,experiments,dev]"
        if ($LASTEXITCODE -ne 0) {
            throw "Falha ao instalar as dependências do projeto via uv."
        }
        $UsedUv = $true
    }
}

if (-not $UsedUv) {
    $PythonExe = $VenvPython
    & $PythonExe -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao atualizar o pip."
    }
    & $PythonExe -m pip install -e "$ProjectRoot[client,ai,experiments,dev]"
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao instalar as dependências do projeto."
    }
}

Write-Host "Ambiente configurado em $VenvPath ($(& $VenvPython --version))"
Write-Host "Valide com: .\scripts\check.ps1"
Write-Host "Use scripts\start-server.ps1 e scripts\start-client.ps1"
