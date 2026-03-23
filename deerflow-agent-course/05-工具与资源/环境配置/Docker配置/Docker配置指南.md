# 🐳 DeerFlow Docker 配置

## 📁 目录结构
```
Docker配置/
├── Dockerfile                    # 主镜像构建
├── Dockerfile.sandbox           # 沙箱镜像
├── Dockerfile.development       # 开发环境镜像
├── docker-compose.yml           # 本地开发环境
├── docker-compose.prod.yml      # 生产环境
└── .dockerignore               # Docker忽略文件
```

## 1. 主镜像 Dockerfile

```dockerfile
# Dockerfile
# DeerFlow 主应用镜像

FROM python:3.12-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_ENV=production

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 2. 沙箱镜像 Dockerfile

```dockerfile
# Dockerfile.sandbox
# DeerFlow 沙箱环境镜像

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 安装沙箱所需的最小依赖
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# 限制资源
RUN echo '* soft nofile 1024' >> /etc/security/limits.conf && \
    echo '* hard nofile 1024' >> /etc/security/limits.conf

# 复制沙箱脚本
COPY sandbox/ /app/sandbox/

# 创建受限用户
RUN useradd -m -u 1001 sandbox && \
    chown -R sandbox:sandbox /app
USER sandbox

# 启动脚本
ENTRYPOINT ["/app/sandbox/entrypoint.sh"]
CMD ["python", "-u", "sandbox_runner.py"]
```

## 3. 开发环境镜像

```dockerfile
# Dockerfile.development
# DeerFlow 开发环境镜像

FROM python:3.12

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    git \
    vim \
    htop \
    tmux \
    man-db \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装开发工具
RUN curl -fsSL https://code-server.dev/install.sh | sh

# 安装 poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# 复制依赖文件
COPY pyproject.toml poetry.lock* ./

# 安装依赖
RUN poetry install --no-root --dev

# 复制代码
COPY . .

# 启动开发服务器
CMD ["poetry", "run", "uvicorn", "src.api:app", "--reload", "--host", "0.0.0.0"]
```

## 4. docker-compose.yml (本地开发)

```yaml
# docker-compose.yml
# DeerFlow 本地开发环境

version: '3.8'

services:
  # 主应用
  deerflow:
    build:
      context: .
      dockerfile: Dockerfile.development
    ports:
      - "8000:8000"
      - "5678:5678"  # debug port
    volumes:
      - .:/app
      - ~/.cache/pip:/root/.cache/pip
    environment:
      - ENV=development
      - LOG_LEVEL=DEBUG
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis
      - postgres
    networks:
      - deerflow-network
    command: >
      sh -c "poetry install && 
             poetry run uvicorn src.api:app --reload --host 0.0.0.0"

  # 沙箱环境
  sandbox:
    build:
      context: .
      dockerfile: Dockerfile.sandbox
    ports:
      - "9000:9000"
    volumes:
      - sandbox-data:/app/data
    environment:
      - SANDBOX_TIMEOUT=300
      - SANDBOX_MEMORY_LIMIT=512m
    networks:
      - deerflow-network

  # Redis 缓存
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    networks:
      - deerflow-network

  # PostgreSQL 数据库
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=deerflow
      - POSTGRES_USER=deerflow
      - POSTGRES_PASSWORD=deerflow_secret
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - deerflow-network

  # Prometheus 监控
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./configs/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - deerflow-network

  # Grafana 可视化
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - deerflow-network

networks:
  deerflow-network:
    driver: bridge

volumes:
  redis-data:
  postgres-data:
  prometheus-data:
  grafana-data:
  sandbox-data:
```

## 5. 生产环境 docker-compose

```yaml
# docker-compose.prod.yml
# DeerFlow 生产环境

version: '3.8'

services:
  # 主应用 - 多副本
  deerflow-api:
    image: deerflow:${VERSION:-latest}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
    ports:
      - "80:8000"
    environment:
      - ENV=production
      - LOG_LEVEL=INFO
      - DATABASE_URL=postgresql://deerflow:${DB_PASSWORD}@postgres:5432/deerflow
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - deerflow-network

  # 沙箱服务
  sandbox:
    image: deerflow-sandbox:${VERSION:-latest}
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 1G
    environment:
      - SANDBOX_TIMEOUT=300
      - SANDBOX_MEMORY_LIMIT=512m
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - deerflow-network

  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=deerflow
      - POSTGRES_USER=deerflow
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U deerflow"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - deerflow-network

  # Redis Cluster
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - deerflow-network

  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./configs/nginx.conf:/etc/nginx/nginx.conf
      - ./configs/ssl:/etc/nginx/ssl
      - nginx-logs:/var/log/nginx
    depends_on:
      - deerflow-api
    restart: unless-stopped
    networks:
      - deerflow-network

  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./configs/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    restart: unless-stopped
    networks:
      - deerflow-network

  # Alertmanager
  alertmanager:
    image: prom/alertmanager:latest
    volumes:
      - ./configs/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    restart: unless-stopped
    networks:
      - deerflow-network

networks:
  deerflow-network:
    driver: overlay

volumes:
  postgres-data:
  redis-data:
  prometheus-data:
  nginx-logs:
```

## 6. .dockerignore

```dockerignore
# Git
.git
.gitignore

# Python
__pycache__
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
.eggs/
dist/
build/

# Virtual environments
venv/
env/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.coverage
htmlcov/
.pytest_cache/
.tox/

# Documentation
docs/_build/
*.md

# Docker
Dockerfile*
docker-compose*.yml
.docker/

# Logs
*.log
logs/

# Environment
.env
.env.*
!.env.example

# Temporary files
*.tmp
*.temp
.DS_Store
```

## 7. requirements.txt

```text
# requirements.txt
# DeerFlow 核心依赖

# Web框架
fastapi==0.109.0
uvicorn[standard]==0.27.0
starlette==0.35.0

# 异步框架
httpx==0.26.0
aiohttp==3.9.1

# 数据验证
pydantic==2.5.3
pydantic-settings==2.1.0

# 数据库
sqlalchemy==2.0.25
asyncpg==0.29.0
alembic==1.13.1

# 缓存
redis==5.0.1
aioredis==2.0.1

# LangChain生态
langchain==0.1.4
langchain-core==0.1.10
langgraph==0.0.20
langchain-openai==0.0.5

# AI模型
openai==1.10.0
anthropic==0.10.0

# 配置管理
pyyaml==6.0.1
python-dotenv==1.0.0

# 日志和监控
structlog==23.2.0
prometheus-client==0.19.0
python-json-logger==2.0.7

# 安全
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# 工具类
tenacity==8.2.3
tiktoken==0.5.2
```

## 8. 使用说明

### 本地开发

```bash
# 启动开发环境
docker-compose up -d

# 查看日志
docker-compose logs -f deerflow

# 进入容器
docker-compose exec deerflow bash

# 停止环境
docker-compose down
```

### 生产部署

```bash
# 构建镜像
docker-compose -f docker-compose.prod.yml build

# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看状态
docker-compose -f docker-compose.prod.yml ps

# 滚动更新
docker-compose -f docker-compose.prod.yml up -d --no-deps --build deerflow-api
```

---

**下一步**：查看 Kubernetes 配置
