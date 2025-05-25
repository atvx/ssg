from typing import Any, List, Dict, Optional
from schemas.response import APIResponse, StatusCode, ErrorType, ErrorDetail, ErrorInfo

def create_success_response(message: str, data: Any = None, code: int = StatusCode.OK):
    """创建成功响应"""
    response = APIResponse(
        code=code,
        success=True,
        message=message,
        data=data
    )
    return response.dict(exclude_none=True)

def create_error_response(message: str, error_type: ErrorType, code: int, details: List[Dict[str, str]] = None):
    """创建错误响应"""
    error_details = []
    if details:
        for detail in details:
            error_details.append(ErrorDetail(**detail))
    
    response = APIResponse(
        code=code,
        success=False,
        message=message,
        data=None,
        error=ErrorInfo(type=error_type, details=error_details)
    )
    return response.dict(exclude_none=True)

def create_validation_error(message: str = "请求参数错误", details: List[Dict[str, str]] = None):
    """创建验证错误响应"""
    return create_error_response(
        message=message,
        error_type=ErrorType.VALIDATION_ERROR,
        code=StatusCode.BAD_REQUEST,
        details=details
    )

def create_server_error(message: str = "服务器内部错误，请稍后重试"):
    """创建服务器错误响应"""
    return create_error_response(
        message=message,
        error_type=ErrorType.SERVER_ERROR,
        code=StatusCode.INTERNAL_SERVER_ERROR,
        details=None
    ) 