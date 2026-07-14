import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile

from app.config import settings
from app.deps import require_any_identity
from app.errors import BizError
from app.schemas.common import Resp

router = APIRouter()

MAX_IMAGE = 5 * 1024 * 1024
MAX_VIDEO = 50 * 1024 * 1024  # 注意：nginx client_max_body_size 需 ≥ 60m
IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
VIDEO_TYPES = {"video/mp4": ".mp4"}


@router.post("/uploads", response_model=Resp[dict], dependencies=[Depends(require_any_identity)])
async def upload(file: UploadFile):
    """图片/视频上传。MVP 存本地磁盘由应用直接伺服；接 COS 后改为直传签名。"""
    mime = file.content_type or ""
    ext = IMAGE_TYPES.get(mime) or VIDEO_TYPES.get(mime)
    if ext is None:
        raise BizError("仅支持 jpg/png/webp 图片或 mp4 视频")
    content = await file.read()
    if mime in IMAGE_TYPES and len(content) > MAX_IMAGE:
        raise BizError("图片不能超过 5MB")
    if mime in VIDEO_TYPES and len(content) > MAX_VIDEO:
        raise BizError("视频不能超过 50MB")
    name = f"{uuid.uuid4().hex}{ext}"
    dest = Path(settings.upload_dir)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / name).write_bytes(content)
    return Resp(data={"url": f"/uploads/{name}"})
