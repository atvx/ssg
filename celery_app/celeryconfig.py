"""Celery配置文件"""
import os

# Redis连接
broker_url = os.getenv('CELERY_BROKER_URL', "redis://:163000@124.221.92.150:6378/0")
result_backend = os.getenv('CELERY_RESULT_BACKEND', "redis://:163000@124.221.92.150:6378/0")

# Redis配置
broker_transport_options = {
    'visibility_timeout': 1800,   # 30分钟 - 减少任务锁定时间
    'socket_timeout': 60,         # socket超时 - 增加到60秒
    'socket_connect_timeout': 10, # 连接超时 - 增加到10秒
    'socket_keepalive': True,    # 保持连接
    'max_connections': 20,       # 最大连接数 - 增加到20
    'retry_on_timeout': True,    # 超时重试
    'retry_on_error': ['redis.ConnectionError', 'redis.TimeoutError'],  # 重试错误类型
}

# Redis结果后端配置
redis_backend_health_check_interval = 30  # 健康检查间隔 - 减少到30秒
redis_backend_socket_connect_timeout = 10  # 连接超时
redis_backend_socket_timeout = 60         # socket超时

# 序列化
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Shanghai'
enable_utc = False

# 任务跟踪
task_track_started = True
worker_max_tasks_per_child = 100

# 任务重试设置
task_acks_late = True           # 任务完成后再确认
task_reject_on_worker_lost = True  # worker丢失时拒绝任务
broker_connection_retry = True   # 连接断开时重试
broker_connection_max_retries = 10  # 最大重试10次
broker_connection_retry_on_startup = True  # 启动时重试连接
broker_heartbeat = 30           # 心跳间隔30秒

# Worker设置
worker_prefetch_multiplier = 1  # 减少预取，避免任务堆积
worker_concurrency = 2         # 设置并发worker数量
worker_hijack_root_logger = False  # 不劫持根日志
worker_log_color = False        # 在容器中禁用颜色输出

# 任务执行超时
task_soft_time_limit = 600      # 10分钟软超时
task_time_limit = 900           # 15分钟硬超时

# 结果过期时间
result_expires = 600  # 10分钟

# 任务注解 - 添加全局任务配置
task_annotations = {
    '*': {
        'expires': 1800,  # 30分钟后任务过期
        'acks_late': True,  # 任务完成后再确认
        'reject_on_worker_lost': True,  # worker丢失时拒绝任务
        'max_retries': 3,  # 最大重试次数
        'retry_backoff': True,  # 使用指数退避重试
        'retry_backoff_max': 600,  # 最大重试间隔10分钟
        'retry_jitter': True  # 添加随机抖动避免重试风暴
    }
}

# 任务默认配置
task_default_rate_limit = '10/m'  # 限制任务执行频率
task_send_sent_event = True  # 发送任务事件，用于监控