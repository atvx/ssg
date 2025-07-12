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
    org_id: str = Field(..., description="组织ID", max_length=50)
    org_name: str = Field(..., description="组织名称", max_length=50)
    year: int = Field(..., description="年份", ge=2000, le=2100)
    month: int = Field(..., description="月份", ge=1, le=12)
    target_income: float = Field(..., description="目标收入")
    car_count: Optional[int] = Field(None, description="车辆数量")
    actual_income: Optional[float] = Field(None, description="实际收入")
    ach_rate: Optional[float] = Field(None, description="达成率")
    sold_car_count: Optional[int] = Field(None, description="销售车辆数量") 
    per_car_income: Optional[float] = Field(None, description="车均收入")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MonthlySalesTargetCreate(BaseModel):
    """创建月度销售目标请求模型"""
    org_id: str = Field(..., description="组织ID", max_length=64)
    org_name: str = Field(..., description="组织名称", max_length=64)
    year: int = Field(..., description="年份", ge=2000, le=2100)
    month: int = Field(..., description="月份", ge=1, le=12)
    target_income: float = Field(..., description="目标收入", ge=0)
    car_count: Optional[int] = Field(None, description="车辆数量")


class MonthlySalesTargetUpdate(BaseModel):
    """更新月度销售目标请求模型"""
    org_id: Optional[str] = Field(None, description="组织ID", max_length=64)
    year: Optional[int] = Field(None, description="年份", ge=2000, le=2100)
    month: Optional[int] = Field(None, description="月份", ge=1, le=12)
    target_income: Optional[float] = Field(None, description="目标收入", ge=0)
    car_count: Optional[int] = Field(None, description="车辆数量")
    actual_income: Optional[float] = Field(None, description="实际收入", ge=0)
    ach_rate: Optional[float] = Field(None, description="达成率", ge=0)
    sold_car_count: Optional[int] = Field(None, description="销售车辆数量")
    per_car_income: Optional[float] = Field(None, description="车均收入", ge=0)


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


class WeeklyStatsWarehouse(BaseModel):
    """仓库周度统计数据模型"""
    name: str = Field(..., description="仓库名称")
    car_count: Optional[int] = Field(None, description="车辆数量")
    target_income: Optional[int] = Field(None, description="月度目标收入")
    this_week_sales: float = Field(..., description="本周销售额")
    last_week_sales: float = Field(..., description="上周销售额")
    sales_wow_pct: float = Field(..., description="销售额环比增长率(%)")
    this_week_avg: float = Field(..., description="本周平均收入")
    last_week_avg: float = Field(..., description="上周平均收入")
    avg_wow_pct: float = Field(..., description="平均收入环比增长率(%)")
    this_week_cart: int = Field(..., description="本周销售车数")
    last_week_cart: int = Field(..., description="上周销售车数")
    cart_wow_pct: float = Field(..., description="销售车数环比增长率(%)")
    this_daily_cart: int = Field(..., description="本周日均销售车数")
    last_daily_cart: int = Field(..., description="上周日均销售车数")
    daily_cart_wow_pct: float = Field(..., description="日均销售车数环比增长率(%)")


class WeekDateRange(BaseModel):
    """周度日期范围模型"""
    start: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    label: str = Field(..., description="日期范围标签")


class WeeklyStatsData(BaseModel):
    """周度统计数据模型"""
    query_date: str = Field(..., description="查询日期 (YYYY-MM-DD)")
    date_ranges: Dict[str, WeekDateRange] = Field(..., description="日期范围信息")
    warehouses: List[WeeklyStatsWarehouse] = Field(..., description="仓库周度统计数据列表")


class WeeklyStatsResponse(BaseModel):
    """周度统计响应模型"""
    code: int = 200
    success: bool = True
    message: str = "获取周度统计数据成功"
    data: Optional[List[WeeklyStatsWarehouse]] = None


class MonthlyStatsWarehouse(BaseModel):
    """仓库月度统计数据模型"""
    id: int = Field(..., description="仓库ID")
    name: str = Field(..., description="仓库名称")
    status: int = Field(..., description="仓库状态（0=停用，1=正常）")
    car_count: int = Field(..., description="车辆数量")
    target_income: float = Field(..., description="月度目标收入")
    actual_income: float = Field(..., description="月度实际收入")
    ach_rate: float = Field(..., description="达成率(%)")
    per_car_income: float = Field(..., description="车均收入")
    sold_car_count: int = Field(..., description="销售车数")


class MonthRange(BaseModel):
    """月度日期范围模型"""
    start: str = Field(..., description="月度开始日期 (YYYY-MM-DD)")
    end: str = Field(..., description="月度结束日期 (YYYY-MM-DD)")
    year: int = Field(..., description="年份")
    month: int = Field(..., description="月份")
    label: str = Field(..., description="月度范围标签")


class MonthlyStatsData(BaseModel):
    """月度统计数据模型"""
    query_date: str = Field(..., description="查询日期 (YYYY-MM-DD)")
    month_range: MonthRange = Field(..., description="月度范围信息")
    warehouses: List[MonthlyStatsWarehouse] = Field(..., description="仓库月度统计数据列表")


class MonthlyStatsResponse(BaseModel):
    """月度统计响应模型"""
    code: int = 200
    success: bool = True
    message: str = "获取月度统计数据成功"
    data: Optional[MonthlyStatsData] = None


class SalesRecordStatsItem(BaseModel):
    """销售记录统计项目模型"""
    id: int = Field(..., description="仓库ID")
    name: str = Field(..., description="仓库名称")
    status: int = Field(..., description="仓库状态（0=停用，1=正常）")
    date: Optional[str] = Field(None, description="销售日期 (YYYY-MM-DD)")
    sales_amount: float = Field(..., description="销售金额")


class SalesRecordsDateRange(BaseModel):
    """销售记录日期范围模型"""
    start: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    year: int = Field(..., description="年份")
    month: int = Field(..., description="月份")
    label: str = Field(..., description="日期范围标签")


class SalesRecordsSummary(BaseModel):
    """销售记录汇总信息模型"""
    total_records: int = Field(..., description="总记录数")
    total_amount: float = Field(..., description="总销售金额")
    warehouses_count: int = Field(..., description="涉及仓库数量")


class SalesRecordsStatsData(BaseModel):
    """销售记录统计数据模型"""
    query_date: str = Field(..., description="查询日期 (YYYY-MM-DD)")
    date_range: SalesRecordsDateRange = Field(..., description="日期范围信息")
    records: List[SalesRecordStatsItem] = Field(..., description="销售记录列表")
    summary: SalesRecordsSummary = Field(..., description="汇总信息")


class SalesRecordsStatsResponse(BaseModel):
    """销售记录统计响应模型"""
    code: int = 200
    success: bool = True
    message: str = "获取销售记录统计数据成功"
    data: Optional[SalesRecordsStatsData] = None
