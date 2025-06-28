import logging
import sys
import os
from logging.handlers import RotatingFileHandler
import time
from functools import wraps
from collections import defaultdict
from typing import Dict, Tuple

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

class DuplicateLogFilter(logging.Filter):
    """过滤重复的日志消息"""
    
    def __init__(self, max_duplicates: int = 5, time_window: int = 60):
        """
        初始化重复日志过滤器
        
        Args:
            max_duplicates: 时间窗口内允许的最大重复日志数量
            time_window: 时间窗口长度（秒）
        """
        super().__init__()
        self.max_duplicates = max_duplicates
        self.time_window = time_window
        self.log_counts: Dict[str, list] = defaultdict(list)
        
    def filter(self, record: logging.LogRecord) -> bool:
        """
        过滤重复的日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            bool: True表示允许记录，False表示过滤掉
        """
        # 生成消息的唯一标识
        message_key = f"{record.levelname}:{record.name}:{record.getMessage()}"
        
        current_time = time.time()
        
        # 获取该消息的历史记录
        timestamps = self.log_counts[message_key]
        
        # 清理过期的时间戳
        timestamps[:] = [ts for ts in timestamps if current_time - ts < self.time_window]
        
        # 检查是否超过重复限制
        if len(timestamps) >= self.max_duplicates:
            # 如果这是第一次超过限制，记录一条汇总消息
            if len(timestamps) == self.max_duplicates:
                # 创建一个汇总日志记录
                summary_record = logging.LogRecord(
                    record.name, 
                    logging.WARNING,
                    record.pathname,
                    record.lineno,
                    f"重复日志消息已被过滤 (最近{self.time_window}秒内出现{self.max_duplicates}次): {record.getMessage()}",
                    (),
                    None
                )
                # 直接输出汇总消息
                logger = logging.getLogger(record.name)
                logger.handle(summary_record)
            return False
        
        # 记录当前时间戳
        timestamps.append(current_time)
        return True

class WebSocketErrorFilter(logging.Filter):
    """专门过滤WebSocket相关的重复错误"""
    
    def __init__(self):
        super().__init__()
        self.websocket_error_patterns = [
            "Cannot call \"receive\" once a disconnect message has been received",
            "WebSocket connection closed",
            "Connection closed",
            "接收WebSocket消息时出错"
        ]
        self.last_websocket_error_time = 0
        self.websocket_error_count = 0
        self.websocket_suppression_interval = 30  # 30秒内最多显示一次WebSocket错误
        
    def filter(self, record: logging.LogRecord) -> bool:
        """过滤WebSocket相关的重复错误"""
        message = record.getMessage()
        
        # 检查是否是WebSocket相关错误
        is_websocket_error = any(pattern in message for pattern in self.websocket_error_patterns)
        
        if is_websocket_error:
            current_time = time.time()
            
            # 如果距离上次显示WebSocket错误不到指定间隔，则过滤掉
            if current_time - self.last_websocket_error_time < self.websocket_suppression_interval:
                self.websocket_error_count += 1
                return False
            else:
                # 如果之前有被过滤的错误，先显示汇总信息
                if self.websocket_error_count > 0:
                    summary_record = logging.LogRecord(
                        record.name,
                        logging.WARNING, 
                        record.pathname,
                        record.lineno,
                        f"WebSocket错误已被过滤 {self.websocket_error_count} 次，最近 {self.websocket_suppression_interval} 秒内",
                        (),
                        None
                    )
                    logger = logging.getLogger(record.name)
                    logger.handle(summary_record)
                
                # 重置计数器和时间
                self.last_websocket_error_time = current_time
                self.websocket_error_count = 0
                return True
        
        return True

def setup_logging_filters():
    """设置日志过滤器"""
    # 获取根日志记录器
    root_logger = logging.getLogger()
    
    # 添加重复日志过滤器
    duplicate_filter = DuplicateLogFilter(max_duplicates=3, time_window=30)
    root_logger.addFilter(duplicate_filter)
    
    # 为WebSocket相关的logger添加专门的过滤器
    ws_logger = logging.getLogger('ws.routes')
    websocket_filter = WebSocketErrorFilter()
    ws_logger.addFilter(websocket_filter)
    
    print("日志过滤器已设置完成")

def get_logger(name: str) -> logging.Logger:
    """获取配置好的logger"""
    return logging.getLogger(name) 