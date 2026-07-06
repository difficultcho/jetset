from fastapi import APIRouter

from app.deps import DB, CurrentUser
from app.schemas.common import Resp
from app.services import points as svc

router = APIRouter()


@router.get("/me/points/logs", response_model=Resp[list[dict]])
async def my_points_logs(user: CurrentUser, session: DB):
    rows = await svc.list_logs(session, user.id)
    return Resp(data=[
        {
            "id": r.id,
            "change": r.change,
            "balance_after": r.balance_after,
            "reason": svc.REASON_LABELS.get(r.reason, r.reason),
            "remark": r.remark,
            "created_at": r.created_at,
        }
        for r in rows
    ])
