FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai

# 解决GPG密钥问题并安装依赖
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
    locales \
    tzdata \
    ntpdate \
    procps \
    htop \
    net-tools \
    netcat-openbsd \
    # 添加更多依赖以解决Chrome崩溃问题
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    # 添加Firefox作为备选浏览器
    firefox-esr \
    && sed -i -e 's/# zh_CN.UTF-8 UTF-8/zh_CN.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 设置时区和时间同步配置
RUN echo "Asia/Shanghai" > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata \
    # 使用ntpdate替换ntp服务
    && echo "#!/bin/bash\nntpdate -u cn.pool.ntp.org || true" > /usr/local/bin/sync_time \
    && chmod +x /usr/local/bin/sync_time

# 设置中文支持
ENV LANG=zh_CN.UTF-8 \
    LANGUAGE=zh_CN:zh \
    LC_ALL=zh_CN.UTF-8

# 下载和安装Chrome和ChromeDriver (AMD64架构)
RUN wget -q --no-verbose -O /tmp/chrome-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/136.0.7103.113/linux64/chrome-linux64.zip" \
    && wget -q --no-verbose -O /tmp/chromedriver-linux64.zip "https://storage.googleapis.com/chrome-for-testing-public/136.0.7103.113/linux64/chromedriver-linux64.zip" \
    && unzip /tmp/chrome-linux64.zip -d /opt/ \
    && unzip /tmp/chromedriver-linux64.zip -d /opt/ \
    && rm /tmp/chrome-linux64.zip /tmp/chromedriver-linux64.zip \
    && chmod +x /opt/chrome-linux64/chrome \
    && chmod +x /opt/chromedriver-linux64/chromedriver

# 下载和安装geckodriver (Firefox WebDriver)
RUN GECKODRIVER_VERSION="v0.33.0" \
    && wget -q --no-verbose -O /tmp/geckodriver.tar.gz "https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz" \
    && tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin/ \
    && rm /tmp/geckodriver.tar.gz \
    && chmod +x /usr/local/bin/geckodriver

# 创建Chrome软链接，避免修改业务代码
RUN ln -sf /opt/chrome-linux64/chrome /usr/bin/google-chrome && \
    ln -sf /opt/chrome-linux64/chrome /usr/bin/google-chrome-stable && \
    ln -sf /opt/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    chmod +x /usr/local/bin/chromedriver

# 创建目录以支持Chrome在沙盒模式下运行
RUN mkdir -p /var/run/chrome && \
    chmod -R 777 /var/run/chrome

# 创建Chrome临时数据目录
RUN mkdir -p /tmp/chrome_tmp && \
    chmod -R 777 /tmp/chrome_tmp

# 设置Chrome/Chromium环境变量
ENV CHROME_BIN=/usr/bin/google-chrome \
    CHROMIUM_PATH=/usr/bin/google-chrome \
    CHROMEDRIVER_PATH=/usr/local/bin/chromedriver \
    GECKODRIVER_PATH=/usr/local/bin/geckodriver \
    FIREFOX_BIN=/usr/bin/firefox-esr \
    PATH="/usr/local/bin:/usr/bin:${PATH}" \
    SELENIUM_DRIVER_PATH="/usr/local/bin/chromedriver" \
    SELENIUM_BROWSER_BINARY="/usr/bin/google-chrome" \
    # 添加Chrome默认启动参数，以适应Docker环境
    CHROMIUM_FLAGS="--no-sandbox --disable-dev-shm-usage --disable-gpu --headless=new --disable-software-rasterizer --remote-debugging-port=9222 --disable-extensions --disable-dev-tools --window-size=1920,1080 --single-process --disable-background-networking --ignore-certificate-errors --disable-infobars"

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

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt \
    # 添加webdriver-manager支持
    && pip install --no-cache-dir selenium-wire webdriver-manager pyvirtualdisplay \
    # 添加更多超时处理库
    && pip install --no-cache-dir retry timeout-decorator requests-toolbelt tenacity

# 复制Selenium和Redis设置脚本
COPY selenium_setup.py /usr/local/bin/selenium_setup.py
COPY redis_config.py /usr/local/bin/redis_config.py
COPY redis_setup.py /usr/local/bin/redis_setup.py
RUN chmod +x /usr/local/bin/selenium_setup.py && \
    chmod +x /usr/local/bin/redis_config.py && \
    chmod +x /usr/local/bin/redis_setup.py

# 创建一个wrapper脚本来设置环境
RUN echo '#!/bin/bash\n\
# 同步时间\n\
/usr/local/bin/sync_time\n\
\n\
# 启动虚拟显示服务器\n\
Xvfb :99 -screen 0 1920x1080x24 -ac &\n\
# 确保chrome_user_data目录存在并有正确权限\n\
mkdir -p /app/chrome_user_data\n\
chmod -R 777 /app/chrome_user_data\n\
# 确保临时目录存在并有正确权限\n\
mkdir -p /tmp/chrome_tmp\n\
chmod -R 777 /tmp/chrome_tmp\n\
# 运行Selenium设置脚本\n\
python /usr/local/bin/selenium_setup.py\n\
# 运行Redis配置脚本\n\
python /usr/local/bin/redis_setup.py\n\
# 设置环境变量\n\
export PYTHONPATH=/app\n\
export CHROME_OPTIONS="--no-sandbox --disable-dev-shm-usage --disable-gpu --headless=new --disable-software-rasterizer --disable-extensions --window-size=1920,1080 --single-process --disable-background-networking --ignore-certificate-errors --disable-infobars --disable-dev-tools"\n\
# 执行命令\n\
exec "$@"' > /usr/local/bin/entrypoint.sh && \
chmod +x /usr/local/bin/entrypoint.sh

# 复制项目文件
COPY . .

# 设置容器入口点
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# 设置容器默认命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "120"] 