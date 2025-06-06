#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Redis连接参数设置脚本
在容器启动时被执行，为Redis连接增加稳定性配置
"""

import os
import sys
import logging
import importlib.util
from pathlib import Path
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("redis_setup")

def patch_redis_client():
    """
    修补Redis客户端连接配置
    """
    from redis_config import get_redis_connection_params
    
    # 检查是否有redis客户端代码
    redis_client_files = [
        Path("/app/db/redis.py"),
        Path("/app/core/redis.py"),
        Path("/app/redis_client.py"),
    ]
    
    found = False
    for file_path in redis_client_files:
        if file_path.exists():
            # 读取文件内容
            content = file_path.read_text(encoding='utf-8')
            logger.info(f"找到Redis客户端文件: {file_path}")
            
            # 获取修改后的参数
            params = get_redis_connection_params()
            
            # 生成参数字符串
            param_str = ", ".join([f"{k}={repr(v)}" for k, v in params.items()])
            
            # 检查是否已包含参数配置
            if "socket_timeout" in content and "retry_on_timeout" in content:
                logger.info(f"Redis客户端已配置连接参数，跳过修改")
                found = True
                continue
                
            # 修改Redis连接
            # 1. 寻找 Redis.from_url 模式
            new_content = re.sub(
                r'redis\.Redis\.from_url\(\s*([^,\)]+)(\s*\))',
                rf'redis.Redis.from_url(\1, {param_str}\2',
                content
            )
            
            # 2. 寻找 redis.from_url 模式
            if new_content == content:
                new_content = re.sub(
                    r'from_url\(\s*([^,\)]+)(\s*\))',
                    rf'from_url(\1, {param_str}\2',
                    content
                )
            
            # 检查是否有修改
            if new_content != content:
                logger.info(f"正在更新Redis客户端配置: {file_path}")
                file_path.write_text(new_content, encoding='utf-8')
                logger.info(f"Redis客户端配置已更新")
                found = True
            else:
                logger.info(f"未找到匹配的Redis连接模式，无需修改: {file_path}")
    
    if not found:
        logger.warning("未找到Redis客户端文件，无法应用连接参数")
        
    return found

def patch_celery_config():
    """
    修补Celery配置
    """
    from redis_config import get_celery_config
    
    # 检查是否有celery配置文件
    celery_files = [
        Path("/app/celery_app.py"),
        Path("/app/core/celery_app.py"),
        Path("/app/celery_config.py"),
    ]
    
    found = False
    for file_path in celery_files:
        if file_path.exists():
            # 读取文件内容
            content = file_path.read_text(encoding='utf-8')
            logger.info(f"找到Celery配置文件: {file_path}")
            
            # 获取Celery配置
            config = get_celery_config()
            
            # 检查是否已配置
            if "broker_connection_timeout" in content and "broker_heartbeat" in content:
                logger.info(f"Celery已配置连接参数，跳过修改")
                found = True
                continue
                
            # 生成配置代码
            config_code = "# Redis连接增强配置\n"
            for key, value in config.items():
                if key not in ["broker_url", "result_backend"]:  # 跳过已有的基本配置
                    if isinstance(value, dict):
                        config_code += f"app.conf.{key} = {{\n"
                        for k, v in value.items():
                            config_code += f"    '{k}': {repr(v)},\n"
                        config_code += "}\n"
                    else:
                        config_code += f"app.conf.{key} = {repr(value)}\n"
            
            # 检查是否有应用对象
            if "app = Celery" in content:
                insert_point = content.find("app = Celery")
                insert_point = content.find("\n", insert_point) + 1
                
                new_content = content[:insert_point] + "\n" + config_code + content[insert_point:]
                
                # 保存修改
                logger.info(f"正在更新Celery配置: {file_path}")
                file_path.write_text(new_content, encoding='utf-8')
                logger.info(f"Celery配置已更新")
                found = True
            else:
                logger.info(f"未找到Celery应用对象，无法应用配置: {file_path}")
    
    if not found:
        logger.warning("未找到Celery配置文件，无法应用连接参数")
        
    return found

def main():
    """主函数"""
    try:
        logger.info("开始设置Redis连接参数...")
        
        # 确保redis_config可被导入
        if not Path("/app/redis_config.py").exists():
            # 尝试将当前目录的redis_config.py复制到应用目录
            current_dir = Path(__file__).parent
            if Path(current_dir, "redis_config.py").exists():
                import shutil
                shutil.copy(Path(current_dir, "redis_config.py"), "/app/redis_config.py")
                logger.info("已复制redis_config.py到应用目录")
            else:
                logger.error("找不到redis_config.py，无法继续")
                return 1
        
        # 添加应用目录到路径
        sys.path.insert(0, "/app")
        
        # 修补Redis客户端
        redis_patched = patch_redis_client()
        
        # 修补Celery配置
        celery_patched = patch_celery_config()
        
        if redis_patched or celery_patched:
            logger.info("Redis连接参数设置完成!")
        else:
            logger.warning("未应用任何Redis连接参数!")
            
        return 0
    except Exception as e:
        logger.error(f"设置过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())