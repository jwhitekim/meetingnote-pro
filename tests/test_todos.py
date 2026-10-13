from backend.app import db
from backend.app.models import Activity

from .test_teams import add_meeting_with_todos


def kinds(team_id):
    with db.SessionLocal() as s:
        return [a.kind for a in s.query(Activity).filter_by(team_id=team_id).order_by(Activity.id)
                if a.kind != "member_join"]


# 팀 할 일 목록
def test_team_todos_include_meeting_title(client, team):
    add_meeting_with_todos(team.id, team.owner.id, [None], title="2차 스프린트")
    rows = client.get(f"/api/teams/{team.id}/todos", headers=team.member.h).json()
    assert rows[0]["meeting_title"] == "2차 스프린트"
    assert set(rows[0]) == {"id", "what", "assignee_id", "assignee_name", "due_text", "status", "meeting_id", "meeting_title"}


def test_team_todos_sorted_by_status(client, team):
    add_meeting_with_todos(team.id, team.owner.id, [None, None, None], statuses=["DONE", "OPEN", "DOING"])
    rows = client.get(f"/api/teams/{team.id}/todos", headers=team.owner.h).json()
    assert [r["status"] for r in rows] == ["OPEN", "DOING", "DONE"]


def test_team_todos_empty(client, team):
    r = client.get(f"/api/teams/{team.id}/todos", headers=team.owner.h)
    assert r.status_code == 200 and r.json() == []


def test_team_todos_other_team_forbidden(client, team):
    assert client.get(f"/api/teams/{team.id}/todos", headers=team.outsider.h).status_code == 403


# 내 할 일 목록
def test_my_todos_only_mine(client, team):
    add_meeting_with_todos(team.id, team.owner.id, [team.member.id, team.member.id, team.owner.id])
    rows = client.get("/api/me/todos", headers=team.member.h).json()
    assert len(rows) == 2 and all(r["assignee_id"] == team.member.id for r in rows)


# 할 일 상태 변경
def _first_todo(client, team):
    return client.get(f"/api/teams/{team.id}/todos", headers=team.owner.h).json()[0]["id"]


def test_move_to_done_records_activity(client, team):
    add_meeting_with_todos(team.id, team.owner.id, [None], statuses=["DOING"])
    tid = _first_todo(client, team)
    r = client.put(f"/api/todos/{tid}", json={"status": "DONE"}, headers=team.member.h)
    assert r.status_code == 200 and r.json()["status"] == "DONE"
    assert kinds(team.id) == ["todo_done"]
    client.put(f"/api/todos/{tid}", json={"status": "DONE"}, headers=team.member.h)  # 같은 값은 다시 남기지 않음
    assert kinds(team.id) == ["todo_done"]


def test_move_back_allowed(client, team):
    add_meeting_with_todos(team.id, team.owner.id, [None], statuses=["DONE"])
    tid = _first_todo(client, team)
    r = client.put(f"/api/todos/{tid}", json={"status": "OPEN"}, headers=team.owner.h)
    assert r.status_code == 200 and r.json()["status"] == "OPEN"


def test_unknown_status(client, team):
    add_meeting_with_todos(team.id, team.owner.id, [None])
    r = client.put(f"/api/todos/{_first_todo(client, team)}", json={"status": "LATER"}, headers=team.owner.h)
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"


def test_update_other_team_forbidden(client, team):
    add_meeting_with_todos(team.id, team.owner.id, [None])
    r = client.put(f"/api/todos/{_first_todo(client, team)}", json={"status": "DONE"}, headers=team.outsider.h)
    assert r.status_code == 403


# 담당자와 기한 변경
def test_assign_records_activity(client, team):
    add_meeting_with_todos(team.id, team.owner.id, [None])
    r = client.put(f"/api/todos/{_first_todo(client, team)}",
                   json={"assignee_id": team.member.id, "due_text": "이번 달 안"}, headers=team.owner.h)
    assert r.status_code == 200
    assert r.json()["assignee_name"] == "박과장" and r.json()["due_text"] == "이번 달 안"
    assert kinds(team.id) == ["todo_assign"]


def test_unassign(client, team):
    add_meeting_with_todos(team.id, team.owner.id, [team.member.id])
    r = client.put(f"/api/todos/{_first_todo(client, team)}", json={"assignee_id": None}, headers=team.owner.h)
    assert r.status_code == 200 and r.json()["assignee_id"] is None
    assert kinds(team.id) == []


def test_assign_outsider_rejected(client, team):
    add_meeting_with_todos(team.id, team.owner.id, [None])
    r = client.put(f"/api/todos/{_first_todo(client, team)}", json={"assignee_id": team.outsider.id}, headers=team.owner.h)
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"


# 할 일 삭제
def test_owner_deletes(client, team):
    add_meeting_with_todos(team.id, team.owner.id, [None])
    tid = _first_todo(client, team)
    assert client.delete(f"/api/todos/{tid}", headers=team.owner.h).status_code == 204
    assert client.get(f"/api/teams/{team.id}/todos", headers=team.owner.h).json() == []


def test_member_cannot_delete(client, team):
    add_meeting_with_todos(team.id, team.owner.id, [None])
    r = client.delete(f"/api/todos/{_first_todo(client, team)}", headers=team.member.h)
    assert r.status_code == 403 and r.json()["code"] == "OWNER_ONLY"
