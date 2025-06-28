#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket修复验证测试
"""
import asyncio
import websockets
import json
import time
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_connection():
    """测试WebSocket连接和断开处理"""
    uri = "ws://localhost:8000/ws"
    
    try:
        logger.info("正在连接WebSocket...")
        async with websockets.connect(uri) as websocket:
            logger.info("WebSocket连接成功")
            
            # 发送ping消息
            await websocket.send("PING")
            response = await websocket.recv()
            logger.info(f"收到响应: {response}")
            
            # 发送JSON消息
            test_message = {
                "type": "subscribe",
                "channels": ["status", "verification"]
            }
            await websocket.send(json.dumps(test_message))
            response = await websocket.recv()
            logger.info(f"订阅响应: {response}")
            
            # 等待一段时间
            await asyncio.sleep(2)
            
            logger.info("正在关闭连接...")
            await websocket.close()
            logger.info("连接已正常关闭")
            
    except Exception as e:
        logger.error(f"WebSocket测试失败: {e}")

async def test_multiple_connections():
    """测试多个连接同时断开的情况"""
    tasks = []
    
    for i in range(5):
        task = asyncio.create_task(test_single_connection(f"client-{i}"))
        tasks.append(task)
    
    # 同时运行所有连接
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("多连接测试完成")

async def test_single_connection(client_id):
    """单个连接测试"""
    uri = f"ws://localhost:8000/ws/status"
    
    try:
        async with websockets.connect(uri, extra_headers={"client-id": client_id}) as websocket:
            logger.info(f"客户端 {client_id} 连接成功")
            
            # 发送几条消息
            for i in range(3):
                await websocket.send(json.dumps({
                    "type": "ping",
                    "timestamp": int(time.time() * 1000)
                }))
                response = await websocket.recv()
                logger.info(f"客户端 {client_id} 收到: {json.loads(response)['type']}")
                await asyncio.sleep(0.5)
            
            logger.info(f"客户端 {client_id} 测试完成")
            
    except Exception as e:
        logger.error(f"客户端 {client_id} 测试失败: {e}")

if __name__ == "__main__":
    logger.info("开始WebSocket修复验证测试")
    
    try:
        # 测试单个连接
        asyncio.run(test_websocket_connection())
        
        # 测试多个连接
        asyncio.run(test_multiple_connections())
        
        logger.info("所有测试完成")
        
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试执行失败: {e}")

"""
使用方法:
1. 启动服务器: python main.py
2. 在另一个终端运行: python test_websocket_fix.py

预期结果:
- 连接应该能正常建立和关闭
- 不应该出现重复的错误消息
- 日志应该显示连接状态变化但不会spam错误信息
""" 