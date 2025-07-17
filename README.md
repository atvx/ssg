# 销售数据系统

## 项目说明

本项目是一个销售数据同步系统，用于从多个平台（美团、多维等）获取销售数据并进行统一管理。系统支持自动定时同步、数据分析及可视化展示。

## 功能特性

- 用户认证与授权管理
- 多平台销售数据采集与管理
- 自动定时数据同步任务
- 任务管理与异步处理
- 实时通知（WebSocket）
- 完整的API文档（Swagger UI）
- 销售数据统计与分析

## 项目结构

```
.
├── api/                  # API路由和端点
│   ├── endpoints/        # API端点实现
│   └── router.py         # 路由配置
├── celery_app/           # Celery异步任务相关
├── config/               # 配置文件
├── core/                 # 核心功能模块
│   ├── meituan/          # 美团平台相关功能
│   └── duowei/           # 多维平台相关功能
├── db/                   # 数据库相关
│   ├── crud.py           # 数据库CRUD操作
│   └── database.py       # 数据库连接配置
├── models/               # 数据库模型
├── schemas/              # Pydantic模型/Schema
├── services/             # 业务服务层
├── utils/                # 工具函数
├── ws/                   # WebSocket相关功能
├── edge_user_data/       # Edge浏览器用户数据目录
├── main.py               # 应用主入口
├── run.py                # 应用启动脚本
└── requirements.txt      # 依赖项
```

## 安装与配置

### 环境要求

- Python 3.8+
- MySQL 数据库
- Redis 服务
- Microsoft Edge 浏览器（用于数据抓取）

### 安装步骤

1. 克隆仓库
   ```bash
   git clone [仓库地址]
   cd ssg
   ```

2. 创建虚拟环境并安装依赖
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

3. 配置环境变量
   ```bash
   cp .env.example .env
   # 编辑.env文件，设置必要的环境变量
   ```

   主要环境变量包括：
   ```
   # 应用配置
   APP_NAME=销售数据系统
   DEBUG=True
   API_V1_STR=/api

   # 数据库配置
   DATABASE_URL=mysql+pymysql://user:password@localhost:3306/salesdb

   # Redis配置
   REDIS_URL=redis://localhost:6379/0

   # Celery配置
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0

   # JWT配置
   SECRET_KEY=your-secret-key
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ```

## 运行应用

### 启动主应用

```bash
python run.py
```

或者使用uvicorn：
```bash
uvicorn main:app --reload
```

### Windows上运行Celery（重要）

在Windows环境下运行Celery需要特别注意以下几点：

1. **启动Celery Worker**

   Windows上必须使用`--pool=solo`选项以避免多进程引起的权限问题：
   ```bash
   # 激活虚拟环境
   .\.venv\Scripts\activate
   
   # 启动Worker（Windows专用命令）
   celery -A celery_app.celery worker --pool=solo --loglevel=info
   ```

2. **启动Celery Beat**

   在另一个命令行窗口中启动Beat调度器：
   ```bash
   .\.venv\Scripts\activate
   celery -A celery_app.celery beat --loglevel=info
   ```

3. **常见问题解决**

   - 如果遇到`PermissionError`或`句柄无效`错误，确保使用了`--pool=solo`选项
   - 如果仍有问题，可以尝试安装并使用eventlet：
     ```bash
     pip install eventlet
     celery -A celery_app.celery worker --pool=eventlet --loglevel=info
     ```
   - 确保Redis服务正在运行且配置正确

4. **定时任务配置**

   系统默认配置了两个定时任务：
   - 上午 (6:00-12:00): 每半小时同步一次数据
   - 下午 (12:00-23:59): 每10分钟同步一次数据

   可以通过API接口动态调整这些配置。

## API文档

启动应用后，可以访问以下地址查看API文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 主要API端点

### 认证相关
- `POST /api/auth/login` - 用户登录，获取JWT令牌
- `GET /api/auth/me` - 获取当前用户信息

### 销售数据相关
- `GET /api/sales` - 获取销售数据列表
- `POST /api/sales/fetch` - 触发数据获取任务
- `GET /api/sales/daily-report/export` - 导出日报

### 任务管理相关
- `GET /api/tasks` - 获取任务列表
- `GET /api/tasks/status/{id}` - 获取任务状态

### 定时任务配置相关
- `GET /api/tasks/schedule` - 获取定时任务配置列表
- `POST /api/tasks/schedule` - 创建新的定时任务配置
- `PUT /api/tasks/schedule/{id}` - 更新定时任务配置
- `DELETE /api/tasks/schedule/{id}` - 删除定时任务配置

## Docker部署

```bash
docker-compose up -d
```

这将启动以下服务：
- API服务 (FastAPI)
- Celery Worker
- Celery Beat
- MySQL数据库
- Redis服务

## 技术栈

- **后端框架**：FastAPI
- **数据库**：MySQL + SQLAlchemy ORM
- **认证**：JWT (JSON Web Token)
- **任务队列**：Celery + Redis
- **浏览器自动化**：Selenium
- **实时通信**：WebSocket
- **容器化**：Docker + Docker Compose

## 作者

atvx

## 许可证

MIT License

Copyright (c) 2023-2024 销售数据系统开发团队 