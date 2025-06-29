from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import hashlib
import base64
import os
import logging
import warnings

from config.settings import settings, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# 忽略特定警告
warnings.filterwarnings("ignore", category=UserWarning)

# 配置日志 - 禁用控制台输出
logger = logging.getLogger("passlib")
logger.setLevel(logging.ERROR)  # 只记录错误级别
logging.getLogger("utils.security").setLevel(logging.ERROR)

# 尝试导入bcrypt并静默处理可能的错误
USING_BCRYPT = False
try:
    from passlib.hash import bcrypt
    # 测试bcrypt而不输出日志
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        test_hash = bcrypt.hash("test_password")
        is_verified = bcrypt.verify("test_password", test_hash)
        USING_BCRYPT = is_verified
except Exception:
    # 静默失败，继续使用SHA256
    pass

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码
        
    Returns:
        bool: 密码是否匹配
    """
    if not plain_password or not hashed_password:
        return False
    
    # 检查是否为bcrypt格式（以$2开头）
    is_bcrypt_hash = hashed_password.startswith('$2') if hashed_password else False
    
    # 如果是bcrypt哈希且bcrypt可用，则使用bcrypt验证
    if is_bcrypt_hash and USING_BCRYPT:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return bcrypt.verify(plain_password, hashed_password)
        except Exception:
            # 静默错误，尝试其他方法
            pass
            
    # 如果是自定义SHA256格式（salt$hash）
    elif "$" in hashed_password and not is_bcrypt_hash:
        try:
            salt, hash_value = hashed_password.split("$", 1)
            new_hash = hashlib.sha256((plain_password + salt).encode()).hexdigest()
            return new_hash == hash_value
        except Exception:
            return False
            
    # 不支持的格式
    return False


def get_password_hash(password: str) -> str:
    """
    获取密码哈希
    
    Args:
        password: 明文密码
        
    Returns:
        str: 哈希后的密码
    """
    if not password:
        raise ValueError("密码不能为空")
    
    # 如果bcrypt可用，使用bcrypt
    if USING_BCRYPT:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return bcrypt.hash(password)
        except Exception:
            # 静默错误，使用SHA256
            pass
    
    # 使用SHA256
    salt = base64.b64encode(os.urandom(16)).decode()
    hash_value = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${hash_value}"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌
    
    Args:
        data: 要编码到令牌中的数据
        expires_delta: 令牌过期时间
        
    Returns:
        str: JWT令牌
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(datetime.UTC) + expires_delta
    else:
        expire = datetime.now(datetime.UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"msg": "服务器内部错误，无法生成令牌", "error_type": "token_generation_error"}
        )


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    获取当前用户
    
    Args:
        token: JWT令牌
        
    Returns:
        User: 当前用户对象
        
    Raises:
        HTTPException: 当令牌无效或用户不存在时
    """
    from db.crud import get_user_by_username
    from db.database import get_db
    from fastapi import Depends
    
    db = next(get_db())
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"msg": "无效的身份凭据或令牌已过期", "error_type": "invalid_credentials"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user = Depends(get_current_user)):
    """
    获取当前活跃用户
    
    Args:
        current_user: 当前用户对象
        
    Returns:
        User: 当前活跃用户对象
        
    Raises:
        HTTPException: 当用户不活跃时
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail={"msg": "用户账号已停用", "error_type": "inactive_user"}
        )
    return current_user


async def get_current_superuser(current_user = Depends(get_current_active_user)):
    """
    获取当前超级用户（管理员）
    
    Args:
        current_user: 当前活跃用户对象
        
    Returns:
        User: 当前超级用户对象
        
    Raises:
        HTTPException: 当用户不是超级用户时
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail={"msg": "权限不足，需要管理员权限", "error_type": "insufficient_permissions"}
        )
    return current_user
