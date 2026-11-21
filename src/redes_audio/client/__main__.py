"""Ponto de entrada do cliente PySide6."""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cliente desktop do Projeto 2 de Redes")
    parser.add_argument("--server", default="127.0.0.1", help="IP ou hostname do servidor")
    parser.add_argument("--udp-port", default=5001, type=int, help="porta UDP local")
    return parser


def main() -> None:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:
        raise SystemExit("PySide6 não instalado. Execute: pip install -e '.[client]'") from exc

    from redes_audio.client.main_window import MainWindow

    args = build_parser().parse_args()
    app = QApplication(sys.argv)
    app.setApplicationName("Redes Audio Live")
    window = MainWindow(args.server, args.udp_port)
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
