"""Configuration via environment variables."""

from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/chessian"

    # Stockfish
    stockfish_path: str = "/usr/bin/stockfish"
    stockfish_depth: int = 20

    # LLM
    anthropic_api_key: str = ""
    groq_api_key: str = ""

    # External APIs
    lichess_api_token: str = ""

    # App
    debug: bool = True
    secret_key: str = "change-me-in-production"

    model_config = {"env_file": str(BASE_DIR / ".env"), "env_file_encoding": "utf-8"}


settings = Settings()
