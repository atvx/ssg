#!/bin/bash
set -e

# 确保Chrome进程在启动时是干净的
echo "清理可能存在的Chrome进程..."
pkill -f chrome || true
pkill -f chromedriver || true
sleep 1
pkill -9 -f chrome || true
pkill -9 -f chromedriver || true
sleep 1

# 清理可能存在的锁文件
echo "清理Chrome用户数据目录锁文件..."
find /app/chrome_user_data* -name "*.lock" -delete 2>/dev/null || true
find /app/chrome_user_data* -name "SingletonLock" -delete 2>/dev/null || true

# 启动指定的命令
echo "启动应用..."
exec "$@" 