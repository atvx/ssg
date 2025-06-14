# 销售数据获取系统API

这是一个基于FastAPI的销售数据获取系统API服务，用于获取并管理销售数据。

## 项目结构

```
.
├── api/                  # API路由和端点
│   ├── endpoints/        # API端点实现
│   └── router.py         # 路由配置
├── celery_app/           # Celery异步任务相关
├── chrome_user_data/     # Chrome浏览器用户数据目录
├── config/               # 配置文件
├── core/                 # 核心功能
├── db/                   # 数据库模型和CRUD操作
│   ├── crud.py           # 数据库CRUD操作
│   └── database.py       # 数据库连接配置
├── models/               # 数据库模型
├── schemas/              # Pydantic模型/Schema
├── services/             # 业务服务
├── utils/                # 工具函数
├── ws/                   # WebSocket相关功能
├── .env                  # 环境变量
├── .gitignore            # Git忽略文件
├── docker-compose.yml    # Docker Compose配置
├── Dockerfile            # Docker配置
├── main.py               # 应用主入口
├── run.py                # 应用启动脚本
├── meituan.py            # 美团数据获取模块
└── requirements.txt      # 依赖项
```

## 功能特性

- 用户认证与授权
- 销售数据采集与管理
- 任务管理与异步处理
- 实时通知（WebSocket）
- API文档（Swagger UI）
- 多平台数据获取支持（美团等）

## 环境设置

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 配置环境变量（编辑.env文件）

主要环境变量包括：
```
# 应用配置
APP_NAME=销售数据获取系统
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

## 启动应用

使用run.py脚本启动应用：

```bash
python run.py
```

或者直接使用uvicorn：

```bash
uvicorn main:app --reload
```

访问 http://localhost:8000/docs 查看API文档。

## Docker部署

使用Docker Compose:

```bash
docker-compose up -d
```

这将启动以下服务：
- API服务 (FastAPI)
- Celery Worker (异步任务处理)
- MySQL数据库
- Redis (缓存和消息队列)

## 技术栈

- **后端框架**：FastAPI
- **数据库**：MySQL
- **ORM**：SQLAlchemy
- **认证**：JWT (JSON Web Token)
- **任务队列**：Celery
- **消息队列/缓存**：Redis
- **浏览器自动化**：Selenium
- **HTTP客户端**：requests
- **WebSocket**：FastAPI WebSocket
- **容器化**：Docker + Docker Compose

## 安装和运行

### 本地开发环境

1. 克隆仓库

```bash
git clone <repository-url>
cd ssg
```

2. 创建虚拟环境并安装依赖

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. 配置环境变量
   
复制`.env.example`文件为`.env`，然后根据实际情况修改配置

4. 运行应用

```bash
python run.py
```

### Docker环境

1. 使用Docker Compose构建和运行

```bash
docker-compose up -d
```

2. 初始化数据库（首次运行）

```bash
docker-compose exec api alembic upgrade head
```

## API文档

启动应用后，可以访问以下地址查看API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 主要API端点

### 认证

- `POST /api/auth/register` - 注册新用户
- `POST /api/auth/login` - 用户登录，获取JWT令牌
- `GET /api/auth/me` - 获取当前用户信息

### 销售数据

- `GET /api/sales` - 获取所有销售数据
- `GET /api/sales/{date}` - 获取指定日期的销售数据
- `POST /api/sales/fetch` - 触发数据获取任务
- `GET /api/sales/platforms` - 获取支持的数据平台列表
- `GET /api/sales/warehouses` - 获取所有仓库列表
- `GET /api/sales/daily-report/export` - 导出日报（Excel/PDF/PNG格式）

### 任务管理

- `GET /api/tasks` - 获取任务列表
- `GET /api/tasks/{id}` - 获取任务详情
- `GET /api/tasks/status/{id}` - 获取任务状态
- `DELETE /api/tasks/{id}` - 取消/删除任务

### WebSocket

- `WS /ws` - WebSocket连接端点，用于实时通知

## 作者

atvx

## 许可证

MIT License

Copyright (c) 2023-2024 销售数据系统开发团队

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. 