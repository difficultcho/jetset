"""配置体检：开发期脚手架总开关的护栏。

关键性质：MOCK_MODE=false 时缺任何真实凭据都必须在启动时报错，
而不是等用户下单才 503。
"""
from app.config import REAL_MODE_REQUIRED, Settings, config_problems


def _s(**kw):
    """绕过 .env 与环境变量，只用给定值 + 字段默认值构造配置。"""
    return Settings.model_construct(**kw)


def test_mock_mode_on_is_clean():
    fatal, warn = config_problems(_s(app_env="dev", mock_mode=True,
                                     database_url="mysql+aiomysql://x/y"))
    assert fatal == [] and warn == []


def test_real_mode_missing_credentials_is_fatal():
    fatal, _ = config_problems(_s(app_env="prod", mock_mode=False,
                                  database_url="mysql+aiomysql://x/y"))
    assert len(fatal) == 1
    # 一次列全，不是报一个改一个
    for env, _field in REAL_MODE_REQUIRED:
        assert env in fatal[0], f"{env} 未出现在报错里：{fatal[0]}"


def test_real_mode_with_all_credentials_passes():
    creds = {field: "x" for _env, field in REAL_MODE_REQUIRED}
    fatal, warn = config_problems(_s(app_env="prod", mock_mode=False,
                                     database_url="mysql+aiomysql://x/y",
                                     jwt_secret="a" * 40, admin_password="s3cret",
                                     **creds))
    assert fatal == [] and warn == []


def test_prod_with_sqlite_is_fatal():
    fatal, _ = config_problems(_s(app_env="prod", mock_mode=True,
                                  database_url="sqlite+aiosqlite:///./x.db"))
    assert any("sqlite" in f for f in fatal)


def test_prod_with_mock_mode_warns_loudly():
    _fatal, warn = config_problems(_s(app_env="prod", mock_mode=True,
                                      database_url="mysql+aiomysql://x/y",
                                      jwt_secret="a" * 40, admin_password="s3cret"))
    assert len(warn) == 1 and "提审前必须置 false" in warn[0]


def test_prod_default_secrets_warn():
    _fatal, warn = config_problems(_s(app_env="prod", mock_mode=True,
                                      database_url="mysql+aiomysql://x/y"))
    assert any("JWT_SECRET" in w for w in warn)
    assert any("ADMIN_PASSWORD" in w for w in warn)


def test_dev_never_fatal_even_with_defaults():
    """开发环境用默认值必须能直接起服务，否则本地开发门槛太高。"""
    fatal, _ = config_problems(_s())
    assert fatal == []
