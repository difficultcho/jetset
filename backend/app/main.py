from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.api import api_router
from app.api.admin import admin_router
from app.config import settings
from app.db import create_all
from app.errors import BizError


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables:
        await create_all()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    # arq 连接池：用于下单时挂精确超时任务；不可用则靠 worker 定时扫描兜底
    app.state.arq = None
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    except Exception:
        pass

    yield

    if app.state.arq is not None:
        await app.state.arq.aclose()


app = FastAPI(title="JETSET Shop API", version="0.1.0", lifespan=lifespan,
              root_path=settings.root_path)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/admin")


# 显式路由伺服上传文件（不用 StaticFiles：其对 root_path 的处理与普通路由不一致，
# 在 nginx 剥前缀 + ROOT_PATH 组合下会 404）
@app.get("/uploads/{name}", include_in_schema=False)
async def serve_upload(name: str):
    if "/" in name or "\\" in name or name.startswith("."):
        raise HTTPException(status_code=404, detail="Not Found")
    path = Path(settings.upload_dir) / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(path)


@app.exception_handler(BizError)
async def biz_error_handler(request: Request, exc: BizError):
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "message": exc.message, "data": None},
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(exc.detail), "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # 只保留可 JSON 序列化的字段（ctx 里可能带异常对象）
    errors = [
        {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "参数错误", "data": errors},
    )


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
