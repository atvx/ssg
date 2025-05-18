from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from sqlalchemy import text

from db.crud import get_user_by_username, create_user, authenticate_user
from schemas.user import UserCreate
from schemas.auth import Token
from utils.security import create_access_token


def get_user_by_mobile(db: Session, mobile: str):
    """根据手机号获取用户"""
    if not mobile:
        return None
    try:
        # 使用原生SQL查询避免ORM问题
        result = db.execute(text("SELECT * FROM users WHERE mobile = :mobile"), {"mobile": mobile})
        user = result.fetchone()
        return user
    except Exception:
        return None


def register_user(db: Session, user: UserCreate):
    """注册新用户"""
    # 参数验证
    if not user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"msg": "用户名不能为空", "field": "username"}
        )
    
    if not user.password or len(user.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"msg": "密码不能为空且长度必须大于6位", "field": "password"}
        )
        
    # 检查用户名是否已存在
    db_user = get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"msg": "用户名已被注册", "field": "username"}
        )
    
    # 检查手机号是否已存在
    if user.mobile:
        mobile_user = get_user_by_mobile(db, user.mobile)
        if mobile_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"msg": "该手机号已被注册", "field": "mobile"}
            )
    
    try:
        return create_user(db, user)
    except Exception as e:
        error_msg = str(e)
        # 尝试从错误消息中提取更具体的信息
        if "Duplicate entry" in error_msg and "mobile" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"msg": "该手机号已被注册", "field": "mobile"}
            )
        elif "Duplicate entry" in error_msg and "username" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"msg": "用户名已被注册", "field": "username"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"msg": "创建用户失败，请稍后重试", "error_type": "server_error"}
            )


def login(db: Session, username: str, password: str) -> Token:
    """用户登录，获取JWT令牌"""
    # 参数验证
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"msg": "用户名不能为空", "field": "username"}
        )
    
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"msg": "密码不能为空", "field": "password"}
        )
    
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"msg": "用户名或密码不正确"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查用户是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"msg": "账号未激活，请联系管理员激活您的账号", "field": "is_active"},
        )
    
    try:
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return Token(access_token=access_token, token_type="bearer")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"msg": "生成令牌失败，请稍后重试", "error_type": "server_error"}
        )
