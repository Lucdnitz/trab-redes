"""Configuração do servidor carregada do ambiente."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDES_", env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    sample_rate: int = 16_000
    frame_duration_ms: int = 20


settings = ServerSettings()
