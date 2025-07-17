# Docker 部署指南

本文档提供了使用 Docker 部署销售数据获取系统的详细步骤。

## 系统架构

系统由以下几个主要组件组成：

1. **API 服务**：提供 RESTful API 接口，处理前端请求
2. **Celery Worker**：处理异步任务，如数据抓取
3. **Celery Beat**：定时任务调度器，负责按计划触发任务
4. **Redis**：作为消息代理和结果后端
5. **MySQL**：存储系统数据

## 环境要求

- Docker 20.10.0 或更高版本
- Docker Compose 2.0.0 或更高版本
- 至少 8GB RAM
- 至少 20GB 可用磁盘空间

## 部署步骤

### 1. 准备环境变量文件

创建 `.env` 文件，包含以下环境变量：

```
# 数据库配置
DATABASE_URL=mysql+pymysql://username:password@host:port/dbname

# Redis配置
REDIS_URL=redis://:password@host:port/0
CELERY_BROKER_URL=redis://:password@host:port/0
CELERY_RESULT_BACKEND=redis://:password@host:port/0

# Redis连接参数
REDIS_SOCKET_TIMEOUT=60
REDIS_SOCKET_CONNECT_TIMEOUT=30
REDIS_SOCKET_KEEPALIVE=True
REDIS_RETRY_ON_TIMEOUT=True
REDIS_MAX_CONNECTIONS=20

# Celery连接参数
CELERY_BROKER_CONNECTION_TIMEOUT=60
CELERY_BROKER_CONNECTION_MAX_RETRIES=10
CELERY_BROKER_HEARTBEAT=30
CELERY_BROKER_POOL_LIMIT=10
CELERY_VISIBILITY_TIMEOUT=43200

# 美团账号配置
MEITUAN_PHONE=your_phone
MEITUAN_ORG=your_org
MEITUAN_USERNAME=your_username
MEITUAN_PASSWORD=your_password

# 滑块验证和登录模式
SLIDER_VERIFY_MODE=0
LOGIN_MODE=1

# 安全密钥
SECRET_KEY=your_secret_key
```

### 2. 构建并启动容器

对于生产环境，使用 `docker-compose.prod.yml`：

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

对于开发环境，使用 `docker-compose.yml`：

```bash
docker-compose up -d --build
```

### 3. 验证部署

检查所有容器是否正常运行：

```bash
docker-compose -f docker-compose.prod.yml ps
```

应该看到 `api`、`celery_worker` 和 `celery_beat` 三个容器都处于 `Up` 状态。

### 4. 查看日志

查看 API 服务日志：

```bash
docker-compose -f docker-compose.prod.yml logs -f api
```

查看 Celery Worker 日志：

```bash
docker-compose -f docker-compose.prod.yml logs -f celery_worker
```

查看 Celery Beat 日志：

```bash
docker-compose -f docker-compose.prod.yml logs -f celery_beat
```

## 定时任务配置

系统使用数据库存储定时任务配置，可以通过 API 接口或直接在数据库中管理。

### 默认定时任务

系统启动时会自动创建以下默认定时任务：

1. **上午数据同步**：
   - 时间段：6:00-12:00
   - 频率：每半小时（0分和30分）
   - 任务类型：全平台数据同步

2. **下午数据同步**：
   - 时间段：12:00-23:59
   - 频率：每5分钟
   - 任务类型：全平台数据同步

### 定时任务配置说明

定时任务支持两种调度类型：

1. **crontab**：基于 cron 表达式的定时调度
   - 支持 `minute`, `hour`, `day_of_week`, `day_of_month`, `month_of_year` 字段
   - 分钟字段支持以下格式：
     - `*`：每分钟
     - `*/5`：每5分钟（0, 5, 10, 15...）
     - `0,30`：每小时的0分和30分

2. **interval**：基于时间间隔的调度
   - 使用 `interval_seconds` 字段指定间隔秒数

### 注意事项

- **crontab 类型**的任务在每个匹配的时间点都会执行，不会更新 `last_run_at` 字段
- **interval 类型**的任务会更新 `last_run_at` 字段，下次执行时间为 `last_run_at + interval_seconds`
- 所有任务都可以设置 `start_time` 和 `end_time` 限制执行时间段

## 故障排除

### 定时任务不执行

1. 检查 Celery Beat 容器是否正常运行：
   ```bash
   docker-compose -f docker-compose.prod.yml ps celery_beat
   ```

2. 检查 Celery Beat 日志：
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f celery_beat
   ```

3. 检查数据库中的调度配置是否正确：
   ```sql
   SELECT * FROM task_schedule_configs WHERE enabled = 1;
   ```

4. 检查 crontab 类型任务的 `last_run_at` 字段是否为 NULL：
   ```sql
   SELECT id, name, schedule_type, last_run_at FROM task_schedule_configs WHERE schedule_type = 'crontab';
   ```
   如果不为 NULL，需要手动清除：
   ```sql
   UPDATE task_schedule_configs SET last_run_at = NULL WHERE schedule_type = 'crontab';
   ```

### 任务执行失败

1. 检查 Celery Worker 日志：
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f celery_worker
   ```

2. 检查任务执行记录：
   ```sql
   SELECT * FROM tasks ORDER BY created_at DESC LIMIT 10;
   ```

## 维护操作

### 重启服务

重启所有服务：

```bash
docker-compose -f docker-compose.prod.yml restart
```

重启特定服务：

```bash
docker-compose -f docker-compose.prod.yml restart api
docker-compose -f docker-compose.prod.yml restart celery_worker
docker-compose -f docker-compose.prod.yml restart celery_beat
```

### 更新系统

1. 拉取最新代码：
   ```bash
   git pull
   ```

2. 重新构建并启动容器：
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --build
   ```

### 备份数据

备份数据库：

```bash
docker exec -it $(docker-compose -f docker-compose.prod.yml ps -q db) mysqldump -u username -p dbname > backup.sql
```

备份 Redis 数据：

```bash
docker exec -it $(docker-compose -f docker-compose.prod.yml ps -q redis) redis-cli -a password SAVE
``` 