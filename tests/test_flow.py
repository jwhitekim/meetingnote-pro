"""사용 시나리오 1 · 2 를 API 로 잇는다 (프로그램정의서 2절)."""
import time

from .conftest import Person, signup

BODY = "김대리: 목록과 검색은 제가 다음 주 금요일까지 하겠습니다.\n박과장: 업로드는 25MB 로 정합시다."


def test_leader_to_member_flow(client, fake_ai):
    # 시나리오 1 - 리더 가입 > 팀 생성 · 초대코드 > 멤버 합류 > 녹취 업로드 > 3항목 구분 > 할 일 배정
    lead = Person(signup(client, "lead@example.com", "김대리"))
    team = client.post("/api/teams", json={"name": "기획팀"}, headers=lead.h).json()
    member = Person(signup(client, "park@example.com", "박과장"))
    assert client.post("/api/teams/join", json={"invite_code": team["invite_code"]}, headers=member.h).status_code == 200

    fake_ai.text = BODY
    wav = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 1000
    text = client.post("/api/upload", files={"file": ("rec.wav", wav, "audio/wav")}, headers=lead.h).json()["text"]
    fake_ai.split_result = {"summary": "목록과 업로드를 정함.", "decisions": ["업로드 25MB"],
                            "todos": [{"what": "목록과 검색", "assignee": "김대리", "due": "다음 주 금요일"},
                                      {"what": "업로드 처리", "assignee": "", "due": ""}]}
    m = client.post(f"/api/teams/{team['id']}/meetings",
                    json={"title": "2차 스프린트", "met_at": "2026-09-24T05:00:00Z", "attendees": "김대리, 박과장", "body": text},
                    headers=lead.h).json()
    unassigned = next(t for t in m["todos"] if t["assignee_id"] is None)
    r = client.put(f"/api/todos/{unassigned['id']}", json={"assignee_id": member.id, "due_text": "이번 주 안"}, headers=lead.h)
    assert r.status_code == 200 and r.json()["assignee_name"] == "박과장"

    # 시나리오 2 - 팀원이 칸반에서 담당 할 일을 완료로 이동 > 활동 기록
    mine = client.get("/api/me/todos", headers=member.h).json()
    assert [t["what"] for t in mine] == ["업로드 처리"]
    assert client.put(f"/api/todos/{mine[0]['id']}", json={"status": "DONE"}, headers=member.h).status_code == 200

    acts = client.get(f"/api/teams/{team['id']}/activities", headers=lead.h).json()
    assert [a["kind"] for a in acts] == ["todo_done", "todo_assign", "meeting_add", "member_join"]
    row = client.get(f"/api/teams/{team['id']}/meetings", headers=member.h).json()[0]
    assert (row["todo_done_count"], row["todo_total_count"], row["decision_count"]) == (1, 2, 1)


def test_list_endpoints_under_100ms(client, team):
    """ACME Metrics - API 100ms 이내. 회의록 20건 · 할 일 60건에서 목록 응답을 잰다 (로컬)."""
    for i in range(20):
        client.post(f"/api/teams/{team.id}/meetings",
                    json={"title": f"회의 {i}", "met_at": f"2026-09-{i + 1:02d}T05:00:00Z", "body": "본문"},
                    headers=team.owner.h)
    from backend.app import db
    from backend.app.models import Meeting, Todo
    with db.SessionLocal() as s:
        for m in s.query(Meeting):
            s.add_all(Todo(meeting_id=m.id, what=f"일 {k}", status="OPEN") for k in range(3))
        s.commit()
    for path in (f"/api/teams/{team.id}/meetings", f"/api/teams/{team.id}/todos"):
        client.get(path, headers=team.owner.h)  # 워밍업
        start = time.perf_counter()
        r = client.get(path, headers=team.owner.h)
        took = (time.perf_counter() - start) * 1000
        assert r.status_code == 200
        assert took < 100, f"{path} {took:.1f}ms"
