"""Vercel 진입점 - Vercel 의 FastAPI 감지는 루트의 app.py 에서 `app` 을 찾는다."""
from backend.app.main import app  # noqa: F401
