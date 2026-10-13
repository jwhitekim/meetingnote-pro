"""활동 기록 - kind 다섯 가지만. 문장은 남길 때 완성해 굳힌다."""
from sqlalchemy.orm import Session

from .models import Activity, User, iso

TEMPLATES = {
    "meeting_add": "{actor}님이 회의록 「{title}」을 올렸습니다",
    "todo_assign": "{actor}님이 「{what}」을 {assignee}님에게 배정했습니다",
    "todo_done": "{actor}님이 「{what}」을 완료했습니다",
    "comment_add": "{actor}님이 「{title}」에 댓글을 남겼습니다",
    "member_join": "{actor}님이 팀에 합류했습니다",
}
LIMIT = 50


def record(db: Session, team_id: int, actor: User, kind: str, **values) -> Activity:
    if kind not in TEMPLATES:
        raise ValueError(f"없는 활동 종류: {kind}")
    a = Activity(team_id=team_id, actor_id=actor.id, kind=kind,
                 target=TEMPLATES[kind].format(actor=actor.name, **values))
    db.add(a)
    return a


def out(a: Activity) -> dict:
    return {"id": a.id, "kind": a.kind, "actor_name": a.actor.name, "text": a.target, "created_at": iso(a.created_at)}
