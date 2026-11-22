#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
venv_path="${REDES_VENV:-${project_root}/.venv-linux}"
python_exe="${venv_path}/bin/python"

if [[ ! -x "${python_exe}" ]]; then
    echo "Ambiente não configurado. Execute: bash scripts/setup.sh" >&2
    exit 1
fi

cd "${project_root}"
"${python_exe}" -m ruff check .
"${python_exe}" -m pytest
