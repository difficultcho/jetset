from fastapi import APIRouter, HTTPException

from app.deps import DB
from app.models.cms import Page
from app.schemas.admin import PageIn
from app.schemas.common import Resp
from app.services.pages import PAGE_KEYS, validate_blocks

router = APIRouter()


def _row(p: Page | None, key: str) -> dict:
    if p is None:
        return {"key": key, "blocks": [], "status": 1}
    return {"key": p.key, "blocks": p.blocks or [], "status": p.status}


@router.get("/pages/{key}", response_model=Resp[dict])
async def get_page(key: str, session: DB):
    if key not in PAGE_KEYS:
        raise HTTPException(status_code=404, detail="页面不存在")
    return Resp(data=_row(await session.get(Page, key), key))


@router.put("/pages/{key}", response_model=Resp[dict])
async def save_page(key: str, req: PageIn, session: DB):
    if key not in PAGE_KEYS:
        raise HTTPException(status_code=404, detail="页面不存在")
    validate_blocks(req.blocks)
    p = await session.get(Page, key)
    if p is None:
        p = Page(key=key)
        session.add(p)
    p.blocks = req.blocks
    p.status = req.status
    await session.commit()
    return Resp(data=_row(p, key))
