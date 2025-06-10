import redis
import json
import uuid
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from redis import ConnectionPool
from config.settings import settings
import logging
import backoff

logger = logging.getLogger(__name__)

# 读取环境变量中的Redis连接参数，提供默认值
REDIS_SOCKET_TIMEOUT = int(getattr(settings, "REDIS_SOCKET_TIMEOUT", 60))
REDIS_SOCKET_CONNECT_TIMEOUT = int(getattr(settings, "REDIS_SOCKET_CONNECT_TIMEOUT", 30))
REDIS_MAX_CONNECTIONS = int(getattr(settings, "REDIS_MAX_CONNECTIONS", 20))
REDIS_HEALTH_CHECK_INTERVAL = 15  # 更频繁的健康检查

# Redis连接池配置
REDIS_POOL = ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,  # 自动解码为字符串
    max_connections=REDIS_MAX_CONNECTIONS,  # 增加最大连接数
    socket_timeout=REDIS_SOCKET_TIMEOUT,  # 增加socket超时时间
    socket_connect_timeout=REDIS_SOCKET_CONNECT_TIMEOUT,  # 增加连接超时时间
    socket_keepalive=True,  # 保持连接
    health_check_interval=REDIS_HEALTH_CHECK_INTERVAL,  # 健康检查间隔
    retry_on_timeout=True,  # 超时时重试
    retry_on_error=[redis.exceptions.ConnectionError, redis.exceptions.TimeoutError]  # 增加重试的错误类型
)

# 创建Redis客户端类，增加重试机制
class RetryingRedis(redis.Redis):
    """带有自动重试机制的Redis客户端"""
    
    @backoff.on_exception(
        backoff.expo,
        (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError),
        max_tries=5,  # 最多重试5次
        max_time=30,  # 最长重试30秒
        jitter=backoff.full_jitter  # 使用抖动算法避免重试风暴
    )
    def execute_command(self, *args, **kwargs):
        """重写执行命令方法，增加重试机制"""
        try:
            return super().execute_command(*args, **kwargs)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
            logger.warning(f"Redis执行命令出错，准备重试: {e}")
            # 尝试重新连接
            self.connection_pool.reset()
            raise  # 重新抛出异常触发重试机制
    
    def safe_publish(self, channel, message, max_retries=3):
        """安全的发布消息方法，包含重试和错误处理"""
        for attempt in range(max_retries):
            try:
                return self.publish(channel, message)
            except redis.RedisError as e:
                logger.error(f"Redis发布消息失败(尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))  # 指数退避
                    continue
                return 0  # 所有重试都失败
    
    def safe_get(self, key, default=None, max_retries=3):
        """安全的获取值方法，包含重试和错误处理"""
        for attempt in range(max_retries):
            try:
                value = self.get(key)
                return value if value is not None else default
            except redis.RedisError as e:
                logger.error(f"Redis获取值失败(尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))  # 指数退避
                    continue
                return default  # 所有重试都失败

# Redis客户端
redis_client = RetryingRedis(
    connection_pool=REDIS_POOL,
    retry_on_timeout=True,
    socket_keepalive=True,
    health_check_interval=REDIS_HEALTH_CHECK_INTERVAL
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
        payload = {
            "channel": channel,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        json_payload = json.dumps(payload)
        logger.info(f"发布WebSocket消息到Redis: 频道={channel}, 消息类型={message.get('type', 'unknown')}")
        
        # 使用安全发布方法
        result = redis_client.safe_publish(REDIS_BROADCAST_CHANNEL, json_payload)
        return result > 0
    except Exception as e:
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
        try:
            redis_client.set(redis_key, json.dumps(task_data), ex=cls.VERIFICATION_TIMEOUT)
        except redis.RedisError as e:
            logger.error(f"创建验证任务时Redis错误: {e}")
        
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
        task_json = redis_client.safe_get(redis_key)
        
        if not task_json:
            return None
        
        try:
            return json.loads(task_json)
        except json.JSONDecodeError:
            logger.error(f"验证任务数据格式错误: {task_json}")
            return None
    
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
        task_json = redis_client.safe_get(redis_key)
        
        if not task_json:
            return False
        
        try:
            task_data = json.loads(task_json)
            # 更新任务数据
            task_data.update(update_data)
            # 添加更新时间
            task_data["updated_at"] = datetime.now().isoformat()
            
            # 重新保存到Redis
            redis_client.set(redis_key, json.dumps(task_data), ex=cls.VERIFICATION_TIMEOUT)
            return True
        except (json.JSONDecodeError, redis.RedisError) as e:
            logger.error(f"更新验证任务状态失败: {e}")
            return False
    
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
            "status": "completed",
            "completed_at": datetime.now().isoformat()
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
        try:
            return bool(redis_client.delete(redis_key))
        except redis.RedisError as e:
            logger.error(f"删除验证任务失败: {e}")
            return False
    
    @classmethod
    def get_pending_verification_tasks(cls) -> List[Dict[str, Any]]:
        """
        获取所有待处理的验证任务
        
        Returns:
            List[Dict[str, Any]]: 待处理任务列表
        """
        # 获取所有验证任务的键
        pattern = f"{cls.VERIFICATION_PREFIX}*"
        try:
            keys = redis_client.keys(pattern)
        except redis.RedisError as e:
            logger.error(f"获取验证任务键失败: {e}")
            return []
        
        # 过滤待处理的任务
        pending_tasks = []
        
        for key in keys:
            try:
                task_json = redis_client.get(key)
                if not task_json:
                    continue
                
                task_data = json.loads(task_json)
                if task_data.get("status") == "pending":
                    # 提取任务ID
                    task_id = key.replace(cls.VERIFICATION_PREFIX, "")
                    task_data["task_id"] = task_id
                    pending_tasks.append(task_data)
            except (redis.RedisError, json.JSONDecodeError) as e:
                logger.error(f"获取验证任务数据失败: {e}")
                continue
        
        return pending_tasks 