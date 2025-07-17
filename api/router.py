from fastapi import APIRouter, Depends
from api.endpoints import auth, users, tasks, sales, orgs, records, report
from utils.auth_utils import get_current_active_user

api_router = APIRouter()

# 认证相关路由
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["认证"]
)

# 用户相关路由
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["用户"],
    dependencies=[Depends(get_current_active_user)]
)

# 任务相关路由
api_router.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["任务"],
    dependencies=[Depends(get_current_active_user)]
)

# 销售数据相关路由
api_router.include_router(
    sales.router,
    prefix="/sales",
    tags=["销售数据"],
    dependencies=[Depends(get_current_active_user)]
)

# 组织机构相关路由
api_router.include_router(
    orgs.router,
    prefix="/orgs",
    tags=["组织机构"],
    dependencies=[Depends(get_current_active_user)]
)

# 销售记录相关路由
api_router.include_router(
    records.router,
    prefix="/records",
    tags=["销售记录"],
    dependencies=[Depends(get_current_active_user)]
)

# 报表相关路由
api_router.include_router(
    report.router,
    prefix="/report",
    tags=["报表"],
    dependencies=[Depends(get_current_active_user)]
)
