"""Celery配置文件"""

# Redis连接
broker_url = "redis://:163000@124.221.92.150:6378/0"
result_backend = "redis://:163000@124.221.92.150:6378/0"

# Redis配置
broker_transport_options = {
    'visibility_timeout': 3600,  # 1小时
    'socket_timeout': 5,         # socket超时
    'socket_connect_timeout': 5,  # 连接超时
    'socket_keepalive': True,    # 保持连接
    'max_connections': 10,       # 最大连接数
    'retry_on_timeout': True,    # 超时重试
}

# Redis结果后端配置
redis_backend_health_check_interval = 30  # 健康检查间隔
redis_backend_socket_connect_timeout = 5  # 连接超时
redis_backend_socket_timeout = 5         # socket超时

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