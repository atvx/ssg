from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any
import logging
import json
import time
import asyncio

from .manager import connection_manager
from utils.redis_utils import VerificationManager

# 安全检查
security = HTTPBearer()

# WebSocket路由
router = APIRouter(prefix="/ws")
logger = logging.getLogger(__name__)

async def handle_websocket_connection(websocket: WebSocket, client_id: str, default_channels: List[str] = None):
    """统一的WebSocket连接处理函数"""
    if default_channels is None:
        default_channels = ["status"]
    
    await connection_manager.connect(websocket, client_id)
    
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket连接已建立",
            "client_id": client_id
        })
        
        # 设置默认订阅
        connection_manager.update_subscriptions(client_id, default_channels, replace=True)
        logger.info(f"客户端 {client_id} 已订阅频道: {default_channels}")
        
        while True:
            try:
                # 使用asyncio.wait_for添加超时检测，避免无限等待
                message = await asyncio.wait_for(
                    websocket.receive_text(), 
                    timeout=30.0  # 30秒超时
                )
                
                # 处理特殊的文本消息
                if message.strip().upper() == "PING":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": int(time.time() * 1000)
                    })
                    logger.debug(f"收到PING消息，已回复PONG")
                    continue
                
                try:
                    # 尝试解析为JSON
                    data = json.loads(message)
                    await handle_websocket_message(websocket, client_id, data)
                    
                except json.JSONDecodeError:
                    # 不是有效的JSON，发送错误消息
                    await safe_send_json(websocket, {
                        "type": "error",
                        "message": "消息必须是有效的JSON格式",
                        "received": message[:100] if len(message) > 100 else message
                    })
                    
            except asyncio.TimeoutError:
                # 超时，发送心跳检测
                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": int(time.time() * 1000)
                    })
                except:
                    # 如果心跳发送失败，说明连接已断开
                    logger.info(f"客户端 {client_id} 心跳发送失败，连接可能已断开")
                    break
                    
            except WebSocketDisconnect:
                # 正常断开连接
                logger.info(f"客户端 {client_id} 正常断开连接")
                break
                
            except Exception as e:
                # 检查是否是连接断开相关的错误
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in [
                    "disconnect", "closed", "cannot call receive", 
                    "connection closed", "websocket closed"
                ]):
                    logger.info(f"客户端 {client_id} 连接已断开: {e}")
                    break
                else:
                    logger.error(f"WebSocket处理时出现未知错误: {e}")
                    # 尝试发送错误消息，如果失败则断开连接
                    try:
                        await safe_send_json(websocket, {
                            "type": "error", 
                            "message": f"处理消息时出错"
                        })
                    except:
                        logger.info(f"无法发送错误消息给客户端 {client_id}，断开连接")
                        break
    
    except WebSocketDisconnect:
        logger.info(f"客户端 {client_id} 断开连接")
    except Exception as e:
        logger.error(f"WebSocket连接处理时出错: {e}")
    finally:
        # 确保清理连接
        connection_manager.disconnect(client_id)

async def safe_send_json(websocket: WebSocket, message: dict) -> bool:
    """安全发送JSON消息，避免在连接断开时抛出异常"""
    try:
        # 检查WebSocket状态
        if hasattr(websocket, 'client_state') and websocket.client_state.name != 'CONNECTED':
            return False
        await websocket.send_json(message)
        return True
    except Exception as e:
        logger.debug(f"发送消息失败: {e}")
        return False

async def handle_websocket_message(websocket: WebSocket, client_id: str, data: dict):
    """处理WebSocket消息"""
    message_type = data.get("type", "")
    
    if message_type == "subscribe":
        # 处理订阅请求
        channels = data.get("channels", [])
        replace = data.get("replace", False)
        
        if not channels:
            await safe_send_json(websocket, {
                "type": "error",
                "message": "未指定订阅频道"
            })
            return
        
        # 更新客户端订阅
        connection_manager.update_subscriptions(client_id, channels, replace=replace)
        
        # 获取当前所有订阅的频道
        current_channels = list(connection_manager.subscriptions.get(client_id, set()))
        
        await safe_send_json(websocket, {
            "type": "subscribed",
            "channels": current_channels,
            "message": "订阅成功"
        })
        logger.info(f"客户端 {client_id} 订阅成功: {current_channels}")
        
    elif message_type == "ping":
        # 处理ping消息
        await safe_send_json(websocket, {
            "type": "pong",
            "timestamp": data.get("timestamp", int(time.time() * 1000))
        })
        logger.debug(f"收到PING JSON消息，已回复PONG")
        
    elif message_type == "verification_code":
        # 处理验证码提交
        task_id = data.get("task_id")
        code = data.get("code")
        
        if not task_id or not code:
            await safe_send_json(websocket, {
                "type": "error",
                "message": "缺少任务ID或验证码"
            })
            return
        
        # 更新验证任务状态
        update_result = VerificationManager.update_verification_code(task_id, code)
        
        if update_result:
            await safe_send_json(websocket, {
                "type": "verification_received",
                "message": "验证码已接收",
                "task_id": task_id
            })
            logger.info(f"已接收客户端 {client_id} 提交的验证码，任务ID: {task_id}")
        else:
            await safe_send_json(websocket, {
                "type": "error",
                "message": "验证任务不存在或已过期",
                "task_id": task_id
            })
    else:
        await safe_send_json(websocket, {
            "type": "echo",
            "message": "未知消息类型",
            "data": data
        })

@router.websocket("")
async def websocket_root(websocket: WebSocket):
    """WebSocket根连接，用于兼容客户端直接连接/ws的情况"""
    client_id = websocket.headers.get("client-id", f"root-{id(websocket)}")
    await handle_websocket_connection(websocket, client_id, ["status"])

@router.websocket("/verification")
async def websocket_verification(websocket: WebSocket):
    """WebSocket连接，用于验证码管理"""
    client_id = websocket.headers.get("client-id", f"verification-{id(websocket)}")
    await handle_websocket_connection(websocket, client_id, ["verification"])

@router.websocket("/status")
async def websocket_status(websocket: WebSocket):
    """WebSocket连接，用于实时状态更新"""
    client_id = websocket.headers.get("client-id", f"status-{id(websocket)}")
    await handle_websocket_connection(websocket, client_id, ["status"]) 