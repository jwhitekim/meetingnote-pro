"""환경 설정. .env 를 읽고, 값은 부를 때마다 os.environ 에서 꺼낸다 (테스트가 바꿀 수 있게)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

FRONTEND_DIR = ROOT / "frontend"


def env(name: str, default: str = "") -> str:
    return os.environ.get(name) or default


def jwt_secret() -> str:
    return env("JWT_SECRET", "dev-only-secret-change-me")


def database_url() -> str:
    return env("DATABASE_URL")


def cors_origins() -> list[str]:
    raw = env("CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000")
    return [o.strip() for o in raw.split(",") if o.strip()]


def bcrypt_rounds() -> int:
    return int(env("BCRYPT_ROUNDS", "12"))
