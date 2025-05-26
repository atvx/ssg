from fastapi import FastAPI, Depends, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
import logging
import warnings

# 配置日志和警告
logging.basicConfig(level=logging.ERROR)
logging.getLogger("uvicorn.access").setLevel(logging.ERROR)
logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
logging.getLogger("fastapi").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy").setLevel(logging.ERROR)

# 忽略所有警告
warnings.filterwarnings("ignore")

from api.router import api_router
from config.settings import settings
from db.database import engine, Base
from schemas.response import APIResponse, ErrorType, StatusCode, ErrorInfo, ErrorDetail
from utils.response_utils import create_success_response, create_error_response, create_validation_error, create_server_error

# WebSocket模块
from ws import router as websocket_router

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="销售数据获取系统API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为特定的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

# 注册WebSocket路由
app.include_router(websocket_router)

logger = logging.getLogger(__name__)

# 添加全局异常处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误，返回友好的错误信息"""
    details = []
    for error in exc.errors():
        error_detail = {
            "message": error["msg"],
            "field": error["loc"][-1] if error["loc"] else None
        }
        
        # 根据错误类型提供更友好的提示
        if error["type"] == "missing":
            field = error["loc"][-1] if error["loc"] else "未知字段"
            error_detail["message"] = f"缺少必填字段: {field}"
            
        elif error["type"] == "value_error.any_str.min_length":
            field = error["loc"][-1] if error["loc"] else "未知字段"
            error_detail["message"] = f"字段长度过短: {field}"
            
        elif error["type"] == "value_error.email":
            error_detail["message"] = "无效的邮箱格式"
            
        elif error["type"] == "type_error":
            field = error["loc"][-1] if error["loc"] else "未知字段"
            error_detail["message"] = f"字段类型错误: {field}"
        
        details.append(error_detail)
    
    # 如果所有尝试都失败，返回友好错误
    try:
        response = create_validation_error(message="请求参数验证失败", details=details)
    except Exception:
        # 使用最简单的响应格式
        response = {"code": 422, "success": False, "message": "请求参数验证失败"}
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response
        )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理HTTP异常，返回标准格式的错误信息"""
    # 处理自定义detail字段
    details = None
    error_type = ErrorType.SERVER_ERROR
    
    # 根据状态码确定错误类型
    if exc.status_code == 401:
        error_type = ErrorType.AUTHENTICATION_ERROR
    elif exc.status_code == 403:
        error_type = ErrorType.AUTHORIZATION_ERROR
    elif exc.status_code == 404:
        error_type = ErrorType.RESOURCE_ERROR
    elif exc.status_code >= 400 and exc.status_code < 500:
        error_type = ErrorType.VALIDATION_ERROR
        
    # 解析错误详情
    if isinstance(exc.detail, dict) and "msg" in exc.detail:
        message = exc.detail["msg"]
        # 如果detail中包含field字段，将其转换为errors数组
        if "field" in exc.detail:
            details = [{
                "field": exc.detail["field"],
                "message": message
            }]
    else:
        message = str(exc.detail)
    
    # 创建统一的响应格式
    try:
        response = create_error_response(
            message=message,
            error_type=error_type,
            code=exc.status_code,
            details=details
        )
    except Exception:
        # 使用最简单的响应格式
        response = {"code": exc.status_code, "success": False, "message": message}
        return JSONResponse(
            status_code=exc.status_code,
            content=response,
            headers=exc.headers
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response,
        headers=exc.headers
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理所有未捕获的异常"""
    # 记录错误日志
    logging.error(f"未捕获的异常: {str(exc)}", exc_info=True)
    
    # 创建统一的响应格式
    try:
        response = create_server_error(message="服务器内部错误，请稍后重试")
    except Exception:
        # 使用最简单的响应格式
        response = {"code": 500, "success": False, "message": "服务器内部错误，请稍后重试"}
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response
        )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response
    )


@app.get("/")
def root():
    """API根路径，用于健康检查"""
    try:
        return create_success_response(
            message="销售数据获取系统API服务正常运行中"
        )
    except Exception:
        return {
            "code": 200,
            "success": True,
            "message": "销售数据获取系统API服务正常运行中"
        }


@app.get("/ping")
def ping():
    """简单的健康检查端点"""
    return {"ping": "pong", "status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=settings.DEBUG,
        log_level="error"
    ) 