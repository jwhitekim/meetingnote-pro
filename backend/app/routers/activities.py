from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import activity
from ..db import get_db
from ..models import Activity, User
from ..security import current_user, membership_of, require_member

router = APIRouter(prefix="/api", tags=["Activity"])


def _recent(q) -> list[dict]:
    return [activity.out(a) for a in q.order_by(Activity.created_at.desc(), Activity.id.desc()).limit(activity.LIMIT)]


@router.get("/teams/{team_id}/activities", summary="팀 활동 - 최근 50건")
def team_activities(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    return _recent(db.query(Activity).filter_by(team_id=team_id))


@router.get("/me/activities", summary="내 활동 - 최근 50건")
def my_activities(user: User = Depends(current_user), db: Session = Depends(get_db)):
    m = membership_of(db, user)
    if m is None:
        return []
    return _recent(db.query(Activity).filter_by(team_id=m.team_id, actor_id=user.id))
