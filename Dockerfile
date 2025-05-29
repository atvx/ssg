# 使用适配ARM架构的Python基础镜像
FROM python:3.11-slim-bullseye

WORKDIR /app

# 设置 DEBIAN_FRONTEND 为非交互模式，避免构建过程中的用户提示
ENV DEBIAN_FRONTEND=noninteractive

# 安装必要的工具及依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    curl \
    jq \
    unzip \
    procps \
    # 添加SSL证书相关包
    openssl \
    apt-transport-https \
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
    gosu \
    --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 更新CA证书
RUN update-ca-certificates

# 为ARM架构安装Chromium而不是Chrome（ARM架构更容易支持Chromium）
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 创建指向chromium的软链接，以便与期望chrome的代码兼容
RUN ln -sf /usr/bin/chromium /usr/bin/google-chrome \
    && ln -sf /usr/bin/chromedriver /usr/local/bin/chromedriver

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# 预先创建所有需要的目录并设置权限
RUN mkdir -p /app/chrome_user_data \
    && mkdir -p /app/tmp \
    && mkdir -p /tmp/chrome_tmp \
    && mkdir -p /tmp/chrome_data \
    && chmod -R 777 /app/chrome_user_data \
    && chmod -R 777 /app/tmp \
    && chmod -R 777 /tmp/chrome_tmp \
    && chmod -R 777 /tmp/chrome_data

# 环境变量设置
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/local/bin:${PATH}"
ENV HEADLESS=true
ENV CHROME_DISABLE_GPU=true
ENV CHROME_NO_SANDBOX=true
ENV CHROME_DISABLE_DEV_SHM=true
ENV TMP=/tmp/chrome_tmp
# 添加Chromium特定环境变量
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_PATH=/usr/lib/chromium
# 添加SSL相关环境变量
ENV OPENSSL_CONF=/etc/ssl/openssl.cnf

# 添加入口脚本
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# 创建非root用户
RUN useradd --system --create-home --no-log-init --shell /bin/bash appuser

# 确保所有目录权限正确设置
RUN chown -R appuser:appuser /app \
    && chown -R appuser:appuser /tmp/chrome_tmp \
    && chown -R appuser:appuser /tmp/chrome_data \
    && chown -R appuser:appuser /app/chrome_user_data

# 保持root用户运行entrypoint.sh，脚本内部会切换到appuser
# 不要在这里切换到appuser用户

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
