from celery import Celery
from app.config.settings import settings

celery_app = Celery(
    "sales_data_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.celery_app.tasks"]
)

# 应用自定义配置
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
    worker_max_tasks_per_child=100
)
