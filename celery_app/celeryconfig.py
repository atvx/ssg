"""Celery配置文件"""

# Redis连接
broker_url = "redis://:163000@124.221.92.150:6378/0"
result_backend = "redis://:163000@124.221.92.150:6378/0"

# Redis配置
broker_transport_options = {
    'visibility_timeout': 43200,  # 12小时 - 增加任务可见性超时
    'socket_timeout': 60,         # socket超时 - 增加到60秒
    'socket_connect_timeout': 10,  # 连接超时 - 增加到10秒
    'socket_keepalive': True,    # 保持连接
    'socket_keepalive_options': {  # TCP保活参数
        'TCP_KEEPIDLE': 1,
        'TCP_KEEPINTVL': 3,
        'TCP_KEEPCNT': 5,
    },
    'max_connections': 20,       # 最大连接数 - 增加到20
    'retry_on_timeout': True,    # 超时重试
    'retry_on_error': ['redis.ConnectionError', 'redis.TimeoutError'],  # 重试错误类型
}

# Redis结果后端配置 - 与broker设置保持一致
redis_backend_health_check_interval = 60  # 健康检查间隔 - 增加到60秒
redis_backend_socket_connect_timeout = 10  # 连接超时 - 增加到10秒
redis_backend_socket_timeout = 60         # socket超时 - 增加到60秒

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
broker_connection_max_retries = 10  # 最大重试10次（原来是无限重试）
broker_connection_retry_on_startup = True  # 启动时重试连接
broker_heartbeat = 60           # 心跳间隔60秒

# Worker设置
worker_prefetch_multiplier = 1  # 减少预取，避免任务堆积
worker_hijack_root_logger = False  # 不劫持根日志
worker_log_color = False        # 在容器中禁用颜色输出

# 任务执行超时 - 增加超时时间
task_soft_time_limit = 1800     # 30分钟软超时
task_time_limit = 2400          # 40分钟硬超时

# 结果过期时间 - 增加保留时间
result_expires = 86400  # 24小时