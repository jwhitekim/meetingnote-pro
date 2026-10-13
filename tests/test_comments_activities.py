from datetime import datetime, timedelta

from backend.app import db
from backend.app.models import Activity

from .conftest import Person, signup
from .test_teams import add_meeting_with_todos


def comment(client, mid, who, content="의견"):
    return client.post(f"/api/meetings/{mid}/comments", json={"content": content}, headers=who.h)


# 댓글 등록
def test_add_comment_records_activity(client, team):
    mid = add_meeting_with_todos(team.id, team.owner.id, [])
    r = comment(client, mid, team.member, "받아쓰기 실패는 구분 실패로 표시")
    assert r.status_code == 201 and r.json()["content"] == "받아쓰기 실패는 구분 실패로 표시"
    acts = client.get(f"/api/teams/{team.id}/activities", headers=team.owner.h).json()
    assert acts[0]["kind"] == "comment_add"


def test_comment_501_chars(client, team):
    mid = add_meeting_with_todos(team.id, team.owner.id, [])
    r = comment(client, mid, team.member, "가" * 501)
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"
    assert comment(client, mid, team.member, "가" * 500).status_code == 201


def test_comment_empty(client, team):
    mid = add_meeting_with_todos(team.id, team.owner.id, [])
    assert comment(client, mid, team.member, "   ").status_code == 400


def test_comment_other_team_forbidden(client, team):
    mid = add_meeting_with_todos(team.id, team.owner.id, [])
    assert comment(client, mid, team.outsider).status_code == 403


# 댓글 목록
def test_can_delete_flag(client, team):
    b = Person(signup(client, "b@example.com", "이주임"))
    client.post("/api/teams/join", json={"invite_code": team.code}, headers=b.h)
    mid = add_meeting_with_todos(team.id, team.owner.id, [])
    comment(client, mid, team.member, "첫째")
    comment(client, mid, team.member, "둘째")
    rows_b = client.get(f"/api/meetings/{mid}/comments", headers=b.h).json()
    rows_owner = client.get(f"/api/meetings/{mid}/comments", headers=team.owner.h).json()
    rows_a = client.get(f"/api/meetings/{mid}/comments", headers=team.member.h).json()
    assert [r["content"] for r in rows_b] == ["첫째", "둘째"]
    assert [r["can_delete"] for r in rows_b] == [False, False]
    assert [r["can_delete"] for r in rows_owner] == [True, True]
    assert [r["can_delete"] for r in rows_a] == [True, True]
    assert set(rows_b[0]) == {"id", "user_id", "user_name", "content", "created_at", "can_delete"}


def test_no_comments(client, team):
    mid = add_meeting_with_todos(team.id, team.owner.id, [])
    r = client.get(f"/api/meetings/{mid}/comments", headers=team.owner.h)
    assert r.status_code == 200 and r.json() == []


# 댓글 삭제
def test_delete_others_comment_forbidden(client, team):
    b = Person(signup(client, "b@example.com", "이주임"))
    client.post("/api/teams/join", json={"invite_code": team.code}, headers=b.h)
    mid = add_meeting_with_todos(team.id, team.owner.id, [])
    cid = comment(client, mid, team.member).json()["id"]
    r = client.delete(f"/api/comments/{cid}", headers=b.h)
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN"


def test_owner_deletes_comment(client, team):
    mid = add_meeting_with_todos(team.id, team.owner.id, [])
    cid = comment(client, mid, team.member).json()["id"]
    assert client.delete(f"/api/comments/{cid}", headers=team.owner.h).status_code == 204
    assert client.get(f"/api/meetings/{mid}/comments", headers=team.owner.h).json() == []


# 활동 종류는 다섯 가지
def test_profile_update_not_recorded(client):
    p = Person(signup(client, "kim@example.com", "김대리"))
    t = client.post("/api/teams", json={"name": "기획팀"}, headers=p.h).json()
    client.put("/api/auth/me", json={"name": "김수석"}, headers=p.h)
    client.put(f"/api/teams/{t['id']}", json={"name": "제품팀"}, headers=p.h)
    client.put(f"/api/teams/{t['id']}/code", headers=p.h)
    assert client.get(f"/api/teams/{t['id']}/activities", headers=p.h).json() == []


# 팀 활동 목록
def test_meeting_add_sentence(client, team):
    r = client.post(f"/api/teams/{team.id}/meetings",
                    json={"title": "2차 스프린트", "met_at": "2026-09-24T05:00:00Z", "body": "본문"}, headers=team.owner.h)
    assert r.status_code == 201
    a = client.get(f"/api/teams/{team.id}/activities", headers=team.member.h).json()[0]
    assert a["kind"] == "meeting_add" and "김대리" in a["text"] and "2차 스프린트" in a["text"]
    assert a["actor_name"] == "김대리"
    assert set(a) == {"id", "kind", "actor_name", "text", "created_at"}


def test_activity_limit_50_recent_first(client, team):
    base = datetime(2026, 9, 1)
    with db.SessionLocal() as s:
        for i in range(60):
            s.add(Activity(team_id=team.id, actor_id=team.owner.id, kind="comment_add", target=f"활동 {i}",
                           created_at=base + timedelta(minutes=i)))
        s.commit()
    rows = client.get(f"/api/teams/{team.id}/activities", headers=team.owner.h).json()
    assert len(rows) == 50
    stamps = [r["created_at"] for r in rows]
    assert stamps == sorted(stamps, reverse=True)
    texts = [r["text"] for r in rows if r["text"].startswith("활동")]
    assert texts[0] == "활동 59" and "활동 9" not in texts


def test_team_activities_other_team_forbidden(client, team):
    assert client.get(f"/api/teams/{team.id}/activities", headers=team.outsider.h).status_code == 403


# 내 활동 목록
def test_my_activities_empty_after_create(client):
    p = Person(signup(client, "kim@example.com"))
    client.post("/api/teams", json={"name": "기획팀"}, headers=p.h)
    r = client.get("/api/me/activities", headers=p.h)
    assert r.status_code == 200 and r.json() == []


def test_my_activities_excludes_others(client, team):
    mid = add_meeting_with_todos(team.id, team.owner.id, [])
    comment(client, mid, team.owner)
    comment(client, mid, team.member)
    rows = client.get("/api/me/activities", headers=team.owner.h).json()
    assert [r["kind"] for r in rows] == ["comment_add"]
