from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WholesaleIn(BaseModel):
    type: str = Field(min_length=1, max_length=32)
    phone: str = Field(min_length=5, max_length=20)
    company: str = Field(min_length=1, max_length=128)
    region: str = Field(default="", max_length=128)
    license_img: str = Field(min_length=1, max_length=512)
    store_img: str = Field(min_length=1, max_length=512)


class WholesaleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    phone: str
    company: str
    region: str
    status: str
    created_at: datetime
