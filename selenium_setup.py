#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Selenium和Redis配置初始化脚本
用于设置浏览器环境和增强Redis连接的可靠性
"""

import os
import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("selenium_setup")

def setup_redis_env():
    """配置Redis环境变量，以提高连接稳定性"""
    logger.info("设置Redis连接参数...")
    
    # 从环境变量中读取Redis配置
    redis_url = os.environ.get("REDIS_URL", "")
    
    # 设置Redis连接参数的默认值
    os.environ.setdefault("REDIS_SOCKET_TIMEOUT", "60")
    os.environ.setdefault("REDIS_SOCKET_CONNECT_TIMEOUT", "30")
    os.environ.setdefault("REDIS_SOCKET_KEEPALIVE", "True")
    os.environ.setdefault("REDIS_RETRY_ON_TIMEOUT", "True")
    os.environ.setdefault("REDIS_MAX_CONNECTIONS", "20")
    
    # 设置Celery连接参数的默认值
    os.environ.setdefault("CELERY_BROKER_CONNECTION_TIMEOUT", "60")
    os.environ.setdefault("CELERY_BROKER_CONNECTION_MAX_RETRIES", "10")
    os.environ.setdefault("CELERY_BROKER_HEARTBEAT", "30")
    os.environ.setdefault("CELERY_BROKER_POOL_LIMIT", "10")
    os.environ.setdefault("CELERY_VISIBILITY_TIMEOUT", "43200")
    
    logger.info(f"Redis连接URL: {redis_url.split('@')[-1].split('/')[0] if redis_url else '未设置'}")
    logger.info(f"Redis连接超时: {os.environ.get('REDIS_SOCKET_TIMEOUT')}秒")
    logger.info(f"Redis连接重试: {os.environ.get('REDIS_RETRY_ON_TIMEOUT')}")
    logger.info("Redis连接参数设置完成")

def setup_selenium_env():
    """配置Selenium环境变量"""
    logger.info("设置Selenium环境...")
    
    # 创建Chrome用户数据目录
    chrome_user_data_dir = Path("/app/chrome_user_data")
    chrome_user_data_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(str(chrome_user_data_dir), 0o777)
    
    # 创建临时目录
    chrome_tmp_dir = Path("/tmp/chrome_tmp")
    chrome_tmp_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(str(chrome_tmp_dir), 0o777)
    
    # 设置Selenium相关环境变量
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    os.environ.setdefault("SE_OPTS", "--disable-dev-shm-usage")
    os.environ.setdefault("WDM_LOG_LEVEL", "0")
    os.environ.setdefault("WDM_SSL_VERIFY", "0")
    
    # 设置Chrome运行参数
    chrome_options = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--headless=new",
        "--disable-software-rasterizer",
        "--remote-debugging-port=9222",
        "--disable-extensions",
        "--disable-dev-tools",
        "--window-size=1920,1080",
        "--single-process",
        "--disable-background-networking",
        "--ignore-certificate-errors",
        "--disable-infobars",
        "--user-data-dir=/app/chrome_user_data",
        "--disk-cache-dir=/tmp/chrome_tmp"
    ]
    
    os.environ["CHROME_OPTIONS"] = " ".join(chrome_options)
    logger.info("Selenium环境设置完成")

def main():
    """主函数"""
    try:
        logger.info("开始初始化环境...")
        setup_redis_env()
        setup_selenium_env()
        logger.info("环境初始化完成!")
        return 0
    except Exception as e:
        logger.error(f"初始化过程中发生错误: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 