# Day 16 - 第62节课：MCP服务器配置 (MCP Server Configuration)

## 📋 课程概述

本课程深入讲解MCP（Model Context Protocol）服务器的配置和管理。MCP是AI Agent系统中用于标准化上下文访问的协议，通过MCP服务器可以安全、统一地访问文件系统、数据库、GitHub等资源。通过学习，您将掌握MCP服务器的YAML配置格式、异步启动管理、健康检查机制和环境变量注入。

### 🎯 学习目标

完成本课程后，您将能够：
- ✅ 理解MCP协议的基本概念和设计目标
- ✅ 掌握MCP服务器配置的YAML格式和关键配置项
- ✅ 实现MCPServerManager异步启动和管理MCP服务器
- ✅ 配置多种MCP服务器类型（filesystem、sql、github等）
- ✅ 实施健康检查、错误处理和状态监控机制
- ✅ 应用环境变量在MCP配置中的动态替换

## 📁 文件结构

```
day16-lesson62/
├── mcp_server_config_demo.py     # 主演示代码文件（800+行）
├── README.md                     # 本说明文档
├── sample_mcp_config.yaml        # 示例配置文件（可选）
└── minimal_mcp_config.yaml       # 最小配置文件（可选）
```

## 🔧 核心组件

### 1. MCP配置YAML结构

#### 1.1 基础配置示例
```yaml
# MCP服务器配置示例
mcp:
  servers:
    filesystem:
      command: "npx"
      args: ["@modelcontextprotocol/server-filesystem", "/workspace"]
      env:
        MCP_PORT: 3001
        LOG_LEVEL: "info"
      auto_start: true
      health_check: "http://localhost:3001/health"
      timeout: 30.0
      description: "文件系统MCP服务器，提供文件访问功能"
  
  # 全局配置
  log_level: "INFO"
  max_retries: 3
  retry_delay: 2.0
```

#### 1.2 配置字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `command` | string | 是 | 服务器启动命令（如 "npx", "python3"） |
| `args` | array | 是 | 命令参数列表 |
| `env` | object | 否 | 环境变量字典，必须包含MCP_PORT |
| `auto_start` | boolean | 否 | 是否自动启动（默认true） |
| `health_check` | string | 否 | 健康检查URL，默认`http://localhost:{PORT}/health` |
| `timeout` | number | 否 | 启动超时时间（秒，默认30） |
| `working_dir` | string | 否 | 工作目录路径 |
| `description` | string | 否 | 服务器描述 |

**全局配置字段：**
| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `log_level` | string | 否 | 日志级别（DEBUG, INFO, WARN, ERROR） |
| `max_retries` | integer | 否 | 最大重试次数（默认3） |
| `retry_delay` | number | 否 | 重试延迟（秒，默认2） |

### 2. 服务器配置类

#### 2.1 MCPServerConfig 数据类
```python
@dataclass
class MCPServerConfig:
    name: str                    # 服务器名称
    command: str                 # 启动命令
    args: List[str]             # 命令参数
    env: Dict[str, str]         # 环境变量
    port: int = 3000            # 服务器端口
    auto_start: bool = True     # 是否自动启动
    health_check: Optional[str] = None  # 健康检查URL
    timeout: float = 30.0       # 启动超时时间
    working_dir: Optional[str] = None  # 工作目录
    description: str = ""       # 描述信息
```

#### 2.2 MCPConfig 配置管理器
```python
@dataclass
class MCPConfig:
    servers: Dict[str, MCPServerConfig]  # 服务器配置字典
    log_level: str = "INFO"     # 日志级别
    max_retries: int = 3        # 最大重试次数
    retry_delay: float = 2.0    # 重试延迟
    
    @classmethod
    def from_yaml(cls, yaml_content: str) -> "MCPConfig":
        """从YAML内容创建配置"""
        # 解析YAML并创建配置对象
```

### 3. MCP服务器类 (MCPServer)

#### 3.1 服务器状态管理
```python
class ServerStatus(Enum):
    STOPPED = "stopped"      # 已停止
    STARTING = "starting"    # 启动中
    RUNNING = "running"      # 运行中
    ERROR = "error"          # 错误
    STOPPING = "stopping"    # 停止中
```

#### 3.2 核心方法
```python
class MCPServer:
    async def start(self) -> bool:
        """启动MCP服务器"""
        # 1. 构建环境变量和命令行
        # 2. 启动异步子进程
        # 3. 收集输出流
        # 4. 等待服务器就绪
    
    async def health_check(self) -> bool:
        """健康检查"""
        # 1. 检查健康检查URL（如果配置）
        # 2. 或检查进程是否存活
    
    async def stop(self, timeout: float = 5.0) -> bool:
        """停止MCP服务器"""
        # 1. 发送SIGTERM信号
        # 2. 等待进程退出
        # 3. 超时后发送SIGKILL
```

### 4. MCP服务器管理器 (MCPServerManager)

#### 4.1 主要功能
```python
class MCPServerManager:
    async def start_all(self) -> bool:
        """启动所有auto_start为true的服务器"""
    
    async def stop_all(self) -> bool:
        """停止所有正在运行的服务器"""
    
    async def health_check_all(self) -> Dict[str, Any]:
        """检查所有服务器的健康状态"""
    
    async def monitor(self):
        """监控循环：定期检查健康状态，自动重启失败的服务器"""
    
    def list_servers(self) -> List[Dict[str, Any]]:
        """列出所有服务器状态信息"""
```

#### 4.2 错误处理和重试机制
- **带重试的启动**：`_start_server_with_retry()` 支持最大重试次数
- **优雅停止**：先SIGTERM，超时后SIGKILL
- **健康检查**：定期检查服务器状态，自动重启失败的服务

## 🚀 快速开始

### 步骤1：导入演示代码
```python
from mcp_server_config_demo import MCPConfig, MCPServerManager, create_sample_config
```

### 步骤2：创建MCP配置
```python
# 从YAML字符串创建配置
config_yaml = """
servers:
  filesystem:
    command: "npx"
    args: ["@modelcontextprotocol/server-filesystem", "/workspace"]
    env:
      MCP_PORT: 3001
    auto_start: true
"""

config = MCPConfig.from_yaml(config_yaml)
```

### 步骤3：创建服务器管理器
```python
manager = MCPServerManager(config)
```

### 步骤4：启动所有服务器
```python
# 启动所有auto_start为true的服务器
await manager.start_all()

# 检查启动状态
servers = manager.list_servers()
for server in servers:
    print(f"{server['name']}: {server['status']}")

# 健康检查
health = await manager.health_check_all()
print(f"整体健康状态: {health['healthy']}")
```

### 步骤5：手动管理服务器
```python
# 启动单个服务器
await manager.start_server("filesystem")

# 停止单个服务器
await manager.stop_server("filesystem")

# 重启服务器
await manager.restart_server("filesystem")
```

### 步骤6：停止所有服务器（清理）
```python
await manager.shutdown()
```

## 📖 详细用法

### 1. 配置环境变量注入

MCP配置支持环境变量替换，格式为`${VAR_NAME}`或`${VAR_NAME:default}`：

```yaml
servers:
  github:
    command: "npx"
    args: ["@modelcontextprotocol/server-github"]
    env:
      MCP_PORT: 3003
      GITHUB_TOKEN: "${GITHUB_TOKEN}"  # 必须的环境变量
      LOG_LEVEL: "${LOG_LEVEL:info}"   # 带默认值的环境变量
```

### 2. 配置多种MCP服务器类型

#### 2.1 文件系统服务器
```yaml
filesystem:
  command: "npx"
  args: ["@modelcontextprotocol/server-filesystem", "/workspace"]
  env:
    MCP_PORT: 3001
    ALLOWED_PATHS: "/workspace,/tmp"
  auto_start: true
  health_check: "http://localhost:3001/health"
```

#### 2.2 SQL数据库服务器
```yaml
sql:
  command: "npx"
  args: ["@modelcontextprotocol/server-sql", "${DATABASE_URL}"]
  env:
    MCP_PORT: 3002
    DB_MAX_CONNECTIONS: "10"
    DB_TIMEOUT: "30"
  auto_start: true
```

#### 2.3 GitHub服务器
```yaml
github:
  command: "npx"
  args: ["@modelcontextprotocol/server-github"]
  env:
    MCP_PORT: 3003
    GITHUB_TOKEN: "${GITHUB_TOKEN}"
  auto_start: false  # 需要时手动启动
```

#### 2.4 Brave搜索服务器
```yaml
brave-search:
  command: "npx"
  args: ["@modelcontextprotocol/server-brave-search"]
  env:
    MCP_PORT: 3004
    BRAVE_API_KEY: "${BRAVE_API_KEY}"
  auto_start: false
```

### 3. 异步启动和就绪等待

#### 3.1 启动超时配置
```yaml
filesystem:
  command: "npx"
  args: ["@modelcontextprotocol/server-filesystem", "/workspace"]
  env:
    MCP_PORT: 3001
  timeout: 60.0  # 60秒启动超时
  health_check: "http://localhost:3001/health"
```

#### 3.2 自定义健康检查
```python
# 实现自定义健康检查逻辑
async def custom_health_check(server: MCPServer) -> bool:
    # 检查特定端点或业务逻辑
    return await check_business_logic()
```

### 4. 错误处理和监控

#### 4.1 配置重试策略
```yaml
# 全局配置
mcp:
  servers:
    # ...服务器配置...
  
  max_retries: 5      # 最大重试次数
  retry_delay: 3.0    # 重试延迟（秒）
  log_level: "DEBUG"  # 详细日志
```

#### 4.2 监控和自动恢复
```python
# 启动监控循环
monitor_task = asyncio.create_task(manager.monitor())

# 稍后停止监控
monitor_task.cancel()
```

### 5. 生产环境最佳实践

#### 5.1 安全配置
```yaml
github:
  command: "npx"
  args: ["@modelcontextprotocol/server-github"]
  env:
    MCP_PORT: 3003
    GITHUB_TOKEN: "${GITHUB_TOKEN}"  # 使用环境变量，不在配置文件中存储密钥
  auto_start: false  # 敏感服务手动启动
```

#### 5.2 资源限制
```yaml
filesystem:
  command: "npx"
  args: ["@modelcontextprotocol/server-filesystem", "/workspace"]
  env:
    MCP_PORT: 3001
    MEMORY_LIMIT: "256m"  # 内存限制
    CPU_LIMIT: "0.5"      # CPU限制
```

#### 5.3 日志和监控
```yaml
# 全局配置
mcp:
  servers:
    filesystem:
      # ...配置...
      env:
        MCP_PORT: 3001
        LOG_LEVEL: "info"
        LOG_FILE: "/var/log/mcp-filesystem.log"
  
  log_level: "INFO"  # 管理器日志级别
```

## 🧪 测试用例

演示代码包含完整的测试函数：

### 1. 配置加载测试 (`test_config_loading`)
- 测试最小配置加载
- 测试完整配置加载
- 测试环境变量解析
- 验证配置字段完整性

### 2. 服务器管理器测试 (`test_server_manager`)
- 测试服务器启动流程
- 测试状态获取功能
- 测试服务器停止功能
- 验证错误处理机制

### 3. 演示函数 (`demo_*`)
- `demo_basic_config()`: 基础配置演示
- `demo_server_lifecycle()`: 服务器生命周期演示
- `demo_error_handling()`: 错误处理演示
- `demo_environment_variables()`: 环境变量注入演示

### 运行所有测试
```bash
cd day16-lesson62
python mcp_server_config_demo.py
```

## 🔍 核心算法和设计模式

### 1. 异步子进程管理

#### 1.1 进程启动和监控
```python
async def start(self) -> bool:
    # 创建异步子进程
    self.process = await asyncio.create_subprocess_exec(
        *cmd,
        env=env,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.DEVNULL
    )
    
    # 启动输出收集任务
    asyncio.create_task(self._collect_output())
    
    # 等待服务器就绪
    return await self.wait_for_ready()
```

#### 1.2 输出流收集
```python
async def _collect_output(self):
    """收集进程的标准输出和错误输出"""
    # 并行收集stdout和stderr
    # 实时日志记录
    # 错误检测和预警
```

### 2. 健康检查算法

#### 2.1 多级健康检查
```python
async def health_check(self) -> bool:
    # 1. 检查进程是否存活
    if self.process.returncode is not None:
        return False
    
    # 2. 检查健康检查端点（如果配置）
    if self.config.health_check:
        return await self._check_health_endpoint()
    
    # 3. 默认健康状态
    return True
```

#### 2.2 就绪等待算法
```python
async def wait_for_ready(self, timeout: float = 30.0) -> bool:
    start_time = time.time()
    check_interval = 0.5
    
    while time.time() - start_time < timeout:
        if await self.health_check():
            return True
        await asyncio.sleep(check_interval)
    
    return False
```

### 3. 错误恢复机制

#### 3.1 带指数退避的重试
```python
async def _start_server_with_retry(self, server_name: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            success = await self.servers[server_name].start()
            if success:
                return True
            
            # 指数退避延迟
            delay = self.config.retry_delay * (2 ** attempt)
            await asyncio.sleep(delay)
            
        except Exception as e:
            logging.error(f"启动尝试 {attempt + 1} 失败: {e}")
    
    return False
```

### 4. 设计模式应用

#### 4.1 建造者模式 (`MCPConfig`)
- **目的**：逐步构建复杂配置对象
- **实现**：`from_yaml()`方法解析YAML并创建配置对象
- **优点**：分离配置解析和对象创建，支持多种配置格式

#### 4.2 观察者模式 (`监控循环`)
- **目的**：监控服务器状态变化
- **实现**：定期健康检查，状态变化时触发相应动作
- **优点**：实时监控，快速响应故障

#### 4.3 策略模式 (`健康检查`)
- **目的**：支持多种健康检查策略
- **实现**：可配置的健康检查URL，可扩展的健康检查逻辑
- **优点**：灵活适应不同服务器类型

## 📊 性能优化建议

### 1. 启动性能优化
- **并行启动**：无依赖关系的服务器并行启动
- **懒加载**：按需启动服务器，减少初始资源占用
- **连接池**：重用HTTP连接进行健康检查

### 2. 内存使用优化
- **输出流限制**：限制收集的日志行数，避免内存泄漏
- **资源清理**：及时关闭不再使用的连接和资源
- **进程管理**：监控子进程内存使用，防止内存泄漏

### 3. 网络性能优化
- **健康检查优化**：减少健康检查频率，合并检查请求
- **连接复用**：使用HTTP连接池复用连接
- **超时优化**：根据网络环境调整超时时间

### 4. 监控和告警优化
- **分级监控**：不同重要性的服务器使用不同的监控策略
- **智能告警**：基于历史数据的智能告警阈值
- **自愈机制**：自动诊断和恢复常见问题

## 🔧 扩展和自定义

### 1. 添加新的MCP服务器类型

#### 步骤1：定义服务器配置
```yaml
custom-server:
  command: "python3"
  args: ["-m", "my_custom_mcp_server"]
  env:
    MCP_PORT: 3005
    CUSTOM_CONFIG: "${CUSTOM_CONFIG_PATH}"
  auto_start: true
```

#### 步骤2：实现自定义健康检查
```python
class CustomMCPServer(MCPServer):
    async def health_check(self) -> bool:
        # 实现自定义健康检查逻辑
        return await self._check_custom_endpoint()
```

#### 步骤3：集成到管理器
```python
# 创建自定义服务器实例
custom_server = CustomMCPServer(custom_config)

# 添加到管理器
manager.servers["custom-server"] = custom_server
```

### 2. 自定义配置格式

#### 支持JSON配置
```python
class JSONMCPConfig(MCPConfig):
    @classmethod
    def from_json(cls, json_content: str) -> "MCPConfig":
        config_data = json.loads(json_content)
        # 转换JSON格式到内部格式
        return cls.from_dict(config_data)
```

#### 支持数据库配置
```python
class DatabaseMCPConfig(MCPConfig):
    def __init__(self, db_connection, config_id: str):
        # 从数据库加载配置
        config_data = db_connection.fetch_config(config_id)
        super().__init__(config_data)
```

### 3. 高级功能扩展

#### 3.1 服务器依赖管理
```python
class MCPServerWithDependencies(MCPServer):
    def __init__(self, config: MCPServerConfig, dependencies: List[str]):
        super().__init__(config)
        self.dependencies = dependencies
    
    async def start(self) -> bool:
        # 先启动依赖的服务器
        for dep_name in self.dependencies:
            if not await self.manager.is_server_running(dep_name):
                await self.manager.start_server(dep_name)
        
        # 然后启动自己
        return await super().start()
```

#### 3.2 自动扩缩容
```python
class AutoScalingMCPServer(MCPServer):
    async def monitor_and_scale(self):
        # 监控负载
        load = await self.get_current_load()
        
        # 根据负载调整实例数
        if load > self.scale_up_threshold:
            await self.scale_out()
        elif load < self.scale_down_threshold:
            await self.scale_in()
```

## 🎓 教学要点

### 重点概念
1. **MCP协议**：理解标准化上下文协议的设计目标和优势
2. **异步编程**：掌握asyncio在服务器管理中的应用
3. **进程管理**：理解子进程的启动、监控和停止机制
4. **健康检查**：掌握多级健康检查的设计和实现
5. **配置管理**：理解YAML配置格式和环境变量注入

### 常见问题
1. **端口冲突**：如何处理MCP服务器端口冲突
2. **启动失败**：诊断MCP服务器启动失败的原因
3. **权限问题**：解决文件系统访问权限问题
4. **环境变量**：正确配置和使用环境变量
5. **资源泄漏**：避免子进程资源泄漏

### 最佳实践
1. **配置版本控制**：MCP配置纳入版本控制
2. **环境分离**：开发、测试、生产环境使用不同配置
3. **密钥管理**：使用环境变量或密钥管理服务保护敏感信息
4. **监控告警**：实施全面的监控和告警机制
5. **文档完整**：为每个MCP服务器提供完整的配置文档

## 📚 延伸学习

### 推荐阅读
1. **MCP官方文档**：https://spec.modelcontextprotocol.io/
2. **Python asyncio**：https://docs.python.org/3/library/asyncio.html
3. **YAML规范**：https://yaml.org/spec/
4. **进程管理**：《Unix环境高级编程》相关章节
5. **配置管理**：《基础设施即代码》相关章节

### 相关技术
1. **Docker容器**：容器化MCP服务器部署
2. **Kubernetes**：在K8s中部署和管理MCP服务器
3. **Prometheus**：MCP服务器指标监控
4. **Grafana**：MCP服务器监控仪表板
5. **Vault**：MCP服务器密钥管理

### 开源项目参考
1. **MCP官方服务器**：https://github.com/modelcontextprotocol/servers
2. **DeerFlow MCP集成**：https://github.com/bytedance/deer-flow
3. **LangGraph MCP集成**：https://github.com/langchain-ai/langgraph
4. **Claude MCP集成**：https://github.com/anthropics/claude-mcp
5. **VSCode MCP客户端**：https://github.com/microsoft/vscode-mcp

## 🏆 学习成果评估

完成本课程学习后，您应该能够：

### 知识掌握
- [ ] 解释MCP协议的基本概念和设计目标
- [ ] 说明MCP服务器配置YAML格式的关键字段
- [ ] 描述MCPServerManager的异步启动流程
- [ ] 理解健康检查机制和错误处理策略
- [ ] 掌握环境变量在MCP配置中的注入机制

### 技能应用
- [ ] 编写正确的MCP服务器YAML配置文件
- [ ] 使用MCPServerManager启动和管理MCP服务器
- [ ] 配置多种MCP服务器类型并解决常见问题
- [ ] 实施健康检查和自动恢复机制
- [ ] 调试和解决MCP服务器启动失败问题

### 项目实践
- [ ] 在DeerFlow项目中集成MCP服务器
- [ ] 设计并实现自定义MCP服务器类型
- [ ] 优化MCP服务器性能和可靠性
- [ ] 实施MCP服务器的监控和告警
- [ ] 建立MCP服务器配置的最佳实践流程

---

**课程完成标志**：能够独立配置和管理至少3种不同类型的MCP服务器，实现完整的生命周期管理和错误处理机制。

**下一步学习**：第63节课《多代理协作配置》将深入讲解AI Agent系统中多代理协作的配置管理，提高系统的协作能力和任务分配效率。

---

**记住**：MCP协议标准化了AI Agent与外部资源的交互方式，掌握MCP服务器配置是构建可扩展AI系统的重要基础。通过本课程的学习，您已经具备了在实际项目中应用MCP协议的能力。