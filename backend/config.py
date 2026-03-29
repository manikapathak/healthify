from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./healthify.db"
    debug: bool = False
    app_version: str = "0.1.0"


settings = Settings()
