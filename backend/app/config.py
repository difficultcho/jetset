from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
