import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.deps import require_any_identity
from app.errors import BizError
from app.schemas.common import Resp

router = APIRouter()

MAX_IMAGE = 5 * 1024 * 1024
MAX_VIDEO = 50 * 1024 * 1024  # 注意：nginx client_max_body_size 需 ≥ 60m
IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
VIDEO_TYPES = {"video/mp4": ".mp4"}

# 素材一经上传不再变更（文件名为 UUID），CDN/浏览器可放心长缓存
CACHE_CONTROL = "public, max-age=31536000, immutable"


def s3_enabled() -> bool:
    return bool(settings.s3_endpoint and settings.s3_bucket
                and settings.s3_access_key and settings.s3_secret_key)


@lru_cache
def s3_client():
    import boto3  # 惰性导入：未启用对象存储的环境（本地/测试）不依赖 boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        region_name=settings.s3_region or None,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
    )


def _put_s3(name: str, content: bytes, mime: str) -> None:
    """boto3 是同步 SDK，放线程池跑避免阻塞事件循环。对象键与 URL 路径一致：uploads/<name>。"""
    s3_client().put_object(
        Bucket=settings.s3_bucket, Key=f"uploads/{name}", Body=content,
        ContentType=mime, CacheControl=CACHE_CONTROL,
    )


@router.post("/uploads", response_model=Resp[dict], dependencies=[Depends(require_any_identity)])
async def upload(file: UploadFile):
    """图片/视频上传：配置了 S3_*（如百度 BOS）则写对象存储（CDN 分发），
    否则存本地磁盘由应用伺服。两种后端返回的都是相对路径 /uploads/x，素材域名由前端拼接。"""
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
    if s3_enabled():
        await run_in_threadpool(_put_s3, name, content, mime)
    else:
        dest = Path(settings.upload_dir)
        dest.mkdir(parents=True, exist_ok=True)
        (dest / name).write_bytes(content)
    return Resp(data={"url": f"/uploads/{name}"})
