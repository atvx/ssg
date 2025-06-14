from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date


class DailyReportExportRequest(BaseModel):
    """日报导出请求模型"""
    date: Optional[str] = Field(None, description="查询日期（格式 YYYY-MM-DD），为空时默认为当前日期")
    formats: Optional[str] = Field("excel,pdf,png", description="导出格式，多个格式用逗号分隔，可选值：excel,pdf,png")


class WarehouseData(BaseModel):
    """仓库数据模型"""
    id: int = Field(description="仓库ID")
    name: str = Field(description="仓库名称")
    car_count: int = Field(description="车辆配置")
    daily_revenue: int = Field(description="当日销售")
    daily_avg_revenue_cart: int = Field(description="当日车均")
    daily_cart_count: int = Field(description="当日车次")
    target_income: int = Field(description="月目标")
    actual_income: int = Field(description="月累计")
    ach_rate: str = Field(description="累计达成率")
    per_car_income: int = Field(description="累计车均")
    sold_car_count: int = Field(description="累计车次")


class MarketSummary(BaseModel):
    """市场汇总数据模型"""
    car_count: int = Field(description="车辆配置总计")
    daily_revenue: int = Field(description="当日销售总计")
    daily_avg_revenue_cart: int = Field(description="当日车均")
    daily_cart_count: int = Field(description="当日车次总计")
    target_income: int = Field(description="月目标总计")
    actual_income: int = Field(description="月累计总计")
    ach_rate: str = Field(description="累计达成率")
    per_car_income: int = Field(description="累计车均")
    sold_car_count: int = Field(description="累计车次总计")


class MarketData(BaseModel):
    """市场数据模型"""
    id: int = Field(description="市场ID")
    name: str = Field(description="市场名称")
    warehouses: List[WarehouseData] = Field(description="仓库列表")
    summary: MarketSummary = Field(description="市场汇总数据")


class DailyReportData(BaseModel):
    """日报数据模型"""
    markets: List[MarketData] = Field(description="市场列表")
    total: MarketSummary = Field(description="总计数据")
    report_date: str = Field(description="报表日期")


class DailyReportExportResponse(BaseModel):
    """日报导出响应模型"""
    report_data: DailyReportData = Field(description="报表数据")
    files: Dict[str, str] = Field(description="生成的文件路径")
    export_formats: List[str] = Field(description="导出格式列表")
    query_date: str = Field(description="查询日期") 