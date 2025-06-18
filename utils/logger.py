import logging
import sys
import os
from logging.handlers import RotatingFileHandler
import time
from functools import wraps

# 配置日志格式
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.INFO
LOG_DIRECTORY = 'logs'

# 确保日志目录存在
if not os.path.exists(LOG_DIRECTORY):
    os.makedirs(LOG_DIRECTORY)

# 为不同模块配置日志
def setup_logger(name, log_file, level=LOG_LEVEL):
    """设置一个日志记录器"""
    handler = RotatingFileHandler(
        os.path.join(LOG_DIRECTORY, log_file),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    
    # 同时将日志输出到控制台
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)
    
    return logger

# 设置通用日志
general_logger = setup_logger('general', 'general.log')
api_logger = setup_logger('api', 'api.log')
db_logger = setup_logger('db', 'database.log')
auth_logger = setup_logger('auth', 'auth.log')
task_logger = setup_logger('task', 'tasks.log')

def log_function_call(logger):
    """装饰器：记录函数调用的开始和结束"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger.info(f"开始执行函数: {func.__name__}")
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                execution_time = end_time - start_time
                logger.info(f"函数 {func.__name__} 执行完成，耗时: {execution_time:.4f}秒")
                return result
            except Exception as e:
                end_time = time.time()
                execution_time = end_time - start_time
                logger.error(f"函数 {func.__name__} 执行失败，耗时: {execution_time:.4f}秒，错误: {str(e)}")
                raise
        return wrapper
    return decorator

# 以下是数据库连接池监控功能，保留代码但默认不启用
# 如果需要监控数据库连接池，可以手动导入并调用这些函数

def monitor_db_pool(engine, interval=60):
    """定期记录数据库连接池状态"""
    import threading
    
    def log_pool_status():
        while True:
            try:
                pool = engine.pool
                db_logger.debug(
                    f"连接池状态: 大小={pool.size()}, "
                    f"已使用={pool.checkedout()}, "
                    f"溢出={pool.overflow()}, "
                    f"可用={pool.checkedin()}"
                )
            except Exception as e:
                db_logger.error(f"监控连接池状态出错: {str(e)}")
            time.sleep(interval)
    
    # 启动监控线程
    monitor_thread = threading.Thread(target=log_pool_status, daemon=True)
    monitor_thread.start()
    
    return monitor_thread

def start_db_pool_monitor(engine, interval=60):
    """启动数据库连接池监控"""
    return monitor_db_pool(engine, interval) 