#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Redis连接配置脚本 - 用于Docker环境中的Redis连接优化
"""

import os
import logging
import sys
import socket
import time
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("redis_setup")

def parse_redis_url():
    """解析Redis URL并返回连接信息"""
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        logger.warning("未设置REDIS_URL环境变量")
        return None
    
    try:
        # 解析URL
        parsed = urlparse(redis_url)
        
        # 提取主机和端口
        host = parsed.hostname
        port = parsed.port or 6379
        
        # 提取密码
        if parsed.password:
            password = parsed.password
        elif '@' in redis_url:
            # 处理格式如 redis://:password@host:port/db 的URL
            auth_part = redis_url.split('@')[0].split('//')[-1]
            if ':' in auth_part:
                password = auth_part.split(':')[-1]
            else:
                password = None
        else:
            password = None
        
        # 提取数据库编号
        db = 0
        if parsed.path:
            try:
                db = int(parsed.path.strip('/'))
            except (ValueError, TypeError):
                pass
        
        return {
            'host': host,
            'port': port,
            'password': password,
            'db': db
        }
    except Exception as e:
        logger.error(f"解析Redis URL时出错: {e}")
        return None

def test_redis_connection(host, port, max_retries=3, timeout=5):
    """测试Redis连接是否可用"""
    for attempt in range(max_retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                logger.info(f"Redis连接成功: {host}:{port}")
                return True
            else:
                logger.warning(f"Redis连接失败 (尝试 {attempt+1}/{max_retries}): {host}:{port}")
        except Exception as e:
            logger.warning(f"测试Redis连接时出错 (尝试 {attempt+1}/{max_retries}): {e}")
        
        if attempt < max_retries - 1:
            time.sleep(2)
    
    logger.error(f"无法连接到Redis服务器: {host}:{port}")
    return False

def setup_redis_env():
    """配置Redis环境变量，以提高连接稳定性"""
    logger.info("设置Redis连接参数...")
    
    # 设置Redis连接参数的默认值
    params = {
        "REDIS_SOCKET_TIMEOUT": "60",
        "REDIS_SOCKET_CONNECT_TIMEOUT": "30",
        "REDIS_SOCKET_KEEPALIVE": "True",
        "REDIS_RETRY_ON_TIMEOUT": "True",
        "REDIS_MAX_CONNECTIONS": "20",
        "CELERY_BROKER_CONNECTION_TIMEOUT": "60",
        "CELERY_BROKER_CONNECTION_MAX_RETRIES": "10",
        "CELERY_BROKER_HEARTBEAT": "30",
        "CELERY_BROKER_POOL_LIMIT": "10",
        "CELERY_VISIBILITY_TIMEOUT": "43200"
    }
    
    # 应用默认参数
    for key, value in params.items():
        os.environ.setdefault(key, value)
    
    # 获取Redis连接信息
    redis_info = parse_redis_url()
    if redis_info:
        logger.info(f"Redis服务器: {redis_info['host']}:{redis_info['port']}, 数据库: {redis_info['db']}")
        
        # 测试连接
        test_redis_connection(redis_info['host'], redis_info['port'])
    
    logger.info("Redis连接参数设置完成")

def configure_redis_client():
    """配置Redis客户端选项，以提高稳定性"""
    # 这些建议将在日志中输出，应用程序代码中需要使用这些配置
    recommendations = [
        "connection_pool=redis.BlockingConnectionPool(max_connections=20, timeout=30)",
        "socket_timeout=60",
        "socket_connect_timeout=30",
        "retry_on_timeout=True",
        "health_check_interval=30"
    ]
    
    logger.info("推荐的Redis客户端配置:")
    for rec in recommendations:
        logger.info(f" - {rec}")

def main():
    """主函数"""
    try:
        logger.info("开始初始化Redis环境...")
        setup_redis_env()
        configure_redis_client()
        logger.info("Redis环境初始化完成!")
        return 0
    except Exception as e:
        logger.error(f"初始化过程中发生错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())