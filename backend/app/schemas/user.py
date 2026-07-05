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
    gender: str | None = Field(default=None, pattern="^(男|女|)$")
    birthday: str | None = Field(default=None, max_length=16)
    region: str | None = Field(default=None, max_length=128)
    reco_enabled: bool | None = None


class LoginReq(BaseModel):
    code: str = Field(min_length=1, max_length=128)


class LoginData(BaseModel):
    token: str
    user: UserOut
