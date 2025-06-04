#!/bin/bash

# 销售数据获取系统 - Docker部署脚本
# 适用于Linux x86_64/AMD64架构

set -e

echo "=== 销售数据获取系统 - Docker部署脚本 ==="
echo "====================================="

# 检查是否有root权限
if [ "$(id -u)" != "0" ]; then
   echo "此脚本需要root权限运行，请使用sudo或以root用户运行" 
   exit 1
fi

echo "=== 1. 创建环境变量文件 ==="
if [ ! -f .env ]; then
    cat > .env << EOF
# 安全配置
SECRET_KEY=your-secret-key-for-development-only
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 数据库配置
DATABASE_URL=mysql+pymysql://qian:qian163@124.221.92.150:3306/ssgmlj

# Redis配置
REDIS_URL=redis://:163000@124.221.92.150:6378/0

# Celery配置
CELERY_BROKER_URL=redis://:163000@124.221.92.150:6378/0
CELERY_RESULT_BACKEND=redis://:163000@124.221.92.150:6378/0

# 美团POS配置
MEITUAN_PHONE=13884950903
MEITUAN_ORG=叁石哥丰都麻辣鸡
MEITUAN_USERNAME=13884950903
MEITUAN_PASSWORD=sanshige123456

# 滑块验证模式: 0=自动, 1=手动
SLIDER_VERIFY_MODE=0

# 登录方式: 0=手机号登录, 1=账号登录
LOGIN_MODE=1

# 多维系统配置
DUOWEI_BASE_URL=http://saas.wxdw.top:8899/web_api
DUOWEI_USER_ID=00016
DUOWEI_DB_NAME=ssgmlj
DUOWEI_OUTPUT_FILE=sales_duowei.json
DUOWEI_SAVE_TO_FILE=False

# 浏览器配置
HEADLESS=True
EOF
    
    echo "已创建.env文件，请修改其中的数据库和Redis连接信息。"
    echo "请编辑.env文件，然后继续..."
    read -p "按回车键继续..." KEY
else
    echo ".env文件已存在，跳过创建步骤。"
fi

# 确保chrome_user_data目录存在
echo "=== 2. 创建Chrome用户数据目录 ==="
mkdir -p chrome_user_data
chmod 777 chrome_user_data

echo "=== 3. 构建和启动Docker服务 ==="
if command -v docker-compose &> /dev/null; then
    docker-compose build
    docker-compose up -d
elif command -v docker compose &> /dev/null; then
    docker compose build
    docker compose up -d
else
    echo "未找到docker-compose命令，请确保Docker和Docker Compose已安装。"
    exit 1
fi

echo "=== 4. 部署完成 ==="
echo "服务已启动，API文档地址: http://localhost:8000/docs"
echo

# 显示容器状态
echo "=== 容器状态 ==="
if command -v docker-compose &> /dev/null; then
    docker-compose ps
elif command -v docker compose &> /dev/null; then
    docker compose ps
fi

echo
echo "使用以下命令查看服务日志："
echo "API服务日志: docker-compose logs -f api"
echo "Celery Worker日志: docker-compose logs -f celery_worker"
echo
echo "感谢使用销售数据获取系统！" 