"""bcrypt · JWT · 현재 사용자 · 팀 권한 확인."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .errors import ApiError
from .models import Membership, Team, User

TOKEN_HOURS = 24  # 갱신 없음
_bearer = HTTPBearer(auto_error=False, description="POST /api/auth/login 으로 받은 token")


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=config.bcrypt_rounds())).decode()


def check_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())


def make_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    return jwt.encode({"sub": str(user_id), "exp": exp}, config.jwt_secret(), algorithm="HS256")


def _expired() -> ApiError:
    # 없음 · 만료 · 위조 모두 같은 코드 - 화면 동작이 같다 (design.md)
    return ApiError(401, "TOKEN_EXPIRED", "세션이 만료되었습니다")


def current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if cred is None:
        raise _expired()
    try:
        payload = jwt.decode(cred.credentials, config.jwt_secret(), algorithms=["HS256"])
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise _expired()
    if user is None:
        raise _expired()
    return user


def membership_of(db: Session, user: User) -> Membership | None:
    return db.query(Membership).filter_by(user_id=user.id).one_or_none()


def require_member(db: Session, user: User, team_id: int) -> Membership:
    if db.get(Team, team_id) is None:
        raise ApiError(404, "NOT_FOUND", "없는 팀입니다")
    m = db.query(Membership).filter_by(team_id=team_id, user_id=user.id).one_or_none()
    if m is None:
        raise ApiError(403, "FORBIDDEN", "이 팀의 멤버가 아닙니다")
    return m


def require_owner(db: Session, user: User, team_id: int) -> Membership:
    m = require_member(db, user, team_id)
    if m.role != "owner":
        raise ApiError(403, "OWNER_ONLY", "owner 만 할 수 있습니다")
    return m
