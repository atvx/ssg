from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
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


class SalesRecord(BaseModel):
    """销售记录模型"""
    id: int
    date: date
    platform: str
    warehouse_name: str
    total_amount: float
    order_count: int
    
    class Config:
        from_attributes = True


class SalesQuery(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    platform: Optional[str] = None
    warehouse_name: Optional[str] = None


class FetchDataRequest(BaseModel):
    """获取数据请求模型"""
    start_date: Optional[str] = Field(None, description="开始日期（格式 YYYY-MM-DD），为空时默认当天")
    end_date: Optional[str] = Field(None, description="结束日期（格式 YYYY-MM-DD），为空时默认当天")
    platform: Optional[str] = Field(None, description="平台筛选")


class WarehouseInfo(BaseModel):
    """仓库信息模型"""
    name: str = Field(..., description="仓库名称")
    sales: float = Field(..., description="销售额")
    orders: int = Field(..., description="订单数")


class DailyData(BaseModel):
    """每日数据模型"""
    date: str = Field(..., description="日期（ISO格式 YYYY-MM-DD）")
    sales: float = Field(..., description="销售额")
    orders: int = Field(..., description="订单数")
    warehouses: List[WarehouseInfo] = Field([], description="仓库数据列表")


class PlatformData(BaseModel):
    """平台数据模型"""
    platform: str = Field(..., description="平台名称")
    total_sales: float = Field(..., description="总销售额")
    total_orders: int = Field(..., description="总订单数")
    days: List[DailyData] = Field([], description="每日数据列表")


class DailySalesData(BaseModel):
    """指定日期的销售数据模型"""
    platform: str = Field(..., description="平台名称")
    date: str = Field(..., description="日期（ISO格式 YYYY-MM-DD）")
    total_sales: float = Field(..., description="总销售额")
    total_orders: int = Field(..., description="总订单数")
    warehouses: List[WarehouseInfo] = Field([], description="仓库数据列表")
