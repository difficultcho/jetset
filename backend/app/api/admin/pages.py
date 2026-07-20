import secrets

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.deps import DB
from app.errors import BizError
from app.models.cms import Page
from app.schemas.admin import PageIn
from app.schemas.common import Resp
from app.services.pages import FIXED_PAGES, validate_blocks

router = APIRouter()

FIXED_TITLES = {"home": "首页", "brand": "关于品牌"}


def _meta(p: Page) -> dict:
    return {"key": p.key, "title": p.title, "cover": p.cover, "cover_tint": p.cover_tint,
            "sort": p.sort, "status": p.status, "fixed": p.key in FIXED_PAGES}


def _full(p: Page) -> dict:
    return {**_meta(p), "blocks": p.blocks or []}


@router.get("/pages", response_model=Resp[list[dict]])
async def list_pages(session: DB):
    rows = (await session.execute(select(Page).order_by(Page.sort, Page.key))).scalars().all()
    have = {p.key for p in rows}
    # 固定页（home/brand）即使未落库也在列表里占位，便于首次编辑
    stubs = [Page(key=k, title=FIXED_TITLES[k]) for k in FIXED_PAGES if k not in have]
    return Resp(data=[_meta(p) for p in [*stubs, *rows]])


@router.get("/pages/{key}", response_model=Resp[dict])
async def get_page(key: str, session: DB):
    p = await session.get(Page, key)
    if p is None:
        if key not in FIXED_PAGES:
            raise HTTPException(status_code=404, detail="页面不存在")
        p = Page(key=key, title=FIXED_TITLES.get(key, ""))  # 内存壳，尚未落库
    return Resp(data=_full(p))


@router.post("/pages", response_model=Resp[dict])
async def create_page(req: PageIn, session: DB):
    if not req.title.strip():
        raise BizError("请填写页面标题")
    validate_blocks(req.blocks)
    key = secrets.token_hex(4)
    while await session.get(Page, key) is not None:
        key = secrets.token_hex(4)
    p = Page(key=key, title=req.title, cover=req.cover, cover_tint=req.cover_tint,
             blocks=req.blocks, sort=req.sort, status=req.status)
    session.add(p)
    await session.commit()
    return Resp(data=_full(p))


@router.put("/pages/{key}", response_model=Resp[dict])
async def save_page(key: str, req: PageIn, session: DB):
    validate_blocks(req.blocks)
    p = await session.get(Page, key)
    if p is None:
        if key not in FIXED_PAGES:
            raise HTTPException(status_code=404, detail="页面不存在")
        p = Page(key=key)  # 固定页首次保存时落库
        session.add(p)
    p.title = req.title or FIXED_TITLES.get(key, "")
    p.cover = req.cover
    p.cover_tint = req.cover_tint
    p.blocks = req.blocks
    p.sort = req.sort
    p.status = req.status
    await session.commit()
    return Resp(data=_full(p))


@router.delete("/pages/{key}", response_model=Resp[None])
async def delete_page(key: str, session: DB):
    if key in FIXED_PAGES:
        raise BizError("固定挂载页不可删除")
    p = await session.get(Page, key)
    if p is None:
        raise HTTPException(status_code=404, detail="页面不存在")
    await session.delete(p)
    await session.commit()
    return Resp()
