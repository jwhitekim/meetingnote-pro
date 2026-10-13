import re
from datetime import datetime

import pytest

from backend.app import activity, db
from backend.app.models import Activity, Meeting, Todo, User

from .conftest import Person, signup


def add_meeting_with_todos(team_id, author_id, assignees, title="2차 스프린트", met_at=None, statuses=None):
    """API 를 거치지 않고 회의록과 할 일을 넣는다 (팀 테스트용)."""
    with db.SessionLocal() as s:
        m = Meeting(team_id=team_id, title=title, met_at=met_at or datetime(2026, 9, 24, 5),
                    attendees="", body="본문", author_id=author_id)
        s.add(m)
        s.flush()
        for i, a in enumerate(assignees):
            s.add(Todo(meeting_id=m.id, what=f"할 일 {i}", assignee_id=a,
                       status=(statuses or ["OPEN"] * len(assignees))[i]))
        s.commit()
        return m.id


# 활동 종류
def test_activity_rejects_unknown_kind(client, team):
    with db.SessionLocal() as s, pytest.raises(ValueError):
        activity.record(s, team.id, s.get(User, team.owner.id), "team_rename")


# 팀 생성
def test_create_team(client):
    p = Person(signup(client, "kim@example.com", "김대리"))
    r = client.post("/api/teams", json={"name": "기획팀"}, headers=p.h)
    assert r.status_code == 201
    t = r.json()
    assert t["name"] == "기획팀" and t["role"] == "owner" and t["member_count"] == 1
    assert re.fullmatch(r"MN-[A-Z0-9]{4}", t["invite_code"])


def test_create_second_team_rejected(client, team):
    r = client.post("/api/teams", json={"name": "또팀"}, headers=team.owner.h)
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"


# 내 팀 목록
def test_no_team_is_empty_list(client):
    p = Person(signup(client, "kim@example.com"))
    r = client.get("/api/teams", headers=p.h)
    assert r.status_code == 200 and r.json() == []


def test_my_teams_one(client, team):
    r = client.get("/api/teams", headers=team.member.h).json()
    assert len(r) == 1 and r[0]["id"] == team.id and r[0]["role"] == "member" and r[0]["member_count"] == 2


# 합류
def test_join_ok_records_member_join(client, team):
    p = Person(signup(client, "lee@example.com", "이주임"))
    r = client.post("/api/teams/join", json={"invite_code": team.code}, headers=p.h)
    assert r.status_code == 200 and r.json()["id"] == team.id and r.json()["member_count"] == 3
    with db.SessionLocal() as s:
        kinds = [a.kind for a in s.query(Activity).filter_by(team_id=team.id, actor_id=p.id)]
    assert kinds == ["member_join"]


def test_join_unknown_code_keeps_account(client):
    p = Person(signup(client, "lee@example.com"))
    r = client.post("/api/teams/join", json={"invite_code": "MN-0000"}, headers=p.h)
    assert r.status_code == 404 and r.json()["code"] == "INVITE_NOT_FOUND"
    assert client.get("/api/auth/me", headers=p.h).status_code == 200


def test_join_team_full(client, team):
    for i in range(4):  # 2명 + 4명 = 6명
        p = Person(signup(client, f"m{i}@example.com"))
        assert client.post("/api/teams/join", json={"invite_code": team.code}, headers=p.h).status_code == 200
    seventh = Person(signup(client, "seven@example.com"))
    r = client.post("/api/teams/join", json={"invite_code": team.code}, headers=seventh.h)
    assert r.status_code == 409 and r.json()["code"] == "TEAM_FULL"


# 멤버 목록
def test_members_with_todo_count(client, team):
    add_meeting_with_todos(team.id, team.owner.id, [team.member.id, team.member.id, None])
    r = client.get(f"/api/teams/{team.id}/members", headers=team.owner.h)
    assert r.status_code == 200
    rows = {m["name"]: m for m in r.json()}
    assert rows["박과장"]["todo_count"] == 2 and rows["김대리"]["todo_count"] == 0
    assert r.json()[0]["role"] == "owner"
    assert set(r.json()[0]) == {"id", "name", "email", "role", "todo_count"}


def test_members_other_team_forbidden(client, team):
    r = client.get(f"/api/teams/{team.id}/members", headers=team.outsider.h)
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN"


# 초대코드 재발급
def test_reissue_code_invalidates_old(client, team):
    r = client.put(f"/api/teams/{team.id}/code", headers=team.owner.h)
    assert r.status_code == 200
    new = r.json()["invite_code"]
    assert new != team.code
    a, b = Person(signup(client, "a@example.com")), Person(signup(client, "b@example.com"))
    assert client.post("/api/teams/join", json={"invite_code": team.code}, headers=a.h).json()["code"] == "INVITE_NOT_FOUND"
    assert client.post("/api/teams/join", json={"invite_code": new}, headers=b.h).status_code == 200
    assert len(client.get(f"/api/teams/{team.id}/members", headers=team.owner.h).json()) == 3


def test_reissue_code_member_forbidden(client, team):
    r = client.put(f"/api/teams/{team.id}/code", headers=team.member.h)
    assert r.status_code == 403 and r.json()["code"] == "OWNER_ONLY"


# 팀 이름 변경
def test_rename_owner(client, team):
    r = client.put(f"/api/teams/{team.id}", json={"name": "제품팀"}, headers=team.owner.h)
    assert r.status_code == 200 and r.json()["name"] == "제품팀"


def test_rename_member_forbidden(client, team):
    r = client.put(f"/api/teams/{team.id}", json={"name": "제품팀"}, headers=team.member.h)
    assert r.status_code == 403 and r.json()["code"] == "OWNER_ONLY"
    assert client.get("/api/teams", headers=team.owner.h).json()[0]["name"] == "기획팀"
