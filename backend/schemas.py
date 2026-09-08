from typing import Optional

from pydantic import BaseModel, Field


class RequestItemIn(BaseModel):
    price_item_id: Optional[int] = None
    category_name: str = Field(default="", max_length=160)
    name: str = Field(min_length=1, max_length=200)
    unit: str = Field(default="шт", max_length=20)
    unit_price: float = Field(ge=0)
    quantity: float = Field(gt=0)


class RequestIn(BaseModel):
    client: str = Field(min_length=1, max_length=160)
    visit_date: str = Field(min_length=16, max_length=32)
    address: str = Field(min_length=1, max_length=500)
    phone: str = Field(min_length=1, max_length=80)
    status: str
    price: float = Field(default=0, ge=0)
    comment: Optional[str] = Field(default="", max_length=2000)
    assignee: str = Field(min_length=1)
    source: str = "unknown"
    contact_method: str = ""
    items: Optional[list[RequestItemIn]] = None


class UserCreate(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=4, max_length=256)
    role: str = "user"


class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    password: Optional[str] = Field(default=None, min_length=4, max_length=256)
    role: Optional[str] = None
