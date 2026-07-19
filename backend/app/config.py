from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # URL 类配置容错：自动补 https:// 前缀、去掉尾斜杠（漏写协议头已翻车两次）
    @field_validator("s3_endpoint", "asset_base_url", check_fields=False)
    @classmethod
    def _normalize_url(cls, v: str) -> str:
        v = (v or "").strip().rstrip("/")
        if v and not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v

    app_env: str = "dev"  # dev | test | prod
    # 反代路径前缀（如 nginx 挂在 /jetset/ 下则设为 /jetset），影响 /docs 等自引用 URL
    root_path: str = ""

    database_url: str = "sqlite+aiosqlite:///./jetset.db"
    redis_url: str = "redis://127.0.0.1:6379/0"
    auto_create_tables: bool = True

    jwt_secret: str = "dev-secret-0123456789abcdef0123456789abcdef"
    jwt_expire_days: int = 30

    wechat_appid: str = ""
    wechat_secret: str = ""
    wechat_mock: bool = True

    payment_provider: str = "mock"  # mock | wechat
    wxpay_mchid: str = ""
    wxpay_cert_serial: str = ""
    wxpay_private_key_path: str = ""
    wxpay_apiv3_key: str = ""
    wxpay_notify_url: str = ""

    order_timeout_minutes: int = 30
    freight_cents: int = 0

    # 积分规则：实付每元返 points_per_yuan 分；points_deduct_rate 积分抵 1 元
    points_per_yuan: int = 1
    points_deduct_rate: int = 100

    upload_dir: str = "./uploads"

    # S3 兼容对象存储（百度 BOS / 腾讯 COS / 阿里 OSS 通用；配齐后上传自动切对象存储，
    # 否则回退本地磁盘，开发/测试零依赖）。百度 BOS 北京区 endpoint: https://s3.bj.bcebos.com
    s3_endpoint: str = ""
    s3_region: str = ""         # 如 bj
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = ""
    # 素材公网域名（CDN 加速域名，如 https://cdn.kkmsee.com）。
    # 配置后：本地不存在的 /uploads/x 由 API 302 跳转到该域名（迁移过渡期的兜底）
    asset_base_url: str = ""

    # 管理后台初始账号（seed 时创建；生产务必改密码）
    admin_username: str = "admin"
    admin_password: str = "jetset-admin"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# 生产环境防线：关键配置缺失必须在启动时报错，而不是静默用默认值拖到运行期
if settings.app_env == "prod":
    import sys

    if settings.database_url.startswith("sqlite"):
        raise RuntimeError(
            "APP_ENV=prod 但 DATABASE_URL 未配置（当前为 sqlite 默认值）。"
            "sqlite 数据存在容器内、重建即丢失，生产必须配置 MySQL。"
        )
    if settings.wechat_mock:
        print("[config] 警告：生产环境 WECHAT_MOCK=true，任何人可伪造登录", file=sys.stderr)
    if settings.jwt_secret.startswith("dev-secret") or settings.admin_password == "jetset-admin":
        print("[config] 警告：JWT_SECRET/ADMIN_PASSWORD 仍为默认值，生产必须更换", file=sys.stderr)
