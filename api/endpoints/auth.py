from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request, Form, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Dict
from pydantic import BaseModel

from db.database import get_db
from services.auth_service import register_user, login
from schemas.user import User, UserCreate, UserUpdate
from schemas.auth import Token, Login, LoginResponse, RegisterResponse, UserInfoResponse, UpdateUserResponse, PasswordChangeRequest, ChangePasswordResponse
from schemas.response import APIResponse, StatusCode, ErrorType
from utils.security import get_current_active_user, create_access_token
from utils.response_utils import create_success_response, create_error_response
from utils.redis_utils import VerificationManager
from ws.manager import connection_manager

router = APIRouter()

# 安全检查
security = HTTPBearer()

# 请求和响应模型
class VerificationCodeRequest(BaseModel):
    code: str
    
class VerificationResponse(BaseModel):
    task_id: str
    status: str
    message: str
    data: dict = None

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED, summary="用户注册")
async def create_user(
    user: UserCreate = Body(..., description="用户注册信息"),
    db: Session = Depends(get_db)
):
    """
    用户注册
    
    参数:
    - username: 用户名
    - password: 密码
    - mobile: 手机号
    
    返回:
    - 注册结果信息
    """
    try:
        try:
            registered_user = register_user(db, user)
        except ValueError as e:
            error_msg = str(e)
            if "密码长度不能少于" in error_msg:
                error_msg = "密码长度不能少于6位"
            elif "手机号格式不正确" in error_msg:
                error_msg = "手机号格式不正确，请输入11位中国大陆手机号"
            
            return create_error_response(
                message=error_msg,
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "password" if "密码" in error_msg else 
                            "mobile" if "手机号" in error_msg else
                            "username" if "用户名" in error_msg else "request_body",
                    "message": error_msg
                }]
            )

        return create_success_response(
            code=StatusCode.CREATED,
            message="用户注册成功"
        )
            
    except Exception as e:
        return create_error_response(
            message=f"用户注册失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.post("/login", response_model=LoginResponse, summary="用户登录")
async def login_for_access_token(
    login_data: Login,
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    参数:
    - username: 用户名
    - password: 密码
    
    返回:
    - 包含访问令牌的响应
    """
    try:
        try:
            username = login_data.username
            password = login_data.password
            
            if not username or not password:
                return create_error_response(
                    message="用户名或密码不能为空",
                    error_type=ErrorType.VALIDATION_ERROR,
                    code=status.HTTP_400_BAD_REQUEST,
                    details=[{
                        "field": "username" if not username else "password",
                        "message": "用户名或密码不能为空"
                    }]
                )
                
            token_data = login(db, username, password)
            return create_success_response(
                code=StatusCode.OK,
                message="登录成功",
                data=token_data.dict()
            )
        except ValueError as e:
            error_msg = str(e)
            return create_error_response(
                message=error_msg,
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "credentials",
                    "message": error_msg
                }]
            )
        except Exception:
            return create_error_response(
                message="无效的登录请求",
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "request_body",
                    "message": "无效的登录请求"
                }]
            )
            
    except Exception as e:
        return create_error_response(
            message=f"登录失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.get("/me", response_model=UserInfoResponse, summary="获取当前用户信息")
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    获取当前用户信息
    
    返回:
    - 当前登录用户的详细信息
    """
    return create_success_response(
        code=StatusCode.OK,
        message="获取用户信息成功",
        data={
            "username": current_user.username,
            "mobile": current_user.mobile,
            "id": current_user.id,
            "is_active": current_user.is_active,
            "is_superuser": current_user.is_superuser
        }
    )


@router.put("/me", response_model=UpdateUserResponse, summary="更新当前用户信息")
def update_user_me(
    user: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新当前用户信息
    
    参数:
    - username: 新用户名（可选）
    - mobile: 新手机号（可选）
    - password: 新密码（可选）
    
    返回:
    - 更新后的用户信息
    """
    # 更新用户信息，但只能更新自己的
    from db.crud import update_user
    updated_user = update_user(db, current_user.id, user)
    return create_success_response(
        code=StatusCode.OK,
        message="用户信息更新成功",
        data={
            "username": updated_user.username,
            "mobile": updated_user.mobile,
            "id": updated_user.id
        }
    )


@router.post("/change-password", response_model=ChangePasswordResponse, summary="修改密码")
def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    修改密码
    
    参数:
    - old_password: 原密码
    - new_password: 新密码
    
    返回:
    - 密码修改结果
    """
    try:
        try:
            # 验证旧密码
            from utils.security import verify_password
            if not verify_password(password_data.old_password, current_user.hashed_password):
                return create_error_response(
                    message="原密码不正确",
                    error_type=ErrorType.VALIDATION_ERROR,
                    code=status.HTTP_400_BAD_REQUEST,
                    details=[{
                        "field": "old_password",
                        "message": "原密码不正确"
                    }]
                )
            
            # 更新密码
            user_update = UserUpdate(password=password_data.new_password)
            from db.crud import update_user
            update_user(db, current_user.id, user_update)
            
            return create_success_response(
                code=StatusCode.OK,
                message="密码修改成功"
            )
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "password",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        return create_error_response(
            message=f"密码修改失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )

@router.get("/verification/{task_id}", response_model=VerificationResponse, summary="获取验证任务状态")
async def get_verification_status(task_id: str):
    """
    获取验证任务状态
    
    参数:
    - task_id: 验证任务ID
    
    返回:
    - 验证任务的当前状态信息
    """
    try:
        try:
            task = VerificationManager.get_verification_task(task_id)
            if not task:
                return create_error_response(
                    message="验证任务不存在",
                    error_type=ErrorType.NOT_FOUND,
                    code=status.HTTP_404_NOT_FOUND,
                    details=[{
                        "field": "task_id",
                        "message": "验证任务不存在"
                    }]
                )
                
            return VerificationResponse(
                task_id=task_id,
                status=task["status"],
                message="Successfully retrieved verification status",
                data=task
            )
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "task_id",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        return create_error_response(
            message=f"获取验证任务状态失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )

@router.post("/verification/{task_id}/submit", response_model=VerificationResponse, summary="提交验证码")
async def submit_verification_code(
    task_id: str, 
    request: VerificationCodeRequest,
    background_tasks: BackgroundTasks
):
    """
    提交验证码
    
    参数:
    - task_id: 验证任务ID
    - request: 包含验证码的请求体
    
    返回:
    - 验证码提交结果信息
    """
    try:
        try:
            task = VerificationManager.get_verification_task(task_id)
            if not task:
                return create_error_response(
                    message="验证任务不存在",
                    error_type=ErrorType.NOT_FOUND,
                    code=status.HTTP_404_NOT_FOUND,
                    details=[{
                        "field": "task_id",
                        "message": "验证任务不存在"
                    }]
                )
                
            # 提交验证码
            success = VerificationManager.submit_verification_code(task_id, request.code)
            if not success:
                return create_error_response(
                    message="验证码提交失败",
                    error_type=ErrorType.VALIDATION_ERROR,
                    code=status.HTTP_400_BAD_REQUEST,
                    details=[{
                        "field": "code",
                        "message": "验证码提交失败，可能验证码无效或已过期"
                    }]
                )
            
            # 异步通知WebSocket客户端
            background_tasks.add_task(
                connection_manager.send_verification_notification,
                task_id,
                {
                    "type": "code_submitted",
                    "task_id": task_id,
                    "code": request.code
                }
            )
                
            return VerificationResponse(
                task_id=task_id,
                status="code_submitted",
                message="Successfully submitted verification code"
            )
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "code",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        return create_error_response(
            message=f"验证码提交失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )
