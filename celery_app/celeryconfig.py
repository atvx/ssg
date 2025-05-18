"""Celery配置文件"""

# Redis连接
broker_url = "redis://:163000@124.221.92.150:6378/0"
result_backend = "redis://:163000@124.221.92.150:6378/0"

# 序列化
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Shanghai'
enable_utc = False

# 任务跟踪
task_track_started = True
worker_max_tasks_per_child = 100 