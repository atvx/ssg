# 销售数据获取系统部署手册

## 部署方式选择

本系统提供两种部署方式：**本地部署**和**Docker部署**。

## 1. 本地部署

### 环境准备
1. Python 3.9+
2. MySQL 数据库
3. Redis 服务
4. Chrome 浏览器（用于数据爬取）

### 安装步骤

1. **克隆代码仓库**
   ```bash
   git clone <repository-url>
   cd ssg
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量**
   - 复制`.env.example`为`.env`（如果存在）
   - 编辑`.env`文件，设置数据库和Redis连接信息：
     ```
     DATABASE_URL=mysql+pymysql://用户名:密码@数据库地址:3306/数据库名
     REDIS_URL=redis://[:密码@]Redis地址:6379/0
     CELERY_BROKER_URL=redis://[:密码@]Redis地址:6379/0
     CELERY_RESULT_BACKEND=redis://[:密码@]Redis地址:6379/0
     ```

5. **启动应用**
   - 启动API服务：
     ```bash
     python run.py
     ```
   - 启动Celery worker（新终端）：
     ```bash
     celery -A celery_app worker --loglevel=info --pool=solo
     ```

6. **访问API文档**
   - 浏览器访问：http://localhost:8000/docs

## 2. Docker部署

### 环境准备
1. Docker
2. Docker Compose

### 部署步骤

1. **克隆代码仓库**
   ```bash
   git clone <repository-url>
   cd ssg
   ```

2. **修改配置**
   - 编辑`docker-compose.yml`文件，根据需要修改数据库和Redis连接信息

3. **启动服务**
   ```bash
   docker-compose up -d
   ```
   这将启动API服务和Celery worker

4. **访问API文档**
   - 浏览器访问：http://localhost:8000/docs

## 端口占用问题解决

如果8000端口被占用，有两种解决方案：

1. **修改本地运行端口**
   ```bash
   # 使用run.py启动时
   python run.py --port 8080
   
   # 或直接使用uvicorn
   uvicorn main:app --host 0.0.0.0 --port 8080
   ```

2. **修改Docker端口映射**
   - 编辑`docker-compose.yml`文件中的端口映射：
     ```yaml
     ports:
       - "8080:8000"  # 将主机8080端口映射到容器8000端口
     ```

## 系统使用指南

### 主要API端点

1. **获取销售数据**
   - 同步数据：`POST http://localhost:8000/api/sales/fetch`
   - 获取所有销售数据：`GET http://localhost:8000/api/sales`
   - 获取指定日期数据：`GET http://localhost:8000/api/sales/{date}`

2. **任务管理**
   - 获取任务列表：`GET http://localhost:8000/api/tasks`
   - 获取任务状态：`GET http://localhost:8000/api/tasks/status/{id}`

### 常见问题

1. **API服务无法启动**
   - 检查端口占用情况
   - 检查数据库连接配置
   - 查看日志输出错误信息

2. **Celery worker无法启动**
   - 检查Redis连接配置
   - 确认Celery配置正确

3. **数据获取失败**
   - 检查Chrome浏览器安装情况
   - 确认网络连接正常
   - 检查目标网站登录凭证是否有效 