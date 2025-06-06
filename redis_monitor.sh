#!/bin/bash
# Redis连接监控脚本
# 检查Redis连接并在必要时重启服务

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检测Docker Compose命令格式
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') 错误: 未找到docker compose命令"
    exit 1
fi

# 从.env文件中获取Redis连接信息
if [ ! -f .env ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') 错误: .env文件不存在"
    exit 1
fi

REDIS_HOST=$(grep -o '@[^:]*' .env | grep -o '[^@]*' | head -1)
REDIS_PORT=$(grep -o ':[0-9]*/' .env | grep -o '[0-9]*' | head -1)

if [ -z "$REDIS_HOST" ] || [ -z "$REDIS_PORT" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') 错误: 无法从.env文件获取Redis连接信息"
    exit 1
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') 开始检查Redis连接: ${REDIS_HOST}:${REDIS_PORT}"

# 测试Redis连接
if command -v nc &> /dev/null; then
    nc -z -w5 ${REDIS_HOST} ${REDIS_PORT}
    RESULT=$?
else
    # 如果没有nc命令，尝试使用timeout和telnet
    timeout 5 bash -c "</dev/tcp/${REDIS_HOST}/${REDIS_PORT}" &>/dev/null
    RESULT=$?
fi

if [ $RESULT -ne 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') Redis连接失败，重启服务..."
    
    # 检查容器是否在运行
    CONTAINER_API=$($COMPOSE_CMD ps -q api 2>/dev/null)
    CONTAINER_WORKER=$($COMPOSE_CMD ps -q celery_worker 2>/dev/null)
    
    if [ -n "$CONTAINER_API" ] || [ -n "$CONTAINER_WORKER" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') 正在重启容器..."
        $COMPOSE_CMD restart api celery_worker
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') 容器未运行，尝试启动服务..."
        $COMPOSE_CMD up -d
    fi
    
    echo "$(date '+%Y-%m-%d %H:%M:%S') 服务处理完成"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') Redis连接正常"
fi

exit 0 