from pydantic import BaseModel, Field, validator
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
    date: Optional[str] = Field(None, description="查询日期（格式 YYYY-MM-DD），为空时默认当天")
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


class MonthlySalesTarget(BaseModel):
    """月度销售目标模型"""
    id: Optional[int] = None
    org_id: str = Field(..., description="组织ID", max_length=64)
    year: int = Field(..., description="年份", ge=2000, le=2100)
    month: int = Field(..., description="月份", ge=1, le=12)
    target_income: float = Field(..., description="目标收入")
    sort: Optional[int] = Field(0, description="排序")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MonthlySalesTargetCreate(BaseModel):
    """创建月度销售目标请求模型"""
    org_id: str = Field(..., description="组织ID", max_length=64)
    year: int = Field(..., description="年份", ge=2000, le=2100)
    month: int = Field(..., description="月份", ge=1, le=12)
    target_income: float = Field(..., description="目标收入", ge=0)
    sort: Optional[int] = Field(0, description="排序")


class MonthlySalesTargetUpdate(BaseModel):
    """更新月度销售目标请求模型"""
    org_id: Optional[str] = Field(None, description="组织ID", max_length=64)
    year: Optional[int] = Field(None, description="年份", ge=2000, le=2100)
    month: Optional[int] = Field(None, description="月份", ge=1, le=12)
    target_income: Optional[float] = Field(None, description="目标收入", ge=0)
    sort: Optional[int] = Field(None, description="排序")


class MonthlySalesTargetResponse(BaseModel):
    """月度销售目标响应模型"""
    code: int = 200
    success: bool = True
    message: str = "操作成功"
    data: Optional[MonthlySalesTarget] = None


class MonthlySalesTargetListResponse(BaseModel):
    """月度销售目标列表响应模型"""
    code: int = 200
    success: bool = True
    message: str = "获取目标列表成功"
    data: Optional[List[MonthlySalesTarget]] = None
