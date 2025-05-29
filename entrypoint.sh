#!/bin/bash
set -e

# 诊断系统信息
echo "系统信息:"
uname -a
echo "内存使用情况:"
free -h
echo "磁盘使用情况:"
df -h

# 确保Chrome进程在启动时是干净的
echo "清理可能存在的Chrome进程..."
pkill -f chrome || true
pkill -f chromedriver || true
sleep 1
pkill -9 -f chrome || true
pkill -9 -f chromedriver || true
sleep 1

# 清理所有Chrome用户数据目录
echo "清理Chrome用户数据目录..."
find /app -name "chrome_user_data*" -type d -exec rm -rf {} \; 2>/dev/null || true
mkdir -p /app/chrome_user_data
chmod -R 777 /app/chrome_user_data

# 清理临时目录
echo "清理临时目录..."
rm -rf /tmp/chrome_tmp/* 2>/dev/null || true
mkdir -p /tmp/chrome_tmp
chmod -R 777 /tmp/chrome_tmp

# 确保/dev/shm有足够空间或创建替代品
echo "配置共享内存..."
if [ -d /dev/shm ] && [ $(df -k /dev/shm | tail -n 1 | awk '{print $4}') -lt 256000 ]; then
    echo "警告: /dev/shm 空间不足，使用 /tmp 作为替代"
    mkdir -p /tmp/chrome-shm
    chmod -R 777 /tmp/chrome-shm
    export CHROME_DISABLE_DEV_SHM=true
fi

echo "Chrome驱动路径:"
which chromedriver || echo "未找到chromedriver"
which google-chrome || echo "未找到google-chrome"

# 验证chromedriver可执行
if [ -f /usr/local/bin/chromedriver ]; then
    echo "测试chromedriver..."
    chmod +x /usr/local/bin/chromedriver
    /usr/local/bin/chromedriver --version || echo "chromedriver执行失败"
fi

# 启动指定的命令
echo "启动应用..."
exec "$@" 