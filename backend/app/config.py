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

    # 开发期脚手架总开关，管三件事：假登录（code 直接映射 openid）、假支付、
    # 跳过内容安全检测。这三者必须同时开关——拆成多个开关只会上线时漏掉某一个。
    # 置 false 时启动会强校验真实凭据是否齐全（见 config_problems），缺什么直接报错。
    mock_mode: bool = True

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


# 关掉 mock 就必须有的真实凭据。缺任何一项，真实登录或真实支付都跑不起来，
# 与其等用户下单时报 503，不如启动就拒绝。
REAL_MODE_REQUIRED = (
    ("WECHAT_APPID", "wechat_appid"),
    ("WECHAT_SECRET", "wechat_secret"),
    ("WXPAY_MCHID", "wxpay_mchid"),
    ("WXPAY_CERT_SERIAL", "wxpay_cert_serial"),
    ("WXPAY_PRIVATE_KEY_PATH", "wxpay_private_key_path"),
    ("WXPAY_APIV3_KEY", "wxpay_apiv3_key"),
    ("WXPAY_NOTIFY_URL", "wxpay_notify_url"),
)


def config_problems(s: Settings) -> tuple[list[str], list[str]]:
    """配置体检，返回 (致命, 警告)。一次列全，避免改一个报一个。"""
    fatal: list[str] = []
    warn: list[str] = []

    if s.app_env == "prod" and s.database_url.startswith("sqlite"):
        fatal.append("APP_ENV=prod 但 DATABASE_URL 仍是 sqlite 默认值："
                     "数据存在容器内、重建即丢失，生产必须配 MySQL")

    if not s.mock_mode:
        miss = [env for env, field in REAL_MODE_REQUIRED if not str(getattr(s, field, "")).strip()]
        if miss:
            fatal.append("MOCK_MODE=false 走真实登录与真实支付，以下凭据未配置："
                         + "、".join(miss))

    if s.app_env == "prod":
        if s.mock_mode:
            warn.append("生产环境 MOCK_MODE=true：登录可伪造、支付是假的、"
                        "内容安全检测被跳过。提审前必须置 false")
        if s.jwt_secret.startswith("dev-secret"):
            warn.append("JWT_SECRET 仍是默认值，生产必须更换（openssl rand -hex 32）")
        if s.admin_password == "jetset-admin":
            warn.append("ADMIN_PASSWORD 仍是默认值，生产必须更换")
    return fatal, warn


settings = get_settings()

_fatal, _warn = config_problems(settings)
if _warn:
    import sys

    for _w in _warn:
        print(f"[config] 警告：{_w}", file=sys.stderr)
if _fatal:
    raise RuntimeError("配置检查未通过：\n  - " + "\n  - ".join(_fatal))
