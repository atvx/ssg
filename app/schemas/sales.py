from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal


class SalesRecordBase(BaseModel):
    date: date
    platform: str
    warehouse_name: str
    income_amt: Decimal
    sales_cart_count: int
    avg_income_amt: Decimal


class SalesRecordCreate(SalesRecordBase):
    pass


class SalesRecord(SalesRecordBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SalesQuery(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    platform: Optional[str] = None
    warehouse_name: Optional[str] = None


class FetchDataRequest(BaseModel):
    date: Optional[date] = None
    platforms: Optional[List[str]] = None  # ["meituan", "duowei"] 或仅其中一个


class WarehouseInfo(BaseModel):
    name: str
    platform: str
