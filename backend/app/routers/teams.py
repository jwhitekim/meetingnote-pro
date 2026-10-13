import secrets
import string

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import activity
from ..db import get_db
from ..errors import ApiError
from ..models import Meeting, Membership, Team, Todo, User
from ..security import current_user, membership_of, require_member, require_owner

router = APIRouter(prefix="/api/teams", tags=["Team"])

TEAM_LIMIT = 6  # ACME Constraints
CODE_CHARS = string.ascii_uppercase + string.digits


class TeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["기획팀"])


class JoinIn(BaseModel):
    invite_code: str = Field(min_length=1, examples=["MN-7K2D"])


def new_code(db: Session) -> str:
    while True:
        code = "MN-" + "".join(secrets.choice(CODE_CHARS) for _ in range(4))
        if not db.query(Team).filter_by(invite_code=code).first():
            return code


def member_count(db: Session, team_id: int) -> int:
    return db.query(Membership).filter_by(team_id=team_id).count()


def team_out(db: Session, t: Team, role: str) -> dict:
    return {"id": t.id, "name": t.name, "invite_code": t.invite_code, "role": role,
            "member_count": member_count(db, t.id)}


@router.post("", status_code=201, summary="팀 생성 - 만든 사람이 owner")
def create_team(body: TeamIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if membership_of(db, user):
        raise ApiError(400, "VALIDATION_ERROR", "이미 팀에 속해 있습니다")
    t = Team(name=body.name.strip(), invite_code=new_code(db), owner_id=user.id)
    db.add(t)
    db.flush()
    db.add(Membership(team_id=t.id, user_id=user.id, role="owner"))
    db.commit()
    return team_out(db, t, "owner")


@router.get("", summary="내 팀 목록 (0~1건)")
def my_teams(user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = membership_of(db, user)
    return [team_out(db, db.get(Team, m.team_id), m.role)] if m else []


@router.post("/join", summary="초대코드로 합류")
def join(body: JoinIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.query(Team).filter_by(invite_code=body.invite_code.strip().upper()).first()
    if t is None:
        raise ApiError(404, "INVITE_NOT_FOUND", "초대코드를 찾을 수 없습니다")
    if membership_of(db, user):
        raise ApiError(400, "VALIDATION_ERROR", "이미 팀에 속해 있습니다")
    if member_count(db, t.id) >= TEAM_LIMIT:
        raise ApiError(409, "TEAM_FULL", "팀 정원(6명)이 찼습니다")
    db.add(Membership(team_id=t.id, user_id=user.id, role="member"))
    activity.record(db, t.id, user, "member_join")
    db.commit()
    return team_out(db, t, "member")


@router.get("/{team_id}/members", summary="멤버 목록 (1인당 할 일 수 포함)")
def members(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    counts = dict(
        db.query(Todo.assignee_id, func.count(Todo.id))
        .join(Meeting, Todo.meeting_id == Meeting.id)
        .filter(Meeting.team_id == team_id, Todo.assignee_id.isnot(None))
        .group_by(Todo.assignee_id)
        .all()
    )
    rows = (db.query(Membership).filter_by(team_id=team_id)
            .order_by((Membership.role != "owner"), Membership.joined_at, Membership.id).all())
    return [{"id": m.user.id, "name": m.user.name, "email": m.user.email, "role": m.role,
             "todo_count": counts.get(m.user.id, 0)} for m in rows]


@router.put("/{team_id}/code", summary="초대코드 재발급 (owner) - 앞의 코드는 폐기")
def reissue_code(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_owner(db, user, team_id)
    t = db.get(Team, team_id)
    t.invite_code = new_code(db)
    db.commit()
    return team_out(db, t, "owner")


@router.put("/{team_id}", summary="팀 이름 변경 (owner)")
def rename(team_id: int, body: TeamIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_owner(db, user, team_id)
    t = db.get(Team, team_id)
    t.name = body.name.strip()
    db.commit()
    return team_out(db, t, "owner")
