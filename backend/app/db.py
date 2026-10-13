"""DB 연결. DATABASE_URL 이 있으면 그 DB, 없으면 로컬 SQLite 파일."""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from . import config


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def _normalize(url: str) -> str:
    # Neon 등은 postgres:// 로 주므로 psycopg 3 드라이버 이름으로 바꾼다
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def init_db(url: str | None = None) -> None:
    global engine
    url = _normalize(url or config.database_url() or f"sqlite:///{config.ROOT / 'meetingnote.db'}")
    is_sqlite = url.startswith("sqlite")
    engine = create_engine(url, connect_args={"check_same_thread": False} if is_sqlite else {})
    if is_sqlite:
        @event.listens_for(engine, "connect")
        def _fk_on(conn, _):
            conn.execute("PRAGMA foreign_keys=ON")
    SessionLocal.configure(bind=engine)
    from . import models  # noqa: F401  테이블 등록
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
