from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request, Form, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Dict
from pydantic import BaseModel

from db.database import get_db
from services.auth_service import register_user, login
from schemas.user import User, UserCreate, UserUpdate
from schemas.auth import Token, Login
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

@router.post("/register", status_code=status.HTTP_201_CREATED, summary="用户注册")
async def create_user(
    request: Request,
    username: Optional[str] = Query(None, description="用户名"),
    mobile: Optional[str] = Query(None, description="手机号"),
    password: Optional[str] = Query(None, description="密码"),
    user: Optional[UserCreate] = None,
    db: Session = Depends(get_db)
):
    """
    注册新用户
    
    支持两种方式提交数据:
    1. 查询参数: /register?username=xxx&mobile=xxx&password=xxx
    2. JSON请求体: {"username": "xxx", "mobile": "xxx", "password": "xxx"}
    
    返回:
         统一的API响应格式
    """
    try:
        registered_user = None
        
        # 检查是否通过查询参数提交
        if username and password:
            try:
                user_data = UserCreate(
                    username=username,
                    mobile=mobile if mobile else None,
                    password=password
                )
                registered_user = register_user(db, user_data)
            except ValueError as e:
                # 捕获Pydantic验证错误
                error_msg = str(e)
                # 提取简洁的错误信息
                if "密码长度不能少于" in error_msg:
                    error_msg = "密码长度不能少于6位"
                elif "手机号格式不正确" in error_msg:
                    error_msg = "手机号格式不正确，请输入11位中国大陆手机号"
                
                return create_error_response(
                    message=error_msg,
                    error_type=ErrorType.VALIDATION_ERROR,
                    code=status.HTTP_400_BAD_REQUEST,
                    details=[{
                        "field": "password",
                        "message": error_msg
                    }]
                )
        
        # 检查是否通过请求体提交
        elif user:
            registered_user = register_user(db, user)
        
        # 尝试从请求体解析JSON数据
        else:
            try:
                body_data = await request.json()
                try:
                    user_data = UserCreate(
                        username=body_data.get("username"),
                        mobile=body_data.get("mobile"),
                        password=body_data.get("password")
                    )
                    registered_user = register_user(db, user_data)
                except ValueError as e:
                    # 捕获Pydantic验证错误
                    error_msg = str(e)
                    # 提取简洁的错误信息
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
            except Exception:
                # 如果无法解析，则返回友好错误
                return create_error_response(
                    message="无效的请求格式",
                    error_type=ErrorType.VALIDATION_ERROR,
                    code=status.HTTP_400_BAD_REQUEST,
                    details=[{
                        "field": "request_body",
                        "message": "无效的请求格式"
                    }]
                )
        
        # 构建统一响应
        return create_success_response(
            code=StatusCode.CREATED,
            message="用户注册成功"
        )
            
    except Exception as e:
        # 处理其他所有异常
        return create_error_response(
            message=f"用户注册失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.post("/login", summary="用户登录")
async def login_for_access_token(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    用户登录，获取访问令牌
    
    支持多种方式提交登录信息:
    1. 表单提交: username=xxx&password=xxx (Content-Type: application/x-www-form-urlencoded)
    2. 查询参数: /login?username=xxx&password=xxx
    3. JSON请求体: {"username": "xxx", "password": "xxx"}
    """
    # 尝试从查询参数获取
    username = request.query_params.get("username")
    password = request.query_params.get("password")
    
    if username and password:
        token_data = login(db, username, password)
        return create_success_response(
            code=StatusCode.OK,
            message="登录成功",
            data=token_data.dict()
        )
    
    # 尝试从请求体解析JSON数据
    try:
        body_data = await request.json()
        username = body_data.get("username")
        password = body_data.get("password")
        if username and password:
            token_data = login(db, username, password)
            return create_success_response(
                code=StatusCode.OK,
                message="登录成功",
                data=token_data.dict()
            )
    except Exception:
        pass
    
    # 尝试解析表单数据
    try:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        if username and password:
            token_data = login(db, username, password)
            return create_success_response(
                code=StatusCode.OK,
                message="登录成功",
                data=token_data.dict()
            )
    except Exception:
        pass
    
    # 如果所有尝试都失败，返回友好错误
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "msg": "无效的登录请求",
            "field": "credentials"
        }
    )


@router.get("/me", summary="获取当前用户信息")
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
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


@router.put("/me", summary="更新当前用户信息")
def update_user_me(
    user: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新当前用户信息"""
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


@router.post("/change-password", summary="修改密码")
def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    # 验证旧密码
    from utils.security import verify_password
    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail={
                "msg": "原密码不正确",
                "field": "old_password"
            }
        )
    
    # 更新密码
    user_update = UserUpdate(password=new_password)
    from db.crud import update_user
    update_user(db, current_user.id, user_update)
    
    return create_success_response(
        code=StatusCode.OK,
        message="密码修改成功"
    )

@router.get("/verification/{task_id}", response_model=VerificationResponse, summary="获取验证任务状态")
async def get_verification_status(task_id: str):
    """
    获取验证任务状态
    
    Args:
        task_id: 验证任务ID
        
    Returns:
        VerificationResponse: 验证任务状态
    """
    task = VerificationManager.get_verification_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification task not found"
        )
        
    return VerificationResponse(
        task_id=task_id,
        status=task["status"],
        message="Successfully retrieved verification status",
        data=task
    )

@router.post("/verification/{task_id}/submit", response_model=VerificationResponse, summary="提交验证码")
async def submit_verification_code(
    task_id: str, 
    request: VerificationCodeRequest,
    background_tasks: BackgroundTasks
):
    """
    提交验证码
    
    Args:
        task_id: 验证任务ID
        request: 验证码请求
        
    Returns:
        VerificationResponse: 验证结果
    """
    task = VerificationManager.get_verification_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification task not found"
        )
        
    # 提交验证码
    success = VerificationManager.submit_verification_code(task_id, request.code)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to submit verification code"
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
