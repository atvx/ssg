#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Redis连接配置
用于提高Redis连接的稳定性和容错能力
"""

import os
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("redis_config")

def get_redis_connection_params() -> Dict[str, Any]:
    """
    从环境变量获取Redis连接参数
    """
    redis_url = os.environ.get("REDIS_URL", "")
    
    # 默认参数
    params = {
        "socket_timeout": int(os.environ.get("REDIS_SOCKET_TIMEOUT", 60)),
        "socket_connect_timeout": int(os.environ.get("REDIS_SOCKET_CONNECT_TIMEOUT", 30)),
        "socket_keepalive": os.environ.get("REDIS_SOCKET_KEEPALIVE", "True").lower() == "true",
        "retry_on_timeout": os.environ.get("REDIS_RETRY_ON_TIMEOUT", "True").lower() == "true",
        "max_connections": int(os.environ.get("REDIS_MAX_CONNECTIONS", 20)),
        "health_check_interval": 30,
    }
    
    # 记录参数设置
    logger.debug(f"Redis连接参数: {params}")
    
    return params

def get_redis_client(url: Optional[str] = None) -> Dict[str, Any]:
    """
    获取配置好的Redis客户端参数
    """
    redis_url = url or os.environ.get("REDIS_URL", "")
    if not redis_url:
        logger.error("未设置REDIS_URL环境变量")
        return {"url": ""}
    
    # 获取连接参数
    params = get_redis_connection_params()
    
    return {
        "url": redis_url,
        "socket_timeout": params["socket_timeout"],
        "socket_connect_timeout": params["socket_connect_timeout"],
        "socket_keepalive": params["socket_keepalive"],
        "retry_on_timeout": params["retry_on_timeout"],
        "max_connections": params["max_connections"],
        "health_check_interval": params["health_check_interval"],
    }

def get_celery_config() -> Dict[str, Any]:
    """
    获取Celery的Redis配置
    """
    broker_url = os.environ.get("CELERY_BROKER_URL", "")
    result_backend = os.environ.get("CELERY_RESULT_BACKEND", "")
    
    # Celery配置
    config = {
        "broker_url": broker_url,
        "result_backend": result_backend,
        "broker_connection_timeout": int(os.environ.get("CELERY_BROKER_CONNECTION_TIMEOUT", 60)),
        "broker_connection_max_retries": int(os.environ.get("CELERY_BROKER_CONNECTION_MAX_RETRIES", 10)), 
        "broker_heartbeat": int(os.environ.get("CELERY_BROKER_HEARTBEAT", 30)),
        "broker_pool_limit": int(os.environ.get("CELERY_BROKER_POOL_LIMIT", 10)),
        "result_expires": 86400,  # 结果保留1天
        "worker_max_tasks_per_child": 100,  # 每个worker子进程处理100个任务后重启
        "task_time_limit": int(os.environ.get("CELERY_TASK_TIME_LIMIT", 600)),
        "task_soft_time_limit": int(os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", 500)),
        "worker_hijack_root_logger": False,
        "worker_prefetch_multiplier": 1,  # 减少预取任务数量，避免任务堆积
        "task_acks_late": True,  # 任务完成后再确认
        "task_reject_on_worker_lost": True,  # worker丢失时拒绝任务
        "broker_transport_options": {
            "visibility_timeout": int(os.environ.get("CELERY_VISIBILITY_TIMEOUT", 43200)),  # 12小时
            "fanout_prefix": True,
            "fanout_patterns": True,
            "socket_timeout": int(os.environ.get("REDIS_SOCKET_TIMEOUT", 60)),
            "socket_connect_timeout": int(os.environ.get("REDIS_SOCKET_CONNECT_TIMEOUT", 30)),
        },
        "redis_max_connections": int(os.environ.get("REDIS_MAX_CONNECTIONS", 20)),
    }
    
    logger.debug(f"Celery配置: {config}")
    
    return config

if __name__ == "__main__":
    # 测试获取配置
    logger.setLevel(logging.INFO)
    redis_config = get_redis_client()
    celery_config = get_celery_config()
    
    print("Redis配置:")
    for key, value in redis_config.items():
        print(f"  {key}: {value}")
    
    print("\nCelery配置:")
    for key, value in celery_config.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}") 