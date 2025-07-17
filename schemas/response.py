from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Generic, TypeVar
from enum import Enum

# 定义泛型类型变量
T = TypeVar('T')


# 状态码枚举
class StatusCode(int, Enum):
    # 成功状态
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    
    # 客户端错误
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    REQUEST_TIMEOUT = 408
    CONFLICT = 409
    TOO_MANY_REQUESTS = 429
    
    # 服务器错误
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


# 错误类型枚举
class ErrorType(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_ERROR = "RESOURCE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    SERVER_ERROR = "SERVER_ERROR"
    NOT_FOUND = "NOT_FOUND"


# 错误详情项
class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


# 错误信息
class ErrorInfo(BaseModel):
    type: ErrorType
    details: List[ErrorDetail] = []


# 基础响应模型 (用于API接口返回)
class ResponseBase(BaseModel):
    code: int = Field(200, description="HTTP状态码")
    success: bool = Field(True, description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="响应数据")


# 通用响应模型
class APIResponse(BaseModel, Generic[T]):
    code: int = Field(200, description="HTTP状态码")
    success: bool = Field(True, description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    error: Optional[ErrorInfo] = Field(None, description="错误信息")
    
    model_config = {
        "json_encoders": {
            # 自定义编码器，如有需要
        },
        "exclude_none": True  # 排除None值
    }


# 创建成功响应
def create_success_response(message: str, data: Any = None) -> Dict[str, Any]:
    return {
        "success": True,
        "code": 200,
        "message": message,
        "data": data
    }


# 创建错误响应
def create_error_response(
    message: str,
    error_type: ErrorType,
    code: int = 400,
    details: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    error_details = []
    if details:
        for detail in details:
            error_details.append(ErrorDetail(**detail))
    
    return {
        "success": False,
        "code": code,
        "message": message,
        "error": {
            "type": error_type,
            "details": error_details or []
        },
        "data": None
    } 