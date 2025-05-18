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
    data: Token
