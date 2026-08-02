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
    """读取侧统一兜底。

    两个来源都可能给出 None：固定页未落库时是内存壳（SQLAlchemy 的列默认值
    要到 flush 才生效，此时字段全是 None），以及历史数据里的 NULL。
    直接透传 None 会被管理端原样回传，撞 PageIn 的类型约束报 422。
    """
    return {
        "key": p.key,
        "title": p.title or FIXED_TITLES.get(p.key, ""),
        "sort": p.sort or 0,
        "status": 1 if p.status is None else p.status,
        "fixed": p.key in FIXED_PAGES,
    }


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
    p = Page(key=key, title=req.title, blocks=req.blocks,
             sort=req.sort, status=req.status)
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
