#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
venv_path="${REDES_VENV:-${project_root}/.venv-linux}"
python_command="${PYTHON:-python3}"

if ! command -v "${python_command}" >/dev/null 2>&1; then
    echo "Python não encontrado. Instale Python 3.11 ou 3.12 e tente novamente." >&2
    exit 1
fi

if [[ ! -x "${venv_path}/bin/python" ]]; then
    "${python_command}" -m venv "${venv_path}"
fi

python_exe="${venv_path}/bin/python"
"${python_exe}" -m pip install --upgrade pip
"${python_exe}" -m pip install -e "${project_root}[client,ai,experiments,dev]"

echo "Ambiente Linux configurado em ${venv_path}"
echo "Use: bash scripts/start-server.sh"
echo "E, em outro terminal: bash scripts/start-client.sh"
