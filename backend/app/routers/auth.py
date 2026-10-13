import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import ApiError
from ..models import User
from ..security import check_password, current_user, hash_password, make_token, membership_of

router = APIRouter(prefix="/api/auth", tags=["Auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8


class SignupIn(BaseModel):
    email: str = Field(examples=["kim@example.com"])
    password: str = Field(examples=["password123"])
    name: str = Field(min_length=1, max_length=100, examples=["김대리"])


class LoginIn(BaseModel):
    email: str = Field(examples=["kim@example.com"])
    password: str = Field(examples=["password123"])


class MeIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    password: str | None = None


def check_password_strength(pw: str) -> None:
    if len(pw) < MIN_PASSWORD:
        raise ApiError(400, "PASSWORD_TOO_WEAK", "8자 이상 입력해 주세요")


def user_out(db: Session, u: User) -> dict:
    m = membership_of(db, u)
    return {"id": u.id, "name": u.name, "email": u.email, "role": m.role if m else None}


@router.post("/signup", status_code=201, summary="회원가입")
def signup(body: SignupIn, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise ApiError(400, "EMAIL_INVALID", "올바른 이메일 형식이 아닙니다")
    check_password_strength(body.password)
    if db.query(User).filter_by(email=email).first():
        raise ApiError(409, "EMAIL_DUPLICATED", "이미 가입된 이메일입니다")
    u = User(email=email, password_hash=hash_password(body.password), name=body.name.strip())
    db.add(u)
    db.commit()
    return {"token": make_token(u.id), "user": user_out(db, u)}


@router.post("/login", summary="로그인 - 받은 token 을 Authorize 에 넣는다")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=body.email.strip().lower()).first()
    if u is None or not check_password(body.password, u.password_hash):
        raise ApiError(401, "INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다")
    return {"token": make_token(u.id), "user": user_out(db, u)}


@router.get("/me", summary="내 정보")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return user_out(db, user)


@router.put("/me", summary="내 정보 수정 - 보낸 값만 바꾼다. 이메일은 바꾸지 않는다")
def update_me(body: MeIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.password is not None:
        check_password_strength(body.password)
        user.password_hash = hash_password(body.password)
    if body.name is not None:
        user.name = body.name.strip()
    db.commit()
    return user_out(db, user)


@router.post("/logout", summary="로그아웃 - 서버는 200 만 돌려주고 화면이 토큰을 지운다")
def logout(_: User = Depends(current_user)):
    return {"ok": True}
