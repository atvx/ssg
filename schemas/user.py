from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import re


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., example="张三", description="用户名")
    mobile: Optional[str] = Field(None, example="13800138000", description="手机号")
    is_active: bool = Field(False, description="是否激活")


class UserCreate(UserBase):
    """用户创建模型"""
    password: str = Field(..., example="password123", description="密码")
    is_superuser: bool = Field(False, description="是否为超级管理员")

    @validator('mobile')
    def validate_mobile(cls, v):
        if v is None:
            return v
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确，请输入11位中国大陆手机号")
        return v

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("密码长度不能少于6位")
        return v


class UserUpdate(BaseModel):
    """用户更新模型"""
    username: Optional[str] = Field(None, example="李四", description="用户名")
    mobile: Optional[str] = Field(None, example="13900139000", description="手机号")
    password: Optional[str] = Field(None, example="newpassword123", description="密码")
    is_active: Optional[bool] = Field(None, description="是否激活")
    is_superuser: Optional[bool] = Field(None, description="是否为超级管理员")

    @validator('mobile')
    def validate_mobile(cls, v):
        if v is None:
            return v
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确，请输入11位中国大陆手机号")
        return v

    @validator('password')
    def validate_password(cls, v):
        if v is None:
            return v
        if len(v) < 6:
            raise ValueError("密码长度不能少于6位")
        return v


class UserInDB(UserBase):
    id: int
    hashed_password: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class User(UserInDB):
    """数据库用户模型"""
    pass


class UserDisplay(BaseModel):
    """用户显示模型（API返回）"""
    id: int
    username: str
    mobile: Optional[str] = None
    is_active: bool
    is_superuser: bool

    class Config:
        orm_mode = True
