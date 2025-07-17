from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Optional
import logging

from config.settings import settings, SECRET_KEY, ALGORITHM
from utils.security import get_current_user, get_current_active_user, get_current_superuser
from utils.security import create_access_token, verify_password, get_password_hash

# 配置日志
logger = logging.getLogger(__name__)

# 重新导出函数，使其可以从auth_utils直接导入
__all__ = [
    'get_current_user',
    'get_current_active_user',
    'get_current_superuser',
    'create_access_token',
    'verify_password',
    'get_password_hash'
]
