#!/bin/bash
set -e

# 这个脚本将以root用户身份运行
echo "脚本以用户$(whoami)身份启动"

# 诊断系统信息
echo "系统信息:"
uname -a
echo "内存使用情况:"
free -h
echo "磁盘使用情况:"
df -h
echo "当前目录:"
pwd
echo "目录权限:"
ls -la /app

# 确保Chromium进程在启动时是干净的
echo "清理可能存在的Chromium进程..."
pkill -f chromium || true
pkill -f chromedriver || true
sleep 1
pkill -9 -f chromium || true
pkill -9 -f chromedriver || true
sleep 1

# 重新创建所有关键目录并设置最宽松的权限
echo "确保所有关键目录存在并设置权限..."
mkdir -p /app/chrome_user_data
mkdir -p /tmp/chrome_user_data
mkdir -p /tmp/chrome_data
mkdir -p /tmp/chrome_tmp
mkdir -p /tmp/chrome-shm

# 设置最宽松的权限
chmod -R 777 /app/chrome_user_data
chmod -R 777 /tmp/chrome_user_data
chmod -R 777 /tmp/chrome_data
chmod -R 777 /tmp/chrome_tmp
chmod -R 777 /tmp/chrome-shm

# 确保所有权限正确设置
chown -R appuser:appuser /app
chown -R appuser:appuser /tmp/chrome_user_data
chown -R appuser:appuser /tmp/chrome_data
chown -R appuser:appuser /tmp/chrome_tmp
chown -R appuser:appuser /tmp/chrome-shm

# 清理所有Chrome用户数据目录
echo "清理Chromium用户数据目录..."
find /app -name "chrome_user_data*" -type d -exec rm -rf {}/* \; 2>/dev/null || true
find /tmp -name "chrome_user_data*" -type d -exec rm -rf {}/* \; 2>/dev/null || true

# 清理临时目录
echo "清理临时目录..."
rm -rf /tmp/chrome_tmp/* 2>/dev/null || true

# 确保/dev/shm有足够空间或创建替代品
echo "配置共享内存..."
if [ -d /dev/shm ] && [ $(df -k /dev/shm | tail -n 1 | awk '{print $4}') -lt 256000 ]; then
    echo "警告: /dev/shm 空间不足，使用 /tmp/chrome-shm 作为替代"
    export CHROME_DISABLE_DEV_SHM=true
fi

# 设置Chrome相关环境变量，特别是SSL选项
export CHROME_ARGS="--no-sandbox --disable-dev-shm-usage --disable-gpu --headless --ignore-certificate-errors --ignore-ssl-errors --allow-insecure-localhost --disable-web-security --disable-features=IsolateOrigins,site-per-process"

# 如果是worker服务，显式设置更多环境变量
if [[ "$*" == *"celery"* ]]; then
    echo "设置Worker服务的额外环境变量..."
    export PYTHONIOENCODING=utf-8
    export SELENIUM_WIRE_CERT_PATH=/etc/ssl/certs/ca-certificates.crt
    export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
    export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
    export CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

    # 确保证书文件权限正确
    chmod 644 /etc/ssl/certs/ca-certificates.crt
fi

echo "Chromium驱动路径:"
which chromedriver || echo "未找到chromedriver"
which chromium || echo "未找到chromium"

# 验证chromedriver可执行
if [ -f /usr/bin/chromedriver ]; then
    echo "测试chromedriver..."
    chmod +x /usr/bin/chromedriver
    /usr/bin/chromedriver --version || echo "chromedriver执行失败"
fi

# 验证目录和文件权限
echo "验证目录权限..."
su appuser -c "touch /tmp/test_file" && echo "appuser可以写入/tmp" || echo "appuser无法写入/tmp"
su appuser -c "touch /app/test_file" && echo "appuser可以写入/app" || echo "appuser无法写入/app"
su appuser -c "touch /app/chrome_user_data/test_file" && echo "appuser可以写入/app/chrome_user_data" || echo "appuser无法写入/app/chrome_user_data"
su appuser -c "touch /tmp/chrome_data/test_file" && echo "appuser可以写入/tmp/chrome_data" || echo "appuser无法写入/tmp/chrome_data"

# 显示创建的所有目录
echo "已创建的目录和权限:"
ls -la /app/chrome_user_data
ls -la /tmp/chrome_data
ls -la /tmp/chrome_tmp

# 使用gosu切换到appuser用户运行命令
echo "以appuser用户身份启动应用..."
exec gosu appuser "$@"