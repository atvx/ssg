from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from db.database import get_db
from db.crud import get_user, get_users, create_user, update_user, delete_user
from schemas.user import User, UserCreate, UserUpdate, UserDisplay
from schemas.response import APIResponse, StatusCode, ErrorType
from utils.security import get_current_active_user, get_current_superuser
from utils.response_utils import create_success_response, create_error_response

router = APIRouter()


@router.get("", summary="获取用户列表")
def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    获取用户列表（仅限管理员）
    
    参数:
    - skip: 跳过记录数
    - limit: 返回记录数上限
    """
    users = get_users(db, skip=skip, limit=limit)
    
    # 转换为展示格式
    user_list = []
    for user in users:
        user_list.append(UserDisplay(
            id=user.id,
            username=user.username,
            mobile=user.mobile,
            is_active=user.is_active,
            is_superuser=user.is_superuser
        ))
    
    return create_success_response(
        message="获取用户列表成功",
        data=user_list
    )


@router.get("/{user_id}", summary="获取用户详情")
def read_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    获取用户详情（仅限管理员）
    
    参数:
    - user_id: 用户ID
    """
    try:
        try:
            db_user = get_user(db, user_id=user_id)
            if db_user is None:
                return create_error_response(
                    message="用户不存在",
                    error_type=ErrorType.NOT_FOUND,
                    code=status.HTTP_404_NOT_FOUND,
                    details=[{
                        "field": "user_id",
                        "message": "用户不存在"
                    }]
                )
            
            return create_success_response(
                message="获取用户详情成功",
                data=UserDisplay(
                    id=db_user.id,
                    username=db_user.username,
                    mobile=db_user.mobile,
                    is_active=db_user.is_active,
                    is_superuser=db_user.is_superuser
                )
            )
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "user_id",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        return create_error_response(
            message=f"获取用户详情失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.put("/{user_id}", summary="更新用户信息")
def update_user_by_id(
    user_id: int, 
    user: UserUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    更新用户信息（仅限管理员）
    
    参数:
    - user_id: 用户ID
    - user: 用户更新数据
    """
    try:
        try:
            db_user = get_user(db, user_id=user_id)
            if db_user is None:
                return create_error_response(
                    message="用户不存在",
                    error_type=ErrorType.NOT_FOUND,
                    code=status.HTTP_404_NOT_FOUND,
                    details=[{
                        "field": "user_id",
                        "message": "用户不存在"
                    }]
                )
            
            updated_user = update_user(db, user_id, user)
            return create_success_response(
                message="用户信息更新成功",
                data=UserDisplay(
                    id=updated_user.id,
                    username=updated_user.username,
                    mobile=updated_user.mobile,
                    is_active=updated_user.is_active,
                    is_superuser=updated_user.is_superuser
                )
            )
        except ValueError as e:
            error_msg = str(e)
            return create_error_response(
                message=error_msg,
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "username" if "username" in error_msg else 
                            "mobile" if "mobile" in error_msg else
                            "password" if "password" in error_msg else "request_body",
                    "message": error_msg
                }]
            )
            
    except Exception as e:
        return create_error_response(
            message=f"更新用户信息失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.post("/{user_id}/activate", summary="激活用户账号")
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    激活用户账号（仅限管理员）
    
    参数:
    - user_id: 用户ID
    """
    try:
        try:
            db_user = get_user(db, user_id=user_id)
            if db_user is None:
                return create_error_response(
                    message="用户不存在",
                    error_type=ErrorType.NOT_FOUND,
                    code=status.HTTP_404_NOT_FOUND,
                    details=[{
                        "field": "user_id",
                        "message": "用户不存在"
                    }]
                )
            
            if db_user.is_active:
                return create_success_response(
                    message="用户已经处于激活状态"
                )
            
            # 更新用户状态
            user_update = UserUpdate(is_active=True)
            updated_user = update_user(db, user_id, user_update)
            
            return create_success_response(
                message="用户账号已激活",
                data=UserDisplay(
                    id=updated_user.id,
                    username=updated_user.username,
                    mobile=updated_user.mobile,
                    is_active=updated_user.is_active,
                    is_superuser=updated_user.is_superuser
                )
            )
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "user_id",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        return create_error_response(
            message=f"激活用户账号失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.post("/{user_id}/deactivate", summary="停用用户账号")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    停用用户账号（仅限管理员）
    
    参数:
    - user_id: 用户ID
    """
    try:
        try:
            if user_id == current_user.id:
                return create_error_response(
                    message="不能停用自己的账号",
                    error_type=ErrorType.VALIDATION_ERROR,
                    code=status.HTTP_400_BAD_REQUEST,
                    details=[{
                        "field": "user_id",
                        "message": "不能停用自己的账号"
                    }]
                )
            
            db_user = get_user(db, user_id=user_id)
            if db_user is None:
                return create_error_response(
                    message="用户不存在",
                    error_type=ErrorType.NOT_FOUND,
                    code=status.HTTP_404_NOT_FOUND,
                    details=[{
                        "field": "user_id",
                        "message": "用户不存在"
                    }]
                )
            
            if not db_user.is_active:
                return create_success_response(
                    message="用户已经处于停用状态"
                )
            
            # 更新用户状态
            user_update = UserUpdate(is_active=False)
            updated_user = update_user(db, user_id, user_update)
            
            return create_success_response(
                message="用户账号已停用",
                data=UserDisplay(
                    id=updated_user.id,
                    username=updated_user.username,
                    mobile=updated_user.mobile,
                    is_active=updated_user.is_active,
                    is_superuser=updated_user.is_superuser
                )
            )
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "user_id",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        return create_error_response(
            message=f"停用用户账号失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.delete("/{user_id}", summary="删除用户")
def delete_user_by_id(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    删除用户（仅限管理员）
    
    参数:
    - user_id: 用户ID
    """
    try:
        try:
            if user_id == current_user.id:
                return create_error_response(
                    message="不能删除自己的账号",
                    error_type=ErrorType.VALIDATION_ERROR,
                    code=status.HTTP_400_BAD_REQUEST,
                    details=[{
                        "field": "user_id",
                        "message": "不能删除自己的账号"
                    }]
                )
            
            db_user = get_user(db, user_id=user_id)
            if db_user is None:
                return create_error_response(
                    message="用户不存在",
                    error_type=ErrorType.NOT_FOUND,
                    code=status.HTTP_404_NOT_FOUND,
                    details=[{
                        "field": "user_id",
                        "message": "用户不存在"
                    }]
                )
            
            # 删除用户
            deleted_user = delete_user(db, user_id=user_id)
            
            return create_success_response(
                message="用户删除成功",
                data=UserDisplay(
                    id=deleted_user.id,
                    username=deleted_user.username,
                    mobile=deleted_user.mobile,
                    is_active=deleted_user.is_active,
                    is_superuser=deleted_user.is_superuser
                )
            )
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "user_id",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        return create_error_response(
            message=f"删除用户失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        ) 