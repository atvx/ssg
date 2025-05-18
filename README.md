# 销售数据获取系统API

这是一个基于FastAPI的销售数据获取系统API服务，用于获取并管理销售数据。

## 项目结构

```
.
├── api/                  # API路由和端点
│   ├── endpoints/        # API端点实现
│   └── router.py         # 路由配置
├── celery_app/           # Celery异步任务相关
├── config/               # 配置文件
├── core/                 # 核心功能
├── db/                   # 数据库模型和CRUD操作
│   ├── crud.py           # 数据库CRUD操作
│   └── database.py       # 数据库连接配置
├── models/               # 数据库模型
├── schemas/              # Pydantic模型/Schema
├── services/             # 业务服务
├── utils/                # 工具函数
├── .env                  # 环境变量
├── .gitignore            # Git忽略文件
├── docker-compose.yml    # Docker Compose配置
├── Dockerfile            # Docker配置
├── main.py               # 应用入口
└── requirements.txt      # 依赖项
```

## 功能特性

- 用户认证与授权
- 销售数据采集与管理
- 任务管理与异步处理
- API文档（Swagger UI）

## 环境设置

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 配置环境变量（编辑.env文件）

## 启动应用

```bash
python main.py
```

访问 http://localhost:8000/docs 查看API文档。

## Docker部署

使用Docker Compose:

```bash
docker-compose up -d
```

## 技术栈

- **后端框架**：FastAPI
- **数据库**：MySQL
- **ORM**：SQLAlchemy
- **认证**：JWT (JSON Web Token)
- **任务队列**：Celery
- **消息队列/缓存**：Redis
- **浏览器自动化**：Selenium
- **HTTP客户端**：requests
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
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. 配置环境变量
   
复制`.env.example`文件为`.env`，然后根据实际情况修改配置

4. 运行应用

```bash
uvicorn app.main:app --reload
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

### 任务管理

- `GET /api/tasks` - 获取任务列表
- `GET /api/tasks/{id}` - 获取任务详情
- `GET /api/tasks/status/{id}` - 获取任务状态
- `DELETE /api/tasks/{id}` - 取消/删除任务

## 作者

[Your Name]

## 许可证

[License Information] 