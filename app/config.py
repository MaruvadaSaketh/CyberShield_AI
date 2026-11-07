from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    discord_bot_token: str = ""
    discord_channel_id: str = ""
    discord_guild_id: str = ""
    google_api_key: str = ""
    agent_name: str = "fraud-detection"
    gemini_model: str = "gemini-2.0-flash"
    switch_room_name: str = "CyberShield"
    switch_enabled: bool = False
    cors_origins: str = "http://localhost:8501,http://127.0.0.1:8501"
    database_path: str = "cybershield.db"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        extra="ignore",
    )

settings = Settings()