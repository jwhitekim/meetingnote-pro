from datetime import datetime, timedelta, timezone

import jwt

from backend.app import db
from backend.app.models import User

from .conftest import auth, signup


# 회원가입
def test_signup_ok_and_password_hashed(client):
    r = client.post("/api/auth/signup", json={"email": "kim@example.com", "password": "password123", "name": "김대리"})
    assert r.status_code == 201
    body = r.json()
    assert body["token"]
    assert body["user"] == {"id": body["user"]["id"], "name": "김대리", "email": "kim@example.com", "role": None}
    with db.SessionLocal() as s:
        u = s.query(User).one()
        assert u.password_hash != "password123" and u.password_hash.startswith("$2")


def test_signup_email_invalid(client):
    r = client.post("/api/auth/signup", json={"email": "kim-at-example", "password": "password123", "name": "김"})
    assert r.status_code == 400 and r.json()["code"] == "EMAIL_INVALID"


def test_signup_email_duplicated(client):
    signup(client, "kim@example.com")
    r = client.post("/api/auth/signup", json={"email": "kim@example.com", "password": "password123", "name": "김"})
    assert r.status_code == 409 and r.json()["code"] == "EMAIL_DUPLICATED"


def test_signup_password_too_weak(client):
    r = client.post("/api/auth/signup", json={"email": "kim@example.com", "password": "1234567", "name": "김"})
    assert r.status_code == 400 and r.json()["code"] == "PASSWORD_TOO_WEAK"
    with db.SessionLocal() as s:
        assert s.query(User).count() == 0


# 로그인
def test_login_ok_token_24h(client):
    signup(client, "kim@example.com")
    r = client.post("/api/auth/login", json={"email": "kim@example.com", "password": "password123"})
    assert r.status_code == 200
    payload = jwt.decode(r.json()["token"], options={"verify_signature": False})
    left = payload["exp"] - datetime.now(timezone.utc).timestamp()
    assert 24 * 3600 - 60 < left <= 24 * 3600


def test_login_same_error_for_unknown_email_and_wrong_password(client):
    signup(client, "kim@example.com")
    a = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    b = client.post("/api/auth/login", json={"email": "kim@example.com", "password": "wrongpass1"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()
    assert a.json()["code"] == "INVALID_CREDENTIALS"


# 토큰 검증
def _token(sub, exp, secret="test-secret"):
    return jwt.encode({"sub": str(sub), "exp": exp}, secret, algorithm="HS256")


def test_expired_token(client):
    uid = signup(client, "kim@example.com")["user"]["id"]
    old = _token(uid, datetime.now(timezone.utc) - timedelta(seconds=1))
    r = client.get("/api/auth/me", headers=auth(old))
    assert r.status_code == 401 and r.json()["code"] == "TOKEN_EXPIRED"


def test_no_token(client):
    r = client.get("/api/teams")
    assert r.status_code == 401 and r.json()["code"] == "TOKEN_EXPIRED"


def test_forged_token(client):
    uid = signup(client, "kim@example.com")["user"]["id"]
    fake = _token(uid, datetime.now(timezone.utc) + timedelta(hours=1), secret="other")
    r = client.get("/api/auth/me", headers=auth(fake))
    assert r.status_code == 401 and r.json()["code"] == "TOKEN_EXPIRED"


# 내 정보 조회
def test_me_owner_role(client, team):
    r = client.get("/api/auth/me", headers=team.owner.h)
    assert r.status_code == 200 and r.json()["role"] == "owner"
    assert client.get("/api/auth/me", headers=team.member.h).json()["role"] == "member"


# 내 정보 수정
def test_update_name_only_keeps_password(client):
    t = signup(client, "kim@example.com")["token"]
    r = client.put("/api/auth/me", json={"name": "김수석"}, headers=auth(t))
    assert r.status_code == 200 and r.json()["name"] == "김수석"
    assert client.post("/api/auth/login", json={"email": "kim@example.com", "password": "password123"}).status_code == 200


def test_update_weak_password(client):
    t = signup(client, "kim@example.com")["token"]
    r = client.put("/api/auth/me", json={"password": "1234567"}, headers=auth(t))
    assert r.status_code == 400 and r.json()["code"] == "PASSWORD_TOO_WEAK"
    assert client.post("/api/auth/login", json={"email": "kim@example.com", "password": "password123"}).status_code == 200


def test_update_new_password(client):
    t = signup(client, "kim@example.com")["token"]
    assert client.put("/api/auth/me", json={"password": "newpass123"}, headers=auth(t)).status_code == 200
    assert client.post("/api/auth/login", json={"email": "kim@example.com", "password": "newpass123"}).status_code == 200


def test_update_ignores_email(client):
    t = signup(client, "kim@example.com")["token"]
    r = client.put("/api/auth/me", json={"email": "new@example.com", "name": "김수석"}, headers=auth(t))
    assert r.json()["email"] == "kim@example.com" and r.json()["name"] == "김수석"


# 로그아웃
def test_logout(client):
    t = signup(client, "kim@example.com")["token"]
    assert client.post("/api/auth/logout", headers=auth(t)).status_code == 200


# 오류 응답 형식
def test_validation_error_is_400_code_msg(client):
    r = client.post("/api/auth/login", json={})
    assert r.status_code == 400
    assert r.json()["code"] == "VALIDATION_ERROR" and r.json()["msg"]
