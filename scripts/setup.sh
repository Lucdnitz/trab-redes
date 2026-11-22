#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
venv_path="${REDES_VENV:-${project_root}/.venv-linux}"
tools_dir="${REDES_TOOLS:-${project_root}/.venv-tools}"

is_supported_python() {
    local candidate="$1"
    command -v "${candidate}" >/dev/null 2>&1 || return 1
    "${candidate}" -c 'import sys; v = sys.version_info; raise SystemExit(0 if (v.major == 3 and v.minor in (11, 12) and v.releaselevel == "final") else 1)' >/dev/null 2>&1
}

has_working_venv() {
    local candidate="$1"
    "${candidate}" -m venv --help >/dev/null 2>&1
}

find_uv() {
    if [[ -x "${tools_dir}/uv" ]]; then
        printf '%s\n' "${tools_dir}/uv"
        return 0
    fi
    if command -v uv >/dev/null 2>&1; then
        command -v uv
        return 0
    fi
    return 1
}

ensure_local_uv() {
    local uv_bin=""
    if uv_bin="$(find_uv)"; then
        printf '%s\n' "${uv_bin}"
        return 0
    fi

    if ! command -v curl >/dev/null 2>&1; then
        echo "Erro: curl não encontrado para baixar o Python 3.11 portátil." >&2
        exit 1
    fi

    echo "Instalando gerenciador portátil (uv) em ${tools_dir} (sem usar sudo)..." >&2
    mkdir -p "${tools_dir}"
    curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL="${tools_dir}" INSTALLER_NO_MODIFY_PATH=1 sh >&2

    if [[ ! -x "${tools_dir}/uv" ]]; then
        echo "Erro: falha ao preparar uv em ${tools_dir}." >&2
        exit 1
    fi
    printf '%s\n' "${tools_dir}/uv"
}

python_command=""
if [[ -n "${PYTHON:-}" ]]; then
    if is_supported_python "${PYTHON}" && has_working_venv "${PYTHON}"; then
        python_command="${PYTHON}"
    else
        echo "Erro: PYTHON='${PYTHON}' não é Python 3.11/3.12 estável com módulo venv." >&2
        exit 1
    fi
else
    for candidate in python3.12 python3.11 python3; do
        if is_supported_python "${candidate}" && has_working_venv "${candidate}"; then
            python_command="${candidate}"
            break
        fi
    done
fi

if [[ -x "${venv_path}/bin/python" ]] && is_supported_python "${venv_path}/bin/python"; then
    python_exe="${venv_path}/bin/python"
    echo "Reutilizando ambiente compatível em ${venv_path}..."
    "${python_exe}" -m pip install --upgrade pip
    "${python_exe}" -m pip install -e "${project_root}[client,ai,experiments,dev]"
elif [[ -n "${python_command}" ]]; then
    if [[ -x "${venv_path}/bin/python" ]] && ! is_supported_python "${venv_path}/bin/python"; then
        echo "Recriando ${venv_path} com ${python_command}..."
        rm -rf "${venv_path}"
    fi
    if [[ ! -x "${venv_path}/bin/python" ]]; then
        "${python_command}" -m venv "${venv_path}"
    fi
    python_exe="${venv_path}/bin/python"
    "${python_exe}" -m pip install --upgrade pip
    "${python_exe}" -m pip install -e "${project_root}[client,ai,experiments,dev]"
else
    echo "Python 3.11/3.12 estável não encontrado no sistema; preparando Python 3.11 isolado no projeto..."
    uv_bin="$(ensure_local_uv)"
    mkdir -p "${tools_dir}/python"
    UV_PYTHON_INSTALL_DIR="${tools_dir}/python" "${uv_bin}" venv --python 3.11 --seed --clear "${venv_path}"
    "${uv_bin}" pip install --python "${venv_path}/bin/python" -e "${project_root}[client,ai,experiments,dev]"
    python_exe="${venv_path}/bin/python"
fi

echo "Ambiente Linux configurado em ${venv_path} ($("${python_exe}" --version))"
echo "Valide com: bash scripts/check.sh"
echo "Para iniciar: bash scripts/start-server.sh e, em outro terminal, bash scripts/start-client.sh"
