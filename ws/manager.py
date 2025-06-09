from fastapi import WebSocket
from typing import Dict, List, Set, Any, Optional
import logging
import json
import threading
import asyncio
from utils.redis_utils import redis_client, REDIS_BROADCAST_CHANNEL
import redis
import time

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃连接，按客户端ID索引
        self.active_connections: Dict[str, WebSocket] = {}
        # 客户端订阅的频道
        self.subscriptions: Dict[str, Set[str]] = {}
        # 启动Redis订阅线程
        self._start_redis_subscriber()
    
    def _start_redis_subscriber(self):
        """启动Redis订阅监听线程"""
        def redis_listener():
            retry_count = 0
            max_retries = 5
            base_delay = 2  # 基础延迟时间(秒)
            max_delay = 60  # 最大延迟时间(秒)
            
            while True:  # 无限循环确保订阅不会中断
                pubsub = None
                try:
                    # 创建独立的Redis连接用于pubsub，避免连接池冲突
                    from config.settings import settings
                    pubsub_redis = redis.Redis.from_url(
                        settings.REDIS_URL,
                        decode_responses=True,
                        socket_timeout=None,  # pubsub不设置超时
                        socket_connect_timeout=10,
                        socket_keepalive=True,
                        socket_keepalive_options={"TCP_KEEPIDLE": 1, "TCP_KEEPINTVL": 3, "TCP_KEEPCNT": 5},
                        retry_on_timeout=True,
                        retry_on_error=[redis.exceptions.ConnectionError, redis.exceptions.TimeoutError]
                    )
                    
                    # 创建Redis发布/订阅对象
                    pubsub = pubsub_redis.pubsub(ignore_subscribe_messages=True)
                    # 订阅广播通道
                    pubsub.subscribe(REDIS_BROADCAST_CHANNEL)
                    logger.info(f"已订阅Redis通道: {REDIS_BROADCAST_CHANNEL}")
                    
                    # 重置重试计数器
                    retry_count = 0
                    
                    # 监听消息
                    for message in pubsub.listen():
                        try:
                            if message['type'] == 'message':
                                try:
                                    # 解析消息
                                    data = json.loads(message['data'])
                                    ws_channel = data.get('channel')
                                    ws_message = data.get('message')
                                    
                                    if ws_channel and ws_message:
                                        logger.info(f"收到Redis消息，将广播到WS频道 {ws_channel}: {ws_message}")
                                        # 创建异步事件循环来执行广播
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                        
                                        try:
                                            # 执行广播
                                            loop.run_until_complete(self.broadcast(ws_message, channel=ws_channel))
                                        except Exception as e:
                                            logger.error(f"处理Redis消息时出错: {str(e)}", exc_info=True)
                                        finally:
                                            loop.close()
                                except json.JSONDecodeError as e:
                                    logger.error(f"解析Redis消息JSON格式出错: {str(e)}, 原始消息: {message['data'][:100]}")
                        except Exception as e:
                            logger.error(f"处理Redis消息时出错: {str(e)}", exc_info=True)
                            
                except (redis.RedisError, redis.exceptions.TimeoutError, redis.exceptions.ConnectionError) as e:
                    retry_count += 1
                    # 计算指数退避延迟时间
                    delay = min(base_delay * (2 ** (retry_count - 1)), max_delay)
                    
                    logger.error(f"Redis连接出错 (重试次数: {retry_count}): {str(e)}")
                    
                    if retry_count <= max_retries:
                        logger.info(f"将在 {delay} 秒后重试Redis连接...")
                        time.sleep(delay)
                    else:
                        logger.error(f"Redis重连失败，已达到最大重试次数 {max_retries}，等待 {max_delay} 秒后重置重试计数器")
                        time.sleep(max_delay)
                        retry_count = 0  # 重置重试计数器
                        
                except Exception as e:
                    retry_count += 1
                    delay = min(base_delay * (2 ** (retry_count - 1)), max_delay)
                    
                    logger.error(f"Redis订阅线程异常 (重试次数: {retry_count}): {str(e)}", exc_info=True)
                    logger.info(f"将在 {delay} 秒后重试...")
                    time.sleep(delay)
                    
                finally:
                    # 确保pubsub连接被正确关闭
                    if pubsub:
                        try:
                            pubsub.close()
                        except Exception as e:
                            logger.error(f"关闭pubsub连接时出错: {e}")
        
        # 创建并启动Redis监听线程
        subscriber_thread = threading.Thread(target=redis_listener, daemon=True)
        subscriber_thread.start()
        logger.info("Redis订阅监听线程已启动")
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """
        建立WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
            client_id: 客户端ID
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        # 初始化空订阅集合
        self.subscriptions[client_id] = set()
        logger.info(f"WebSocket客户端 {client_id} 已连接，当前活跃连接数: {len(self.active_connections)}")
    
    def disconnect(self, client_id: str):
        """
        断开WebSocket连接
        
        Args:
            client_id: 客户端ID
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # 清理订阅
        if client_id in self.subscriptions:
            del self.subscriptions[client_id]
    
    def update_subscriptions(self, client_id: str, channels: List[str], replace: bool = False):
        """
        更新客户端订阅的频道
        
        Args:
            client_id: 客户端ID
            channels: 频道列表
            replace: 是否替换现有订阅，默认为False(添加到现有订阅)
        """
        if client_id in self.subscriptions:
            if replace:
                self.subscriptions[client_id] = set(channels)
            else:
                self.subscriptions[client_id].update(channels)
    
    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """
        向特定客户端发送消息
        
        Args:
            message: 消息内容
            client_id: 客户端ID
        """
        if client_id in self.active_connections:
            try:
                # 确保消息是字典格式
                if not isinstance(message, dict):
                    logger.warning(f"消息不是字典格式，尝试转换: {message}")
                    try:
                        if isinstance(message, str):
                            message = json.loads(message)
                        else:
                            message = {"data": message}
                    except Exception as e:
                        logger.error(f"消息格式转换失败: {e}")
                        message = {"type": "error", "message": "消息格式错误"}
                
                await self.active_connections[client_id].send_json(message)
                return True
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                return False
        return False
    
    async def broadcast(self, message: Dict[str, Any], channel: Optional[str] = None):
        """
        广播消息给所有客户端或特定频道的订阅者
        
        Args:
            message: 消息内容
            channel: 可选的频道名称
        """
        disconnected_clients = []
        sent_count = 0
        
        # 确保消息是字典格式
        if not isinstance(message, dict):
            logger.warning(f"广播消息不是字典格式，尝试转换: {message}")
            try:
                if isinstance(message, str):
                    message = json.loads(message)
                else:
                    message = {"data": message}
            except Exception as e:
                logger.error(f"广播消息格式转换失败: {e}")
                message = {"type": "error", "message": "消息格式错误"}
        
        # 记录广播开始
        if channel:
            logger.info(f"开始广播消息到频道 {channel}，活跃连接数: {len(self.active_connections)}")
        else:
            logger.info(f"开始广播消息到所有客户端，活跃连接数: {len(self.active_connections)}")
        
        for client_id, websocket in self.active_connections.items():
            # 如果指定了频道，只发送给订阅了该频道的客户端
            if channel and client_id in self.subscriptions:
                if channel not in self.subscriptions[client_id]:
                    logger.debug(f"客户端 {client_id} 未订阅频道 {channel}，跳过广播")
                    continue
                else:
                    logger.debug(f"客户端 {client_id} 已订阅频道 {channel}，准备广播")
            
            try:
                await websocket.send_json(message)
                sent_count += 1
                logger.debug(f"成功向客户端 {client_id} 发送消息")
            except Exception as e:
                logger.error(f"向客户端 {client_id} 广播消息失败: {e}")
                disconnected_clients.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)
            logger.info(f"已断开失效的客户端连接: {client_id}")
        
        # 记录广播结果
        logger.info(f"广播完成，成功发送给 {sent_count}/{len(self.active_connections)} 个客户端")
        
        return sent_count > 0  # 返回是否至少有一个客户端收到消息
    
    async def send_verification_notification(self, task_id: str, message: Dict[str, Any]):
        """
        发送验证通知
        
        Args:
            task_id: 验证任务ID
            message: 消息内容
        """
        logger.info(f"准备发送验证码通知，任务ID: {task_id}")
        
        # 确保消息是字典格式
        if not isinstance(message, dict):
            logger.warning(f"验证通知消息不是字典格式，尝试转换: {message}")
            try:
                if isinstance(message, str):
                    message = json.loads(message)
                else:
                    message = {
                        "type": "verification_needed",
                        "message": str(message)
                    }
            except Exception as e:
                logger.error(f"验证通知消息格式转换失败: {e}")
                message = {
                    "type": "verification_needed",
                    "message": "需要验证码"
                }
        
        # 添加任务ID到消息
        message["task_id"] = task_id
        
        # 检查verification频道的订阅者
        verification_subscribers = []
        for client_id, channels in self.subscriptions.items():
            if "verification" in channels:
                verification_subscribers.append(client_id)
        
        if not verification_subscribers:
            logger.warning(f"没有客户端订阅verification频道，通知可能无法送达")
        else:
            logger.info(f"找到 {len(verification_subscribers)} 个verification频道订阅者: {verification_subscribers}")
        
        # 广播到验证频道
        sent = await self.broadcast(message, channel="verification")
        
        if sent:
            logger.info(f"验证通知已成功广播到verification频道")
        else:
            logger.warning(f"验证通知广播可能失败，没有客户端收到消息")
        
        return sent


# 全局连接管理器实例
connection_manager = ConnectionManager() 