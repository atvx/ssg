from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from db.database import get_db
from services.daily_report_service import DailyReportService
from schemas.response import APIResponse
from utils.security import get_current_active_user
from schemas.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

daily_report_service = DailyReportService()

@router.get("/daily", response_model=APIResponse[List[Dict[str, Any]]])
async def get_daily_report(
    query_date: Optional[str] = Query(None, description="查询日期，格式为YYYY-MM-DD，默认为今天"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取日报数据
    
    返回指定日期的销售日报数据，包含市场和仓库的销售统计信息
    """
    try:
        # 如果未提供日期，使用当前日期
        if query_date is None:
            query_date = datetime.now().strftime("%Y-%m-%d")
        
        # 验证日期格式
        try:
            datetime.strptime(query_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式无效，请使用YYYY-MM-DD格式")
        
        # 从数据库获取原始数据
        from db.crud import find_daily_sales_data
        raw_data = find_daily_sales_data(db, query_date)
        
        return {
            "code": 200,
            "success": True,
            "message": "获取日报数据成功",
            "data": raw_data
        }
    except Exception as e:
        logger.error(f"获取日报数据时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取日报数据失败: {str(e)}") 