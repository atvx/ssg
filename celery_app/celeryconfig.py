"""Celery配置文件"""

import os

# Redis连接 - 使用环境变量
broker_url = os.getenv("CELERY_BROKER_URL", "redis://:163000@124.221.92.150:6378/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://:163000@124.221.92.150:6378/0")

# Redis配置 - 优化连接参数
broker_transport_options = {
    'visibility_timeout': int(os.getenv("CELERY_VISIBILITY_TIMEOUT", 43200)),  # 12小时
    'socket_timeout': 60,         # 增加socket超时到60秒
    'socket_connect_timeout': 30,  # 增加连接超时到30秒
    'socket_keepalive': True,    # 保持连接
    'socket_keepalive_options': {
        'TCP_KEEPIDLE': 60,      # TCP保持活跃间隔
        'TCP_KEEPINTVL': 30,     # TCP保持活跃探测间隔
        'TCP_KEEPCNT': 3,        # TCP保持活跃探测次数
    },
    'max_connections': int(os.getenv("CELERY_BROKER_POOL_LIMIT", 20)),  # 增加最大连接数
    'retry_on_timeout': True,    # 超时重试
    'retry_on_error': [          # 增加重试的错误类型
        'redis.exceptions.ConnectionError',
        'redis.exceptions.TimeoutError',
        'redis.exceptions.BusyLoadingError',
    ],
    'health_check_interval': int(os.getenv("CELERY_BROKER_HEARTBEAT", 60)),  # 健康检查间隔
}

# Redis结果后端配置 - 优化超时设置
redis_backend_health_check_interval = 60  # 增加健康检查间隔
redis_backend_socket_connect_timeout = 30  # 增加连接超时
redis_backend_socket_timeout = 60         # 增加socket超时
redis_socket_keepalive = True             # 启用socket保持活跃
redis_socket_keepalive_options = {
    'TCP_KEEPIDLE': 60,
    'TCP_KEEPINTVL': 30, 
    'TCP_KEEPCNT': 3,
}

# Broker连接配置
broker_connection_timeout = int(os.getenv("CELERY_BROKER_CONNECTION_TIMEOUT", 60))
broker_connection_max_retries = int(os.getenv("CELERY_BROKER_CONNECTION_MAX_RETRIES", 10))
broker_heartbeat = int(os.getenv("CELERY_BROKER_HEARTBEAT", 60))
broker_pool_limit = int(os.getenv("CELERY_BROKER_POOL_LIMIT", 20))

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
broker_connection_max_retries = 0  # 无限重试

# 任务执行超时
task_soft_time_limit = 3600  # 1小时
task_time_limit = 3600      # 1小时

# 结果过期时间
result_expires = 3600  # 1小时 