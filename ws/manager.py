from fastapi import WebSocket
from typing import Dict, List, Set, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃连接，按客户端ID索引
        self.active_connections: Dict[str, WebSocket] = {}
        # 客户端订阅的频道
        self.subscriptions: Dict[str, Set[str]] = {}
    
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
    
    def update_subscriptions(self, client_id: str, channels: List[str]):
        """
        更新客户端订阅的频道
        
        Args:
            client_id: 客户端ID
            channels: 频道列表
        """
        if client_id in self.subscriptions:
            self.subscriptions[client_id] = set(channels)
    
    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """
        向特定客户端发送消息
        
        Args:
            message: 消息内容
            client_id: 客户端ID
        """
        if client_id in self.active_connections:
            try:
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
        
        for client_id, websocket in self.active_connections.items():
            # 如果指定了频道，只发送给订阅了该频道的客户端
            if channel and client_id in self.subscriptions:
                if channel not in self.subscriptions[client_id]:
                    continue
            
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"向客户端 {client_id} 广播消息失败: {e}")
                disconnected_clients.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def send_verification_notification(self, task_id: str, message: Dict[str, Any]):
        """
        发送验证通知
        
        Args:
            task_id: 验证任务ID
            message: 消息内容
        """
        # 添加任务ID到消息
        message["task_id"] = task_id
        
        # 广播到验证频道
        await self.broadcast(message, channel="verification")


# 全局连接管理器实例
connection_manager = ConnectionManager() 