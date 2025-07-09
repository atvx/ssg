# ========================
# 阶段1: 构建阶段
# ========================
FROM python:3.13-slim as builder

# 设置构建环境
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore --upgrade pip \
    && pip install --no-cache-dir --root-user-action=ignore \
       --find-links https://pypi.tuna.tsinghua.edu.cn/simple/ \
       --timeout 60 \
       -r requirements.txt \
    && pip install --no-cache-dir --root-user-action=ignore \
       selenium-wire pyvirtualdisplay retry timeout-decorator requests-toolbelt tenacity

# ========================
# 阶段2: 运行时阶段
# ========================
FROM python:3.13-slim as runtime

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    LANG=zh_CN.UTF-8 \
    LANGUAGE=zh_CN:zh \
    LC_ALL=zh_CN.UTF-8 \
    DISPLAY=:99

# 从构建阶段复制Python包
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 一次性安装所有运行时依赖
RUN apt-get update -o Acquire::Check-Valid-Until=false \
    && apt-get install -y --no-install-recommends \
    # 基础工具
    wget curl unzip gnupg apt-transport-https \
    # 虚拟显示和进程管理
    xvfb procps net-tools netcat-openbsd \
    # 字体支持
    fonts-wqy-zenhei fonts-noto-cjk fonts-noto-color-emoji \
    ttf-ancient-fonts-symbola fonts-liberation fonts-dejavu-core \
    fontconfig libfontconfig1 \
    # 本地化支持
    locales tzdata ntpdate \
    # Edge浏览器运行时依赖
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libgbm1 libpango-1.0-0 \
    # 日报导出功能依赖
    libreoffice poppler-utils \
    # 添加Microsoft Edge仓库
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-edge.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-edge.gpg] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends microsoft-edge-stable \
    # 配置本地化
    && sed -i -e 's/# zh_CN.UTF-8 UTF-8/zh_CN.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen \
    && echo "Asia/Shanghai" > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata \
    # 刷新字体缓存
    && fc-cache -f -v \
    # 创建时间同步脚本
    && echo '#!/bin/bash\nntpdate -u cn.pool.ntp.org || true' > /usr/local/bin/sync_time \
    && chmod +x /usr/local/bin/sync_time \
    # 彻底清理
    && apt-get autoremove -y \
    && apt-get autoclean \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && rm -rf /usr/share/doc /usr/share/man /usr/share/locale

# 设置应用相关环境变量
ENV EDGE_BIN=/usr/bin/microsoft-edge \
    EDGE_PATH=/usr/bin/microsoft-edge \
    SELENIUM_BROWSER_BINARY="/usr/bin/microsoft-edge" \
    EDGE_FLAGS="--no-sandbox --disable-dev-shm-usage --disable-gpu --headless=new --disable-software-rasterizer --remote-debugging-port=9222 --disable-extensions --disable-dev-tools --window-size=1920,1080 --single-process --disable-background-networking --ignore-certificate-errors --disable-infobars" \
    WDM_LOG_LEVEL=0 \
    WDM_SSL_VERIFY=0 \
    WDM_LOCAL=1 \
    LIBREOFFICE_PATH=/usr/bin/libreoffice \
    POPPLER_PATH=/usr/bin \
    REDIS_SOCKET_TIMEOUT=60 \
    REDIS_SOCKET_CONNECT_TIMEOUT=30 \
    REDIS_SOCKET_KEEPALIVE=True \
    REDIS_RETRY_ON_TIMEOUT=True \
    REDIS_MAX_CONNECTIONS=20

# 复制配置脚本
COPY selenium_setup.py redis_config.py redis_setup.py /usr/local/bin/
RUN chmod +x /usr/local/bin/*.py

# 创建优化的entrypoint脚本
RUN cat > /usr/local/bin/entrypoint.sh << 'EOF'
#!/bin/bash
set -e

echo "=== 容器启动 - 快速初始化 ==="

# 并行执行非关键初始化任务
{
    /usr/local/bin/sync_time 2>/dev/null || true
    fc-cache -f -v 2>/dev/null || true
} &

# 启动虚拟显示服务器
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!

# 快速创建目录
mkdir -p /app/{edge_user_data,data} /tmp/edge_tmp /var/run/edge
chmod -R 777 /app/edge_user_data /tmp/edge_tmp /var/run/edge /app/data

# 检查Edge浏览器
if [ -f /usr/bin/microsoft-edge ]; then
    echo "✓ Edge浏览器已安装"
else
    echo "✗ Edge浏览器未找到"
fi

echo "✓ EdgeDriver由webdriver-manager自动管理"

# 设置环境变量
export PYTHONPATH=/app
export EDGE_OPTIONS="--no-sandbox --disable-dev-shm-usage --disable-gpu --headless=new --disable-software-rasterizer --disable-extensions --window-size=1920,1080 --single-process --disable-background-networking --ignore-certificate-errors --disable-infobars --disable-dev-tools"
export OOO_FORCE_DESKTOP=gnome
export SAL_USE_VCLPLUGIN=gen

# 等待后台任务完成
wait

# 快速运行配置脚本
python /usr/local/bin/selenium_setup.py 2>/dev/null || true
python /usr/local/bin/redis_setup.py 2>/dev/null || true

echo "=== 初始化完成，启动应用 ==="

# 确保在退出时清理Xvfb进程
trap "kill $XVFB_PID 2>/dev/null || true" EXIT

# 执行主命令
exec "$@"
EOF

RUN chmod +x /usr/local/bin/entrypoint.sh

# 最后复制项目文件（利用.dockerignore优化）
COPY . .

# 设置容器入口点
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# 设置容器默认命令
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "120", "--log-level", "info"] 