from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent / ".env"


def _read_env_file() -> dict[str, str]:
    """Read .env file directly — bypasses shell environment overrides."""
    env: dict[str, str] = {}
    if not _ENV_FILE.exists():
        return env
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        # env_file takes priority over shell env vars
        env_ignore_empty=True,
    )

    gemini_api_key: str = ""
    groq_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./healthify.db"
    debug: bool = False
    app_version: str = "0.1.0"

    def model_post_init(self, __context: object) -> None:
        """
        Permanent fix: if groq_api_key is empty or blank after pydantic loads it
        (shell env var was empty string overriding .env), read directly from .env file.
        Also validates the key format so bad keys are caught at startup.
        """
        if not self.groq_api_key.strip():
            direct = _read_env_file()
            if direct.get("GROQ_API_KEY", "").strip():
                object.__setattr__(self, "groq_api_key", direct["GROQ_API_KEY"].strip())

        key = self.groq_api_key.strip()
        if key and not key.startswith("gsk_"):
            raise ValueError(
                f"GROQ_API_KEY looks wrong (got '{key[:6]}...'). "
                "Groq keys must start with 'gsk_'. Check your .env file."
            )


settings = Settings()
