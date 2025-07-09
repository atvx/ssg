# ========================
# 阶段1: 构建阶段
# ========================
FROM python:3.13-slim AS builder

# 设置构建环境和时区
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai \
    DEBIAN_FRONTEND=noninteractive \
    APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1

# 修复GPG密钥和时间同步问题
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
    echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/10no-check-valid-until && \
    echo 'APT::Get::Assume-Yes "true";' > /etc/apt/apt.conf.d/90assumeyes

# 安装构建依赖并清理
RUN apt-get update --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends --allow-unauthenticated \
    build-essential \
    curl \
    ca-certificates \
    gnupg \
    && apt-get autoremove -y \
    && apt-get autoclean \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/cache/apt/archives/*

# 复制并安装Python依赖，立即清理缓存
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore --upgrade pip \
    && pip install --no-cache-dir --root-user-action=ignore \
       --find-links https://pypi.tuna.tsinghua.edu.cn/simple/ \
       --timeout 60 \
       setuptools==68.2.2 \
       -r requirements.txt \
    && pip install --no-cache-dir --root-user-action=ignore \
       selenium-wire pyvirtualdisplay retry timeout-decorator requests-toolbelt tenacity \
    && rm -rf /tmp/* /var/tmp/* ~/.cache/pip /root/.cache

# ========================
# 阶段2: 运行时阶段
# ========================
FROM python:3.13-slim AS runtime

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
    DISPLAY=:99 \
    APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1

# 从构建阶段复制Python包
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 一次性安装所有运行时依赖
RUN echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/10no-check-valid-until && \
    echo 'APT::Get::Assume-Yes "true";' > /etc/apt/apt.conf.d/90assumeyes && \
    apt-get update --allow-releaseinfo-change -o Acquire::Check-Valid-Until=false \
    && apt-get install -y --no-install-recommends --allow-unauthenticated \
    # 基础工具
    wget curl unzip gnupg apt-transport-https ca-certificates \
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
    && apt-get update --allow-releaseinfo-change \
    && apt-get install -y --no-install-recommends --allow-unauthenticated microsoft-edge-stable \
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
    # 彻底清理所有缓存和临时文件
    && apt-get autoremove -y \
    && apt-get autoclean \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/cache/apt/archives/* \
    && rm -rf /usr/share/doc /usr/share/man /usr/share/locale /usr/share/info \
    && rm -rf ~/.cache /root/.cache \
    && find /var/log -type f -exec truncate -s 0 {} \; \
    && find /usr -name "*.pyc" -delete \
    && find /usr -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

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
RUN echo '#!/bin/bash' > /usr/local/bin/entrypoint.sh && \
    echo 'set -e' >> /usr/local/bin/entrypoint.sh && \
    echo 'echo "=== 容器启动 - 快速初始化 ==="' >> /usr/local/bin/entrypoint.sh && \
    echo '# 清理可能存在的X服务器lock文件和进程' >> /usr/local/bin/entrypoint.sh && \
    echo 'pkill -f "Xvfb :99" 2>/dev/null || true' >> /usr/local/bin/entrypoint.sh && \
    echo 'rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 2>/dev/null || true' >> /usr/local/bin/entrypoint.sh && \
    echo '# 启动虚拟显示服务器' >> /usr/local/bin/entrypoint.sh && \
    echo 'Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &' >> /usr/local/bin/entrypoint.sh && \
    echo 'XVFB_PID=$!' >> /usr/local/bin/entrypoint.sh && \
    echo 'sleep 1  # 等待Xvfb启动' >> /usr/local/bin/entrypoint.sh && \
    echo '# 快速创建目录' >> /usr/local/bin/entrypoint.sh && \
    echo 'mkdir -p /app/{edge_user_data,data} /tmp/edge_tmp /var/run/edge' >> /usr/local/bin/entrypoint.sh && \
    echo 'chmod -R 777 /app/edge_user_data /tmp/edge_tmp /var/run/edge /app/data' >> /usr/local/bin/entrypoint.sh && \
    echo '# 执行非关键初始化任务（同步执行，避免wait阻塞）' >> /usr/local/bin/entrypoint.sh && \
    echo '/usr/local/bin/sync_time 2>/dev/null || true' >> /usr/local/bin/entrypoint.sh && \
    echo 'fc-cache -f -v >/dev/null 2>&1 || true' >> /usr/local/bin/entrypoint.sh && \
    echo '# 检查Edge浏览器' >> /usr/local/bin/entrypoint.sh && \
    echo 'if [ -f /usr/bin/microsoft-edge ]; then' >> /usr/local/bin/entrypoint.sh && \
    echo '    echo "✓ Edge浏览器已安装"' >> /usr/local/bin/entrypoint.sh && \
    echo 'else' >> /usr/local/bin/entrypoint.sh && \
    echo '    echo "✗ Edge浏览器未找到"' >> /usr/local/bin/entrypoint.sh && \
    echo 'fi' >> /usr/local/bin/entrypoint.sh && \
    echo 'echo "✓ EdgeDriver由webdriver-manager自动管理"' >> /usr/local/bin/entrypoint.sh && \
    echo '# 设置环境变量' >> /usr/local/bin/entrypoint.sh && \
    echo 'export PYTHONPATH=/app' >> /usr/local/bin/entrypoint.sh && \
    echo 'export EDGE_OPTIONS="--no-sandbox --disable-dev-shm-usage --disable-gpu --headless=new --disable-software-rasterizer --disable-extensions --window-size=1920,1080 --single-process --disable-background-networking --ignore-certificate-errors --disable-infobars --disable-dev-tools"' >> /usr/local/bin/entrypoint.sh && \
    echo 'export OOO_FORCE_DESKTOP=gnome' >> /usr/local/bin/entrypoint.sh && \
    echo 'export SAL_USE_VCLPLUGIN=gen' >> /usr/local/bin/entrypoint.sh && \
    echo '# 快速运行配置脚本' >> /usr/local/bin/entrypoint.sh && \
    echo 'python /usr/local/bin/selenium_setup.py >/dev/null 2>&1 || true' >> /usr/local/bin/entrypoint.sh && \
    echo 'python /usr/local/bin/redis_setup.py >/dev/null 2>&1 || true' >> /usr/local/bin/entrypoint.sh && \
    echo 'echo "=== 初始化完成，启动应用 ==="' >> /usr/local/bin/entrypoint.sh && \
    echo '# 确保在退出时清理Xvfb进程' >> /usr/local/bin/entrypoint.sh && \
    echo 'trap "kill $XVFB_PID 2>/dev/null || true" EXIT' >> /usr/local/bin/entrypoint.sh && \
    echo '# 执行主命令' >> /usr/local/bin/entrypoint.sh && \
    echo 'echo "启动命令: $@"' >> /usr/local/bin/entrypoint.sh && \
    echo 'exec "$@"' >> /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh

# 最后复制项目文件（利用.dockerignore优化）
COPY . .

# 复制后立即清理不需要的文件
RUN rm -rf /app/*.tar /app/*.tar.gz /app/*.zip /app/*.bak \
    && find /app -name "*.pyc" -delete \
    && find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true \
    && rm -rf /tmp/* /var/tmp/*

# 设置容器入口点
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# 设置容器默认命令
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "120", "--log-level", "info"] 