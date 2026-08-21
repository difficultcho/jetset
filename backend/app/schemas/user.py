from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatar: str
    phone: str | None
    gender: str
    birthday: str
    region: str
    points: int
    reco_enabled: bool


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    avatar: str | None = Field(default=None, max_length=512)
    # 小程序展示用「男士/女士」，历史数据里还有「男/女」，两种都收。
    # 这个值不参与任何逻辑，只是展示标签。
    gender: str | None = Field(default=None, pattern="^(男士|女士|男|女|)$")
    birthday: str | None = Field(default=None, max_length=16)
    region: str | None = Field(default=None, max_length=128)
    # 联系方式，不是身份——身份始终是 openid。允许留空，不做真实性校验。
    phone: str | None = Field(default=None, max_length=20)
    reco_enabled: bool | None = None


class LoginReq(BaseModel):
    code: str = Field(min_length=1, max_length=128)


class LoginData(BaseModel):
    token: str
    user: UserOut
    new_coupons: int = 0  # 注册时发放的新客券数量（老用户恒为 0）
