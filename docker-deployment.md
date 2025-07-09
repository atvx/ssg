# Docker部署指南 - 销售数据获取系统

本指南详细说明如何在Ubuntu 22.04.5 LTS aarch64架构上使用Docker部署销售数据获取系统。

## 环境需求

- Ubuntu 22.04.5 LTS aarch64架构
- Docker 20.10+ 和 Docker Compose v2.0+
- 已有的MySQL服务
- 已有的Redis服务

## 部署步骤

### 1. 准备工作

确保服务器已安装Docker和Docker Compose：

```bash
# 更新软件包信息
sudo apt-get update

# 安装必要的依赖
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 添加Docker官方GPG密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 设置稳定版仓库
echo \
  "deb [arch=arm64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# 安装Docker Compose
sudo apt-get install -y docker-compose-plugin
```

### 2. 创建环境变量文件

在项目根目录创建`.env`文件：

```bash
# 复制模板文件
cp .env.example .env

# 编辑环境变量
nano .env
```

需要修改的关键环境变量：
```
# 数据库配置 - 填写现有MySQL的连接信息
DATABASE_URL=mysql+pymysql://用户名:密码@MySQL主机地址:3306/数据库名

# Redis配置 - 填写现有Redis的连接信息
REDIS_URL=redis://Redis主机地址:6379/0

# Celery配置
CELERY_BROKER_URL=redis://Redis主机地址:6379/0
CELERY_RESULT_BACKEND=redis://Redis主机地址:6379/0

# 安全配置
SECRET_KEY=生成一个随机密钥

# 浏览器配置
HEADLESS=true
EDGE_USER_DATA_DIR=/app/edge_user_data

# webdriver-manager配置
WDM_LOG_LEVEL=0
WDM_SSL_VERIFY=0
WDM_LOCAL=1
```

### 3. 项目构建与启动

在项目根目录执行以下命令：

```bash
# 构建Docker镜像
docker-compose build

# 启动服务
docker-compose up -d
```

镜像构建可能需要一些时间，请耐心等待。建议使用`-d`参数以守护进程模式运行容器。

### 4. 验证部署

服务启动后，可通过以下方式验证：

```bash
# 查看容器状态
docker-compose ps

# 查看API服务日志
docker-compose logs -f api

# 查看Celery Worker日志
docker-compose logs -f celery_worker
```

访问API文档： http://服务器IP:8000/docs

### 5. 注意事项

#### Microsoft Edge浏览器和EdgeDriver管理

本系统现已集成自动EdgeDriver管理：

- **自动安装**: 容器启动时会自动安装Microsoft Edge浏览器
- **自动管理**: 使用`webdriver-manager`自动下载和管理EdgeDriver
- **版本匹配**: 自动匹配Edge浏览器版本下载对应的EdgeDriver
- **无需手动配置**: 无需手动下载或配置EdgeDriver路径

#### webdriver-manager配置

系统支持以下webdriver-manager配置选项：

```yaml
environment:
  - WDM_LOG_LEVEL=0          # 日志级别（0=关闭详细日志）
  - WDM_SSL_VERIFY=0         # 禁用SSL验证
  - WDM_LOCAL=1              # 使用本地缓存
  - WDM_PRINT_FIRST_LINE=False  # 不打印首行信息
```

#### 数据持久化

配置文件中已设置将`edge_user_data`目录挂载到容器中，确保浏览器会话数据能够持久化：

```yaml
volumes:
  - ./edge_user_data:/app/edge_user_data
```

EdgeDriver缓存也会自动持久化在容器的`~/.wdm`目录中。

#### 网络配置

如果需要通过内部网络连接MySQL和Redis，可能需要调整网络配置：

```yaml
networks:
  app-network:
    driver: bridge
  external-network:
    external: true
    name: existing-network-name
```

### 6. 管理命令

```bash
# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看服务日志
docker-compose logs

# 进入容器
docker-compose exec api bash
docker-compose exec celery_worker bash

# 清理webdriver-manager缓存（如果需要重新下载EdgeDriver）
docker-compose exec api rm -rf ~/.wdm
```

### 7. 故障排除

1. **镜像构建失败**
   - 检查网络连接
   - 确保有足够的存储空间
   - 查看详细构建日志：`docker-compose build --progress=plain`

2. **服务无法启动**
   - 检查环境变量配置
   - 确保MySQL和Redis服务可访问
   - 查看容器日志

3. **数据获取失败**
   - 检查Edge浏览器是否正确安装
   - 确认网络连接正常（用于下载EdgeDriver）
   - 检查目标网站登录凭证是否有效

4. **EdgeDriver相关问题**
   - EdgeDriver现在自动管理，无需手动干预
   - 如遇到版本不匹配，重启容器会自动重新下载
   - 可通过设置`WDM_LOG_LEVEL=1`启用详细日志
   - 网络问题导致下载失败时，检查防火墙和代理设置

5. **Celery任务不执行**
   - 确认Redis连接正确
   - 检查Celery Worker是否正常运行
   - 查看Celery日志以了解详情

### 8. 性能优化建议

1. **webdriver-manager缓存**
   - 首次运行后EdgeDriver会被缓存，后续启动更快
   - 可通过卷映射持久化缓存目录

2. **浏览器性能**
   - 无头模式减少资源消耗
   - 自动禁用不必要的浏览器功能
   - 优化内存使用设置

3. **网络优化**
   - 在内网环境中可设置代理加速下载
   - 使用本地镜像仓库缓存Docker镜像 