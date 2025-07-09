#!/bin/bash

# 生产环境部署脚本 - 销售数据获取系统
# 适用于已有Docker镜像的服务器部署

set -e

echo "=== 销售数据获取系统 - 生产环境部署 ==="
echo "========================================="

# 检查是否有root权限
if [ "$(id -u)" != "0" ]; then
   echo "此脚本需要root权限运行，请使用sudo或以root用户运行" 
   exit 1
fi

echo "=== 1. 创建必要目录 ==="
mkdir -p edge_user_data data
chmod 777 edge_user_data data

echo "=== 2. 创建Edge临时文件目录 ==="
mkdir -p /tmp/edge_tmp
chmod 777 /tmp/edge_tmp

echo "=== 3. 检查环境变量文件 ==="
if [ ! -f .env ]; then
    echo "创建默认.env文件..."
    cat > .env << EOF
# 安全配置
SECRET_KEY=QIAN
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 数据库配置 - 请修改为实际的数据库连接信息
DATABASE_URL=mysql+pymysql://用户名:密码@数据库地址:3306/数据库名

# Redis配置 - 请修改为实际的Redis连接信息
REDIS_URL=redis://:密码@Redis地址:6379/0

# Celery配置
CELERY_BROKER_URL=redis://:密码@Redis地址:6379/0
CELERY_RESULT_BACKEND=redis://:密码@Redis地址:6379/0

# Redis连接参数
REDIS_SOCKET_TIMEOUT=60
REDIS_SOCKET_CONNECT_TIMEOUT=30
REDIS_SOCKET_KEEPALIVE=True
REDIS_RETRY_ON_TIMEOUT=True
REDIS_MAX_CONNECTIONS=20

# Celery连接参数
CELERY_BROKER_CONNECTION_TIMEOUT=60
CELERY_BROKER_CONNECTION_MAX_RETRIES=10
CELERY_BROKER_HEARTBEAT=30
CELERY_BROKER_POOL_LIMIT=10
CELERY_VISIBILITY_TIMEOUT=43200

# 美团POS配置 - 请修改为实际账号信息
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
EDGE_USER_DATA_DIR=edge_user_data

# webdriver-manager配置
WDM_LOG_LEVEL=0
WDM_SSL_VERIFY=0
WDM_LOCAL=1

# 浏览器类型环境变量
SELENIUM_BROWSER=edge
BROWSER_TYPE=edge
USE_EDGE=true
EOF
    
    echo "已创建默认.env文件，请编辑其中的数据库和Redis连接信息！"
    echo "特别注意修改以下配置："
    echo "  - DATABASE_URL: 数据库连接信息"
    echo "  - REDIS_URL: Redis连接信息"
    echo "  - CELERY_BROKER_URL: Celery消息队列连接信息" 
    echo "  - CELERY_RESULT_BACKEND: Celery结果存储连接信息"
    echo "  - MEITUAN_*: 美团账号信息"
    echo ""
    read -p "请编辑.env文件后按回车键继续..." KEY
else
    echo ".env文件已存在，跳过创建"
fi

echo "=== 4. 检查Docker Compose配置 ==="
if [ ! -f docker-compose.prod.yml ]; then
    echo "错误: 未找到docker-compose.prod.yml文件"
    echo "请确保已上传完整的部署文件包"
    exit 1
fi

# 检测Docker Compose命令格式
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "未找到docker compose命令，请确保Docker和Docker Compose已安装。"
    exit 1
fi

echo "使用的Docker Compose命令: $COMPOSE_CMD"

echo "=== 5. 停止现有服务（如果存在）==="
$COMPOSE_CMD -f docker-compose.prod.yml down 2>/dev/null || true

echo "=== 6. 启动生产环境服务 ==="
$COMPOSE_CMD -f docker-compose.prod.yml up -d

echo "=== 7. 等待服务启动 ==="
sleep 10

echo "=== 8. 检查服务状态 ==="
$COMPOSE_CMD -f docker-compose.prod.yml ps

echo "=== 9. 检查API健康状态 ==="
for i in {1..6}; do
    if curl -f http://localhost:3400/ping --max-time 5 >/dev/null 2>&1; then
        echo "✓ API服务健康检查通过"
        break
    else
        echo "等待API服务启动... ($i/6)"
        sleep 5
    fi
done

echo ""
echo "=== 部署完成 ==="
echo "服务已启动，API文档地址: http://localhost:3400/docs"
echo ""
echo "使用以下命令查看服务日志："
echo "$COMPOSE_CMD -f docker-compose.prod.yml logs -f api"
echo "$COMPOSE_CMD -f docker-compose.prod.yml logs -f celery_worker"
echo ""
echo "感谢使用销售数据获取系统！" 