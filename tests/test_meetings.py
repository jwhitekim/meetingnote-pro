from sqlalchemy import text

from backend.app import db
from backend.app.models import Activity, Comment, Todo

from .conftest import Person, signup
from .test_teams import add_meeting_with_todos

BODY = "김대리: 목록은 제가 다음 주 금요일까지 하겠습니다.\n박과장: 업로드는 25MB 로 하죠."


def new_meeting(client, team, who=None, **over):
    data = {"title": "2차 스프린트", "met_at": "2026-09-24T05:00:00Z", "attendees": "김대리, 박과장", "body": BODY}
    data.update(over)
    return client.post(f"/api/teams/{team.id}/meetings", json=data, headers=(who or team.owner).h)


# 회의록 생성과 세 항목 구분
def test_create_splits_into_three(client, team, fake_ai):
    fake_ai.split_result = {
        "summary": "스프린트 계획.",
        "decisions": ["업로드 25MB"],
        "todos": [{"what": "목록 구현", "assignee": "김대리", "due": "다음 주 금요일"},
                  {"what": "업로드 처리", "assignee": "박과장", "due": ""}],
    }
    r = new_meeting(client, team)
    assert r.status_code == 201
    m = r.json()
    assert m["summary"] == "스프린트 계획." and m["decisions"] == "업로드 25MB" and m["decision_count"] == 1
    assert [(t["what"], t["assignee_name"], t["due_text"], t["status"]) for t in m["todos"]] == [
        ("목록 구현", "김대리", "다음 주 금요일", "OPEN"), ("업로드 처리", "박과장", "", "OPEN")]
    assert fake_ai.split_calls[0] == (BODY, ["김대리", "박과장"])
    with db.SessionLocal() as s:
        assert [a.kind for a in s.query(Activity).filter_by(team_id=team.id, kind="meeting_add")] == ["meeting_add"]


def test_create_requires_body(client, team):
    r = new_meeting(client, team, body="")
    assert r.status_code == 400 and r.json()["code"] == "VALIDATION_ERROR"
    r = client.post(f"/api/teams/{team.id}/meetings", json={"title": "t", "met_at": "2026-09-24T05:00:00Z"},
                    headers=team.owner.h)
    assert r.status_code == 400
    assert client.get(f"/api/teams/{team.id}/meetings", headers=team.owner.h).json() == []


def test_create_other_team_forbidden(client, team):
    r = new_meeting(client, team, who=team.outsider)
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN"


# 구분 결과의 할 일 담당자와 기한
def test_unknown_assignee_left_empty(client, team, fake_ai):
    fake_ai.split_result = {"summary": "", "decisions": [], "todos": [{"what": "인터뷰", "assignee": "최선임", "due": ""}]}
    t = new_meeting(client, team).json()["todos"][0]
    assert t["assignee_id"] is None and t["assignee_name"] is None and t["due_text"] == ""


def test_no_decisions(client, team, fake_ai):
    fake_ai.split_result = {"summary": "논의만 함.", "decisions": [], "todos": []}
    m = new_meeting(client, team).json()
    assert m["decisions"] == "" and m["decision_count"] == 0


# 구분 실패 시에도 저장
def test_ai_failure_still_saves(client, team, fake_ai):
    fake_ai.fail = True
    r = new_meeting(client, team)
    assert r.status_code == 201
    m = r.json()
    assert m["body"] == BODY and m["summary"] == "" and m["todos"] == []


# 회의록 목록
def test_list_has_no_body_and_sorted(client, team):
    new_meeting(client, team, title="이른 회의", met_at="2026-09-10T01:00:00Z")
    new_meeting(client, team, title="늦은 회의", met_at="2026-09-24T01:00:00Z")
    rows = client.get(f"/api/teams/{team.id}/meetings", headers=team.member.h).json()
    assert [r["title"] for r in rows] == ["늦은 회의", "이른 회의"]
    assert all("body" not in r for r in rows)
    assert set(rows[0]) == {"id", "title", "met_at", "attendees", "summary", "created_at",
                            "todo_done_count", "todo_total_count", "decision_count"}


def test_list_counts(client, team, fake_ai):
    fake_ai.split_result = {"summary": "", "decisions": ["결정 1", "결정 2"],
                            "todos": [{"what": f"일 {i}", "assignee": "", "due": ""} for i in range(3)]}
    m = new_meeting(client, team).json()
    client.put(f"/api/todos/{m['todos'][0]['id']}", json={"status": "DONE"}, headers=team.owner.h)
    with db.SessionLocal() as s:  # 빈 줄이 섞여도 decision_count 는 빈 줄을 뺀다
        s.execute(text("UPDATE meetings SET decisions = :d"), {"d": "결정 1\n\n결정 2\n"})
        s.commit()
    row = client.get(f"/api/teams/{team.id}/meetings", headers=team.owner.h).json()[0]
    assert (row["todo_done_count"], row["todo_total_count"], row["decision_count"]) == (1, 3, 2)


def test_list_empty(client, team):
    r = client.get(f"/api/teams/{team.id}/meetings", headers=team.owner.h)
    assert r.status_code == 200 and r.json() == []


def test_list_other_team_forbidden(client, team):
    assert client.get(f"/api/teams/{team.id}/meetings", headers=team.outsider.h).status_code == 403


# 회의록 검색과 기간
def test_search_attendees(client, team):
    new_meeting(client, team, title="A", attendees="김대리, 박과장")
    new_meeting(client, team, title="B", attendees="김대리")
    rows = client.get(f"/api/teams/{team.id}/meetings", params={"q": "박과장"}, headers=team.owner.h).json()
    assert [r["title"] for r in rows] == ["A"]


def test_search_title(client, team):
    new_meeting(client, team, title="2차 스프린트 계획")
    new_meeting(client, team, title="주간 회고")
    rows = client.get(f"/api/teams/{team.id}/meetings", params={"q": "스프린트"}, headers=team.owner.h).json()
    assert [r["title"] for r in rows] == ["2차 스프린트 계획"]


def test_search_body_only_is_empty(client, team):
    new_meeting(client, team, body="사용자 인터뷰를 다섯 분 하기로")
    r = client.get(f"/api/teams/{team.id}/meetings", params={"q": "인터뷰"}, headers=team.owner.h)
    assert r.status_code == 200 and r.json() == []


def test_date_range(client, team):
    new_meeting(client, team, title="9월 10일", met_at="2026-09-10T01:00:00Z")
    new_meeting(client, team, title="9월 24일", met_at="2026-09-24T01:00:00Z")
    new_meeting(client, team, title="9월 30일 끝", met_at="2026-09-30T23:00:00Z")
    rows = client.get(f"/api/teams/{team.id}/meetings", params={"from": "2026-09-20", "to": "2026-09-30"},
                      headers=team.owner.h).json()
    assert [r["title"] for r in rows] == ["9월 30일 끝", "9월 24일"]


# 회의록 단건
def test_get_detail_with_body_and_todos(client, team):
    mid = add_meeting_with_todos(team.id, team.owner.id, [team.member.id, None, None])
    r = client.get(f"/api/meetings/{mid}", headers=team.member.h)
    assert r.status_code == 200
    m = r.json()
    assert m["body"] == "본문" and len(m["todos"]) == 3 and m["author_name"] == "김대리"
    assert m["todos"][0]["meeting_title"] == "2차 스프린트"


def test_get_missing(client, team):
    r = client.get("/api/meetings/9999", headers=team.owner.h)
    assert r.status_code == 404 and r.json()["code"] == "MEETING_NOT_FOUND"


def test_get_other_team_forbidden(client, team):
    mid = add_meeting_with_todos(team.id, team.owner.id, [])
    assert client.get(f"/api/meetings/{mid}", headers=team.outsider.h).status_code == 403


# 회의록 수정
def test_update_title_keeps_split(client, team, fake_ai):
    fake_ai.split_result = {"summary": "요약", "decisions": [], "todos": [{"what": "일", "assignee": "", "due": ""}]}
    m = new_meeting(client, team, who=team.member).json()
    r = client.put(f"/api/meetings/{m['id']}", json={"title": "3차 스프린트"}, headers=team.member.h)
    assert r.status_code == 200
    assert r.json()["title"] == "3차 스프린트" and r.json()["summary"] == "요약" and len(r.json()["todos"]) == 1
    assert len(fake_ai.split_calls) == 1
    assert client.put(f"/api/meetings/{m['id']}", json={"title": "owner 수정"}, headers=team.owner.h).status_code == 200


def test_update_others_meeting_forbidden(client, team):
    m = new_meeting(client, team).json()
    r = client.put(f"/api/meetings/{m['id']}", json={"title": "x"}, headers=team.member.h)
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN"


# 회의록 삭제
def test_delete_cascades(client, team):
    mid = add_meeting_with_todos(team.id, team.owner.id, [None, None, None])
    assert client.post(f"/api/meetings/{mid}/comments", json={"content": "의견"}, headers=team.member.h).status_code == 201
    r = client.delete(f"/api/meetings/{mid}", headers=team.owner.h)
    assert r.status_code == 204
    assert client.get(f"/api/teams/{team.id}/todos", headers=team.owner.h).json() == []
    with db.SessionLocal() as s:
        assert s.query(Todo).count() == 0 and s.query(Comment).count() == 0
    assert client.get(f"/api/meetings/{mid}", headers=team.owner.h).status_code == 404


def test_delete_others_meeting_forbidden(client, team):
    m = new_meeting(client, team).json()
    r = client.delete(f"/api/meetings/{m['id']}", headers=team.member.h)
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN"


# 녹취 업로드와 받아쓰기
WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 4_000_000
MP3 = b"ID3\x04\x00\x00" + b"\x00" * 1000
MP4 = b"\x00\x00\x00\x20ftypisom" + b"\x00" * 1000


def test_upload_wav_returns_text(client, team, fake_ai):
    r = client.post("/api/upload", files={"file": ("회의_녹음.wav", WAV, "audio/wav")}, headers=team.owner.h)
    assert r.status_code == 200 and r.json() == {"text": fake_ai.text}
    assert fake_ai.transcribe_kinds == ["wav"]
    assert client.get(f"/api/teams/{team.id}/meetings", headers=team.owner.h).json() == []


def test_upload_mp3(client, team, fake_ai):
    r = client.post("/api/upload", files={"file": ("a.mp3", MP3, "audio/mpeg")}, headers=team.owner.h)
    assert r.status_code == 200
    assert fake_ai.transcribe_kinds == ["mp3"]


def test_upload_fake_mp3_extension(client, team):
    r = client.post("/api/upload", files={"file": ("a.mp3", MP4, "audio/mpeg")}, headers=team.owner.h)
    assert r.status_code == 415 and r.json()["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_upload_too_large(client, team):
    big = b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * (25 * 1024 * 1024)
    r = client.post("/api/upload", files={"file": ("big.wav", big, "audio/wav")}, headers=team.owner.h)
    assert r.status_code == 413 and r.json()["code"] == "PAYLOAD_TOO_LARGE"


def test_upload_transcribe_failed(client, team, fake_ai):
    fake_ai.fail = True
    r = client.post("/api/upload", files={"file": ("a.wav", WAV, "audio/wav")}, headers=team.owner.h)
    assert r.status_code == 502 and r.json()["code"] == "TRANSCRIBE_FAILED"


def test_upload_requires_login(client):
    r = client.post("/api/upload", files={"file": ("a.wav", WAV, "audio/wav")})
    assert r.status_code == 401
