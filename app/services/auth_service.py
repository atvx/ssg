from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status

from app.db.crud import get_user_by_username, create_user, authenticate_user
from app.schemas.user import UserCreate
from app.schemas.auth import Token
from app.utils.security import create_access_token


def register_user(db: Session, user: UserCreate):
    """注册新用户"""
    db_user = get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    return create_user(db, user)


def login(db: Session, username: str, password: str) -> Token:
    """用户登录，获取JWT令牌"""
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")
