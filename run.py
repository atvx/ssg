import os
import logging
import sys
import uvicorn
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

if __name__ == "__main__":
    # 清理浏览器用户数据目录
    try:
        from utils.chrome_cleanup import clean_browser_user_data
        logger.info("正在清理浏览器用户数据目录...")
        clean_browser_user_data()
        logger.info("浏览器用户数据目录清理完成")
    except Exception as e:
        logger.error(f"清理浏览器用户数据目录失败: {e}")
    
    # 强制结束所有浏览器进程
    try:
        from utils.file_utils import force_kill_processes
        logger.info("正在强制结束所有浏览器进程...")
        force_kill_processes(['msedge', 'msedgedriver', 'Microsoft Edge'])
        logger.info("浏览器进程清理完成")
    except Exception as e:
        logger.error(f"强制结束浏览器进程失败: {e}")
    
    # 启动前初始化定时任务
    try:
        from celery_app.tasks import init_scheduled_tasks
        logger.info("正在初始化定时任务...")
        init_scheduled_tasks()
        logger.info("定时任务初始化完成")
    except Exception as e:
        logger.error(f"初始化定时任务失败: {e}")
    
    # 启动FastAPI应用
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true",
        workers=int(os.getenv("WORKERS", 1))
    ) 