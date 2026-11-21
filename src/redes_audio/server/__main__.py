"""Ponto de entrada do servidor."""

import uvicorn

from redes_audio.server.config import settings


def main() -> None:
    uvicorn.run(
        "redes_audio.server.app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
