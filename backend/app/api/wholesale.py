from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB, CurrentUser
from app.models.wholesale import WholesaleApplication
from app.schemas.common import Resp
from app.schemas.wholesale import WholesaleIn, WholesaleOut

router = APIRouter()


@router.post("/wholesale/applications", response_model=Resp[WholesaleOut])
async def apply(req: WholesaleIn, user: CurrentUser, session: DB):
    app_row = WholesaleApplication(user_id=user.id, **req.model_dump())
    session.add(app_row)
    await session.commit()
    return Resp(data=WholesaleOut.model_validate(app_row))


@router.get("/wholesale/applications/mine", response_model=Resp[list[WholesaleOut]])
async def mine(user: CurrentUser, session: DB):
    rows = (
        await session.execute(
            select(WholesaleApplication)
            .where(WholesaleApplication.user_id == user.id)
            .order_by(WholesaleApplication.id.desc())
        )
    ).scalars().all()
    return Resp(data=[WholesaleOut.model_validate(r) for r in rows])
