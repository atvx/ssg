# 使用较新的稳定版 Python (例如 Python 3.13，基于 Debian Bookworm slim)
FROM python:3.13-slim-bookworm

WORKDIR /app

# 设置 DEBIAN_FRONTEND 为非交互模式，避免构建过程中的用户提示
ENV DEBIAN_FRONTEND=noninteractive

# 安装必要的工具及 Chrome 运行依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    curl \
    jq \
    unzip \
    procps \
    # Chrome 运行所需的核心依赖库
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 添加 Google Chrome 官方软件源
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list

# 安装最新稳定版的 Google Chrome
RUN apt-get update && apt-get install -y \
    google-chrome-stable \
    --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装与已安装 Chrome 版本对应的 ChromeDriver
RUN CHROME_VERSION_NUMBER=137.0.7151.55 \
    && echo "已安装的 Chrome 浏览器版本: ${CHROME_VERSION_NUMBER}" \
    && DOWNLOAD_URL="https://storage.googleapis.com/chrome-for-testing-public/137.0.7151.55/linux64/chromedriver-linux64.zip" \
    && echo "找到 ChromeDriver 下载链接: ${DOWNLOAD_URL}" \
    # 增加更多的日志来帮助调试
    && echo "开始下载 ChromeDriver..." \
    && curl -sSL "${DOWNLOAD_URL}" -o /tmp/chromedriver.zip \
    && if [ ! -f /tmp/chromedriver.zip ]; then \
        echo "下载失败！"; \
        exit 1; \
    fi \
    && echo "ChromeDriver 下载成功，解压中..." \
    # 解压到临时目录
    && unzip -q /tmp/chromedriver.zip -d /tmp/ \
    && echo "解压后的文件内容：" \
    && ls -l /tmp/ \
    # 移动 chromedriver 可执行文件
    && mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/ \
    && rm -rf /tmp/chromedriver-linux64 \
    && rm /tmp/chromedriver.zip \
    && chmod +x /usr/local/bin/chromedriver \
    && echo "已安装的 ChromeDriver 版本: $(chromedriver --version)" # 验证安装

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# 创建临时目录和用户数据目录
RUN mkdir -p /app/chrome_user_data \
    && mkdir -p /app/tmp \
    && mkdir -p /tmp/chrome_tmp \
    && chmod -R 777 /app/chrome_user_data \
    && chmod -R 777 /app/tmp \
    && chmod -R 777 /tmp/chrome_tmp

# 环境变量设置
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/local/bin:${PATH}"
ENV HEADLESS=true
ENV CHROME_DISABLE_GPU=true
ENV CHROME_NO_SANDBOX=true
ENV CHROME_DISABLE_DEV_SHM=true
ENV TMP=/tmp/chrome_tmp

# 添加入口脚本
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# 创建非root用户并设置权限
RUN useradd --system --create-home --no-log-init --shell /bin/bash appuser \
    && chown -R appuser:appuser /app \
    && chown -R appuser:appuser /tmp/chrome_tmp \
    && chown -R appuser:appuser /usr/local/bin/entrypoint.sh \
    && chown -R appuser:appuser /app/chrome_user_data

USER appuser

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
