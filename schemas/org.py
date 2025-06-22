from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal


class OrgBase(BaseModel):
    """机构基础模型"""
    id: str = Field(..., description="机构ID")
    name: Optional[str] = Field(None, description="机构名称")
    org_type: Optional[int] = Field(None, description="机构类型")
    parent_id: Optional[str] = Field(None, description="父级机构ID")
    parent_name: Optional[str] = Field(None, description="父级机构名称")
    sort: Optional[int] = Field(None, description="排序")
    status: Optional[int] = Field(1, description="状态（0禁用/1正常）")
    per_car_target: Optional[int] = Field(None, description="车均目标")
    cost_rate: Optional[Decimal] = Field(0, description="成本率")


class OrgCreate(BaseModel):
    """创建机构请求模型"""
    id: str = Field(..., description="机构ID")
    name: str = Field(..., description="机构名称")
    org_type: Optional[int] = Field(None, description="机构类型")
    parent_id: Optional[str] = Field(None, description="父级机构ID")
    sort: Optional[int] = Field(0, description="排序")
    status: Optional[int] = Field(1, description="状态（0禁用/1正常）")
    per_car_target: Optional[int] = Field(None, description="车均目标")
    cost_rate: Optional[Decimal] = Field(0, description="成本率")


class OrgUpdate(BaseModel):
    """更新机构请求模型"""
    name: Optional[str] = Field(None, description="机构名称")
    org_type: Optional[int] = Field(None, description="机构类型")
    parent_id: Optional[str] = Field(None, description="父级机构ID")
    sort: Optional[int] = Field(None, description="排序")
    status: Optional[int] = Field(None, description="状态（0禁用/1正常）")
    per_car_target: Optional[int] = Field(None, description="车均目标")
    cost_rate: Optional[Decimal] = Field(None, description="成本率")


class OrgDetail(OrgBase):
    """机构详情模型"""
    class Config:
        from_attributes = True


class OrgListItem(BaseModel):
    """机构列表项模型"""
    org_id: str = Field(..., description="机构ID")
    org_name: Optional[str] = Field(None, description="机构名称")
    org_type: Optional[int] = Field(None, description="机构类型")
    parent_id: Optional[str] = Field(None, description="父级机构ID")
    parent_name: Optional[str] = Field(None, description="父级机构名称")
    sort: Optional[int] = Field(None, description="排序")
    status: Optional[int] = Field(None, description="状态（0禁用/1正常）")
    per_car_target: Optional[int] = Field(None, description="车均目标")
    cost_rate: Optional[Decimal] = Field(None, description="成本率")
    
    class Config:
        from_attributes = True


class OrgResponse(BaseModel):
    """机构详情响应模型"""
    code: int = 200
    success: bool = True
    message: str = "获取机构详情成功"
    data: Optional[OrgDetail] = None


class OrgListResponse(BaseModel):
    """机构列表响应模型"""
    code: int = 200
    success: bool = True
    message: str = "获取机构列表成功"
    data: Optional[List[OrgListItem]] = None 