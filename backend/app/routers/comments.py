from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import activity
from ..db import get_db
from ..errors import ApiError
from ..models import Comment, Meeting, Membership, User, iso
from ..security import current_user, require_member

router = APIRouter(prefix="/api", tags=["Comment"])


class CommentIn(BaseModel):
    content: str = Field(max_length=500, examples=["받아쓰기 실패는 구분 실패로 표시하기로 했습니다."])


def _can_delete(c: Comment, user: User, membership: Membership) -> bool:
    return c.user_id == user.id or membership.role == "owner"


def comment_out(c: Comment, user: User, membership: Membership) -> dict:
    return {"id": c.id, "user_id": c.user_id, "user_name": c.user.name, "content": c.content,
            "created_at": iso(c.created_at), "can_delete": _can_delete(c, user, membership)}


def _meeting(db: Session, user: User, meeting_id: int) -> tuple[Meeting, Membership]:
    m = db.get(Meeting, meeting_id)
    if m is None:
        raise ApiError(404, "MEETING_NOT_FOUND", "없는 회의록입니다")
    return m, require_member(db, user, m.team_id)


@router.post("/meetings/{meeting_id}/comments", status_code=201, summary="댓글 등록 (500자 이내)")
def add_comment(meeting_id: int, body: CommentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m, membership = _meeting(db, user, meeting_id)
    content = body.content.strip()
    if not content:
        raise ApiError(400, "VALIDATION_ERROR", "댓글을 입력해 주세요")
    c = Comment(meeting_id=m.id, user_id=user.id, content=content)
    db.add(c)
    activity.record(db, m.team_id, user, "comment_add", title=m.title)
    db.commit()
    return comment_out(c, user, membership)


@router.get("/meetings/{meeting_id}/comments", summary="댓글 목록 - can_delete 는 서버가 판정")
def list_comments(meeting_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    m, membership = _meeting(db, user, meeting_id)
    rows = db.query(Comment).filter_by(meeting_id=m.id).order_by(Comment.created_at, Comment.id).all()
    return [comment_out(c, user, membership) for c in rows]


@router.delete("/comments/{comment_id}", status_code=204, summary="댓글 삭제 (쓴 사람 · owner)")
def delete_comment(comment_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = db.get(Comment, comment_id)
    if c is None:
        raise ApiError(404, "NOT_FOUND", "없는 댓글입니다")
    _, membership = _meeting(db, user, c.meeting_id)
    if not _can_delete(c, user, membership):
        raise ApiError(403, "FORBIDDEN", "쓴 사람과 owner 만 지울 수 있습니다")
    db.delete(c)
    db.commit()
    return Response(status_code=204)
