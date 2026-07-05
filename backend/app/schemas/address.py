from pydantic import BaseModel, ConfigDict, Field


class AddressIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    phone: str = Field(min_length=5, max_length=20)
    region: str = Field(default="", max_length=128)
    detail: str = Field(min_length=1, max_length=256)


class AddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    region: str
    detail: str
    is_default: bool
