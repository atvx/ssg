from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.auth_service import register_user, login
from app.schemas.user import User, UserCreate, UserUpdate
from app.schemas.auth import Token
from app.utils.security import get_current_active_user

router = APIRouter()


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """注册新用户"""
    return register_user(db, user)


@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录，获取访问令牌"""
    return login(db, form_data.username, form_data.password)


@router.get("/me", response_model=User)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


@router.put("/me", response_model=User)
def update_user_me(
    user: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新当前用户信息"""
    # 更新用户信息，但只能更新自己的
    from app.db.crud import update_user
    return update_user(db, current_user.id, user)


@router.post("/change-password", response_model=User)
def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    # 验证旧密码
    from app.utils.security import verify_password
    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    
    # 更新密码
    user_update = UserUpdate(password=new_password)
    from app.db.crud import update_user
    return update_user(db, current_user.id, user_update)
