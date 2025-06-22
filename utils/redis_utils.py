import redis
import json
import uuid
import time
import socket
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from redis import ConnectionPool
from config.settings import settings

# 构建socket_keepalive_options，检查系统支持
keepalive_options = {}
try:
    if hasattr(socket, 'TCP_KEEPIDLE'):
        keepalive_options[socket.TCP_KEEPIDLE] = 1
    if hasattr(socket, 'TCP_KEEPINTVL'):
        keepalive_options[socket.TCP_KEEPINTVL] = 3
    if hasattr(socket, 'TCP_KEEPCNT'):
        keepalive_options[socket.TCP_KEEPCNT] = 5
except AttributeError:
    pass  # 当前系统不支持TCP keep-alive选项

# Redis连接池配置
REDIS_POOL = ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,  # 自动解码为字符串
    max_connections=20,     # 增加最大连接数
    socket_timeout=60,      # 增加socket超时时间到60秒
    socket_connect_timeout=10,  # 增加连接超时时间到10秒
    socket_keepalive=True,    # 保持连接
    socket_keepalive_options=keepalive_options if keepalive_options else None,  # TCP保活参数
    health_check_interval=60,  # 健康检查间隔改为60秒
    retry_on_timeout=True,    # 超时时重试
    retry_on_error=[redis.exceptions.ConnectionError, redis.exceptions.TimeoutError]  # 连接和超时错误时重试
)

# Redis客户端
redis_client = redis.Redis(
    connection_pool=REDIS_POOL,
    retry_on_timeout=True,
    socket_keepalive=True
)

# 用于广播的Redis发布/订阅通道
REDIS_BROADCAST_CHANNEL = "ws_broadcast"

def publish_ws_message(channel: str, message: dict) -> bool:
    """
    通过Redis发布WebSocket消息，用于跨进程通信
    
    Args:
        channel: WebSocket频道名称
        message: 要广播的消息
    
    Returns:
        bool: 发布成功返回True，否则返回False
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        payload = {
            "channel": channel,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        json_payload = json.dumps(payload)
        logger.info(f"发布WebSocket消息到Redis: 频道={channel}, 消息类型={message.get('type', 'unknown')}")
        redis_client.publish(REDIS_BROADCAST_CHANNEL, json_payload)
        return True
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Redis发布消息失败: {e}", exc_info=True)
        return False


class VerificationManager:
    """验证码任务管理器"""
    
    # 验证任务前缀
    VERIFICATION_PREFIX = "verification:"
    # 验证任务过期时间（秒）
    VERIFICATION_TIMEOUT = 300  # 5分钟
    
    @classmethod
    def create_verification_task(cls, task_data: Dict[str, Any]) -> str:
        """
        创建验证任务
        
        Args:
            task_data: 任务数据
            
        Returns:
            str: 任务ID
        """
        # 生成唯一任务ID
        task_id = str(uuid.uuid4())
        
        # 添加创建时间
        task_data["created_at"] = datetime.now().isoformat()
        
        # 保存任务数据到Redis
        redis_key = f"{cls.VERIFICATION_PREFIX}{task_id}"
        redis_client.set(redis_key, json.dumps(task_data), ex=cls.VERIFICATION_TIMEOUT)
        
        return task_id
    
    @classmethod
    def get_verification_task(cls, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取验证任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict[str, Any]]: 任务数据，不存在则返回None
        """
        redis_key = f"{cls.VERIFICATION_PREFIX}{task_id}"
        task_json = redis_client.get(redis_key)
        
        if not task_json:
            return None
        
        return json.loads(task_json)
    
    @classmethod
    def update_verification_status(cls, task_id: str, update_data: Dict[str, Any]) -> bool:
        """
        更新验证任务状态
        
        Args:
            task_id: 任务ID
            update_data: 更新数据
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        redis_key = f"{cls.VERIFICATION_PREFIX}{task_id}"
        task_json = redis_client.get(redis_key)
        
        if not task_json:
            return False
        
        task_data = json.loads(task_json)
        # 更新任务数据
        task_data.update(update_data)
        # 添加更新时间
        task_data["updated_at"] = datetime.now().isoformat()
        
        # 重新保存到Redis
        redis_client.set(redis_key, json.dumps(task_data), ex=cls.VERIFICATION_TIMEOUT)
        
        return True
    
    @classmethod
    def update_verification_code(cls, task_id: str, code: str) -> bool:
        """
        更新验证码
        
        Args:
            task_id: 任务ID
            code: 验证码
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        return cls.update_verification_status(task_id, {
            "code": code,
            "status": "completed"
        })
    
    @classmethod
    def get_verification_code(cls, task_id: str) -> Optional[str]:
        """
        获取验证码
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[str]: 验证码，不存在则返回None
        """
        task_data = cls.get_verification_task(task_id)
        
        if not task_data or task_data.get("status") != "completed":
            return None
        
        return task_data.get("code")
    
    @classmethod
    def submit_verification_code(cls, task_id: str, code: str) -> bool:
        """
        提交验证码
        
        Args:
            task_id: 任务ID
            code: 验证码
            
        Returns:
            bool: 更新成功返回True，否则返回False
        """
        return cls.update_verification_code(task_id, code)
    
    @classmethod
    def remove_verification_task(cls, task_id: str) -> bool:
        """
        删除验证任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 删除成功返回True，否则返回False
        """
        redis_key = f"{cls.VERIFICATION_PREFIX}{task_id}"
        return bool(redis_client.delete(redis_key))
    
    @classmethod
    def get_pending_verification_tasks(cls) -> List[Dict[str, Any]]:
        """
        获取所有待处理的验证任务
        
        Returns:
            List[Dict[str, Any]]: 待处理任务列表
        """
        # 获取所有验证任务的键
        pattern = f"{cls.VERIFICATION_PREFIX}*"
        keys = redis_client.keys(pattern)
        
        # 过滤待处理的任务
        pending_tasks = []
        
        for key in keys:
            task_json = redis_client.get(key)
            if not task_json:
                continue
            
            task_data = json.loads(task_json)
            if task_data.get("status") == "pending":
                # 提取任务ID
                task_id = key.replace(cls.VERIFICATION_PREFIX, "")
                task_data["task_id"] = task_id
                pending_tasks.append(task_data)
        
        return pending_tasks 