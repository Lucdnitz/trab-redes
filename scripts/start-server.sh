#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
venv_path="${REDES_VENV:-${project_root}/.venv-linux}"
server_exe="${venv_path}/bin/redes-server"

if [[ ! -x "${server_exe}" ]]; then
    echo "Ambiente não configurado. Execute: bash scripts/setup.sh" >&2
    exit 1
fi

cd "${project_root}"
exec "${server_exe}" "$@"
