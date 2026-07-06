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

    upload_dir: str = "./uploads"

    # 管理后台初始账号（seed 时创建；生产务必改密码）
    admin_username: str = "admin"
    admin_password: str = "jetset-admin"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
