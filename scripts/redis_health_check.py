#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis连接健康检查脚本
用于诊断和监控Redis连接状态
"""

import redis
import time
import logging
import json
from datetime import datetime
from typing import Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedisHealthChecker:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client = None
        
    def connect(self) -> bool:
        """连接到Redis"""
        try:
            self.client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=5,
                socket_keepalive=True,
                retry_on_timeout=True
            )
            # 测试连接
            self.client.ping()
            logger.info("✅ Redis连接成功")
            return True
        except Exception as e:
            logger.error(f"❌ Redis连接失败: {e}")
            return False
    
    def check_connection_info(self) -> Dict[str, Any]:
        """检查连接信息"""
        if not self.client:
            return {"error": "未连接到Redis"}
        
        try:
            info = self.client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "Unknown"),
                "redis_version": info.get("redis_version", "Unknown"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def test_pubsub(self, channel: str = "test_channel", timeout: int = 5) -> bool:
        """测试发布订阅功能"""
        if not self.client:
            logger.error("未连接到Redis")
            return False
        
        try:
            pubsub = self.client.pubsub()
            pubsub.subscribe(channel)
            
            # 发送测试消息
            test_message = {"test": True, "timestamp": datetime.now().isoformat()}
            self.client.publish(channel, json.dumps(test_message))
            
            # 等待消息
            message = pubsub.get_message(timeout=timeout)
            if message and message['type'] == 'subscribe':
                # 跳过订阅确认消息，获取实际消息
                message = pubsub.get_message(timeout=timeout)
            
            if message and message['type'] == 'message':
                received_data = json.loads(message['data'])
                if received_data.get('test'):
                    logger.info("✅ PubSub测试成功")
                    return True
            
            logger.warning("⚠️ PubSub测试超时或消息不匹配")
            return False
            
        except Exception as e:
            logger.error(f"❌ PubSub测试失败: {e}")
            return False
        finally:
            try:
                pubsub.close()
            except:
                pass
    
    def test_set_get(self) -> bool:
        """测试基础读写操作"""
        if not self.client:
            logger.error("未连接到Redis")
            return False
        
        try:
            test_key = f"health_check_{int(time.time())}"
            test_value = "test_value"
            
            # 写入
            self.client.set(test_key, test_value, ex=60)  # 60秒过期
            
            # 读取
            retrieved_value = self.client.get(test_key)
            
            # 清理
            self.client.delete(test_key)
            
            if retrieved_value == test_value:
                logger.info("✅ 基础读写测试成功")
                return True
            else:
                logger.error("❌ 读写测试失败：值不匹配")
                return False
                
        except Exception as e:
            logger.error(f"❌ 读写测试失败: {e}")
            return False
    
    def monitor_connection(self, duration: int = 60, interval: int = 5):
        """监控连接状态"""
        logger.info(f"开始监控Redis连接，持续{duration}秒，间隔{interval}秒")
        
        start_time = time.time()
        failed_checks = 0
        total_checks = 0
        
        while time.time() - start_time < duration:
            total_checks += 1
            
            try:
                # 发送ping命令
                response_time = time.time()
                result = self.client.ping()
                response_time = (time.time() - response_time) * 1000  # 转换为毫秒
                
                if result:
                    logger.info(f"📊 Ping成功，响应时间: {response_time:.2f}ms")
                else:
                    failed_checks += 1
                    logger.warning("⚠️ Ping失败")
                    
            except Exception as e:
                failed_checks += 1
                logger.error(f"❌ 连接检查失败: {e}")
            
            time.sleep(interval)
        
        success_rate = ((total_checks - failed_checks) / total_checks) * 100
        logger.info(f"📈 监控完成：成功率 {success_rate:.1f}% ({total_checks - failed_checks}/{total_checks})")
        
        return success_rate > 95  # 95%以上成功率认为健康
    
    def full_health_check(self) -> Dict[str, Any]:
        """完整健康检查"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "connection": False,
            "basic_operations": False,
            "pubsub": False,
            "connection_info": {},
            "overall_health": False
        }
        
        # 连接测试
        if self.connect():
            results["connection"] = True
            
            # 获取连接信息
            results["connection_info"] = self.check_connection_info()
            
            # 基础操作测试
            results["basic_operations"] = self.test_set_get()
            
            # PubSub测试
            results["pubsub"] = self.test_pubsub()
            
            # 整体健康状态
            results["overall_health"] = all([
                results["connection"],
                results["basic_operations"],
                results["pubsub"]
            ])
        
        return results


def main():
    """主函数"""
    import os
    
    # 从环境变量获取Redis URL
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    
    print(f"🔍 Redis健康检查")
    print(f"Redis URL: {redis_url}")
    print("=" * 50)
    
    checker = RedisHealthChecker(redis_url)
    
    # 执行完整健康检查
    results = checker.full_health_check()
    
    # 输出结果
    print("\n📋 健康检查结果:")
    print(f"连接状态: {'✅' if results['connection'] else '❌'}")
    print(f"基础操作: {'✅' if results['basic_operations'] else '❌'}")
    print(f"发布订阅: {'✅' if results['pubsub'] else '❌'}")
    print(f"整体健康: {'✅' if results['overall_health'] else '❌'}")
    
    if results["connection_info"]:
        info = results["connection_info"]
        if "error" not in info:
            print(f"\n📊 Redis信息:")
            print(f"连接客户端数: {info.get('connected_clients', 'N/A')}")
            print(f"内存使用: {info.get('used_memory_human', 'N/A')}")
            print(f"Redis版本: {info.get('redis_version', 'N/A')}")
            print(f"运行时间: {info.get('uptime_in_seconds', 0)} 秒")
    
    # 可选：连续监控
    if "--monitor" in os.sys.argv:
        checker.monitor_connection(duration=300, interval=10)  # 监控5分钟
    
    return 0 if results["overall_health"] else 1


if __name__ == "__main__":
    exit(main()) 