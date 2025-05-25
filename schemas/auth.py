from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class Token(BaseModel):
    """令牌模型"""
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field("bearer", description="令牌类型")


class Login(BaseModel):
    """登录请求模型"""
    username: str = Field(..., example="zhang_san", description="用户名")
    password: str = Field(..., example="password123", description="密码")


class TokenData(BaseModel):
    """令牌数据模型"""
    username: Optional[str] = None
    user_id: Optional[int] = None


class LoginResponse(BaseModel):
    """登录响应模型（用于文档生成，实际使用APIResponse）"""
    code: int = 200
    success: bool = True
    message: str = "登录成功"
    data: Optional[Token] = None


class RegisterResponse(BaseModel):
    """注册响应模型（用于文档生成，实际使用APIResponse）"""
    code: int = 201
    success: bool = True
    message: str = "用户注册成功"
    data: Optional[Dict[str, Any]] = None


class UserInfo(BaseModel):
    """用户信息模型"""
    id: int
    username: str
    mobile: str
    is_active: bool
    is_superuser: bool


class UserInfoResponse(BaseModel):
    """用户信息响应模型（用于文档生成，实际使用APIResponse）"""
    code: int = 200
    success: bool = True
    message: str = "获取用户信息成功"
    data: Optional[UserInfo] = None


class UserUpdateInfo(BaseModel):
    """更新后的用户信息"""
    id: int
    username: str
    mobile: str


class UpdateUserResponse(BaseModel):
    """更新用户信息响应模型（用于文档生成，实际使用APIResponse）"""
    code: int = 200
    success: bool = True
    message: str = "用户信息更新成功"
    data: Optional[UserUpdateInfo] = None


class PasswordChangeRequest(BaseModel):
    """修改密码请求模型"""
    old_password: str = Field(..., example="old_password123", description="原密码")
    new_password: str = Field(..., example="new_password456", description="新密码")


class ChangePasswordResponse(BaseModel):
    """修改密码响应模型（用于文档生成，实际使用APIResponse）"""
    code: int = 200
    success: bool = True
    message: str = "密码修改成功"
    data: Optional[Dict[str, Any]] = None
