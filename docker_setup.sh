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
# Redis连接参数
REDIS_SOCKET_TIMEOUT=60
REDIS_SOCKET_CONNECT_TIMEOUT=30
REDIS_SOCKET_KEEPALIVE=True
REDIS_RETRY_ON_TIMEOUT=True
REDIS_MAX_CONNECTIONS=20

# Celery配置
CELERY_BROKER_URL=redis://:163000@124.221.92.150:6378/0
CELERY_RESULT_BACKEND=redis://:163000@124.221.92.150:6378/0
CELERY_BROKER_CONNECTION_TIMEOUT=60
CELERY_BROKER_CONNECTION_MAX_RETRIES=10
CELERY_BROKER_HEARTBEAT=30
CELERY_BROKER_POOL_LIMIT=10
CELERY_VISIBILITY_TIMEOUT=43200

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
    echo ".env文件已存在，更新Redis和Celery连接参数..."
    # 添加或更新Redis连接参数
    if ! grep -q "REDIS_SOCKET_TIMEOUT" .env; then
        echo "" >> .env
        echo "# Redis连接参数" >> .env
        echo "REDIS_SOCKET_TIMEOUT=60" >> .env
        echo "REDIS_SOCKET_CONNECT_TIMEOUT=30" >> .env
        echo "REDIS_SOCKET_KEEPALIVE=True" >> .env
        echo "REDIS_RETRY_ON_TIMEOUT=True" >> .env
        echo "REDIS_MAX_CONNECTIONS=20" >> .env
    fi
    
    # 添加或更新Celery连接参数
    if ! grep -q "CELERY_BROKER_CONNECTION_TIMEOUT" .env; then
        echo "" >> .env
        echo "# Celery连接参数" >> .env
        echo "CELERY_BROKER_CONNECTION_TIMEOUT=60" >> .env
        echo "CELERY_BROKER_CONNECTION_MAX_RETRIES=10" >> .env
        echo "CELERY_BROKER_HEARTBEAT=30" >> .env
        echo "CELERY_BROKER_POOL_LIMIT=10" >> .env
        echo "CELERY_VISIBILITY_TIMEOUT=43200" >> .env
    fi
fi

# 确保chrome_user_data目录存在
echo "=== 2. 创建Chrome用户数据目录 ==="
mkdir -p chrome_user_data
chmod 777 chrome_user_data

# 创建Chrome临时目录
echo "=== 3. 创建Chrome临时文件目录 ==="
mkdir -p /tmp/chrome_tmp
chmod 777 /tmp/chrome_tmp

# 创建时间同步脚本
echo "=== 4. 创建时间同步脚本 ==="
cat > sync_time.sh << EOF
#!/bin/bash
# 同步主机系统时间
ntpdate -u cn.pool.ntp.org

# 同步Docker容器的时间
docker exec ssg-api /usr/local/bin/sync_time
docker exec ssg-celery-worker /usr/local/bin/sync_time

echo "\$(date '+%Y-%m-%d %H:%M:%S') 时间同步完成"
EOF
chmod +x sync_time.sh

# 创建定时任务
echo "=== 5. 创建定时同步任务 ==="
(crontab -l 2>/dev/null || echo "") | grep -v "sync_time.sh" | { cat; echo "*/10 * * * * $(pwd)/sync_time.sh >> $(pwd)/time_sync.log 2>&1"; } | crontab -

# 创建Redis连接检查脚本
echo "=== 6. 创建Redis连接监控脚本 ==="
cat > redis_monitor.sh << EOF
#!/bin/bash
# Redis连接监控脚本
# 检查Redis连接并在必要时重启服务

REDIS_HOST=\$(grep -o '@[^:]*' .env | grep -o '[^@]*' | head -1)
REDIS_PORT=\$(grep -o ':[0-9]*/' .env | grep -o '[0-9]*' | head -1)

echo "\$(date '+%Y-%m-%d %H:%M:%S') 开始检查Redis连接: \${REDIS_HOST}:\${REDIS_PORT}"

# 测试Redis连接
nc -z -w5 \${REDIS_HOST} \${REDIS_PORT}
RESULT=\$?

if [ \$RESULT -ne 0 ]; then
    echo "\$(date '+%Y-%m-%d %H:%M:%S') Redis连接失败，重启服务..."
    
    # 停止并重启服务
    cd \$(dirname \$0)
    docker-compose restart api celery_worker
    
    echo "\$(date '+%Y-%m-%d %H:%M:%S') 服务已重启"
else
    echo "\$(date '+%Y-%m-%d %H:%M:%S') Redis连接正常"
fi
EOF

chmod +x redis_monitor.sh

# 添加Redis连接监控定时任务
(crontab -l 2>/dev/null || echo "") | grep -v "redis_monitor.sh" | { cat; echo "*/15 * * * * $(pwd)/redis_monitor.sh >> $(pwd)/redis_monitor.log 2>&1"; } | crontab -

echo "=== 7. 构建和启动Docker服务 ==="
# 检查是否安装了Docker Compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo "未找到docker-compose命令，请确保Docker和Docker Compose已安装。"
    exit 1
fi

# 停止并移除现有容器
$COMPOSE_CMD down -v

# 强制重建镜像
$COMPOSE_CMD build --no-cache

# 启动服务
$COMPOSE_CMD up -d

echo "=== 8. 部署完成 ==="
echo "服务已启动，API文档地址: http://localhost:3400/docs"
echo

# 显示容器状态
echo "=== 容器状态 ==="
$COMPOSE_CMD ps

# 立即同步一次时间
echo "=== 执行时间同步 ==="
./sync_time.sh

echo
echo "使用以下命令查看服务日志："
echo "API服务日志: $COMPOSE_CMD logs -f api"
echo "Celery Worker日志: $COMPOSE_CMD logs -f celery_worker"
echo
echo "感谢使用销售数据获取系统！" 