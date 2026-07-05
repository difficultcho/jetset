from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Resp(BaseModel, Generic[T]):
    """统一响应包裹：code=0 成功，非 0 为业务错误码。"""

    code: int = 0
    message: str = "ok"
    data: T | None = None


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
