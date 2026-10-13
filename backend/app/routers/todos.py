from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import case
from sqlalchemy.orm import Session

from .. import activity
from ..db import get_db
from ..errors import ApiError
from ..models import Meeting, Membership, Todo, User
from ..security import current_user, membership_of, require_member, require_owner

router = APIRouter(prefix="/api", tags=["Todo"])

STATUSES = ("OPEN", "DOING", "DONE")
_status_order = case({"OPEN": 0, "DOING": 1, "DONE": 2}, value=Todo.status)


class TodoIn(BaseModel):
    status: str | None = Field(default=None, examples=["DONE"])
    assignee_id: int | None = Field(default=None, description="팀 멤버 id. null 이면 미정")
    due_text: str | None = Field(default=None, max_length=100, examples=["이번 달 안"])


def todo_out(t: Todo) -> dict:
    return {"id": t.id, "what": t.what, "assignee_id": t.assignee_id,
            "assignee_name": t.assignee.name if t.assignee else None,
            "due_text": t.due_text, "status": t.status,
            "meeting_id": t.meeting_id, "meeting_title": t.meeting.title}


def _sorted(q):
    return q.order_by(_status_order, Todo.due_text, Todo.id).all()


def _todo_in_my_team(db: Session, user: User, todo_id: int) -> Todo:
    t = db.get(Todo, todo_id)
    if t is None:
        raise ApiError(404, "NOT_FOUND", "없는 할 일입니다")
    require_member(db, user, t.meeting.team_id)
    return t


@router.get("/teams/{team_id}/todos", summary="팀 할 일 목록 (회의록 제목 포함)")
def team_todos(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    return [todo_out(t) for t in _sorted(db.query(Todo).join(Meeting).filter(Meeting.team_id == team_id))]


@router.get("/me/todos", summary="내 할 일 목록")
def my_todos(user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = membership_of(db, user)
    if m is None:
        return []
    q = db.query(Todo).join(Meeting).filter(Meeting.team_id == m.team_id, Todo.assignee_id == user.id)
    return [todo_out(t) for t in _sorted(q)]


@router.put("/todos/{todo_id}", summary="상태 · 담당자 · 기한 변경 - 보낸 값만 바꾼다")
def update_todo(todo_id: int, body: TodoIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = _todo_in_my_team(db, user, todo_id)
    sent = body.model_fields_set
    team_id = t.meeting.team_id
    if "status" in sent:
        if body.status not in STATUSES:
            raise ApiError(400, "VALIDATION_ERROR", "상태는 OPEN · DOING · DONE 중 하나입니다")
        if body.status == "DONE" and t.status != "DONE":
            activity.record(db, team_id, user, "todo_done", what=t.what)
        t.status = body.status
    if "assignee_id" in sent:
        if body.assignee_id is not None:
            m = db.query(Membership).filter_by(team_id=team_id, user_id=body.assignee_id).one_or_none()
            if m is None:
                raise ApiError(400, "VALIDATION_ERROR", "팀 멤버만 담당자가 될 수 있습니다")
            if body.assignee_id != t.assignee_id:
                activity.record(db, team_id, user, "todo_assign", what=t.what, assignee=m.user.name)
        t.assignee_id = body.assignee_id
    if "due_text" in sent:
        t.due_text = (body.due_text or "").strip()
    db.commit()
    db.refresh(t)
    return todo_out(t)


@router.delete("/todos/{todo_id}", status_code=204, summary="할 일 삭제 (owner)")
def delete_todo(todo_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.get(Todo, todo_id)
    if t is None:
        raise ApiError(404, "NOT_FOUND", "없는 할 일입니다")
    require_owner(db, user, t.meeting.team_id)
    db.delete(t)
    db.commit()
    return Response(status_code=204)
