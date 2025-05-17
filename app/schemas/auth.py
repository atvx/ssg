from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None


class Login(BaseModel):
    username: str
    password: str


class PlatformAuth(BaseModel):
    platform: str
    status: str
    task_id: Optional[str] = None


class VerifyCode(BaseModel):
    task_id: str
    code: str
