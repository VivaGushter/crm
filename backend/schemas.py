from typing import Optional

from pydantic import BaseModel, Field


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


class UserCreate(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=4, max_length=256)
    role: str = "user"


class UserUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    password: Optional[str] = Field(default=None, min_length=4, max_length=256)
    role: Optional[str] = None
