from fastapi import APIRouter
from api.endpoints import auth, sales, tasks

api_router = APIRouter()

# 注册认证相关路由
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

# 注册销售数据相关路由
api_router.include_router(
    sales.router,
    prefix="/sales",
    tags=["sales"]
)

# 注册任务管理相关路由
api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["tasks"]
)
