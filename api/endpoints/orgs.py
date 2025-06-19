from fastapi import APIRouter, Depends, HTTPException, Query, status, Path
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from db.database import get_db
from db.crud import get_org_list, get_org, create_org, update_org, delete_org
from schemas.org import OrgListResponse, OrgListItem, OrgCreate, OrgUpdate, OrgResponse, OrgDetail
from utils.security import get_current_active_user, get_current_superuser
from schemas.user import User
from utils.response_utils import create_success_response, create_error_response
from schemas.response import ErrorType

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/list", response_model=OrgListResponse, summary="获取机构列表")
def get_orgs(
    skip: int = Query(0, description="跳过记录数"),
    limit: int = Query(100, description="返回记录数上限"),
    type: Optional[str] = Query(None, description="机构类型，支持多选，使用逗号分隔，例如：1,2,3"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取机构列表
    
    参数:
    - skip: 跳过记录数，默认0
    - limit: 返回记录数上限，默认100
    - type: 机构类型，支持多选，使用逗号分隔，例如：1,2,3，不传则不过滤
    
    返回:
    - 机构列表，包含org_id, org_name, org_type, parent_id, sort字段
    """
    try:
        # 处理逗号分隔的type参数
        org_types = None
        if type:
            org_types = [t.strip() for t in type.split(",") if t.strip()]
        
        orgs = get_org_list(db, skip=skip, limit=limit, org_types=org_types)
        
        # 将查询结果转换为响应模型
        org_items = []
        for org in orgs:
            org_item = OrgListItem(
                org_id=org['org_id'],
                org_name=org['org_name'],
                org_type=org['org_type'],
                parent_id=org['parent_id'],
                parent_name=org['parent_name'],
                sort=org['sort'],
                status=org['status']
            )
            org_items.append(org_item)
        
        return create_success_response(
            message="获取机构列表成功",
            data=org_items
        )
    except Exception as e:
        logger.error(f"获取机构列表失败: {str(e)}")
        return create_error_response(
            message=f"获取机构列表失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.get("/{org_id}", response_model=OrgResponse, summary="获取机构详情")
def get_org_detail(
    org_id: str = Path(..., description="机构ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取机构详情
    
    参数:
    - org_id: 机构ID (路径参数)
    
    返回:
    - 机构详情，包含id, name, org_type, parent_id, sort字段
    """
    try:
        org = get_org(db, org_id)
        
        if not org:
            return create_error_response(
                message=f"找不到ID为'{org_id}'的机构",
                error_type=ErrorType.NOT_FOUND,
                code=status.HTTP_404_NOT_FOUND,
                details=[{
                    "field": "org_id",
                    "message": "机构不存在"
                }]
            )
        
        # 构建响应数据
        org_detail = OrgDetail(
            id=org.id,
            name=org.name,
            org_type=org.org_type,
            parent_id=org.parent_id,
            parent_name=org.parent_name,
            sort=org.sort,
            status=org.status
        )
        
        return create_success_response(
            message="获取机构详情成功",
            data=org_detail
        )
    except Exception as e:
        logger.error(f"获取机构详情失败: {str(e)}")
        return create_error_response(
            message=f"获取机构详情失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.post("", response_model=OrgResponse, status_code=status.HTTP_201_CREATED, summary="新增机构")
def add_org(
    org_create: OrgCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    新增机构
    
    参数:
    - id: 机构ID (必填)
    - name: 机构名称 (必填)
    - org_type: 机构类型 (可选)
    - parent_id: 父级机构ID (可选)
    - sort: 排序 (可选，默认0)
    
    返回:
    - 创建成功的机构信息
    """
    try:
        try:
            # 验证父级机构是否存在
            if org_create.parent_id:
                parent_org = get_org(db, org_create.parent_id)
                if not parent_org:
                    return create_error_response(
                        message=f"父级机构ID '{org_create.parent_id}' 不存在",
                        error_type=ErrorType.VALIDATION_ERROR,
                        code=status.HTTP_400_BAD_REQUEST,
                        details=[{
                            "field": "parent_id",
                            "message": "父级机构不存在"
                        }]
                    )
            
            # 创建机构
            new_org = create_org(db, org_create)
            
            # 构建响应数据
            org_detail = OrgDetail(
                id=new_org.id,
                name=new_org.name,
                org_type=new_org.org_type,
                parent_id=new_org.parent_id,
                parent_name=new_org.parent_name,
                sort=new_org.sort,
                status=new_org.status
            )
            
            return create_success_response(
                code=status.HTTP_201_CREATED,
                message="机构创建成功",
                data=org_detail
            )
            
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "request_body",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        logger.error(f"创建机构失败: {str(e)}")
        return create_error_response(
            message=f"创建机构失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.put("/{org_id}", response_model=OrgResponse, summary="修改机构")
def update_org_info(
    org_id: str = Path(..., description="机构ID"),
    org_update: OrgUpdate = ...,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    修改机构信息
    
    参数:
    - org_id: 机构ID (路径参数)
    - name: 机构名称 (可选)
    - org_type: 机构类型 (可选)
    - parent_id: 父级机构ID (可选)
    - sort: 排序 (可选)
    
    返回:
    - 更新后的机构信息
    """
    try:
        try:
            # 验证父级机构是否存在
            if org_update.parent_id:
                parent_org = get_org(db, org_update.parent_id)
                if not parent_org:
                    return create_error_response(
                        message=f"父级机构ID '{org_update.parent_id}' 不存在",
                        error_type=ErrorType.VALIDATION_ERROR,
                        code=status.HTTP_400_BAD_REQUEST,
                        details=[{
                            "field": "parent_id",
                            "message": "父级机构不存在"
                        }]
                    )
                
                # 检查是否形成循环引用
                if org_id == org_update.parent_id:
                    return create_error_response(
                        message="父级机构不能是自身",
                        error_type=ErrorType.VALIDATION_ERROR,
                        code=status.HTTP_400_BAD_REQUEST,
                        details=[{
                            "field": "parent_id",
                            "message": "父级机构不能是自身"
                        }]
                    )
            
            # 更新机构
            updated_org = update_org(db, org_id, org_update)
            
            # 构建响应数据
            org_detail = OrgDetail(
                id=updated_org.id,
                name=updated_org.name,
                org_type=updated_org.org_type,
                parent_id=updated_org.parent_id,
                parent_name=updated_org.parent_name,
                sort=updated_org.sort,
                status=updated_org.status
            )
            
            return create_success_response(
                message="机构更新成功",
                data=org_detail
            )
            
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "request_body",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        logger.error(f"更新机构失败: {str(e)}")
        return create_error_response(
            message=f"更新机构失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        )


@router.delete("/{org_id}", summary="删除机构")
def remove_org(
    org_id: str = Path(..., description="机构ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """
    删除机构
    
    参数:
    - org_id: 机构ID (路径参数)
    
    返回:
    - 删除操作结果
    """
    try:
        try:
            # 检查机构是否存在
            org = get_org(db, org_id)
            if not org:
                return create_error_response(
                    message=f"找不到ID为'{org_id}'的机构",
                    error_type=ErrorType.NOT_FOUND,
                    code=status.HTTP_404_NOT_FOUND,
                    details=[{
                        "field": "org_id",
                        "message": "机构不存在"
                    }]
                )
            
            # 删除机构
            success = delete_org(db, org_id)
            
            if success:
                return create_success_response(
                    message="机构删除成功"
                )
            else:
                return create_error_response(
                    message="机构删除失败",
                    error_type=ErrorType.SERVER_ERROR,
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except ValueError as e:
            return create_error_response(
                message=str(e),
                error_type=ErrorType.VALIDATION_ERROR,
                code=status.HTTP_400_BAD_REQUEST,
                details=[{
                    "field": "request_body",
                    "message": str(e)
                }]
            )
            
    except Exception as e:
        logger.error(f"删除机构失败: {str(e)}")
        return create_error_response(
            message=f"删除机构失败: {str(e)}",
            error_type=ErrorType.SERVER_ERROR,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=[{
                "field": "system",
                "message": str(e)
            }]
        ) 