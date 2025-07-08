FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai

# 解决GPG密钥问题并安装依赖 - 合并安装和清理步骤减少层数
RUN apt-get update -o Acquire::Check-Valid-Until=false -o Acquire::AllowInsecureRepositories=true \
    && apt-get install -y --no-install-recommends gnupg \
    && apt-key update \
    && apt-get update --allow-insecure-repositories \
    && apt-get install -y --no-install-recommends --allow-unauthenticated \
    wget \
    curl \
    unzip \
    xvfb \
    fonts-wqy-zenhei \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    ttf-ancient-fonts-symbola \
    locales \
    tzdata \
    ntpdate \
    procps \
    net-tools \
    netcat-openbsd \
    # Edge浏览器依赖
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libgbm1 \
    libpango-1.0-0 \
    # 新增：日报导出功能依赖
    libreoffice \
    poppler-utils \
    fontconfig \
    libfontconfig1 \
    # 额外字体支持，确保Excel/PDF中文显示正常
    fonts-liberation \
    fonts-dejavu-core \
    && sed -i -e 's/# zh_CN.UTF-8 UTF-8/zh_CN.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen \
    # 刷新字体缓存
    && fc-cache -f -v \
    # 立即清理减少镜像大小
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 设置时区和时间同步配置 - 合并到单个RUN命令
RUN echo "Asia/Shanghai" > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata \
    && echo "#!/bin/bash\nntpdate -u cn.pool.ntp.org || true" > /usr/local/bin/sync_time \
    && chmod +x /usr/local/bin/sync_time

# 设置中文支持
ENV LANG=zh_CN.UTF-8 \
    LANGUAGE=zh_CN:zh \
    LC_ALL=zh_CN.UTF-8

# 安装Microsoft Edge - 分开安装Edge和EdgeDriver
RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    gnupg \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft-edge.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-edge.gpg] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge.list \
    && apt-get update \
    && apt-get install -y microsoft-edge-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装EdgeDriver - 使用固定版本号
RUN EDGE_DRIVER_VERSION="138.0.3351.77" \
    && mkdir -p /tmp/edgedriver \
    && wget -q "https://msedgedriver.azureedge.net/${EDGE_DRIVER_VERSION}/edgedriver_linux64.zip" -O /tmp/edgedriver.zip \
    && unzip /tmp/edgedriver.zip -d /tmp/edgedriver \
    && mv /tmp/edgedriver/msedgedriver /usr/local/bin/ \
    && chmod +x /usr/local/bin/msedgedriver \
    && rm -rf /tmp/edgedriver /tmp/edgedriver.zip

# 设置Edge浏览器环境变量
ENV EDGE_BIN=/usr/bin/microsoft-edge \
    EDGE_PATH=/usr/bin/microsoft-edge \
    MSEDGEDRIVER_PATH=/usr/local/bin/msedgedriver \
    SELENIUM_DRIVER_PATH="/usr/local/bin/msedgedriver" \
    SELENIUM_BROWSER_BINARY="/usr/bin/microsoft-edge" \
    EDGE_FLAGS="--no-sandbox --disable-dev-shm-usage --disable-gpu --headless=new --disable-software-rasterizer --remote-debugging-port=9222 --disable-extensions --disable-dev-tools --window-size=1920,1080 --single-process --disable-background-networking --ignore-certificate-errors --disable-infobars" \
    # 新增：日报导出相关环境变量
    LIBREOFFICE_PATH=/usr/bin/libreoffice \
    POPPLER_PATH=/usr/bin

# 设置Xvfb（虚拟显示服务器）
ENV DISPLAY=:99

# 设置Redis连接配置
ENV REDIS_SOCKET_TIMEOUT=60 \
    REDIS_SOCKET_CONNECT_TIMEOUT=30 \
    REDIS_SOCKET_KEEPALIVE=True \
    REDIS_RETRY_ON_TIMEOUT=True \
    REDIS_MAX_CONNECTIONS=20

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖 - 使用no-cache-dir减少构建空间需求
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt \
    && pip install --no-cache-dir --root-user-action=ignore selenium-wire pyvirtualdisplay retry timeout-decorator requests-toolbelt tenacity

# 复制Selenium和Redis设置脚本
COPY selenium_setup.py /usr/local/bin/selenium_setup.py
COPY redis_config.py /usr/local/bin/redis_config.py
COPY redis_setup.py /usr/local/bin/redis_setup.py
RUN chmod +x /usr/local/bin/selenium_setup.py /usr/local/bin/redis_config.py /usr/local/bin/redis_setup.py

# 创建一个wrapper脚本来设置环境
RUN echo '#!/bin/bash\n\
# 同步时间\n\
/usr/local/bin/sync_time\n\
\n\
# 确保字体缓存刷新\n\
fc-cache -f -v\n\
\n\
# 启动虚拟显示服务器\n\
Xvfb :99 -screen 0 1920x1080x24 -ac &\n\
# 确保edge_user_data目录存在并有正确权限\n\
mkdir -p /app/edge_user_data\n\
chmod -R 777 /app/edge_user_data\n\
# 确保临时目录存在并有正确权限\n\
mkdir -p /tmp/edge_tmp\n\
chmod -R 777 /tmp/edge_tmp\n\
# 新增：确保日报导出数据目录存在并有正确权限\n\
mkdir -p /app/data\n\
chmod -R 777 /app/data\n\
# 运行Selenium设置脚本\n\
python /usr/local/bin/selenium_setup.py\n\
# 运行Redis配置脚本\n\
python /usr/local/bin/redis_setup.py\n\
# 设置环境变量\n\
export PYTHONPATH=/app\n\
export EDGE_OPTIONS="--no-sandbox --disable-dev-shm-usage --disable-gpu --headless=new --disable-software-rasterizer --disable-extensions --window-size=1920,1080 --single-process --disable-background-networking --ignore-certificate-errors --disable-infobars --disable-dev-tools"\n\
# LibreOffice 字体配置\n\
export OOO_FORCE_DESKTOP=gnome\n\
export SAL_USE_VCLPLUGIN=gen\n\
# 执行命令\n\
exec "$@"' > /usr/local/bin/entrypoint.sh && \
chmod +x /usr/local/bin/entrypoint.sh

# 复制项目文件
COPY . .

# 设置容器入口点
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# 设置容器默认命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "120"] 