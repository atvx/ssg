from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date as date_type, datetime

from db.database import get_db
from schemas.record import (
    SalesRecordCreate, SalesRecordUpdate, SalesRecordResponse,
    SalesRecordListResponse, SalesRecordDetailResponse, SalesRecordQuery
)
from schemas.response import APIResponse
from schemas.user import User
from utils.security import get_current_active_user, get_current_superuser
from utils.response_utils import create_success_response, create_error_response
from services.record_service import RecordService

router = APIRouter()


@router.post("/records", response_model=SalesRecordDetailResponse, status_code=status.HTTP_201_CREATED, summary="创建销售记录")
def create_sales_record(
    record: SalesRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    创建新的销售记录
    
    参数:
    - **record**: 销售记录创建模型
    
    返回:
    - 创建的销售记录详情
    """
    try:
        db_record = RecordService.create_sales_record(db, record)
        return SalesRecordDetailResponse(
            message="创建销售记录成功",
            data=db_record
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建销售记录失败: {str(e)}"
        )


@router.get("/records", response_model=SalesRecordListResponse, summary="获取销售记录列表")
def list_sales_records(
    start_date: Optional[date_type] = None,
    end_date: Optional[date_type] = None,
    platform: Optional[str] = None,
    warehouse: Optional[str] = None,
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=500, description="返回记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取销售记录列表，支持多种筛选条件
    
    参数:
    - **start_date**: 开始日期（可选）
    - **end_date**: 结束日期（可选）
    - **platform**: 平台（可选）
    - **warehouse**: 仓库（可选）
    - **skip**: 跳过记录数，默认为0
    - **limit**: 返回记录数，默认为100，最大500
    
    返回:
    - 销售记录列表和总记录数
    """
    try:
        query = SalesRecordQuery(
            start_date=start_date,
            end_date=end_date,
            platform=platform,
            warehouse_name=warehouse,
            skip=skip,
            limit=limit
        )
        records, total = RecordService.get_sales_records(db, query)
        
        return SalesRecordListResponse(
            message="获取销售记录列表成功",
            data=records,
            total=total
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取销售记录列表失败: {str(e)}"
        )


@router.get("/records/{record_id}", response_model=SalesRecordDetailResponse, summary="获取销售记录详情")
def get_sales_record(
    record_id: int = Path(..., description="销售记录ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取指定销售记录的详情
    
    参数:
    - **record_id**: 销售记录ID
    
    返回:
    - 销售记录详情
    """
    try:
        record = RecordService.get_sales_record(db, record_id)
        if not record:
            return create_error_response(
                message=f"未找到ID为{record_id}的销售记录",
                code=status.HTTP_404_NOT_FOUND
            )
        
        return SalesRecordDetailResponse(
            message="获取销售记录详情成功",
            data=record
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取销售记录详情失败: {str(e)}"
        )


@router.put("/records/{record_id}", response_model=SalesRecordDetailResponse, summary="更新销售记录")
def update_sales_record(
    record_id: int = Path(..., description="销售记录ID"),
    record: SalesRecordUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    更新指定的销售记录
    
    参数:
    - **record_id**: 销售记录ID
    - **record**: 销售记录更新模型
    
    返回:
    - 更新后的销售记录详情
    """
    try:
        updated_record = RecordService.update_sales_record(db, record_id, record)
        if not updated_record:
            return create_error_response(
                message=f"未找到ID为{record_id}的销售记录",
                code=status.HTTP_404_NOT_FOUND
            )
        
        return SalesRecordDetailResponse(
            message="更新销售记录成功",
            data=updated_record
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新销售记录失败: {str(e)}"
        )


@router.delete("/records/{record_id}", response_model=APIResponse, summary="删除销售记录")
def delete_sales_record(
    record_id: int = Path(..., description="销售记录ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    删除指定的销售记录
    
    参数:
    - **record_id**: 销售记录ID
    
    返回:
    - 操作结果
    """
    try:
        success = RecordService.delete_sales_record(db, record_id)
        if not success:
            return create_error_response(
                message=f"未找到ID为{record_id}的销售记录",
                code=status.HTTP_404_NOT_FOUND
            )
        
        return create_success_response(message=f"销售记录(ID:{record_id})删除成功")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除销售记录失败: {str(e)}"
        ) 