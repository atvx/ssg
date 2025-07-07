from fastapi import APIRouter
from api.endpoints import auth, sales, tasks, orgs, records, report

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

# 注册机构管理相关路由
api_router.include_router(
    orgs.router,
    prefix="/orgs",
    tags=["organizations"]
)

# 注册销售记录相关路由
api_router.include_router(
    records.router,
    prefix="/sales",
    tags=["sales-records"]
)

# 注册报告相关路由
api_router.include_router(
    report.router,
    prefix="/report",
    tags=["reports"]
)
