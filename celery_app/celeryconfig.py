"""Celery配置文件"""

import os

# Redis连接
broker_url = os.environ.get("CELERY_BROKER_URL", "redis://:163000@124.221.92.150:6378/0")
result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://:163000@124.221.92.150:6378/0")

# Redis配置
broker_transport_options = {
    'visibility_timeout': int(os.environ.get("CELERY_VISIBILITY_TIMEOUT", "3600")),  # 1小时 - 降低任务可见性超时，避免任务卡住太久
    'socket_timeout': int(os.environ.get("REDIS_SOCKET_TIMEOUT", "60")),         # socket超时 - 60秒
    'socket_connect_timeout': int(os.environ.get("REDIS_SOCKET_CONNECT_TIMEOUT", "10")),  # 连接超时 - 10秒
    'socket_keepalive': os.environ.get("REDIS_SOCKET_KEEPALIVE", "True").lower() == 'true',    # 保持连接
    'max_connections': int(os.environ.get("REDIS_MAX_CONNECTIONS", "20")),       # 最大连接数 - 20
    'retry_on_timeout': os.environ.get("REDIS_RETRY_ON_TIMEOUT", "True").lower() == 'true',    # 超时重试
    'retry_on_error': ['redis.ConnectionError', 'redis.TimeoutError'],  # 重试错误类型
}

# Redis结果后端配置 - 与broker设置保持一致
redis_backend_health_check_interval = 30  # 健康检查间隔 - 30秒
redis_backend_socket_connect_timeout = int(os.environ.get("REDIS_SOCKET_CONNECT_TIMEOUT", "10"))  # 连接超时 - 10秒
redis_backend_socket_timeout = int(os.environ.get("REDIS_SOCKET_TIMEOUT", "60"))         # socket超时 - 60秒

# 序列化
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Shanghai'
enable_utc = False

# 任务跟踪
task_track_started = True
worker_max_tasks_per_child = int(os.environ.get("CELERY_WORKER_MAX_TASKS", "50"))  # 单个worker处理的最大任务数

# 任务重试设置
task_acks_late = True           # 任务完成后再确认
task_reject_on_worker_lost = True  # worker丢失时拒绝任务
broker_connection_retry = True   # 连接断开时重试
broker_connection_max_retries = int(os.environ.get("CELERY_BROKER_CONNECTION_MAX_RETRIES", "10"))  # 最大重试10次
broker_connection_retry_on_startup = True  # 启动时重试连接
broker_heartbeat = int(os.environ.get("CELERY_BROKER_HEARTBEAT", "30"))           # 心跳间隔30秒

# Worker设置
worker_prefetch_multiplier = 1  # 减少预取，避免任务堆积
worker_hijack_root_logger = False  # 不劫持根日志
worker_log_color = False        # 在容器中禁用颜色输出

# 任务执行超时 - 调整超时时间
task_soft_time_limit = int(os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", "600"))      # 10分钟软超时
task_time_limit = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "900"))           # 15分钟硬超时

# 结果过期时间
result_expires = 86400  # 24小时

# Beat调度器配置
beat_scheduler = 'celery.beat.PersistentScheduler'
beat_schedule_filename = 'celerybeat-schedule'  # 调度器数据文件
beat_max_loop_interval = 60     # 最大循环间隔（秒）
beat_sync_every = 1             # 每次循环都同步到数据库

# 启用调度器任务自动加载
imports = ('celery_app.tasks',)

# 调度器锁超时设置
beat_schedule_expire_seconds = 3600  # 调度器锁超时时间（秒）