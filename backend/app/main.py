from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
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
app.mount("/uploads", StaticFiles(directory=settings.upload_dir, check_dir=False), name="uploads")


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
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "参数错误", "data": exc.errors()},
    )


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
