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
SECRET_KEY=QIAN
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
# Edge用户数据目录
EDGE_USER_DATA_DIR=edge_user_data
# webdriver-manager配置
WDM_LOG_LEVEL=0
WDM_SSL_VERIFY=0
WDM_LOCAL=1
# 添加浏览器类型环境变量
SELENIUM_BROWSER=edge
BROWSER_TYPE=edge
USE_EDGE=true
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
    
    # 添加Edge用户数据目录配置
    if ! grep -q "EDGE_USER_DATA_DIR" .env; then
        echo "" >> .env
        echo "# Edge用户数据目录" >> .env
        echo "EDGE_USER_DATA_DIR=edge_user_data" >> .env
    fi
    
    # 添加webdriver-manager配置
    if ! grep -q "WDM_LOG_LEVEL" .env; then
        echo "" >> .env
        echo "# webdriver-manager配置" >> .env
        echo "WDM_LOG_LEVEL=0" >> .env
        echo "WDM_SSL_VERIFY=0" >> .env
        echo "WDM_LOCAL=1" >> .env
    fi
    
    # 添加浏览器类型环境变量
    if ! grep -q "SELENIUM_BROWSER" .env; then
        echo "" >> .env
        echo "# 添加浏览器类型环境变量" >> .env
        echo "SELENIUM_BROWSER=edge" >> .env
        echo "BROWSER_TYPE=edge" >> .env
        echo "USE_EDGE=true" >> .env
    fi
fi

# 确保edge_user_data目录存在
echo "=== 2. 创建Edge用户数据目录 ==="
mkdir -p edge_user_data
chmod 777 edge_user_data

# 创建Edge临时目录
echo "=== 3. 创建Edge临时文件目录 ==="
mkdir -p /tmp/edge_tmp
chmod 777 /tmp/edge_tmp

# 创建时间同步脚本
echo "=== 4. 创建时间同步脚本 ==="
cat > sync_time.sh << EOF
#!/bin/bash
# 同步主机系统时间
ntpdate -u cn.pool.ntp.org

# 同步Docker容器的时间
docker exec ssg-api /usr/local/bin/sync_time || echo "无法同步API容器时间"
docker exec ssg-celery-worker /usr/local/bin/sync_time || echo "无法同步Worker容器时间"

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
    docker compose restart api celery_worker || docker-compose restart api celery_worker
    
    echo "\$(date '+%Y-%m-%d %H:%M:%S') 服务已重启"
else
    echo "\$(date '+%Y-%m-%d %H:%M:%S') Redis连接正常"
fi
EOF

chmod +x redis_monitor.sh

# 添加Redis连接监控定时任务
(crontab -l 2>/dev/null || echo "") | grep -v "redis_monitor.sh" | { cat; echo "*/15 * * * * $(pwd)/redis_monitor.sh >> $(pwd)/redis_monitor.log 2>&1"; } | crontab -

# 清理Docker缓存和未使用的镜像/卷
echo "=== 7. 清理Docker系统缓存 ==="
echo "清理Docker缓存以释放空间..."
docker system prune -f
docker image prune -f
docker volume prune -f
docker builder prune -f

echo "=== 8. 构建和启动Docker服务 ==="
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

# 检查当前是否有容器在运行
if $COMPOSE_CMD ps -q &>/dev/null; then
    # 停止现有容器
    echo "停止并移除现有容器..."
    $COMPOSE_CMD down || true
else
    echo "没有发现运行中的容器..."
fi

# 检查docker-compose.yml文件
echo "检查docker-compose.yml配置..."
# 备份原始文件
cp docker-compose.yml docker-compose.yml.bak

echo "跳过文件更新，使用现有的docker-compose.yml配置"

# 强制重建镜像
echo "构建Docker镜像..."
$COMPOSE_CMD build --no-cache --pull || {
    echo "构建失败，尝试修复依赖问题..."
    # 检查requirements.txt中的urllib3版本
    if grep -q "urllib3==2.0.7" requirements.txt; then
        echo "检测到urllib3版本冲突，正在修复..."
        sed -i 's/urllib3==2.0.7/urllib3>=2.5.0/g' requirements.txt
        echo "已更新requirements.txt中的urllib3版本"
        # 重新尝试构建
        $COMPOSE_CMD build --no-cache --pull
    else
        echo "构建失败，请检查日志以获取详细错误信息"
        exit 1
    fi
}

# 启动服务
echo "启动服务..."
$COMPOSE_CMD up -d

# 等待服务启动
echo "等待服务启动..."
sleep 10

# 检查容器状态
echo "检查容器状态..."
$COMPOSE_CMD ps

# 检查API容器是否正常运行
if ! $COMPOSE_CMD ps | grep -q "ssg-api.*Up"; then
    echo "警告: API容器未正常运行，查看日志..."
    $COMPOSE_CMD logs api | tail -n 50
    echo "尝试重新启动API容器..."
    $COMPOSE_CMD restart api
    sleep 5
    if ! $COMPOSE_CMD ps | grep -q "ssg-api.*Up"; then
        echo "错误: API容器无法正常启动，请检查日志"
    fi
fi

echo "=== 9. 部署完成 ==="
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