from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import activity, ai
from ..db import get_db
from ..errors import ApiError
from ..models import Meeting, Membership, Todo, User, iso
from ..security import current_user, require_member
from .todos import todo_out

router = APIRouter(prefix="/api", tags=["Meeting"])

MAX_UPLOAD = 25 * 1024 * 1024  # ACME Constraints: 25MB


class MeetingIn(BaseModel):
    title: str = Field(min_length=1, max_length=200, examples=["2차 스프린트 계획 회의"])
    met_at: datetime = Field(examples=["2026-09-24T05:00:00Z"])
    attendees: str = Field(default="", examples=["김대리, 박과장, 이주임"])
    body: str = Field(min_length=1, examples=["김대리: 목록과 검색은 제가 다음 주 금요일까지 하겠습니다."])


class MeetingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    met_at: datetime | None = None
    attendees: str | None = None
    body: str | None = Field(default=None, min_length=1)


def to_utc(dt: datetime) -> datetime:
    """시간대가 있으면 UTC 로 바꾸고, 없으면 UTC 로 본다. 저장은 naive UTC."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def decision_lines(decisions: str) -> list[str]:
    return [s for s in (decisions or "").split("\n") if s.strip()]


def detail_out(m: Meeting) -> dict:
    todos = sorted(m.todos, key=lambda t: t.id)
    return {"id": m.id, "team_id": m.team_id, "title": m.title, "met_at": iso(m.met_at), "attendees": m.attendees,
            "summary": m.summary, "created_at": iso(m.created_at),
            "todo_done_count": sum(t.status == "DONE" for t in todos), "todo_total_count": len(todos),
            "decision_count": len(decision_lines(m.decisions)),
            "body": m.body, "decisions": m.decisions, "author_id": m.author_id, "author_name": m.author.name,
            "todos": [todo_out(t) for t in todos]}


def _meeting_in_my_team(db: Session, user: User, meeting_id: int) -> tuple[Meeting, Membership]:
    m = db.get(Meeting, meeting_id)
    if m is None:
        raise ApiError(404, "MEETING_NOT_FOUND", "없는 회의록입니다")
    return m, require_member(db, user, m.team_id)


def _require_author_or_owner(m: Meeting, membership: Membership, user: User) -> None:
    if m.author_id != user.id and membership.role != "owner":
        raise ApiError(403, "FORBIDDEN", "쓴 사람과 owner 만 할 수 있습니다")


@router.post("/teams/{team_id}/meetings", status_code=201, summary="회의록 저장 - 저장하며 요약 · 결정사항 · 할 일로 구분")
def create_meeting(team_id: int, body: MeetingIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    members = {m.user.name: m.user.id for m in db.query(Membership).filter_by(team_id=team_id).order_by(Membership.id)}
    try:
        parts = ai.split(body.body, list(members))
    except ai.AIError:
        parts = {"summary": "", "decisions": [], "todos": []}  # 본문은 잃지 않는다
    m = Meeting(team_id=team_id, title=body.title.strip(), met_at=to_utc(body.met_at), attendees=body.attendees.strip(),
                body=body.body, summary=parts["summary"], decisions="\n".join(parts["decisions"]), author_id=user.id)
    db.add(m)
    db.flush()
    for t in parts["todos"]:
        # 팀 멤버 이름과 정확히 같을 때만 연결. 나머지는 미정 - 지어내지 않는다
        db.add(Todo(meeting_id=m.id, what=t["what"], assignee_id=members.get(t["assignee"]),
                    due_text=t["due"], status="OPEN"))
    activity.record(db, team_id, user, "meeting_add", title=m.title)
    db.commit()
    db.refresh(m)
    return detail_out(m)


@router.get("/teams/{team_id}/meetings", summary="회의록 목록 - body 미포함. q 는 제목 · 참석자만, from/to 는 ISO 날짜")
def list_meetings(
    team_id: int,
    q: str | None = Query(default=None, description="제목 · 참석자 부분 일치"),
    date_from: date | None = Query(default=None, alias="from", examples=["2026-09-01"]),
    date_to: date | None = Query(default=None, alias="to", examples=["2026-09-30"]),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    require_member(db, user, team_id)
    done = (select(func.count(Todo.id)).where(Todo.meeting_id == Meeting.id, Todo.status == "DONE")
            .correlate(Meeting).scalar_subquery())
    total = select(func.count(Todo.id)).where(Todo.meeting_id == Meeting.id).correlate(Meeting).scalar_subquery()
    query = db.query(Meeting.id, Meeting.title, Meeting.met_at, Meeting.attendees, Meeting.summary,
                     Meeting.created_at, Meeting.decisions, done, total).filter(Meeting.team_id == team_id)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(or_(Meeting.title.ilike(like), Meeting.attendees.ilike(like)))
    if date_from:
        query = query.filter(Meeting.met_at >= datetime.combine(date_from, time.min))
    if date_to:
        query = query.filter(Meeting.met_at <= datetime.combine(date_to, time.max))
    rows = query.order_by(Meeting.met_at.desc(), Meeting.id.desc()).all()
    return [{"id": r[0], "title": r[1], "met_at": iso(r[2]), "attendees": r[3], "summary": r[4],
             "created_at": iso(r[5]), "todo_done_count": r[7], "todo_total_count": r[8],
             "decision_count": len(decision_lines(r[6]))} for r in rows]


@router.get("/meetings/{meeting_id}", summary="회의록 단건 - body 와 할 일 포함")
def get_meeting(meeting_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m, _ = _meeting_in_my_team(db, user, meeting_id)
    return detail_out(m)


@router.put("/meetings/{meeting_id}", summary="회의록 수정 (쓴 사람 · owner) - 세 항목은 다시 구분하지 않음")
def update_meeting(meeting_id: int, body: MeetingUpdate, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    m, membership = _meeting_in_my_team(db, user, meeting_id)
    _require_author_or_owner(m, membership, user)
    sent = body.model_fields_set
    if "title" in sent and body.title is not None:
        m.title = body.title.strip()
    if "met_at" in sent and body.met_at is not None:
        m.met_at = to_utc(body.met_at)
    if "attendees" in sent and body.attendees is not None:
        m.attendees = body.attendees.strip()
    if "body" in sent and body.body is not None:
        m.body = body.body
    db.commit()
    return detail_out(m)


@router.delete("/meetings/{meeting_id}", status_code=204, summary="회의록 삭제 (쓴 사람 · owner) - 딸린 할 일 · 댓글도 함께")
def delete_meeting(meeting_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m, membership = _meeting_in_my_team(db, user, meeting_id)
    _require_author_or_owner(m, membership, user)
    db.delete(m)
    db.commit()
    return Response(status_code=204)


def audio_kind(head: bytes) -> str | None:
    """확장자가 아니라 내용 앞 바이트로 판정."""
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[:3] == b"ID3" or (len(head) >= 2 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
        return "mp3"
    return None


@router.post("/upload", summary="녹취 업로드 - mp3 · wav, 25MB 이하. 받아쓴 본문만 돌려주고 저장은 하지 않음")
def upload(file: UploadFile = File(...), user: User = Depends(current_user)):
    data = file.file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", "25MB 를 넘는 파일은 올릴 수 없습니다")
    kind = audio_kind(data[:16])
    if kind is None:
        raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", "mp3 또는 wav 만 올릴 수 있습니다")
    try:
        text = ai.transcribe(data, kind)
    except ai.AIError:
        raise ApiError(502, "TRANSCRIBE_FAILED", "받아쓰기에 실패했습니다. 잠시 뒤 다시 올려 주세요")
    return {"text": text}
