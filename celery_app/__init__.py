"""Celery应用初始化"""

import os

# 设置环境变量以确保Redis连接一致
os.environ['CELERY_BROKER_URL'] = "redis://:163000@124.221.92.150:6378/0"
os.environ['CELERY_RESULT_BACKEND'] = "redis://:163000@124.221.92.150:6378/0"
os.environ['REDIS_URL'] = "redis://:163000@124.221.92.150:6378/0"

from celery_app.celery import celery_app

__all__ = ['celery_app']
