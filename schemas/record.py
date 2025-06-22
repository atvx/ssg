from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date as date_type, datetime
from decimal import Decimal


class SalesRecordBase(BaseModel):
    """销售记录基础模型"""
    date: date_type = Field(..., description="销售日期")
    platform: str = Field(..., description="平台")
    warehouse_name: str = Field(..., description="仓库名称")
    income_amt: Decimal = Field(..., description="营业收入")
    sales_cart_count: int = Field(..., description="销售车辆")
    avg_income_amt: Decimal = Field(..., description="平均车营业额")


class SalesRecordCreate(SalesRecordBase):
    """销售记录创建模型"""
    pass


class SalesRecordUpdate(BaseModel):
    """销售记录更新模型"""
    date: Optional[date_type] = Field(None, description="销售日期")
    platform: Optional[str] = Field(None, description="平台")
    warehouse_name: Optional[str] = Field(None, description="仓库名称")
    income_amt: Optional[Decimal] = Field(None, description="营业收入")
    sales_cart_count: Optional[int] = Field(None, description="销售车辆")
    avg_income_amt: Optional[Decimal] = Field(None, description="平均车营业额")


class SalesRecordResponse(SalesRecordBase):
    """销售记录响应模型"""
    id: int = Field(..., description="记录编号")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    
    class Config:
        from_attributes = True


class SalesRecordQuery(BaseModel):
    """销售记录查询模型"""
    start_date: Optional[date_type] = Field(None, description="开始日期")
    end_date: Optional[date_type] = Field(None, description="结束日期")
    platform: Optional[str] = Field(None, description="平台")
    warehouse_name: Optional[str] = Field(None, description="仓库名称")
    skip: int = Field(0, description="跳过记录数")
    limit: int = Field(100, description="返回记录数")


class SalesRecordListResponse(BaseModel):
    """销售记录列表响应模型"""
    code: int = 200
    success: bool = True
    message: str = "获取销售记录列表成功"
    data: List[SalesRecordResponse] = []
    total: int = Field(0, description="总记录数")


class SalesRecordDetailResponse(BaseModel):
    """销售记录详情响应模型"""
    code: int = 200
    success: bool = True
    message: str = "获取销售记录详情成功"
    data: Optional[SalesRecordResponse] = None 