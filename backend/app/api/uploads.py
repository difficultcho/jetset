import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile

from app.config import settings
from app.deps import CurrentUser
from app.errors import BizError
from app.schemas.common import Resp

router = APIRouter()

MAX_SIZE = 5 * 1024 * 1024
ALLOWED = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


@router.post("/uploads", response_model=Resp[dict])
async def upload(file: UploadFile, user: CurrentUser):
    """图片上传。MVP 存本地磁盘由应用直接伺服；接 COS 后改为直传签名。"""
    ext = ALLOWED.get(file.content_type or "")
    if ext is None:
        raise BizError("仅支持 jpg/png/webp 图片")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise BizError("图片不能超过 5MB")
    name = f"{uuid.uuid4().hex}{ext}"
    dest = Path(settings.upload_dir)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / name).write_bytes(content)
    return Resp(data={"url": f"/uploads/{name}"})
