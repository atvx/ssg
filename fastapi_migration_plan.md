# 销售数据获取系统 FastAPI 迁移方案（修订版）

## 1. 项目概述

将现有的销售数据获取命令行工具改造为基于FastAPI的RESTful API服务，提供接口获取美团POS系统和多维系统的销售数据，并支持数据合并，采用JWT认证机制和MySQL数据库。

## 2. 技术栈

- **后端框架**：FastAPI
- **数据库**：MySQL
- **ORM**：SQLAlchemy
- **认证**：JWT (JSON Web Token)
- **任务队列**：Celery
- **消息队列/缓存**：Redis
- **验证码通知**：WebSockets
- **浏览器自动化**：Selenium (用于获取美团数据)
- **HTTP客户端**：requests (用于获取多维系统数据)
- **容器化**：Docker + Docker Compose

## 3. 系统架构

```
                                    ┌───────────────┐
                                    │  数据源        │
                                    │ (美团POS/多维) │
                                    └───────┬───────┘
                                            │
                                            ▼
┌─────────────┐    ┌─────────────┐    ┌──────────────┐
│ HTTP客户端   │◄───┤  FastAPI    │◄───┤ 数据获取服务   │
└─────────────┘    └──────┬──────┘    └──────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ MySQL    │    │ Redis    │    │ Celery   │
    └──────────┘    └──────────┘    └──────────┘
```

## 4. 项目结构

```
project/
├── app/                       # FastAPI应用目录
│   ├── __init__.py
│   ├── main.py                # 应用入口
│   ├── api/                   # API路由
│   │   ├── __init__.py
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py        # 认证相关API
│   │   │   ├── sales.py       # 销售数据API
│   │   │   └── tasks.py       # 任务管理API
│   │   └── router.py          # 路由注册
│   ├── core/                  # 核心业务逻辑
│   │   ├── meituan/           # 美团模块(保留原有)
│   │   │   ├── auth.py
│   │   │   ├── browser.py
│   │   │   ├── navigation.py
│   │   │   └── data.py
│   │   └── duowei/            # 多维模块(保留原有)
│   │       ├── api.py
│   │       └── data.py
│   ├── models/                # 数据库模型
│   │   ├── __init__.py
│   │   ├── sales.py           # 销售数据模型
│   │   ├── user.py            # 用户模型
│   │   ├── auth.py            # 认证会话模型
│   │   └── task.py            # 任务模型
│   ├── schemas/               # Pydantic验证模型
│   │   ├── __init__.py
│   │   ├── sales.py           # 销售数据模式
│   │   ├── auth.py            # 认证相关模式
│   │   ├── task.py            # 任务相关模式
│   │   └── user.py            # 用户相关模式
│   ├── services/              # 业务服务
│   │   ├── __init__.py
│   │   ├── meituan_service.py
│   │   ├── duowei_service.py
│   │   ├── data_service.py    # 综合数据服务
│   │   ├── auth_service.py    # 认证服务
│   │   └── browser_service.py
│   ├── db/                    # 数据库
│   │   ├── __init__.py
│   │   ├── database.py        # 数据库连接
│   │   └── crud.py            # 数据库操作
│   ├── utils/                 # 工具函数
│   │   ├── __init__.py
│   │   ├── browser_utils.py
│   │   ├── data_utils.py
│   │   ├── file_utils.py
│   │   ├── security.py        # JWT安全相关
│   │   └── auth_utils.py
│   ├── config/                # 配置
│   │   ├── __init__.py
│   │   └── settings.py
│   └── celery_app/            # Celery配置
│       ├── __init__.py
│       ├── celery.py
│       └── tasks.py
├── scripts/                   # 脚本和工具
├── .env                       # 环境变量
├── requirements.txt           # 依赖
├── docker-compose.yml         # Docker配置
├── Dockerfile                 # Docker构建文件
└── README.md                  # 文档
```

## 5. 数据库模型设计

### 5.1 用户模型
```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    mobile = Column(String(11), unique=True, index=True, nullable=True)
    hashed_password = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 5.2 销售数据模型
```python
class SalesRecord(Base):
    __tablename__ = "sales_records"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True, nullable=False)
    platform = Column(String(20), index=True, nullable=False)  # "meituan" 或 "duowei"
    warehouse_name = Column(String(100), index=True, nullable=False)  # 仓库名称
    income_amt = Column(DECIMAL(10, 2), nullable=False)  # 收入金额
    sales_cart_count = Column(Integer, nullable=False)   # 销售数量
    avg_income_amt = Column(DECIMAL(10, 2), nullable=False)  # 平均收入
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 使用平台+日期+仓库名称作为唯一约束
    __table_args__ = (
        UniqueConstraint('platform', 'date', 'warehouse_name', name='uix_sales_record'),
    )
```

### 5.3 认证会话模型
```python
class AuthSession(Base):
    __tablename__ = "auth_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(20), nullable=False)  # "meituan" 或 "duowei"
    status = Column(String(20), nullable=False)  # "active", "expired", "failed"
    cookies = Column(Text)  # JSON格式的cookies
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    last_used = Column(DateTime)
```

### 5.4 任务模型
```python
class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_type = Column(String(50), nullable=False)  # "fetch_meituan", "fetch_duowei", "fetch_all"
    status = Column(String(20), nullable=False)  # "pending", "running", "completed", "failed"
    progress = Column(Integer, default=0)
    result = Column(Text)  # 存储JSON格式的结果
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # 与用户表关联
    user = relationship("User", back_populates="tasks")
```

## 6. API接口设计

### 6.1 认证与用户API

```
POST   /api/auth/register              - 注册新用户
POST   /api/auth/login                 - 用户登录，获取JWT令牌
POST   /api/auth/refresh-token         - 刷新JWT令牌
GET    /api/auth/me                    - 获取当前用户信息
PUT    /api/auth/me                    - 更新当前用户信息
POST   /api/auth/change-password       - 修改密码
```

### 6.2 销售数据API

```
GET    /api/sales                      - 获取合并后的所有销售数据
GET    /api/sales/{date}               - 获取指定日期的所有销售数据
POST   /api/sales/fetch                - 触发新的销售数据获取任务
GET    /api/sales/platforms            - 获取支持的数据平台列表
GET    /api/sales/warehouses           - 获取所有仓库列表
GET    /api/sales/warehouses/{platform} - 获取指定平台的仓库列表
GET    /api/sales/history              - 获取历史销售数据(支持分页和筛选)
```

### 6.3 平台数据源会话管理API

```
GET    /api/platforms/sessions         - 获取所有平台会话状态
GET    /api/platforms/sessions/{platform} - 获取指定平台会话状态
POST   /api/platforms/meituan/login    - 启动美团登录任务
POST   /api/platforms/duowei/login     - 启动多维系统登录任务
DELETE /api/platforms/sessions/{platform} - 删除指定平台会话
```

### 6.4 任务管理API

```
GET    /api/tasks                      - 获取任务列表
GET    /api/tasks/{id}                 - 获取任务详情
GET    /api/tasks/status/{id}          - 获取任务状态
DELETE /api/tasks/{id}                 - 取消/删除任务
```

### 6.5 美团验证码处理API

```
GET    /api/platforms/meituan/auth-status/{task_id} - 获取美团验证状态
POST   /api/platforms/meituan/verify   - 提交验证码验证
```



## 7 部署方案

### 7.1 Docker Compose配置


### 7.2 环境变量配置

```
# .env
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/salesdb
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```


