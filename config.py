from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    discord_token: str
    openai_api_key: str
    openai_base_url: str | None
    ai_model: str
    ai_image_model: str
    ai_max_tokens: int
    ai_temperature: float
    database_path: str
    dev_guild_id: int | None


def load_settings() -> Settings:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not token:
        raise RuntimeError("DISCORD_TOKEN est manquant dans le fichier .env")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY est manquant dans le fichier .env")

    guild = os.getenv("DEV_GUILD_ID", "").strip()
    return Settings(
        discord_token=token,
        openai_api_key=api_key,
        openai_base_url=os.getenv("OPENAI_BASE_URL", "").strip() or None,
        ai_model=os.getenv("AI_MODEL", "gpt-4o-mini"),
        ai_image_model=os.getenv("AI_IMAGE_MODEL", "gpt-image-1"),
        ai_max_tokens=max(200, int(os.getenv("AI_MAX_TOKENS", "1200"))),
        ai_temperature=min(2.0, max(0.0, float(os.getenv("AI_TEMPERATURE", "0.7")))),
        database_path=os.getenv("DATABASE_PATH", "husey_ai.sqlite3"),
        dev_guild_id=int(guild) if guild else None,
    )
