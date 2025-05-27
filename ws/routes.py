from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any
import logging
import json
import time

from .manager import connection_manager
from utils.redis_utils import VerificationManager

# 安全检查
security = HTTPBearer()

# WebSocket路由
router = APIRouter(prefix="/ws")
logger = logging.getLogger(__name__)

@router.websocket("")
async def websocket_root(websocket: WebSocket):
    """
    WebSocket根连接，用于兼容客户端直接连接/ws的情况
    默认转发到状态WebSocket
    """
    client_id = websocket.headers.get("client-id", f"root-{id(websocket)}")
    
    await connection_manager.connect(websocket, client_id)
    
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket连接已建立",
            "client_id": client_id
        })
        
        # 默认订阅状态频道
        connection_manager.update_subscriptions(client_id, ["status"], replace=True)
        
        while True:
            # 接收消息，先以文本方式接收
            try:
                message = await websocket.receive_text()
                
                # 处理特殊的文本消息
                if message.strip().upper() == "PING":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": int(time.time() * 1000)
                    })
                    logger.debug(f"收到PING文本消息，已回复PONG")
                    continue
                
                try:
                    # 尝试解析为JSON
                    data = json.loads(message)
                    
                    # 处理客户端传来的消息
                    message_type = data.get("type", "")
                    
                    if message_type == "subscribe":
                        # 处理订阅请求
                        channels = data.get("channels", [])
                        replace = data.get("replace", False)
                        
                        if not channels:
                            await websocket.send_json({
                                "type": "error",
                                "message": "未指定订阅频道"
                            })
                            continue
                        
                        # 更新客户端订阅
                        connection_manager.update_subscriptions(client_id, channels, replace=replace)
                        
                        # 获取当前所有订阅的频道
                        current_channels = list(connection_manager.subscriptions.get(client_id, set()))
                        
                        await websocket.send_json({
                            "type": "subscribed",
                            "channels": current_channels,
                            "message": "订阅成功"
                        })
                        logger.info(f"客户端 {client_id} 订阅成功: {current_channels}")
                    elif message_type == "ping":
                        # 处理ping消息
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": data.get("timestamp", int(time.time() * 1000))
                        })
                        logger.debug(f"收到PING JSON消息，已回复PONG")
                    else:
                        await websocket.send_json({
                            "type": "echo",
                            "message": "未知消息类型",
                            "data": data
                        })
                except json.JSONDecodeError:
                    # 不是有效的JSON，发送错误消息
                    await websocket.send_json({
                        "type": "error",
                        "message": "消息必须是有效的JSON格式",
                        "received": message[:100] if len(message) > 100 else message
                    })
            except Exception as e:
                # 接收消息时出错
                logger.error(f"接收WebSocket消息时出错: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"接收消息出错: {str(e)}"
                })
    
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
        logger.info(f"客户端 {client_id} 断开连接")
    except Exception as e:
        logger.error(f"根WebSocket处理时出错: {e}")
        connection_manager.disconnect(client_id)

@router.websocket("/verification")
async def websocket_verification(websocket: WebSocket):
    """
    WebSocket连接，用于验证码管理
    """
    client_id = websocket.headers.get("client-id", f"client-{id(websocket)}")
    
    await connection_manager.connect(websocket, client_id)
    
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": "验证码WebSocket连接已建立",
            "client_id": client_id
        })
        
        # 订阅验证频道
        connection_manager.update_subscriptions(client_id, ["verification"], replace=True)
        logger.info(f"客户端 {client_id} 已订阅verification频道")
        
        while True:
            # 接收消息，先以文本方式接收
            try:
                message = await websocket.receive_text()
                
                # 处理特殊的文本消息
                if message.strip().upper() == "PING":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": int(time.time() * 1000)
                    })
                    logger.debug(f"收到PING文本消息，已回复PONG")
                    continue
                
                try:
                    # 尝试解析为JSON
                    data = json.loads(message)
                    
                    # 处理客户端传来的消息
                    message_type = data.get("type", "")
                    
                    if message_type == "verification_code":
                        # 处理验证码提交
                        task_id = data.get("task_id")
                        code = data.get("code")
                        
                        if not task_id or not code:
                            await websocket.send_json({
                                "type": "error",
                                "message": "缺少任务ID或验证码"
                            })
                            continue
                        
                        # 更新验证任务状态
                        update_result = VerificationManager.update_verification_code(task_id, code)
                        
                        if update_result:
                            await websocket.send_json({
                                "type": "verification_received",
                                "message": "验证码已接收",
                                "task_id": task_id
                            })
                            logger.info(f"已接收客户端 {client_id} 提交的验证码，任务ID: {task_id}")
                        else:
                            await websocket.send_json({
                                "type": "error",
                                "message": "验证任务不存在或已过期",
                                "task_id": task_id
                            })
                    elif message_type == "ping":
                        # 处理ping消息
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": data.get("timestamp", int(time.time() * 1000))
                        })
                        logger.debug(f"收到PING JSON消息，已回复PONG")
                    else:
                        await websocket.send_json({
                            "type": "echo",
                            "message": "未知消息类型",
                            "data": data
                        })
                except json.JSONDecodeError:
                    # 不是有效的JSON，发送错误消息
                    await websocket.send_json({
                        "type": "error",
                        "message": "消息必须是有效的JSON格式",
                        "received": message[:100] if len(message) > 100 else message
                    })
            except Exception as e:
                # 接收消息时出错
                logger.error(f"接收WebSocket消息时出错: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"接收消息出错: {str(e)}"
                })
    
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
        logger.info(f"客户端 {client_id} 断开连接")
    except Exception as e:
        logger.error(f"WebSocket处理时出错: {e}")
        connection_manager.disconnect(client_id)

@router.websocket("/status")
async def websocket_status(websocket: WebSocket):
    """
    WebSocket连接，用于实时状态更新
    """
    client_id = websocket.headers.get("client-id", f"status-{id(websocket)}")
    
    await connection_manager.connect(websocket, client_id)
    
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": "状态WebSocket连接已建立",
            "client_id": client_id
        })
        
        # 默认订阅状态频道
        connection_manager.update_subscriptions(client_id, ["status"], replace=True)
        logger.info(f"客户端 {client_id} 已订阅status频道")
        
        while True:
            # 接收消息，先以文本方式接收
            try:
                message = await websocket.receive_text()
                
                # 处理特殊的文本消息
                if message.strip().upper() == "PING":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": int(time.time() * 1000)
                    })
                    logger.debug(f"收到PING文本消息，已回复PONG")
                    continue
                
                try:
                    # 尝试解析为JSON
                    data = json.loads(message)
                    
                    # 处理客户端传来的消息
                    message_type = data.get("type", "")
                    
                    if message_type == "subscribe":
                        # 处理订阅请求
                        channels = data.get("channels", [])
                        replace = data.get("replace", False)
                        
                        if not channels:
                            await websocket.send_json({
                                "type": "error",
                                "message": "未指定订阅频道"
                            })
                            continue
                        
                        # 更新客户端订阅
                        connection_manager.update_subscriptions(client_id, channels, replace=replace)
                        
                        # 获取当前所有订阅的频道
                        current_channels = list(connection_manager.subscriptions.get(client_id, set()))
                        
                        await websocket.send_json({
                            "type": "subscribed",
                            "channels": current_channels,
                            "message": "订阅成功"
                        })
                        logger.info(f"客户端 {client_id} 订阅成功: {current_channels}")
                    elif message_type == "ping":
                        # 处理ping消息
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": data.get("timestamp", int(time.time() * 1000))
                        })
                        logger.debug(f"收到PING JSON消息，已回复PONG")
                    else:
                        await websocket.send_json({
                            "type": "echo",
                            "message": "未知消息类型",
                            "data": data
                        })
                except json.JSONDecodeError:
                    # 不是有效的JSON，发送错误消息
                    await websocket.send_json({
                        "type": "error",
                        "message": "消息必须是有效的JSON格式",
                        "received": message[:100] if len(message) > 100 else message
                    })
            except Exception as e:
                # 接收消息时出错
                logger.error(f"接收WebSocket消息时出错: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"接收消息出错: {str(e)}"
                })
    
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
        logger.info(f"客户端 {client_id} 断开连接")
    except Exception as e:
        logger.error(f"状态WebSocket处理时出错: {e}")
        connection_manager.disconnect(client_id) 