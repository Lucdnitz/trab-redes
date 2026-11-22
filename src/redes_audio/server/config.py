"""Configuração do servidor carregada do ambiente."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDES_", env_file=".env", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    sample_rate: int = 16_000
    frame_duration_ms: int = 20
    whisper_model: str = "base"
    whisper_language: str = "pt"
    transcription_window_seconds: float = 1.5
    summary_backend: str = "auto"
    summary_min_chars: int = 80
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:1.5b"


settings = ServerSettings()
