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
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    class Config:
        from_attributes = True


class SalesRecordQuery(BaseModel):
    """销售记录查询模型"""
    start_date: Optional[date_type] = Field(None, description="开始日期")
    end_date: Optional[date_type] = Field(None, description="结束日期")
    platform: Optional[str] = Field(None, description="平台")
    name: Optional[str] = Field(None, description="仓库名称")
    show_empty_poi: bool = Field(False, description="是否展示无数据门店")
    skip: int = Field(0, description="跳过记录数")
    limit: int = Field(100, description="返回记录数")


class PageInfo(BaseModel):
    """分页信息模型"""
    pageNo: int = Field(..., description="当前页码")
    pageSize: int = Field(..., description="每页大小")
    totalCount: int = Field(..., description="总记录数")
    totalPageSize: int = Field(..., description="总页数")


class SalesRecordSummary(BaseModel):
    """销售记录汇总信息模型"""
    income_amt: str = Field(..., description="总收入金额")
    sales_cart_count: str = Field(..., description="总销售车辆数")
    avg_income_amt: str = Field(..., description="平均收入金额")


class SalesRecordListData(BaseModel):
    """销售记录列表数据模型"""
    items: List[SalesRecordResponse] = Field([], description="销售记录列表")
    pageInfo: PageInfo = Field(..., description="分页信息")
    summary: SalesRecordSummary = Field(..., description="汇总信息")


class SalesRecordListResponse(BaseModel):
    """销售记录列表响应模型"""
    code: int = 200
    success: bool = True
    message: str = "获取销售记录列表成功"
    data: SalesRecordListData = Field(..., description="响应数据")


class SalesRecordDetailResponse(BaseModel):
    """销售记录详情响应模型"""
    code: int = 200
    success: bool = True
    message: str = "获取销售记录详情成功"
    data: Optional[SalesRecordResponse] = None 