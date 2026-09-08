from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# === User schemas ===

class UserBase(BaseModel):
    username: str
    role: str = "user"

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None

class User(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# === Permission schemas ===

class PermissionCreate(BaseModel):
    user_id: int
    permission: str

class Permission(PermissionCreate):
    id: int
    granted_at: datetime
    
    class Config:
        from_attributes = True

# === Price category schemas ===

class PriceCategoryBase(BaseModel):
    name: str
    sort_order: int = 0
    is_active: bool = True

class PriceCategoryCreate(PriceCategoryBase):
    pass

class PriceCategory(PriceCategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# === Price item schemas ===

class PriceItemBase(BaseModel):
    category_id: int
    name: str
    price: str
    unit: str = "шт"
    is_active: bool = True
    sort_order: int = 0

class PriceItemCreate(PriceItemBase):
    pass

class PriceItem(PriceItemBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# === Request schemas ===

class RequestBase(BaseModel):
    client_name: str
    phone: str
    visit_date: Optional[str] = None
    address: Optional[str] = None
    status: str = "new"
    price: Optional[float] = None
    notes: Optional[str] = None

class RequestCreate(RequestBase):
    # v2.1 Calculator fields
    work_amount: float = 0
    discount_type: str = "none"  # "none", "percent", "rubles"
    discount_value: float = 0
    discount_amount: float = 0
    materials_amount: float = 0
    calculation_items: List["CalculationItemCreate"] = []

class RequestUpdate(BaseModel):
    client_name: Optional[str] = None
    phone: Optional[str] = None
    visit_date: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None
    price: Optional[float] = None
    notes: Optional[str] = None
    # v2.1 Calculator fields
    work_amount: Optional[float] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    discount_amount: Optional[float] = None
    materials_amount: Optional[float] = None
    calculation_items: Optional[List["CalculationItemCreate"]] = None

class Request(RequestBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# === Calculation item schemas ===

class CalculationItemBase(BaseModel):
    price_item_id: Optional[int] = None
    category_name_snapshot: str = ""
    name_snapshot: str
    unit_snapshot: str = "шт"
    unit_price: float = 0
    quantity: float = 1
    line_total: float = 0
    sort_order: int = 0

class CalculationItemCreate(CalculationItemBase):
    pass

class CalculationItem(CalculationItemBase):
    id: int
    request_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# === Audit log schemas ===

class AuditLogBase(BaseModel):
    user_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    details: Optional[str] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLog(AuditLogBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
