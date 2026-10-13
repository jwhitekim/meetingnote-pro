import os

os.environ["BCRYPT_ROUNDS"] = "4"  # 테스트 속도. 운영 기본값은 12
os.environ["JWT_SECRET"] = "test-secret"
os.environ["STT_API_KEY"] = ""
# .env 값이 테스트에 섞이지 않게 비워 둔다 (load_dotenv 는 이미 있는 값을 덮지 않는다)
for _k in ("STT_MODEL", "LLM_MODEL", "DATABASE_URL"):
    os.environ[_k] = ""

import pytest
from fastapi.testclient import TestClient

from backend.app import ai, db
from backend.app.main import app


class FakeAI:
    """ai.transcribe · ai.split 을 대신한다. 테스트가 결과와 실패를 정한다."""

    def __init__(self):
        self.text = "김대리: 목록은 제가 다음 주 금요일까지 하겠습니다."
        self.split_result = {"summary": "", "decisions": [], "todos": []}
        self.fail = False
        self.split_calls = []
        self.transcribe_kinds = []

    def transcribe(self, data: bytes, kind: str) -> str:
        self.transcribe_kinds.append(kind)
        if self.fail:
            raise ai.AIError("받아쓰기 실패")
        return self.text

    def split(self, body: str, member_names: list[str]) -> dict:
        self.split_calls.append((body, member_names))
        if self.fail:
            raise ai.AIError("구분 실패")
        return self.split_result


@pytest.fixture
def fake_ai(monkeypatch):
    fake = FakeAI()
    monkeypatch.setattr(ai, "transcribe", fake.transcribe)
    monkeypatch.setattr(ai, "split", fake.split)
    return fake


@pytest.fixture
def client(tmp_path, fake_ai):
    db.init_db(f"sqlite:///{tmp_path / 'test.db'}")
    with TestClient(app) as c:
        yield c
    db.engine.dispose()
    db.engine = None


def signup(client, email, name="사용자", password="password123"):
    r = client.post("/api/auth/signup", json={"email": email, "password": password, "name": name})
    assert r.status_code == 201, r.text
    return r.json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


class Person:
    def __init__(self, data):
        self.token = data["token"]
        self.id = data["user"]["id"]
        self.name = data["user"]["name"]
        self.h = auth(self.token)


@pytest.fixture
def team(client):
    """owner 김대리 · member 박과장 · 다른 팀 owner 남의팀장."""
    owner = Person(signup(client, "kim@example.com", "김대리"))
    t = client.post("/api/teams", json={"name": "기획팀"}, headers=owner.h).json()
    member = Person(signup(client, "park@example.com", "박과장"))
    client.post("/api/teams/join", json={"invite_code": t["invite_code"]}, headers=member.h)
    outsider = Person(signup(client, "out@example.com", "남의팀장"))
    client.post("/api/teams", json={"name": "다른팀"}, headers=outsider.h)

    class T:
        pass
    T.id, T.code, T.owner, T.member, T.outsider = t["id"], t["invite_code"], owner, member, outsider
    return T
