"""MeetingNote Pro - API · 화면 · Swagger UI 를 한 서버에서 제공 (로컬 일체형)."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, errors
from .routers import activities, auth, comments, meetings, teams, todos


@asynccontextmanager
async def lifespan(_: FastAPI):
    if db.engine is None:
        db.init_db()
    yield


app = FastAPI(
    title="MeetingNote Pro API",
    description="팀 회의록 · 할 일 칸반 · 댓글 · 활동 기록. 로그인 API 로 받은 token 을 Authorize 에 넣으면 인증 API 를 시험할 수 있습니다.",
    version="1.0.0",
    lifespan=lifespan,
)
errors.install(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

ROUTERS = [auth.router, teams.router, meetings.router, todos.router, comments.router, activities.router]
for r in ROUTERS:
    app.include_router(r)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/login.html")


app.mount("/", StaticFiles(directory=config.FRONTEND_DIR), name="frontend")
