from celery import Celery

# 创建Celery应用
celery_app = Celery(
    "sales_data_worker",
    include=["celery_app.tasks"]
)

# 加载配置
celery_app.config_from_object('celery_app.celeryconfig')
