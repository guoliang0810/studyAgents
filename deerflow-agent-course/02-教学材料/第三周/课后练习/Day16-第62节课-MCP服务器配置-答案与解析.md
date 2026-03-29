# Day 16 - 第62节课：MCP服务器配置 - 答案与解析

## 📋 答案概述

本答案提供课后练习的参考实现和详细解析，帮助您理解MCP服务器配置的最佳实践。每个任务都包含：
1. **参考实现**：完整的代码或配置示例
2. **设计思路**：实现背后的设计决策和考虑因素
3. **关键要点**：需要特别注意的技术要点
4. **常见错误**：可能遇到的问题和解决方法

## 🎯 任务1：MCP配置YAML设计

### 参考实现：mcp_config.yaml

```yaml
# MCP服务器配置示例
version: "1.0.0"
description: "DeerFlow AI Agent系统MCP服务器配置"
environment: "${ENVIRONMENT:development}"

# 全局配置
global:
  log_level: "INFO"
  max_retries: 3
  retry_delay: 2.0
  health_check_interval: 30
  enable_monitoring: true
  monitoring_interval: 60
  enable_auto_recovery: true
  auto_recovery_delay: 10.0
  enable_metrics: true
  metrics_port: 9090

# 服务器配置
servers:
  filesystem:
    command: "npx"
    args:
      - "@modelcontextprotocol/server-filesystem"
      - "/workspace"
    env:
      MCP_PORT: 3001
      LOG_LEVEL: "info"
      ALLOWED_PATHS: "/workspace,/tmp,/data"
      MAX_FILE_SIZE: "10485760"  # 10MB
      ENABLE_CORS: "true"
    auto_start: true
    health_check: "http://localhost:3001/health"
    timeout: 30.0
    working_dir: "/workspace"
    description: "文件系统MCP服务器，提供安全的文件访问功能"
    max_retries: 3
    retry_delay: 2.0
    depends_on: []
    user: "appuser"  # 模拟用户权限
    group: "appgroup"
    security_context:
      read_only: false
      allow_symlinks: true
      allow_hidden: false
      max_depth: 10

  sql:
    command: "npx"
    args:
      - "@modelcontextprotocol/server-sql"
      - "${DATABASE_URL}"
    env:
      MCP_PORT: 3002
      LOG_LEVEL: "info"
      DB_MAX_CONNECTIONS: "10"
      DB_TIMEOUT: "30"
      DB_POOL_SIZE: "5"
      DB_IDLE_TIMEOUT: "300"
      DB_STATEMENT_TIMEOUT: "60"
    auto_start: true
    health_check: "http://localhost:3002/health"
    timeout: 45.0
    working_dir: "/var/lib/mcp-sql"
    description: "SQL数据库MCP服务器，提供数据库访问功能"
    max_retries: 5
    retry_delay: 3.0
    depends_on: []
    security_context:
      ssl_mode: "prefer"
      ssl_cert: "${DB_SSL_CERT}"
      ssl_key: "${DB_SSL_KEY}"
      ssl_root_cert: "${DB_SSL_ROOT_CERT}"

  github:
    command: "npx"
    args:
      - "@modelcontextprotocol/server-github"
    env:
      MCP_PORT: 3003
      LOG_LEVEL: "info"
      GITHUB_TOKEN: "${GITHUB_TOKEN}"
      GITHUB_API_URL: "https://api.github.com"
      GITHUB_GRAPHQL_URL: "https://api.github.com/graphql"
      RATE_LIMIT_ENABLED: "true"
      RATE_LIMIT_PER_HOUR: "5000"
      CACHE_ENABLED: "true"
      CACHE_TTL: "300"
    auto_start: false  # GitHub服务器包含敏感令牌，建议手动启动
    health_check: "http://localhost:3003/health"
    timeout: 60.0
    working_dir: "/var/lib/mcp-github"
    description: "GitHub MCP服务器，提供GitHub API访问功能"
    max_retries: 2  # 令牌相关失败重试次数少
    retry_delay: 5.0
    depends_on: ["filesystem"]  # 可能需要文件系统存储缓存
    security_context:
      token_scope: "repo,read:user,read:org"
      allow_private_repos: true
      max_repo_size: "1000000"  # 1MB
      enable_webhooks: false

# 网络配置
network:
  bind_address: "0.0.0.0"
  enable_ssl: false
  ssl_cert: "${SSL_CERT_PATH}"
  ssl_key: "${SSL_KEY_PATH}"
  cors_allowed_origins:
    - "http://localhost:3000"
    - "https://deerflow.example.com"
  rate_limiting:
    enabled: true
    requests_per_minute: 100
    burst_size: 20

# 监控配置
monitoring:
  enabled: true
  prometheus_endpoint: "/metrics"
  health_check_endpoint: "/health"
  metrics:
    - name: "server_start_time"
      help: "服务器启动时间"
      type: "gauge"
    - name: "server_uptime"
      help: "服务器运行时间"
      type: "counter"
    - name: "requests_total"
      help: "总请求数"
      type: "counter"
    - name: "errors_total"
      help: "总错误数"
      type: "counter"
  alerting:
    enabled: true
    rules:
      - alert: "MCP服务器宕机"
        expr: "up == 0"
        for: "1m"
        labels:
          severity: "critical"
        annotations:
          summary: "MCP服务器 {{ $labels.instance }} 已宕机"
          description: "MCP服务器 {{ $labels.instance }} 已经宕机超过1分钟"
      - alert: "高错误率"
        expr: "rate(errors_total[5m]) > 0.1"
        for: "5m"
        labels:
          severity: "warning"
        annotations:
          summary: "MCP服务器 {{ $labels.instance }} 错误率过高"
          description: "MCP服务器 {{ $labels.instance }} 错误率超过10%持续5分钟"
```

### 设计思路

1. **分层配置结构**：
   - **全局配置**：适用于所有服务器的通用设置
   - **服务器配置**：每个服务器的具体配置
   - **网络配置**：网络相关设置（SSL、CORS、速率限制）
   - **监控配置**：监控和告警设置

2. **环境变量支持**：
   - 敏感信息（令牌、密码）使用环境变量
   - 支持默认值：`${VAR_NAME:default_value}`
   - 环境特定配置：`${ENVIRONMENT:development}`

3. **安全考虑**：
   - GitHub服务器`auto_start: false`，避免自动启动暴露令牌
   - 文件系统路径限制，防止目录遍历攻击
   - 用户/组权限模拟，限制服务器权限

4. **可靠性设计**：
   - 每个服务器独立的`max_retries`和`retry_delay`
   - 健康检查配置，确保服务器可用性
   - 依赖关系管理，确保依赖服务器先启动

### 关键要点

1. **端口管理**：
   - 为每个服务器分配唯一端口（3001、3002、3003）
   - 避免端口冲突，确保服务器可以同时运行

2. **环境变量设计**：
   - 必需环境变量：`GITHUB_TOKEN`、`DATABASE_URL`
   - 可选环境变量：`LOG_LEVEL`、`DB_MAX_CONNECTIONS`
   - 安全环境变量：不在配置文件中硬编码敏感信息

3. **健康检查配置**：
   - 每个服务器配置独立的健康检查URL
   - 超时时间根据服务器类型调整（文件系统30秒，GitHub 60秒）

4. **依赖关系管理**：
   - `depends_on`字段定义服务器启动顺序
   - GitHub服务器可能依赖文件系统服务器存储缓存

5. **监控集成**：
   - Prometheus指标端点配置
   - 告警规则定义，自动检测服务器问题

### 常见错误

1. **端口冲突**：
   ```
   错误：Address already in use: ('0.0.0.0', 3001)
   解决方案：更改端口号或停止占用端口的进程
   ```

2. **环境变量未设置**：
   ```
   错误：KeyError: 'GITHUB_TOKEN'
   解决方案：设置环境变量或提供默认值
   ```

3. **路径权限问题**：
   ```
   错误：Permission denied: '/workspace'
   解决方案：检查目录权限或更改working_dir
   ```

4. **健康检查失败**：
   ```
   错误：Health check failed for server 'filesystem'
   解决方案：检查服务器是否真的启动，增加超时时间
   ```

5. **依赖循环**：
   ```
   错误：Circular dependency detected: A -> B -> A
   解决方案：检查depends_on配置，消除循环依赖
   ```

## 🎯 任务2：MCP服务器管理器实现

### 参考实现：mcp_server_manager.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP服务器管理器实现
Day 16 - 第62节课：MCP服务器配置 - 课后练习答案

本实现提供了完整的MCP服务器管理功能，包括：
1. 单个MCP服务器的启动、停止、健康检查
2. 多个MCP服务器的批量管理
3. 异步子进程管理和输出收集
4. 服务器状态实时跟踪
"""

import os
import sys
import asyncio
import logging
import signal
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import aiohttp
import yaml

# ============================================================================
# 数据类定义
# ============================================================================

class ServerStatus(Enum):
    """服务器状态枚举"""
    STOPPED = "stopped"      # 已停止
    STARTING = "starting"    # 启动中
    RUNNING = "running"      # 运行中
    ERROR = "error"          # 错误
    STOPPING = "stopping"    # 停止中


@dataclass
class ServerConfig:
    """服务器配置数据类"""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    port: int = 3000
    auto_start: bool = True
    health_check: Optional[str] = None
    timeout: float = 30.0
    working_dir: Optional[str] = None
    description: str = ""
    max_retries: int = 3
    retry_delay: float = 2.0


class MCPServer:
    """单个MCP服务器管理类"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.status = ServerStatus.STOPPED
        self.process: Optional[asyncio.subprocess.Process] = None
        self.start_time: Optional[float] = None
        self.pid: Optional[int] = None
        self.logger = logging.getLogger(f"mcp.{config.name}")
        
    async def start(self) -> bool:
        """启动MCP服务器"""
        try:
            self.status = ServerStatus.STARTING
            self.logger.info(f"正在启动服务器 {self.config.name}")
            
            # 构建环境变量
            env = os.environ.copy()
            env.update(self.config.env)
            
            # 构建命令行
            cmd = [self.config.command] + self.config.args
            
            # 工作目录
            cwd = self.config.working_dir or os.getcwd()
            
            # 启动异步子进程
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL
            )
            
            self.pid = self.process.pid
            self.start_time = time.time()
            
            # 启动输出收集任务
            asyncio.create_task(self._collect_output())
            
            # 等待服务器就绪
            success = await self.wait_for_ready(self.config.timeout)
            
            if success:
                self.status = ServerStatus.RUNNING
                self.logger.info(f"服务器 {self.config.name} 启动成功 (PID: {self.pid})")
                return True
            else:
                self.status = ServerStatus.ERROR
                self.logger.error(f"服务器 {self.config.name} 启动超时")
                await self.stop()
                return False
                
        except Exception as e:
            self.status = ServerStatus.ERROR
            self.logger.error(f"启动服务器 {self.config.name} 失败: {e}")
            return False
    
    async def stop(self, timeout: float = 5.0) -> bool:
        """停止MCP服务器"""
        if not self.process:
            self.status = ServerStatus.STOPPED
            return True
            
        try:
            self.status = ServerStatus.STOPPING
            self.logger.info(f"正在停止服务器 {self.config.name} (PID: {self.pid})")
            
            # 发送SIGTERM信号
            self.process.terminate()
            
            try:
                # 等待进程退出
                await asyncio.wait_for(self.process.wait(), timeout=timeout)
                self.logger.info(f"服务器 {self.config.name} 已停止")
                self.status = ServerStatus.STOPPED
                return True
            except asyncio.TimeoutError:
                # 超时后强制终止
                self.logger.warning(f"服务器 {self.config.name} 停止超时，强制终止")
                self.process.kill()
                await self.process.wait()
                self.status = ServerStatus.STOPPED
                return True
                
        except Exception as e:
            self.logger.error(f"停止服务器 {self.config.name} 失败: {e}")
            self.status = ServerStatus.ERROR
            return False
    
    async def health_check(self) -> bool:
        """健康检查"""
        # 检查进程是否存活
        if self.process and self.process.returncode is not None:
            self.logger.error(f"服务器 {self.config.name} 进程已退出，返回码: {self.process.returncode}")
            self.status = ServerStatus.ERROR
            return False
        
        # 如果有健康检查URL，检查端点
        if self.config.health_check:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.config.health_check, timeout=5.0) as resp:
                        if resp.status == 200:
                            return True
                        else:
                            self.logger.warning(f"服务器 {self.config.name} 健康检查失败: HTTP {resp.status}")
                            return False
            except Exception as e:
                self.logger.warning(f"服务器 {self.config.name} 健康检查异常: {e}")
                return False
        
        # 默认检查进程是否运行
        return self.process is not None and self.process.returncode is None
    
    async def wait_for_ready(self, timeout: float = 30.0) -> bool:
        """等待服务器就绪"""
        start_time = time.time()
        check_interval = 0.5
        
        while time.time() - start_time < timeout:
            if await self.health_check():
                return True
            await asyncio.sleep(check_interval)
        
        return False
    
    async def _collect_output(self):
        """收集进程的输出"""
        if not self.process:
            return
            
        try:
            # 并行收集stdout和stderr
            stdout_task = asyncio.create_task(self._read_stream(self.process.stdout, "stdout"))
            stderr_task = asyncio.create_task(self._read_stream(self.process.stderr, "stderr"))
            
            await asyncio.gather(stdout_task, stderr_task)
        except Exception as e:
            self.logger.error(f"收集输出失败: {e}")
    
    async def _read_stream(self, stream, stream_name):
        """读取输出流"""
        if not stream:
            return
            
        while True:
            line = await stream.readline()
            if not line:
                break
            line_text = line.decode('utf-8', errors='replace').rstrip()
            self.logger.debug(f"[{self.config.name}.{stream_name}] {line_text}")


class MCPServerManager:
    """MCP服务器管理器类"""
    
    def __init__(self, config_path: str = "mcp_config.yaml"):
        self.config_path = config_path
        self.servers: Dict[str, MCPServer] = {}
        self.logger = logging.getLogger("mcp.manager")
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # 解析全局配置
            global_config = config_data.get('global', {})
            self.log_level = global_config.get('log_level', 'INFO')
            self.max_retries = global_config.get('max_retries', 3)
            self.retry_delay = global_config.get('retry_delay', 2.0)
            
            # 解析服务器配置
            servers_config = config_data.get('servers', {})
            for server_name, server_config in servers_config.items():
                config = ServerConfig(
                    name=server_name,
                    command=server_config['command'],
                    args=server_config.get('args', []),
                    env=server_config.get('env', {}),
                    port=server_config.get('port', 3000),
                    auto_start=server_config.get('auto_start', True),
                    health_check=server_config.get('health_check'),
                    timeout=server_config.get('timeout', 30.0),
                    working_dir=server_config.get('working_dir'),
                    description=server_config.get('description', ''),
                    max_retries=server_config.get('max_retries', self.max_retries),
                    retry_delay=server_config.get('retry_delay', self.retry_delay)
                )
                self.servers[server_name] = MCPServer(config)
                
            self.logger.info(f"已加载 {len(self.servers)} 个服务器配置")
            
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            raise
    
    async def start_all(self) -> Dict[str, bool]:
        """启动所有auto_start为true的服务器"""
        results = {}
        
        # 筛选需要自动启动的服务器
        auto_start_servers = {
            name: server for name, server in self.servers.items() 
            if server.config.auto_start
        }
        
        self.logger.info(f"准备启动 {len(auto_start_servers)} 个自动启动服务器")
        
        # 并行启动服务器
        tasks = []
        for name, server in auto_start_servers.items():
            task = asyncio.create_task(self._start_server_with_retry(name))
            tasks.append((name, task))
        
        # 等待所有启动任务完成
        for name, task in tasks:
            try:
                success = await task
                results[name] = success
                if success:
                    self.logger.info(f"服务器 {name} 启动成功")
                else:
                    self.logger.error(f"服务器 {name} 启动失败")
            except Exception as e:
                self.logger.error(f"启动服务器 {name} 异常: {e}")
                results[name] = False
        
        return results
    
    async def stop_all(self) -> Dict[str, bool]:
        """停止所有正在运行的服务器"""
        results = {}
        
        for name, server in self.servers.items():
            if server.status in [ServerStatus.RUNNING, ServerStatus.STARTING, ServerStatus.ERROR]:
                try:
                    success = await server.stop()
                    results[name] = success
                    if success:
                        self.logger.info(f"服务器 {name} 停止成功")
                    else:
                        self.logger.warning(f"服务器 {name} 停止失败")
                except Exception as e:
                    self.logger.error(f"停止服务器 {name} 异常: {e}")
                    results[name] = False
        
        return results
    
    async def start_server(self, server_name: str) -> bool:
        """启动单个服务器"""
        if server_name not in self.servers:
            self.logger.error(f"服务器 {server_name} 不存在")
            return False
        
        return await self._start_server_with_retry(server_name)
    
    async def stop_server(self, server_name: str) -> bool:
        """停止单个服务器"""
        if server_name not in self.servers:
            self.logger.error(f"服务器 {server_name} 不存在")
            return False
        
        server = self.servers[server_name]
        return await server.stop()
    
    async def health_check_all(self) -> Dict[str, bool]:
        """检查所有服务器的健康状态"""
        results = {}
        
        for name, server in self.servers.items():
            if server.status == ServerStatus.RUNNING:
                try:
                    healthy = await server.health_check()
                    results[name] = healthy
                    if not healthy:
                        server.status = ServerStatus.ERROR
                        self.logger.warning(f"服务器 {name} 健康检查失败")
                except Exception as e:
                    self.logger.error(f"检查服务器 {name} 健康状态异常: {e}")
                    results[name] = False
        
        return results
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """列出所有服务器状态信息"""
        server_list = []
        
        for name, server in self.servers.items():
            server_info = {
                'name': name,
                'status': server.status.value,
                'config': {
                    'command': server.config.command,
                    'args': server.config.args,
                    'port': server.config.port,
                    'auto_start': server.config.auto_start,
                    'description': server.config.description
                }
            }
            
            if server.pid:
                server_info['pid'] = server.pid
            if server.start_time:
                server_info['uptime'] = time.time() - server.start_time
                
            server_list.append(server_info)
        
        return server_list
    
    async def _start_server_with_retry(self, server_name: str, max_retries: int = None) -> bool:
        """带重试的服务器启动"""
        if server_name not in self.servers:
            return False
        
        server = self.servers[server_name]
        max_retries = max_retries or server.config.max_retries
        
        for attempt in range(max_retries):
            try:
                success = await server.start()
                if success:
                    return True
                
                # 指数退避延迟
                delay = server.config.retry_delay * (2 ** attempt)
                self.logger.info(f"启动尝试 {attempt + 1} 失败，等待 {delay:.1f} 秒后重试")
                await asyncio.sleep(delay)
                
            except Exception as e:
                self.logger.error(f"启动尝试 {attempt + 1} 失败: {e}")
        
        self.logger.error(f"服务器 {server_name} 启动失败，已达到最大重试次数 {max_retries}")
        return False
```

### 设计思路

1. **异步架构设计**：
   - 使用Python的`asyncio`库实现非阻塞的服务器管理
   - 异步子进程启动和监控，避免阻塞主线程
   - 并行启动多个服务器，提高启动效率

2. **状态管理机制**：
   - 明确的服务器状态枚举（STOPPED、STARTING、RUNNING、ERROR、STOPPING）
   - 状态转换逻辑清晰，避免状态混乱
   - 实时更新状态，支持外部查询

3. **进程生命周期管理**：
   - 优雅启动：构建完整环境变量和命令行，收集输出流
   - 优雅停止：先SIGTERM，超时后SIGKILL，确保资源释放
   - 进程监控：监控进程退出，自动更新状态

4. **健康检查策略**：
   - 多级健康检查：进程存活检查 + HTTP端点检查
   - 可配置的健康检查URL，适应不同服务器类型
   - 超时机制，避免长时间阻塞

5. **错误处理和重试**：
   - 带指数退避的重试机制，提高启动成功率
   - 详细的错误日志，便于问题诊断
   - 异常隔离，单个服务器失败不影响其他服务器

### 关键要点

1. **异步子进程管理**：
   - 使用`asyncio.create_subprocess_exec`创建异步子进程
   - 正确设置环境变量和工作目录
   - 及时收集标准输出和错误输出，避免缓冲区阻塞

2. **状态一致性**：
   - 状态更新必须与实际情况一致
   - 状态转换需要处理边界情况（如启动过程中停止）
   - 并发访问状态时需要确保线程安全（本实现使用单线程asyncio）

3. **资源管理**：
   - 进程资源需要正确释放（文件描述符、内存等）
   - 网络连接需要及时关闭（HTTP客户端连接池）
   - 日志系统需要合理配置，避免磁盘空间耗尽

4. **性能优化**：
   - 并行启动无依赖关系的服务器
   - 健康检查使用连接池复用HTTP连接
   - 输出收集使用异步流读取，避免阻塞

5. **可扩展性**：
   - 支持通过继承`MCPServer`类扩展新的服务器类型
   - 配置驱动，可以通过YAML配置增加新的服务器
   - 插件化设计，支持自定义健康检查逻辑

### 常见错误

1. **端口冲突错误**：
   ```
   错误：Address already in use: ('0.0.0.0', 3001)
   解决方案：检查端口占用情况，修改配置使用不同端口
   ```

2. **命令不存在错误**：
   ```
   错误：FileNotFoundError: [Errno 2] No such file or directory: 'npx'
   解决方案：确保命令在PATH中，或使用绝对路径
   ```

3. **权限不足错误**：
   ```
   错误：PermissionError: [Errno 13] Permission denied
   解决方案：检查文件和目录权限，或使用合适的用户权限
   ```

4. **环境变量缺失错误**：
   ```
   错误：KeyError: 'GITHUB_TOKEN'
   解决方案：确保必需的环境变量已设置
   ```

5. **健康检查超时错误**：
   ```
   错误：TimeoutError: Health check timeout
   解决方案：增加超时时间，或检查服务器启动是否成功
   ```

6. **进程资源泄漏错误**：
   ```
   错误：ResourceWarning: unclosed resource
   解决方案：确保正确关闭进程和网络连接，使用`async with`管理资源
   ```

## 🎯 任务3：服务器生命周期管理

### 参考实现：server_lifecycle.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务器生命周期管理
Day 16 - 第62节课：MCP服务器配置 - 课后练习答案

本实现提供了完整的服务器生命周期管理功能，包括：
1. 依赖关系解析和启动顺序控制
2. 并发启动优化和无依赖服务器并行启动
3. 服务器状态持久化和恢复机制
4. 生命周期钩子机制（启动前/后、停止前/后回调）
5. 自动监控和故障恢复
"""

import asyncio
import logging
import json
import os
import time
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque

# ============================================================================
# 数据类定义
# ============================================================================

class LifecycleHook(Enum):
    """生命周期钩子类型"""
    BEFORE_START = "before_start"
    AFTER_START = "after_start"
    BEFORE_STOP = "before_stop"
    AFTER_STOP = "after_stop"


@dataclass
class LifecycleConfig:
    """生命周期配置"""
    server_name: str
    depends_on: List[str] = field(default_factory=list)
    auto_restart: bool = True
    restart_delay: float = 5.0
    max_restart_attempts: int = 3
    startup_timeout: float = 30.0
    shutdown_timeout: float = 10.0


class ServerLifecycleManager:
    """服务器生命周期管理器"""
    
    def __init__(self, server_manager, config_file: str = "lifecycle_config.yaml"):
        self.server_manager = server_manager
        self.config_file = config_file
        self.configs: Dict[str, LifecycleConfig] = {}
        self.hooks: Dict[LifecycleHook, Dict[str, List[Callable]]] = {
            hook: defaultdict(list) for hook in LifecycleHook
        }
        self.monitor_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
        self.logger = logging.getLogger("lifecycle.manager")
        self.state_file = "server_state.json"
        
        self._load_config()
    
    def _load_config(self):
        """加载生命周期配置"""
        try:
            # 这里简化实现，实际应从YAML文件加载
            # 本示例使用硬编码配置，实际项目中应从配置文件加载
            self.configs = {
                "filesystem": LifecycleConfig(
                    server_name="filesystem",
                    depends_on=[],
                    auto_restart=True,
                    restart_delay=2.0,
                    max_restart_attempts=3
                ),
                "sql": LifecycleConfig(
                    server_name="sql",
                    depends_on=["filesystem"],
                    auto_restart=True,
                    restart_delay=3.0,
                    max_restart_attempts=5
                ),
                "github": LifecycleConfig(
                    server_name="github",
                    depends_on=["filesystem", "sql"],
                    auto_restart=False,  # GitHub服务器需要令牌，不自动重启
                    restart_delay=5.0,
                    max_restart_attempts=2
                )
            }
            self.logger.info(f"已加载 {len(self.configs)} 个生命周期配置")
            
        except Exception as e:
            self.logger.error(f"加载生命周期配置失败: {e}")
            raise
    
    def add_hook(self, server_name: str, hook_type: LifecycleHook, callback: Callable):
        """添加生命周期钩子"""
        self.hooks[hook_type][server_name].append(callback)
        self.logger.debug(f"为服务器 {server_name} 添加 {hook_type.value} 钩子")
    
    async def _execute_hooks(self, server_name: str, hook_type: LifecycleHook):
        """执行生命周期钩子"""
        if server_name not in self.hooks[hook_type]:
            return
        
        for callback in self.hooks[hook_type][server_name]:
            try:
                self.logger.debug(f"执行 {server_name} 的 {hook_type.value} 钩子")
                if asyncio.iscoroutinefunction(callback):
                    await callback(server_name)
                else:
                    callback(server_name)
            except Exception as e:
                self.logger.error(f"执行 {server_name} 的 {hook_type.value} 钩子失败: {e}")
    
    def resolve_dependencies(self, server_name: str) -> List[str]:
        """解析服务器的依赖关系，返回拓扑排序的启动顺序"""
        if server_name not in self.configs:
            return [server_name]
        
        # 使用Kahn算法进行拓扑排序
        in_degree = defaultdict(int)
        graph = defaultdict(list)
        all_servers = set()
        
        # 构建依赖图
        for s_name, config in self.configs.items():
            all_servers.add(s_name)
            for dep in config.depends_on:
                graph[dep].append(s_name)
                in_degree[s_name] += 1
        
        # 确保所有服务器都有入度计数
        for server in all_servers:
            if server not in in_degree:
                in_degree[server] = 0
        
        # 拓扑排序
        queue = deque([s for s in all_servers if in_degree[s] == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检查是否有循环依赖
        if len(result) != len(all_servers):
            raise ValueError(f"检测到循环依赖，无法解析启动顺序")
        
        # 只返回目标服务器及其依赖
        target_index = result.index(server_name)
        return result[:target_index + 1]
    
    async def start_with_dependencies(self, server_name: str) -> bool:
        """启动服务器及其依赖"""
        if server_name not in self.server_manager.servers:
            self.logger.error(f"服务器 {server_name} 不存在")
            return False
        
        try:
            # 解析依赖关系
            dependency_order = self.resolve_dependencies(server_name)
            self.logger.info(f"启动顺序: {dependency_order}")
            
            # 按顺序启动服务器
            for dep_name in dependency_order:
                if dep_name == server_name:
                    self.logger.info(f"启动目标服务器: {dep_name}")
                else:
                    self.logger.info(f"启动依赖服务器: {dep_name}")
                
                # 执行启动前钩子
                await self._execute_hooks(dep_name, LifecycleHook.BEFORE_START)
                
                # 启动服务器
                success = await self.server_manager.start_server(dep_name)
                
                if success:
                    # 执行启动后钩子
                    await self._execute_hooks(dep_name, LifecycleHook.AFTER_START)
                    self.logger.info(f"服务器 {dep_name} 启动成功")
                else:
                    self.logger.error(f"服务器 {dep_name} 启动失败")
                    return False
            
            self.logger.info(f"服务器 {server_name} 及其依赖启动完成")
            return True
            
        except Exception as e:
            self.logger.error(f"启动服务器 {server_name} 及其依赖失败: {e}")
            return False
    
    async def graceful_shutdown(self, timeout: float = 30.0) -> bool:
        """优雅关闭所有服务器"""
        self.logger.info("开始优雅关闭所有服务器")
        
        # 停止监控
        if self.is_monitoring:
            await self.stop_monitoring()
        
        # 获取所有服务器的依赖逆序（反向拓扑排序）
        all_servers = list(self.configs.keys())
        try:
            shutdown_order = self.resolve_dependencies(all_servers[-1])
            shutdown_order.reverse()  # 按依赖逆序停止
        except:
            shutdown_order = all_servers
        
        self.logger.info(f"关闭顺序: {shutdown_order}")
        
        success = True
        start_time = time.time()
        
        for server_name in shutdown_order:
            if time.time() - start_time > timeout:
                self.logger.error("优雅关闭超时")
                success = False
                break
            
            if server_name not in self.server_manager.servers:
                continue
            
            server = self.server_manager.servers[server_name]
            if server.status not in ["RUNNING", "STARTING"]:
                continue
            
            try:
                # 执行停止前钩子
                await self._execute_hooks(server_name, LifecycleHook.BEFORE_STOP)
                
                # 停止服务器
                stop_success = await server.stop(timeout=5.0)
                
                if stop_success:
                    # 执行停止后钩子
                    await self._execute_hooks(server_name, LifecycleHook.AFTER_STOP)
                    self.logger.info(f"服务器 {server_name} 停止成功")
                else:
                    self.logger.warning(f"服务器 {server_name} 停止失败")
                    success = False
                    
            except Exception as e:
                self.logger.error(f"停止服务器 {server_name} 异常: {e}")
                success = False
        
        # 保存状态
        await self.save_state()
        
        self.logger.info("优雅关闭完成" if success else "优雅关闭部分失败")
        return success
    
    async def restart_server(self, server_name: str) -> bool:
        """重启单个服务器"""
        if server_name not in self.server_manager.servers:
            self.logger.error(f"服务器 {server_name} 不存在")
            return False
        
        self.logger.info(f"重启服务器 {server_name}")
        
        try:
            # 停止服务器
            server = self.server_manager.servers[server_name]
            stop_success = await server.stop()
            
            if not stop_success:
                self.logger.warning(f"停止服务器 {server_name} 失败，尝试强制重启")
            
            # 等待一段时间
            await asyncio.sleep(2.0)
            
            # 启动服务器
            start_success = await self.server_manager.start_server(server_name)
            
            if start_success:
                self.logger.info(f"服务器 {server_name} 重启成功")
                return True
            else:
                self.logger.error(f"服务器 {server_name} 重启失败")
                return False
                
        except Exception as e:
            self.logger.error(f"重启服务器 {server_name} 异常: {e}")
            return False
    
    async def monitor_servers(self):
        """监控服务器状态，自动恢复失败的服务器"""
        self.is_monitoring = True
        self.logger.info("开始监控服务器状态")
        
        check_interval = 10.0  # 每10秒检查一次
        
        while self.is_monitoring:
            try:
                # 检查所有服务器状态
                for server_name, config in self.configs.items():
                    if not config.auto_restart:
                        continue
                    
                    if server_name not in self.server_manager.servers:
                        continue
                    
                    server = self.server_manager.servers[server_name]
                    
                    # 如果服务器应该运行但状态为ERROR，尝试重启
                    if server.status == "ERROR":
                        self.logger.warning(f"检测到服务器 {server_name} 状态为 ERROR，尝试重启")
                        
                        # 记录重启尝试
                        if not hasattr(server, 'restart_attempts'):
                            server.restart_attempts = 0
                        
                        if server.restart_attempts < config.max_restart_attempts:
                            server.restart_attempts += 1
                            self.logger.info(f"第 {server.restart_attempts} 次重启尝试")
                            
                            restart_success = await self.restart_server(server_name)
                            if restart_success:
                                server.restart_attempts = 0
                                self.logger.info(f"服务器 {server_name} 重启成功")
                            else:
                                self.logger.error(f"服务器 {server_name} 重启失败")
                        else:
                            self.logger.error(f"服务器 {server_name} 已达到最大重启尝试次数，停止自动重启")
                
                # 保存当前状态
                await self.save_state()
                
                # 等待下一次检查
                await asyncio.sleep(check_interval)
                
            except asyncio.CancelledError:
                self.logger.info("监控任务被取消")
                break
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(check_interval)
    
    async def start_monitoring(self):
        """启动监控任务"""
        if self.monitor_task and not self.monitor_task.done():
            self.logger.warning("监控任务已在运行")
            return
        
        self.monitor_task = asyncio.create_task(self.monitor_servers())
        self.logger.info("监控任务已启动")
    
    async def stop_monitoring(self):
        """停止监控任务"""
        self.is_monitoring = False
        
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("监控任务已停止")
    
    async def save_state(self):
        """保存服务器状态"""
        try:
            state = {}
            for server_name, server in self.server_manager.servers.items():
                state[server_name] = {
                    'status': server.status.value if hasattr(server.status, 'value') else str(server.status),
                    'pid': server.pid,
                    'start_time': server.start_time,
                    'config': {
                        'auto_start': server.config.auto_start,
                        'description': server.config.description
                    }
                }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=str)
            
            self.logger.debug(f"服务器状态已保存到 {self.state_file}")
            
        except Exception as e:
            self.logger.error(f"保存服务器状态失败: {e}")
    
    async def restore_state(self):
        """恢复服务器状态"""
        if not os.path.exists(self.state_file):
            self.logger.info(f"状态文件 {self.state_file} 不存在，无需恢复")
            return
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            self.logger.info(f"从 {self.state_file} 恢复服务器状态")
            
            for server_name, server_state in state.items():
                if server_name not in self.server_manager.servers:
                    continue
                
                # 如果服务器之前是运行状态，尝试重新启动
                if server_state.get('status') == 'RUNNING':
                    config = self.configs.get(server_name)
                    if config and config.auto_restart:
                        self.logger.info(f"恢复启动服务器 {server_name}")
                        await self.server_manager.start_server(server_name)
            
            self.logger.info("服务器状态恢复完成")
            
        except Exception as e:
            self.logger.error(f"恢复服务器状态失败: {e}")
```

### 设计思路

1. **依赖关系管理**：
   - 使用有向无环图（DAG）表示服务器依赖关系
   - 拓扑排序算法（Kahn算法）确定启动顺序
   - 依赖逆序确定停止顺序，确保优雅关闭

2. **并发启动优化**：
   - 无依赖关系的服务器可以并行启动
   - 使用异步任务实现真正的并发启动
   - 启动顺序控制确保依赖服务器先启动

3. **状态持久化**：
   - 定期保存服务器状态到JSON文件
   - 支持系统重启后自动恢复服务器状态
   - 状态信息包括运行状态、PID、启动时间等

4. **生命周期钩子**：
   - 四种钩子类型：启动前、启动后、停止前、停止后
   - 支持同步和异步回调函数
   - 钩子执行错误隔离，不影响主流程

5. **自动监控和恢复**：
   - 定期检查服务器健康状态
   - 自动重启失败的服务器（可配置）
   - 最大重启尝试次数限制，避免无限重启

### 关键要点

1. **依赖关系解析**：
   - 必须检测循环依赖，避免死锁
   - 拓扑排序算法需要正确处理孤立节点
   - 依赖关系应存储在配置中，而不是硬编码

2. **优雅关闭机制**：
   - 按依赖逆序停止服务器
   - 每个服务器有独立的停止超时
   - 超时后强制终止，但记录警告

3. **状态管理**：
   - 状态保存应定期进行，避免数据丢失
   - 状态恢复应考虑服务器配置变化
   - 状态文件需要妥善处理并发访问

4. **监控策略**：
   - 监控频率应可配置，避免资源消耗过大
   - 自动重启应考虑服务器间的依赖关系
   - 监控循环需要正确处理取消信号

5. **错误处理**：
   - 单个服务器失败不应影响其他服务器
   - 监控循环异常应有重试机制
   - 钩子执行错误应有隔离机制

### 常见错误

1. **循环依赖错误**：
   ```
   错误：Circular dependency detected: A -> B -> A
   解决方案：检查depends_on配置，消除循环依赖
   ```

2. **依赖服务器不存在错误**：
   ```
   错误：Dependency server 'nonexistent' does not exist
   解决方案：确保所有依赖的服务器都在配置中定义
   ```

3. **状态文件损坏错误**：
   ```
   错误：JSONDecodeError: Expecting value: line 1 column 1 (char 0)
   解决方案：检查状态文件完整性，或删除损坏的文件
   ```

4. **钩子执行超时错误**：
   ```
   错误：TimeoutError: Hook execution timeout
   解决方案：优化钩子函数性能，或增加超时时间
   ```

5. **监控资源泄漏错误**：
   ```
   错误：Too many open files
   解决方案：确保监控循环正确关闭资源，增加文件描述符限制
   ```

## 🎯 任务4：错误处理和重试机制

### 参考实现：error_handler.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
错误处理和重试机制
Day 16 - 第62节课：MCP服务器配置 - 课后练习答案

本实现提供了健壮的错误处理和重试机制，包括：
1. 带指数退避的启动重试机制
2. 健康检查失败的自愈机制
3. 进程异常监控和自动重启
4. 资源泄漏防护和清理机制
"""

import asyncio
import logging
import time
import signal
import psutil  # 需要安装: pip install psutil
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import traceback
import resource

# ============================================================================
# 数据类定义
# ============================================================================

class ErrorSeverity(Enum):
    """错误严重程度"""
    INFO = "info"        # 信息性错误，不影响功能
    WARNING = "warning"  # 警告性错误，可能影响功能
    ERROR = "error"      # 错误，功能受影响但可恢复
    CRITICAL = "critical"  # 严重错误，需要人工干预


@dataclass
class ErrorContext:
    """错误上下文信息"""
    timestamp: float
    server_name: str
    error_type: str
    severity: ErrorSeverity
    message: str
    stack_trace: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    recovery_action: Optional[str] = None


class ExponentialBackoffRetry:
    """指数退避重试机制"""
    
    def __init__(self, base_delay: float = 2.0, max_delay: float = 60.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.logger = logging.getLogger("retry")
    
    async def execute_with_retry(
        self,
        operation: Callable,
        operation_name: str,
        max_retries: int = 3,
        should_retry: Optional[Callable[[Exception], bool]] = None
    ) -> Any:
        """执行带指数退避重试的操作"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"执行 {operation_name}，尝试 {attempt + 1}/{max_retries}")
                
                if asyncio.iscoroutinefunction(operation):
                    result = await operation()
                else:
                    result = operation()
                
                self.logger.info(f"{operation_name} 执行成功")
                return result
                
            except Exception as e:
                last_exception = e
                
                # 检查是否需要重试
                if should_retry and not should_retry(e):
                    self.logger.error(f"{operation_name} 失败且不可重试: {e}")
                    raise
                
                # 计算指数退避延迟
                delay = self._calculate_backoff(attempt)
                
                # 最后一次尝试不重试，直接抛出异常
                if attempt == max_retries - 1:
                    self.logger.error(f"{operation_name} 达到最大重试次数 {max_retries}，最终失败: {e}")
                    raise
                
                self.logger.warning(f"{operation_name} 尝试 {attempt + 1} 失败: {e}，等待 {delay:.1f} 秒后重试")
                await asyncio.sleep(delay)
        
        # 理论上不会执行到这里
        raise last_exception
    
    def _calculate_backoff(self, attempt: int) -> float:
        """计算指数退避延迟"""
        delay = self.base_delay * (2 ** attempt)
        return min(delay, self.max_delay)


class ServerErrorHandler:
    """服务器错误处理器"""
    
    def __init__(self, server_manager):
        self.server_manager = server_manager
        self.logger = logging.getLogger("error.handler")
        self.retry_strategy = ExponentialBackoffRetry()
        self.error_history: List[ErrorContext] = []
        self.max_history_size = 1000
        
    async def start_with_retry(self, server_name: str, max_retries: int = 3) -> bool:
        """带重试的服务器启动"""
        async def start_operation():
            return await self.server_manager.start_server(server_name)
        
        def should_retry(e: Exception) -> bool:
            # 以下错误类型应该重试
            retryable_errors = [
                "TimeoutError",
                "ConnectionError",
                "OSError",
                "subprocess.TimeoutExpired"
            ]
            
            error_type = type(e).__name__
            self.logger.debug(f"错误类型: {error_type}，是否可重试: {error_type in retryable_errors}")
            return error_type in retryable_errors
        
        try:
            success = await self.retry_strategy.execute_with_retry(
                operation=start_operation,
                operation_name=f"启动服务器 {server_name}",
                max_retries=max_retries,
                should_retry=should_retry
            )
            return success
            
        except Exception as e:
            self._record_error(
                server_name=server_name,
                error_type=type(e).__name__,
                severity=ErrorSeverity.ERROR,
                message=f"启动失败: {e}",
                stack_trace=traceback.format_exc(),
                retry_count=max_retries,
                recovery_action="手动检查服务器配置和状态"
            )
            return False
    
    async def auto_heal_server(self, server_name: str) -> bool:
        """自动恢复失败的服务器"""
        if server_name not in self.server_manager.servers:
            self.logger.error(f"服务器 {server_name} 不存在")
            return False
        
        server = self.server_manager.servers[server_name]
        
        self.logger.info(f"开始自动恢复服务器 {server_name}")
        
        try:
            # 步骤1：检查当前状态
            current_status = server.status
            self.logger.info(f"服务器 {server_name} 当前状态: {current_status}")
            
            # 步骤2：如果正在运行但健康检查失败，先停止
            if current_status == "RUNNING":
                healthy = await server.health_check()
                if not healthy:
                    self.logger.warning(f"服务器 {server_name} 运行但健康检查失败，先停止")
                    await server.stop(timeout=5.0)
                    await asyncio.sleep(2.0)  # 等待清理
                    current_status = "STOPPED"
            
            # 步骤3：如果已停止，尝试启动
            if current_status in ["STOPPED", "ERROR"]:
                self.logger.info(f"尝试启动服务器 {server_name}")
                success = await self.start_with_retry(server_name, max_retries=2)
                
                if success:
                    self._record_error(
                        server_name=server_name,
                        error_type="AutoHealSuccess",
                        severity=ErrorSeverity.INFO,
                        message="自动恢复成功",
                        recovery_action="无"
                    )
                    return True
                else:
                    self._record_error(
                        server_name=server_name,
                        error_type="AutoHealFailed",
                        severity=ErrorSeverity.ERROR,
                        message="自动恢复失败，已达到最大重试次数",
                        recovery_action="需要人工干预"
                    )
                    return False
            
            # 步骤4：如果状态异常，记录但不处理
            else:
                self.logger.warning(f"服务器 {server_name} 状态异常: {current_status}，跳过自动恢复")
                return False
                
        except Exception as e:
            self._record_error(
                server_name=server_name,
                error_type=type(e).__name__,
                severity=ErrorSeverity.ERROR,
                message=f"自动恢复过程中发生错误: {e}",
                stack_trace=traceback.format_exc(),
                recovery_action="需要人工检查"
            )
            return False
    
    async def monitor_processes(self):
        """监控所有服务器进程状态"""
        self.logger.info("开始监控服务器进程状态")
        
        check_interval = 5.0  # 每5秒检查一次
        
        while True:
            try:
                for server_name, server in self.server_manager.servers.items():
                    if not server.process:
                        continue
                    
                    # 检查进程是否存活
                    process = server.process
                    if process.returncode is not None:
                        self.logger.warning(f"服务器 {server_name} 进程已退出，返回码: {process.returncode}")
                        
                        # 记录错误
                        self._record_error(
                            server_name=server_name,
                            error_type="ProcessExited",
                            severity=ErrorSeverity.ERROR,
                            message=f"进程异常退出，返回码: {process.returncode}",
                            recovery_action="尝试自动重启"
                        )
                        
                        # 更新服务器状态
                        server.status = "ERROR"
                        
                        # 尝试自动恢复（如果配置了自动重启）
                        config = getattr(server, 'config', None)
                        if config and getattr(config, 'auto_restart', False):
                            self.logger.info(f"尝试自动重启服务器 {server_name}")
                            await self.auto_heal_server(server_name)
                
                # 检查资源使用情况
                await self._check_resource_usage()
                
                # 等待下一次检查
                await asyncio.sleep(check_interval)
                
            except asyncio.CancelledError:
                self.logger.info("进程监控任务被取消")
                break
            except Exception as e:
                self.logger.error(f"进程监控异常: {e}")
                await asyncio.sleep(check_interval)
    
    async def _check_resource_usage(self):
        """检查资源使用情况"""
        try:
            # 获取当前进程资源使用
            memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if memory_usage > 100 * 1024 * 1024:  # 100MB
                self.logger.warning(f"内存使用较高: {memory_usage / 1024 / 1024:.1f}MB")
            
            # 检查所有服务器进程的资源使用
            for server_name, server in self.server_manager.servers.items():
                if not server.process or not server.pid:
                    continue
                
                try:
                    # 使用psutil获取进程信息
                    proc = psutil.Process(server.pid)
                    
                    # 检查CPU使用率
                    cpu_percent = proc.cpu_percent(interval=0.1)
                    if cpu_percent > 80:  # 80% CPU
                        self.logger.warning(f"服务器 {server_name} CPU使用率高: {cpu_percent}%")
                    
                    # 检查内存使用
                    memory_info = proc.memory_info()
                    if memory_info.rss > 50 * 1024 * 1024:  # 50MB
                        self.logger.warning(f"服务器 {server_name} 内存使用高: {memory_info.rss / 1024 / 1024:.1f}MB")
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # 进程已退出或无权限访问
                    pass
                    
        except Exception as e:
            self.logger.debug(f"检查资源使用失败: {e}")
    
    def _record_error(
        self,
        server_name: str,
        error_type: str,
        severity: ErrorSeverity,
        message: str,
        stack_trace: Optional[str] = None,
        retry_count: int = 0,
        recovery_action: Optional[str] = None
    ):
        """记录错误到历史"""
        error_context = ErrorContext(
            timestamp=time.time(),
            server_name=server_name,
            error_type=error_type,
            severity=severity,
            message=message,
            stack_trace=stack_trace,
            retry_count=retry_count,
            recovery_action=recovery_action
        )
        
        self.error_history.append(error_context)
        
        # 限制历史记录大小
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
        
        # 根据严重程度记录日志
        log_method = {
            ErrorSeverity.INFO: self.logger.info,
            ErrorSeverity.WARNING: self.logger.warning,
            ErrorSeverity.ERROR: self.logger.error,
            ErrorSeverity.CRITICAL: self.logger.critical
        }.get(severity, self.logger.error)
        
        log_message = f"[{server_name}] {error_type}: {message}"
        if recovery_action:
            log_message += f" | 恢复动作: {recovery_action}"
        
        log_method(log_message)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        if not self.error_history:
            return {"total_errors": 0, "by_server": {}, "by_severity": {}}
        
        by_server = {}
        by_severity = {}
        
        for error in self.error_history:
            # 按服务器统计
            if error.server_name not in by_server:
                by_server[error.server_name] = {
                    "total": 0,
                    "by_severity": {sev.value: 0 for sev in ErrorSeverity}
                }
            by_server[error.server_name]["total"] += 1
            by_server[error.server_name]["by_severity"][error.severity.value] += 1
            
            # 按严重程度统计
            if error.severity.value not in by_severity:
                by_severity[error.severity.value] = 0
            by_severity[error.severity.value] += 1
        
        return {
            "total_errors": len(self.error_history),
            "by_server": by_server,
            "by_severity": by_severity,
            "recent_errors": [
                {
                    "timestamp": error.timestamp,
                    "server": error.server_name,
                    "type": error.error_type,
                    "severity": error.severity.value,
                    "message": error.message[:100]  # 截断长消息
                }
                for error in self.error_history[-10:]  # 最近10个错误
            ]
        }
    
    async def cleanup_resources(self):
        """清理资源，防止泄漏"""
        self.logger.info("开始清理资源")
        
        # 清理所有服务器的进程资源
        for server_name, server in self.server_manager.servers.items():
            if server.process:
                try:
                    # 检查进程是否还在运行
                    if server.process.returncode is None:
                        server.process.terminate()
                        try:
                            await asyncio.wait_for(server.process.wait(), timeout=2.0)
                        except (asyncio.TimeoutError, ProcessLookupError):
                            pass
                except Exception as e:
                    self.logger.debug(f"清理服务器 {server_name} 资源失败: {e}")
        
        # 清理错误历史
        self.error_history.clear()
        
        self.logger.info("资源清理完成")


class HealthCheckFailureHandler:
    """健康检查失败处理器"""
    
    def __init__(self, error_handler: ServerErrorHandler):
        self.error_handler = error_handler
        self.logger = logging.getLogger("health.check")
        self.failure_count: Dict[str, int] = {}
        self.max_consecutive_failures = 3
    
    async def handle_health_check_failure(self, server_name: str) -> bool:
        """处理健康检查失败"""
        if server_name not in self.failure_count:
            self.failure_count[server_name] = 0
        
        self.failure_count[server_name] += 1
        failure_count = self.failure_count[server_name]
        
        self.logger.warning(f"服务器 {server_name} 健康检查失败，连续失败次数: {failure_count}")
        
        # 记录错误
        self.error_handler._record_error(
            server_name=server_name,
            error_type="HealthCheckFailure",
            severity=ErrorSeverity.WARNING,
            message=f"健康检查失败，连续失败次数: {failure_count}",
            recovery_action="等待恢复或重启"
        )
        
        # 如果连续失败次数达到阈值，尝试恢复
        if failure_count >= self.max_consecutive_failures:
            self.logger.error(f"服务器 {server_name} 健康检查连续失败 {failure_count} 次，尝试自动恢复")
            
            success = await self.error_handler.auto_heal_server(server_name)
            
            if success:
                self.logger.info(f"服务器 {server_name} 自动恢复成功")
                self.failure_count[server_name] = 0  # 重置计数器
                return True
            else:
                self.logger.error(f"服务器 {server_name} 自动恢复失败")
                return False
        
        return False
    
    def reset_failure_count(self, server_name: str):
        """重置健康检查失败计数器"""
        if server_name in self.failure_count:
            self.failure_count[server_name] = 0
            self.logger.debug(f"重置服务器 {server_name} 的健康检查失败计数器")
```

### 设计思路

1. **分层错误处理**：
   - **信息性错误**：记录日志，不影响功能
   - **警告性错误**：可能影响功能，需要监控
   - **错误**：功能受影响，自动尝试恢复
   - **严重错误**：需要人工干预

2. **指数退避重试**：
   - 避免"惊群效应"，减少对失败服务的压力
   - 可配置的基础延迟和最大延迟
   - 支持自定义重试条件判断

3. **自动恢复机制**：
   - 多步骤恢复：检查状态 → 停止 → 等待 → 启动
   - 支持配置驱动的恢复策略（哪些服务器可自动恢复）
   - 恢复过程有详细日志和错误记录

4. **进程监控**：
   - 定期检查进程状态和资源使用
   - 检测异常退出并自动重启
   - 资源使用监控，防止内存泄漏和CPU过载

5. **健康检查失败处理**：
   - 连续失败计数，避免偶发性失败触发恢复
   - 阈值触发自动恢复机制
   - 成功恢复后重置计数器

### 关键要点

1. **错误分类和记录**：
   - 错误需要包含足够的上下文信息（时间、服务器、类型、堆栈等）
   - 错误历史需要限制大小，避免内存泄漏
   - 错误记录应支持后续分析和监控

2. **重试策略设计**：
   - 不同错误类型应有不同的重试策略
   - 指数退避参数需要根据实际场景调整
   - 重试条件判断函数应允许自定义

3. **自动恢复安全**：
   - 自动恢复前应检查服务器状态
   - 恢复过程应有超时机制
   - 恢复失败应有明确的错误记录和通知

4. **资源监控**：
   - 进程资源监控需要处理权限问题
   - 资源阈值应可配置
   - 监控频率应平衡准确性和性能

5. **健康检查失败处理**：
   - 连续失败计数需要持久化，防止重启后丢失
   - 恢复成功后及时重置计数器
   - 阈值配置应考虑服务器类型和重要性

### 常见错误

1. **指数退避无限延迟错误**：
   ```
   错误：延迟计算溢出，导致无限等待
   解决方案：设置最大延迟上限，避免指数增长过大
   ```

2. **进程监控权限错误**：
   ```
   错误：psutil.AccessDenied: 无法访问进程信息
   解决方案：以适当权限运行，或处理权限异常
   ```

3. **自动恢复循环错误**：
   ```
   错误：服务器反复失败和恢复，形成循环
   解决方案：设置最大恢复尝试次数，超过后停止自动恢复
   ```

4. **资源泄漏监控遗漏错误**：
   ```
   错误：监控遗漏了某些资源泄漏情况
   解决方案：定期审查资源监控逻辑，确保覆盖所有关键资源
   ```

5. **健康检查误报错误**：
   ```
   错误：网络波动导致健康检查误报失败
   解决方案：增加连续失败阈值，或实现更智能的健康检查
   ```

## 🎯 任务5：环境变量注入和配置解析

### 参考实现：environment_variables.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量注入和配置解析
Day 16 - 第62节课：MCP服务器配置 - 课后练习答案

本实现提供了完整的环境变量注入和配置解析功能，包括：
1. 环境变量解析：支持${VAR_NAME}和${VAR_NAME:default}格式
2. 配置模板渲染：将环境变量注入到配置模板中
3. 环境验证：验证必需环境变量是否设置
4. 配置加密：敏感配置的加密和解密（模拟实现）
"""

import os
import re
import logging
import json
import yaml
import base64
import hashlib
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
from cryptography.fernet import Fernet  # 需要安装: pip install cryptography

# ============================================================================
# 数据类定义
# ============================================================================

@dataclass
class EnvironmentVariable:
    """环境变量定义"""
    name: str
    value: Optional[str] = None
    required: bool = False
    description: str = ""
    default_value: Optional[str] = None
    sensitive: bool = False


class EnvironmentVariableResolver:
    """环境变量解析器"""
    
    # 匹配 ${VAR_NAME} 或 ${VAR_NAME:default} 格式的正则表达式
    ENV_VAR_PATTERN = re.compile(r'\$\{([^}:]+)(?::([^}]+))?\}')
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("env.resolver")
    
    def resolve(self, text: str, env_vars: Optional[Dict[str, str]] = None) -> str:
        """解析文本中的环境变量引用"""
        if not text or not isinstance(text, str):
            return text
        
        # 使用提供的环境变量或系统环境变量
        env_dict = env_vars or os.environ.copy()
        
        def replace_match(match):
            var_name = match.group(1)
            default_value = match.group(2)  # 可能为None
            
            # 查找环境变量值
            value = env_dict.get(var_name)
            
            if value is not None:
                self.logger.debug(f"解析环境变量: ${var_name} -> {self._mask_sensitive(var_name, value)}")
                return value
            elif default_value is not None:
                self.logger.debug(f"使用环境变量默认值: ${var_name} -> {default_value}")
                return default_value
            else:
                # 环境变量未设置且无默认值
                error_msg = f"环境变量 {var_name} 未设置且无默认值"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
        
        # 替换所有匹配的环境变量引用
        return self.ENV_VAR_PATTERN.sub(replace_match, text)
    
    def resolve_config(self, config: Any, env_vars: Optional[Dict[str, str]] = None) -> Any:
        """递归解析配置中的所有环境变量"""
        if isinstance(config, str):
            return self.resolve(config, env_vars)
        elif isinstance(config, dict):
            resolved = {}
            for key, value in config.items():
                resolved[key] = self.resolve_config(value, env_vars)
            return resolved
        elif isinstance(config, list):
            return [self.resolve_config(item, env_vars) for item in config]
        else:
            # 数字、布尔值等直接返回
            return config
    
    def validate_required_vars(self, config: Dict) -> List[str]:
        """验证必需环境变量是否已设置"""
        missing_vars = []
        
        def find_required_vars(obj, path=""):
            if isinstance(obj, str):
                # 查找所有环境变量引用
                matches = self.ENV_VAR_PATTERN.findall(obj)
                for var_name, default_value in matches:
                    # 如果没有默认值，则视为必需环境变量
                    if default_value is None:
                        full_path = f"{path}.{var_name}" if path else var_name
                        if var_name not in missing_vars:
                            missing_vars.append(var_name)
                            
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    find_required_vars(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{path}[{i}]"
                    find_required_vars(item, new_path)
        
        find_required_vars(config)
        
        # 检查缺失的环境变量是否在系统环境中设置
        actually_missing = []
        for var_name in missing_vars:
            if var_name not in os.environ:
                actually_missing.append(var_name)
        
        if actually_missing:
            self.logger.error(f"缺失必需环境变量: {actually_missing}")
        
        return actually_missing
    
    def extract_env_vars(self, config: Dict) -> List[EnvironmentVariable]:
        """从配置中提取所有环境变量定义"""
        env_vars = {}
        
        def extract_from_obj(obj):
            if isinstance(obj, str):
                matches = self.ENV_VAR_PATTERN.findall(obj)
                for var_name, default_value in matches:
                    if var_name not in env_vars:
                        env_vars[var_name] = EnvironmentVariable(
                            name=var_name,
                            default_value=default_value,
                            required=default_value is None,
                            description=f"从配置中提取的环境变量"
                        )
                        
            elif isinstance(obj, dict):
                for value in obj.values():
                    extract_from_obj(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_from_obj(item)
        
        extract_from_obj(config)
        
        # 更新现有值
        for var_name, env_var in env_vars.items():
            if var_name in os.environ:
                env_var.value = os.environ[var_name]
        
        return list(env_vars.values())
    
    def _mask_sensitive(self, var_name: str, value: str) -> str:
        """掩码敏感信息（用于日志）"""
        sensitive_keywords = ['TOKEN', 'PASSWORD', 'SECRET', 'KEY', 'CREDENTIAL']
        
        if any(keyword in var_name.upper() for keyword in sensitive_keywords):
            if len(value) > 4:
                return value[:2] + '*' * (len(value) - 4) + value[-2:]
            else:
                return '***'
        else:
            return value


class ConfigTemplateRenderer:
    """配置模板渲染器"""
    
    def __init__(self, resolver: Optional[EnvironmentVariableResolver] = None):
        self.resolver = resolver or EnvironmentVariableResolver()
        self.logger = logging.getLogger("config.renderer")
    
    def render(self, template_path: str, output_path: str, env_vars: Optional[Dict[str, str]] = None):
        """渲染配置模板"""
        try:
            self.logger.info(f"渲染配置模板: {template_path} -> {output_path}")
            
            # 读取模板文件
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # 确定文件类型（YAML或JSON）
            file_ext = Path(template_path).suffix.lower()
            
            if file_ext in ['.yaml', '.yml']:
                # 解析YAML模板
                template_data = yaml.safe_load(template_content)
                # 解析环境变量
                resolved_data = self.resolver.resolve_config(template_data, env_vars)
                # 写入输出文件
                with open(output_path, 'w', encoding='utf-8') as f:
                    yaml.dump(resolved_data, f, default_flow_style=False, allow_unicode=True)
                    
            elif file_ext == '.json':
                # 解析JSON模板
                template_data = json.loads(template_content)
                # 解析环境变量
                resolved_data = self.resolver.resolve_config(template_data, env_vars)
                # 写入输出文件
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(resolved_data, f, indent=2, ensure_ascii=False)
                    
            elif file_ext == '.template':
                # 文本模板，直接替换
                resolved_content = self.resolver.resolve(template_content, env_vars)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(resolved_content)
                    
            else:
                raise ValueError(f"不支持的模板文件类型: {file_ext}")
            
            self.logger.info(f"配置模板渲染完成: {output_path}")
            
        except Exception as e:
            self.logger.error(f"渲染配置模板失败: {e}")
            raise
    
    def render_string(self, template_string: str, env_vars: Optional[Dict[str, str]] = None) -> str:
        """渲染字符串模板"""
        return self.resolver.resolve(template_string, env_vars)
    
    def render_to_dict(self, template_path: str, env_vars: Optional[Dict[str, str]] = None) -> Dict:
        """渲染模板并返回字典"""
        try:
            # 读取模板文件
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # 确定文件类型
            file_ext = Path(template_path).suffix.lower()
            
            if file_ext in ['.yaml', '.yml']:
                template_data = yaml.safe_load(template_content)
            elif file_ext == '.json':
                template_data = json.loads(template_content)
            else:
                raise ValueError(f"不支持的模板文件类型: {file_ext}")
            
            # 解析环境变量
            resolved_data = self.resolver.resolve_config(template_data, env_vars)
            return resolved_data
            
        except Exception as e:
            self.logger.error(f"渲染模板到字典失败: {e}")
            raise


class ConfigEncryptor:
    """配置加密器（模拟实现）"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        初始化加密器
        
        Args:
            encryption_key: 加密密钥，如果为None则自动生成（仅用于模拟）
        """
        self.logger = logging.getLogger("config.encryptor")
        
        # 模拟加密密钥
        if encryption_key:
            # 使用提供的密钥生成Fernet密钥（需要32字节的base64编码密钥）
            key = base64.urlsafe_b64encode(hashlib.sha256(encryption_key.encode()).digest())
            self.cipher = Fernet(key)
        else:
            # 生成随机密钥（仅用于演示，生产环境应使用安全的密钥管理）
            self.cipher = Fernet.generate_key()
            self.cipher = Fernet(self.cipher)
        
        self.logger.info("配置加密器初始化完成")
    
    def encrypt_sensitive_values(self, config: Dict, sensitive_keys: List[str]) -> Dict:
        """加密敏感配置值"""
        if not sensitive_keys:
            return config
        
        encrypted_config = config.copy()
        
        def encrypt_recursive(obj, path=""):
            if isinstance(obj, dict):
                result = {}
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    result[key] = encrypt_recursive(value, new_path)
                return result
            elif isinstance(obj, list):
                return [encrypt_recursive(item, f"{path}[{i}]") for i, item in enumerate(obj)]
            elif isinstance(obj, str):
                # 检查路径是否匹配敏感键
                current_key = path.split('.')[-1] if '.' in path else path
                if current_key in sensitive_keys:
                    try:
                        encrypted = self.cipher.encrypt(obj.encode())
                        encrypted_str = encrypted.decode('utf-8')
                        self.logger.debug(f"加密敏感值: {path} -> [ENCRYPTED]")
                        return f"ENCRYPTED:{encrypted_str}"
                    except Exception as e:
                        self.logger.error(f"加密失败: {path}, 错误: {e}")
                        return obj
                else:
                    return obj
            else:
                return obj
        
        return encrypt_recursive(encrypted_config)
    
    def decrypt_sensitive_values(self, config: Dict) -> Dict:
        """解密敏感配置值"""
        decrypted_config = config.copy()
        
        def decrypt_recursive(obj, path=""):
            if isinstance(obj, dict):
                result = {}
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    result[key] = decrypt_recursive(value, new_path)
                return result
            elif isinstance(obj, list):
                return [decrypt_recursive(item, f"{path}[{i}]") for i, item in enumerate(obj)]
            elif isinstance(obj, str) and obj.startswith("ENCRYPTED:"):
                try:
                    encrypted_str = obj[len("ENCRYPTED:"):]
                    decrypted = self.cipher.decrypt(encrypted_str.encode())
                    decrypted_str = decrypted.decode('utf-8')
                    self.logger.debug(f"解密敏感值: {path} -> [DECRYPTED]")
                    return decrypted_str
                except Exception as e:
                    self.logger.error(f"解密失败: {path}, 错误: {e}")
                    return obj
            else:
                return obj
        
        return decrypt_recursive(decrypted_config)
    
    def identify_sensitive_values(self, config: Dict) -> List[str]:
        """识别配置中的敏感值（基于命名约定）"""
        sensitive_patterns = [
            r'.*[Pp]assword.*',
            r'.*[Tt]oken.*',
            r'.*[Ss]ecret.*',
            r'.*[Kk]ey.*',
            r'.*[Cc]redential.*',
            r'.*[Aa]pi[Kk]ey.*',
            r'.*[Aa]ccess[Kk]ey.*',
            r'.*[Ss]ecret[Kk]ey.*'
        ]
        
        sensitive_keys = []
        
        def find_sensitive_keys(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    # 检查键名是否匹配敏感模式
                    if any(re.match(pattern, key) for pattern in sensitive_patterns):
                        current_key = new_path.split('.')[-1]
                        if current_key not in sensitive_keys:
                            sensitive_keys.append(current_key)
                    find_sensitive_keys(value, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    find_sensitive_keys(item, f"{path}[{i}]")
        
        find_sensitive_keys(config)
        self.logger.info(f"识别到敏感键: {sensitive_keys}")
        return sensitive_keys


class EnvironmentManager:
    """环境管理器（整合所有功能）"""
    
    def __init__(self):
        self.resolver = EnvironmentVariableResolver()
        self.renderer = ConfigTemplateRenderer(self.resolver)
        self.encryptor = ConfigEncryptor()
        self.logger = logging.getLogger("env.manager")
        
    def load_and_validate_config(self, config_path: str) -> Dict:
        """加载并验证配置"""
        self.logger.info(f"加载配置: {config_path}")
        
        # 读取原始配置
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析为字典
        file_ext = Path(config_path).suffix.lower()
        if file_ext in ['.yaml', '.yml']:
            config = yaml.safe_load(content)
        elif file_ext == '.json':
            config = json.loads(content)
        else:
            raise ValueError(f"不支持的配置文件类型: {file_ext}")
        
        # 验证必需环境变量
        missing_vars = self.resolver.validate_required_vars(config)
        if missing_vars:
            raise ValueError(f"缺失必需环境变量: {missing_vars}")
        
        # 解析环境变量
        resolved_config = self.resolver.resolve_config(config)
        
        # 识别敏感值
        sensitive_keys = self.encryptor.identify_sensitive_values(resolved_config)
        
        # 加密敏感值（模拟）
        if sensitive_keys:
            self.logger.info(f"加密敏感配置键: {sensitive_keys}")
            encrypted_config = self.encryptor.encrypt_sensitive_values(resolved_config, sensitive_keys)
        else:
            encrypted_config = resolved_config
        
        self.logger.info(f"配置加载完成，大小: {len(str(encrypted_config))} 字符")
        return encrypted_config
    
    def generate_env_file(self, config_path: str, output_path: str):
        """生成环境变量文件"""
        self.logger.info(f"为配置 {config_path} 生成环境变量文件")
        
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_ext = Path(config_path).suffix.lower()
        if file_ext in ['.yaml', '.yml']:
            config = yaml.safe_load(content)
        elif file_ext == '.json':
            config = json.loads(content)
        else:
            raise ValueError(f"不支持的配置文件类型: {file_ext}")
        
        # 提取环境变量
        env_vars = self.resolver.extract_env_vars(config)
        
        # 生成.env文件内容
        env_lines = ["# 自动生成的环境变量文件", "# 来源: " + config_path, ""]
        
        for env_var in env_vars:
            if env_var.description:
                env_lines.append(f"# {env_var.description}")
            
            if env_var.required:
                env_lines.append(f"# 必需: {env_var.name}=<value>")
            else:
                default = env_var.default_value or ""
                env_lines.append(f"# 可选（默认值: {default}）")
            
            if env_var.value:
                env_lines.append(f"{env_var.name}={env_var.value}")
            elif env_var.default_value:
                env_lines.append(f"# {env_var.name}={env_var.default_value}")
            else:
                env_lines.append(f"{env_var.name}=")
            
            env_lines.append("")
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(env_lines))
        
        self.logger.info(f"环境变量文件已生成: {output_path}")
```

### 设计思路

1. **环境变量解析**：
   - 支持两种格式：`${VAR_NAME}`（必需）和`${VAR_NAME:default}`（带默认值）
   - 使用正则表达式高效匹配和替换
   - 递归解析嵌套的字典和列表结构

2. **配置模板渲染**：
   - 支持多种文件格式：YAML、JSON、纯文本模板
   - 自动检测文件类型并选择相应解析器
   - 提供字符串渲染和字典渲染两种输出方式

3. **环境验证**：
   - 自动识别必需环境变量（无默认值的引用）
   - 验证环境变量是否已在系统中设置
   - 提供清晰的错误信息，指出缺失的变量

4. **配置加密**：
   - 基于命名约定自动识别敏感配置项
   - 使用Fernet对称加密保护敏感值
   - 加密值在配置中标记为`ENCRYPTED:`前缀，便于识别

5. **环境管理整合**：
   - 提供统一的`EnvironmentManager`整合所有功能
   - 支持从配置文件生成环境变量模板
   - 完整的配置加载、验证、解析、加密流程

### 关键要点

1. **正则表达式设计**：
   - `r'\$\{([^}:]+)(?::([^}]+))?\}'` 匹配 `${VAR}` 和 `${VAR:default}`
   - 需要正确处理转义字符和嵌套情况
   - 性能考虑：避免在大型配置中频繁使用正则匹配

2. **递归解析算法**：
   - 需要处理各种数据类型：字符串、字典、列表、数字、布尔值
   - 递归深度限制，避免栈溢出
   - 路径跟踪，便于错误定位

3. **敏感信息识别**：
   - 基于命名约定（包含password、token、secret等关键词）
   - 支持正则表达式模式匹配
   - 可扩展的识别规则

4. **加密安全考虑**：
   - 加密密钥需要安全存储（本实现仅为演示）
   - 生产环境应使用密钥管理服务（KMS）或环境变量注入密钥
   - 加密算法需要定期更新和密钥轮换

5. **错误处理**：
   - 缺失环境变量需要明确的错误信息
   - 加密失败需要回退到明文并记录警告
   - 文件操作需要处理权限和不存在的情况

### 常见错误

1. **环境变量格式错误**：
   ```
   错误：Invalid environment variable format: $VAR
   解决方案：使用正确的格式 ${VAR} 或 ${VAR:default}
   ```

2. **递归深度超限错误**：
   ```
   错误：RecursionError: maximum recursion depth exceeded
   解决方案：检查配置是否存在循环引用，或增加递归深度限制
   ```

3. **加密密钥错误**：
   ```
   错误：InvalidToken: 解密失败
   解决方案：检查加密密钥是否正确，或重新生成加密配置
   ```

4. **文件权限错误**：
   ```
   错误：PermissionError: [Errno 13] Permission denied
   解决方案：检查文件读写权限，或以适当用户身份运行
   ```

5. **配置格式错误**：
   ```
   错误：YAMLError: mapping values are not allowed here
   解决方案：检查配置文件语法，确保YAML/JSON格式正确
   ```

## 🎯 任务6：GitHub MCP服务器配置实战

### 参考实现：github_mcp_server.py

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub MCP服务器配置实战
Day 16 - 第62节课：MCP服务器配置 - 课后练习答案

本实现提供了完整的GitHub MCP服务器配置和管理功能，包括：
1. GitHub令牌的安全获取和管理
2. GitHub MCP服务器配置生成和验证
3. 连接测试和功能验证
4. 权限范围检查和令牌验证
"""

import os
import sys
import asyncio
import logging
import aiohttp
import yaml
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import base64
import hashlib
import hmac
import time

# ============================================================================
# 数据类定义
# ============================================================================

class GitHubTokenSource(Enum):
    """GitHub令牌来源"""
    ENVIRONMENT = "environment"      # 环境变量
    FILE = "file"                    # 文件
    KEYCHAIN = "keychain"            # 密钥链（模拟）
    AWS_SECRETS_MANAGER = "aws_secrets_manager"  # AWS Secrets Manager（模拟）


@dataclass
class GitHubTokenInfo:
    """GitHub令牌信息"""
    token: str
    source: GitHubTokenSource
    scopes: List[str] = field(default_factory=list)
    expires_at: Optional[float] = None
    last_used: Optional[float] = None
    is_valid: bool = False
    username: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[float] = None


class GitHubTokenManager:
    """GitHub令牌管理器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("github.token")
        self.tokens: Dict[str, GitHubTokenInfo] = {}
        self.default_token_name = "default"
        
    def get_token(self, token_name: str = "default", prefer_source: GitHubTokenSource = None) -> str:
        """获取GitHub令牌"""
        # 如果令牌已缓存且有效，直接返回
        if token_name in self.tokens and self.tokens[token_name].is_valid:
            token_info = self.tokens[token_name]
            # 检查是否过期
            if token_info.expires_at and time.time() > token_info.expires_at:
                self.logger.warning(f"令牌 {token_name} 已过期，重新获取")
            else:
                token_info.last_used = time.time()
                self.logger.debug(f"使用缓存的令牌 {token_name}")
                return token_info.token
        
        # 按优先级从不同来源获取令牌
        token_sources = []
        
        if prefer_source:
            token_sources.append(prefer_source)
        
        # 默认优先级：环境变量 → 文件 → 密钥链 → AWS Secrets Manager
        token_sources.extend([
            GitHubTokenSource.ENVIRONMENT,
            GitHubTokenSource.FILE,
            GitHubTokenSource.KEYCHAIN,
            GitHubTokenSource.AWS_SECRETS_MANAGER
        ])
        
        token = None
        source = None
        
        for source_type in token_sources:
            if source_type == GitHubTokenSource.ENVIRONMENT:
                token = self._get_token_from_env(token_name)
                if token:
                    source = source_type
                    break
                    
            elif source_type == GitHubTokenSource.FILE:
                token = self._get_token_from_file(token_name)
                if token:
                    source = source_type
                    break
                    
            elif source_type == GitHubTokenSource.KEYCHAIN:
                token = self._get_token_from_keychain(token_name)
                if token:
                    source = source_type
                    break
                    
            elif source_type == GitHubTokenSource.AWS_SECRETS_MANAGER:
                token = self._get_token_from_aws_secrets(token_name)
                if token:
                    source = source_type
                    break
        
        if not token:
            raise ValueError(f"无法从任何来源获取GitHub令牌 {token_name}")
        
        # 验证令牌
        is_valid = self.validate_token(token)
        
        # 获取令牌信息
        scopes = self.get_token_scopes(token)
        user_info = self._get_user_info(token)
        
        # 缓存令牌信息
        token_info = GitHubTokenInfo(
            token=token,
            source=source,
            scopes=scopes,
            is_valid=is_valid,
            username=user_info.get('login') if user_info else None,
            last_used=time.time()
        )
        
        self.tokens[token_name] = token_info
        self.logger.info(f"成功获取令牌 {token_name}，来源: {source.value}，权限: {scopes}")
        
        return token
    
    def _get_token_from_env(self, token_name: str) -> Optional[str]:
        """从环境变量获取令牌"""
        env_var_name = f"GITHUB_TOKEN_{token_name.upper()}" if token_name != "default" else "GITHUB_TOKEN"
        token = os.environ.get(env_var_name)
        
        if token:
            self.logger.debug(f"从环境变量 {env_var_name} 获取令牌")
            return token.strip()
        
        return None
    
    def _get_token_from_file(self, token_name: str) -> Optional[str]:
        """从文件获取令牌"""
        file_paths = [
            f"~/.github/tokens/{token_name}.txt",
            f"~/.config/github/token_{token_name}",
            f"./secrets/github_{token_name}.token"
        ]
        
        for file_path in file_paths:
            expanded_path = os.path.expanduser(file_path)
            if os.path.exists(expanded_path):
                try:
                    with open(expanded_path, 'r', encoding='utf-8') as f:
                        token = f.read().strip()
                    if token:
                        self.logger.debug(f"从文件 {expanded_path} 获取令牌")
                        return token
                except Exception as e:
                    self.logger.warning(f"读取令牌文件失败 {expanded_path}: {e}")
        
        return None
    
    def _get_token_from_keychain(self, token_name: str) -> Optional[str]:
        """从密钥链获取令牌（模拟实现）"""
        # 模拟实现，实际应调用系统密钥链
        self.logger.debug(f"尝试从密钥链获取令牌 {token_name}（模拟）")
        return None
    
    def _get_token_from_aws_secrets(self, token_name: str) -> Optional[str]:
        """从AWS Secrets Manager获取令牌（模拟实现）"""
        # 模拟实现，实际应调用AWS SDK
        self.logger.debug(f"尝试从AWS Secrets Manager获取令牌 {token_name}（模拟）")
        return None
    
    def validate_token(self, token: str) -> bool:
        """验证GitHub令牌有效性"""
        try:
            # 调用GitHub API验证令牌
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # 使用同步请求简化实现，实际应用中使用异步
            import requests
            response = requests.get(
                "https://api.github.com/user",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.debug("GitHub令牌验证成功")
                return True
            else:
                self.logger.warning(f"GitHub令牌验证失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"验证GitHub令牌失败: {e}")
            return False
    
    def get_token_scopes(self, token: str) -> List[str]:
        """获取令牌权限范围"""
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            import requests
            response = requests.get(
                "https://api.github.com/user",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                # 从响应头获取权限范围
                scopes_header = response.headers.get('X-OAuth-Scopes', '')
                scopes = [scope.strip() for scope in scopes_header.split(',') if scope.strip()]
                self.logger.debug(f"令牌权限范围: {scopes}")
                return scopes
            else:
                self.logger.warning(f"获取令牌权限失败: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"获取令牌权限失败: {e}")
            return []
    
    def _get_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            import requests
            response = requests.get(
                "https://api.github.com/user",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"获取用户信息失败: {e}")
            return None
    
    def get_rate_limit_info(self, token: str) -> Dict[str, Any]:
        """获取速率限制信息"""
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            import requests
            response = requests.get(
                "https://api.github.com/rate_limit",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                resources = data.get('resources', {})
                core = resources.get('core', {})
                
                return {
                    'limit': core.get('limit', 60),
                    'remaining': core.get('remaining', 60),
                    'reset': core.get('reset', time.time() + 3600),
                    'used': core.get('used', 0)
                }
            else:
                self.logger.warning(f"获取速率限制失败: HTTP {response.status_code}")
                return {}
                
        except Exception as e:
            self.logger.error(f"获取速率限制失败: {e}")
            return {}


class GitHubMCPServerConfigurator:
    """GitHub MCP服务器配置器"""
    
    def __init__(self, token_manager: Optional[GitHubTokenManager] = None):
        self.token_manager = token_manager or GitHubTokenManager()
        self.logger = logging.getLogger("github.mcp.configurator")
    
    def create_config(self, token_name: str = "default", additional_config: Dict = None) -> Dict:
        """创建GitHub MCP服务器配置"""
        try:
            # 获取令牌
            token = self.token_manager.get_token(token_name)
            
            # 获取令牌信息
            token_info = self.token_manager.tokens.get(token_name)
            scopes = token_info.scopes if token_info else []
            
            # 基本配置
            config = {
                "github": {
                    "command": "npx",
                    "args": ["@modelcontextprotocol/server-github"],
                    "env": {
                        "MCP_PORT": 3003,
                        "GITHUB_TOKEN": token,
                        "GITHUB_API_URL": "https://api.github.com",
                        "GITHUB_GRAPHQL_URL": "https://api.github.com/graphql",
                        "LOG_LEVEL": "info"
                    },
                    "auto_start": False,  # GitHub服务器包含敏感令牌，建议手动启动
                    "health_check": "http://localhost:3003/health",
                    "timeout": 60.0,
                    "working_dir": "/var/lib/mcp-github",
                    "description": "GitHub MCP服务器，提供GitHub API访问功能",
                    "max_retries": 2,  # 令牌相关失败重试次数少
                    "retry_delay": 5.0,
                    "depends_on": ["filesystem"],  # 可能需要文件系统存储缓存
                    "security_context": {
                        "token_scopes": scopes,
                        "allow_private_repos": "repo" in scopes or "repo:status" in scopes,
                        "max_repo_size": "1000000",  # 1MB
                        "enable_webhooks": False,
                        "rate_limit_enabled": True,
                        "rate_limit_per_hour": "5000"
                    }
                }
            }
            
            # 合并额外配置
            if additional_config:
                self._deep_merge(config["github"], additional_config)
            
            # 根据令牌权限调整配置
            self._adjust_config_by_scopes(config["github"], scopes)
            
            self.logger.info(f"GitHub MCP服务器配置创建完成，权限: {scopes}")
            return config
            
        except Exception as e:
            self.logger.error(f"创建GitHub MCP服务器配置失败: {e}")
            raise
    
    def _deep_merge(self, base: Dict, update: Dict):
        """深度合并字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _adjust_config_by_scopes(self, config: Dict, scopes: List[str]):
        """根据令牌权限调整配置"""
        security_context = config.get("security_context", {})
        
        # 检查是否有仓库访问权限
        has_repo_access = any(scope.startswith("repo") for scope in scopes)
        security_context["allow_private_repos"] = has_repo_access
        
        # 检查是否有用户权限
        has_user_access = any(scope.startswith("user") for scope in scopes)
        security_context["allow_user_info"] = has_user_access
        
        # 检查是否有组织权限
        has_org_access = any(scope.startswith("org") for scope in scopes)
        security_context["allow_org_info"] = has_org_access
        
        # 检查是否有写入权限
        has_write_access = any("write" in scope or "admin" in scope for scope in scopes)
        security_context["allow_writes"] = has_write_access
        
        config["security_context"] = security_context
    
    async def test_connection(self, config: Dict) -> bool:
        """测试GitHub MCP服务器连接"""
        try:
            self.logger.info("开始测试GitHub MCP服务器连接")
            
            # 提取配置信息
            github_config = config.get("github", {})
            env = github_config.get("env", {})
            port = env.get("MCP_PORT", 3003)
            token = env.get("GITHUB_TOKEN")
            
            if not token:
                self.logger.error("配置中未找到GitHub令牌")
                return False
            
            # 测试GitHub API连接
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with aiohttp.ClientSession() as session:
                # 测试用户API
                async with session.get(
                    "https://api.github.com/user",
                    headers=headers,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        self.logger.error(f"GitHub API测试失败: HTTP {response.status}")
                        return False
                    
                    user_data = await response.json()
                    self.logger.info(f"GitHub API连接成功，用户: {user_data.get('login', 'unknown')}")
            
            # 如果配置了健康检查URL，测试健康检查
            health_check_url = github_config.get("health_check")
            if health_check_url:
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(health_check_url, timeout=5) as response:
                            if response.status == 200:
                                self.logger.info(f"健康检查成功: {health_check_url}")
                            else:
                                self.logger.warning(f"健康检查失败: HTTP {response.status}")
                    except Exception as e:
                        self.logger.warning(f"健康检查异常: {e}")
            
            self.logger.info("GitHub MCP服务器连接测试完成")
            return True
            
        except Exception as e:
            self.logger.error(f"测试GitHub MCP服务器连接失败: {e}")
            return False
    
    def check_permissions(self, token_name: str = "default") -> Dict[str, bool]:
        """检查GitHub令牌权限"""
        try:
            token = self.token_manager.get_token(token_name)
            scopes = self.token_manager.get_token_scopes(token)
            
            permissions = {
                "repo_read": any(scope.startswith("repo") for scope in scopes),
                "repo_write": any("write" in scope or "admin" in scope for scope in scopes),
                "user_read": any(scope.startswith("user") for scope in scopes),
                "org_read": any(scope.startswith("org") for scope in scopes),
                "gist": "gist" in scopes,
                "notifications": "notifications" in scopes,
                "workflow": "workflow" in scopes,
                "package": "write:packages" in scopes or "read:packages" in scopes,
            }
            
            self.logger.info(f"GitHub令牌权限检查完成: {permissions}")
            return permissions
            
        except Exception as e:
            self.logger.error(f"检查GitHub令牌权限失败: {e}")
            return {}


class GitHubMCPServerManager:
    """GitHub MCP服务器管理器"""
    
    def __init__(self, config_path: str = "github_mcp_config.yaml"):
        self.config_path = config_path
        self.token_manager = GitHubTokenManager()
        self.configurator = GitHubMCPServerConfigurator(self.token_manager)
        self.logger = logging.getLogger("github.mcp.manager")
        self.config: Optional[Dict] = None
        
    def generate_config(self, output_path: Optional[str] = None):
        """生成GitHub MCP服务器配置文件"""
        try:
            # 创建配置
            config = self.configurator.create_config()
            
            # 输出路径
            if not output_path:
                output_path = self.config_path
            
            # 写入YAML文件
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"GitHub MCP服务器配置文件已生成: {output_path}")
            self.config = config
            
            # 生成环境变量示例文件
            env_file = output_path.replace('.yaml', '.env.example')
            self._generate_env_example(env_file)
            
            return config
            
        except Exception as e:
            self.logger.error(f"生成GitHub MCP服务器配置文件失败: {e}")
            raise
    
    def _generate_env_example(self, env_file: str):
        """生成环境变量示例文件"""
        env_content = """# GitHub MCP服务器环境变量配置示例
# 将本文件复制为 .env 并填入实际值

# GitHub个人访问令牌 (必需)
# 创建地址: https://github.com/settings/tokens
# 建议权限: repo, read:user, read:org
GITHUB_TOKEN=your_personal_access_token_here

# 可选环境变量
LOG_LEVEL=info
MCP_PORT=3003
GITHUB_API_URL=https://api.github.com
GITHUB_GRAPHQL_URL=https://api.github.com/graphql

# 高级配置 (可选)
# RATE_LIMIT_ENABLED=true
# RATE_LIMIT_PER_HOUR=5000
# CACHE_ENABLED=true
# CACHE_TTL=300
"""
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        self.logger.info(f"环境变量示例文件已生成: {env_file}")
    
    async def run_test_suite(self):
        """运行完整的测试套件"""
        self.logger.info("开始运行GitHub MCP服务器测试套件")
        
        test_results = {}
        
        # 测试1: 令牌获取和验证
        try:
            token = self.token_manager.get_token()
            is_valid = self.token_manager.validate_token(token)
            test_results["token_validation"] = is_valid
            self.logger.info(f"令牌验证测试: {'通过' if is_valid else '失败'}")
        except Exception as e:
            test_results["token_validation"] = False
            self.logger.error(f"令牌验证测试失败: {e}")
        
        # 测试2: 权限检查
        try:
            permissions = self.configurator.check_permissions()
            test_results["permission_check"] = bool(permissions)
            self.logger.info(f"权限检查测试: {'通过' if permissions else '失败'}")
        except Exception as e:
            test_results["permission_check"] = False
            self.logger.error(f"权限检查测试失败: {e}")
        
        # 测试3: 配置生成
        try:
            config = self.configurator.create_config()
            test_results["config_generation"] = bool(config)
            self.logger.info(f"配置生成测试: {'通过' if config else '失败'}")
        except Exception as e:
            test_results["config_generation"] = False
            self.logger.error(f"配置生成测试失败: {e}")
        
        # 测试4: 连接测试
        try:
            if config:
                connection_ok = await self.configurator.test_connection(config)
                test_results["connection_test"] = connection_ok
                self.logger.info(f"连接测试: {'通过' if connection_ok else '失败'}")
            else:
                test_results["connection_test"] = False
                self.logger.warning("连接测试跳过，配置生成失败")
        except Exception as e:
            test_results["connection_test"] = False
            self.logger.error(f"连接测试失败: {e}")
        
        # 汇总结果
        all_passed = all(test_results.values())
        self.logger.info(f"测试套件完成: {'全部通过' if all_passed else '部分失败'}")
        self.logger.info(f"详细结果: {test_results}")
        
        return test_results
```

### 设计思路

1. **令牌安全获取**：
   - 支持多种令牌来源：环境变量、文件、密钥链、AWS Secrets Manager
   - 优先级机制，确保灵活性和安全性
   - 令牌缓存和验证，避免重复获取和无效令牌使用

2. **配置动态生成**：
   - 基于令牌权限动态调整配置
   - 支持额外配置合并，提供灵活性
   - 自动生成环境变量示例文件，便于部署

3. **连接测试**：
   - 多层级测试：令牌验证、API连接、健康检查
   - 异步测试，提高测试效率
   - 详细的测试结果报告，便于问题诊断

4. **权限管理**：
   - 自动检测令牌权限范围
   - 根据权限调整服务器功能配置
   - 权限检查报告，确保服务器功能与权限匹配

5. **完整测试套件**：
   - 端到端测试流程，覆盖所有关键功能
   - 模块化测试设计，便于扩展和维护
   - 详细的测试日志和结果汇总

### 关键要点

1. **令牌安全管理**：
   - 令牌不在代码中硬编码，使用安全来源获取
   - 令牌验证确保有效性，避免使用无效令牌
   - 令牌缓存需要安全存储（本实现仅为内存缓存）

2. **配置灵活性**：
   - 支持通过额外配置覆盖默认设置
   - 根据环境动态调整配置（开发、测试、生产）
   - 配置验证确保必要参数存在

3. **错误处理和恢复**：
   - 令牌获取失败有明确的错误信息和备选方案
   - 连接测试失败提供详细的诊断信息
   - 测试套件失败不影响主程序运行

4. **异步性能优化**：
   - 使用aiohttp进行异步HTTP请求，提高并发性能
   - 连接测试并行化，减少总测试时间
   - 合理的超时设置，避免长时间阻塞

5. **可扩展性设计**：
   - 支持新的令牌来源（如Azure Key Vault、HashiCorp Vault）
   - 支持新的测试用例添加
   - 支持自定义配置模板

### 常见错误

1. **令牌无效错误**：
   ```
   错误：GitHub API返回401 Unauthorized
   解决方案：检查令牌是否有效，是否已过期或被撤销
   ```

2. **权限不足错误**：
   ```
   错误：API调用返回403 Forbidden
   解决方案：检查令牌权限范围，确保有所需权限
   ```

3. **速率限制错误**：
   ```
   错误：API调用返回403 Rate limit exceeded
   解决方案：等待速率限制重置，或使用多个令牌轮换
   ```

4. **网络连接错误**：
   ```
   错误：无法连接到GitHub API
   解决方案：检查网络连接，或配置代理
   ```

5. **配置文件错误**：
   ```
   错误：YAML解析失败，无效的配置格式
   解决方案：检查配置文件语法，确保YAML格式正确
   ```

---

## 🎉 练习完成总结

恭喜！您已经完成了MCP服务器配置的所有练习任务。通过本练习，您掌握了：

### 核心技能
1. **MCP配置YAML设计**：设计完整的MCP服务器配置，支持多种服务器类型
2. **异步服务器管理**：实现MCPServerManager异步启动和管理MCP服务器
3. **生命周期管理**：实现依赖关系解析、并发启动和自动恢复机制
4. **错误处理和重试**：实现健壮的错误处理和指数退避重试机制
5. **环境变量注入**：实现环境变量解析、配置模板渲染和敏感信息加密
6. **GitHub MCP实战**：完成GitHub MCP服务器的完整配置和测试

### 最佳实践
1. **配置即代码**：MCP配置使用YAML格式，支持版本控制和环境差异
2. **安全性**：敏感信息使用环境变量，支持配置加密
3. **可靠性**：完善的错误处理、重试机制和自动恢复
4. **可维护性**：模块化设计，清晰的代码结构和完整文档
5. **可测试性**：完整的测试套件，支持端到端测试

### 下一步行动
1. **集成测试**：将本练习的代码集成到实际DeerFlow项目中
2. **性能优化**：根据实际使用情况优化启动速度和资源使用
3. **监控告警**：添加Prometheus指标和Grafana仪表板
4. **生产部署**：配置Docker容器和Kubernetes部署清单
5. **持续改进**：收集使用反馈，持续改进MCP服务器管理功能

### 扩展挑战
1. **多环境支持**：支持开发、测试、生产环境的差异化配置
2. **配置版本管理**：实现配置版本控制和回滚机制
3. **动态配置更新**：支持运行时配置热更新，无需重启服务器
4. **跨平台支持**：支持Windows、Linux、macOS平台的统一管理
5. **插件系统**：支持第三方MCP服务器的插件化集成

祝您在MCP服务器配置和管理方面取得更大进步！