# Day 15 - 第59节课：工具配置管理

## 📚 课程概述

本节课讲解现代AI Agent系统中的工具配置管理，包括配置结构设计、工具加载器、安全配置管理、环境变量注入和依赖管理。重点掌握可扩展的工具配置架构和基于类型的安全策略，培养安全第一的工具管理思维。

## 🎯 学习目标

1. **掌握工具配置结构设计**：理解工具配置的多层结构，包括内置工具、自定义工具、MCP工具、外部工具和脚本工具等不同类型
2. **掌握工具加载器设计**：掌握ToolLoader的设计原理和工作流程，理解异步加载和类型分发机制
3. **掌握安全配置管理**：了解工具安全配置的重要性，包括命令限制、资源限制、权限控制、沙箱隔离等安全策略
4. **掌握环境变量注入**：理解配置中环境变量动态替换的实现原理和应用场景
5. **掌握工具依赖管理**：能够管理工具间的依赖关系和初始化顺序，解决循环依赖问题
6. **培养安全思维**：掌握从配置设计到安全执行的完整工具管理系统构建流程，树立安全第一的设计理念

## 📁 文件结构

```
day15-lesson59/
├── tool_config_manager_demo.py    # 主演示代码（包含8个测试）
└── README.md                      # 本文件
```

## 🚀 运行方式

```bash
python tool_config_manager_demo.py              # 运行演示示例
python tool_config_manager_demo.py --test       # 运行测试（建议）
python tool_config_manager_demo.py --demo       # 运行详细演示
python tool_config_manager_demo.py --all        # 运行所有演示和测试
```

## 📖 核心概念

### 1. 工具配置设计哲学

**工具即服务**：
- 工具作为AI Agent系统的扩展能力，需要统一配置和管理
- 支持多种工具类型（内置、自定义、MCP、外部、脚本）
- 平衡功能、安全性和性能需求

**安全第一设计**：
- 所有工具默认运行在受限环境中，需要显式授权
- 支持细粒度的安全策略（命令白名单、资源限制、网络访问控制）
- 配置验证确保系统安全性和稳定性

**配置驱动扩展**：
- 工具配置决定系统能力，支持运行时动态扩展
- 配置包含技术参数（入口点、命令）和业务参数（描述、版本）
- 环境变量注入支持敏感信息的动态配置

### 2. 工具配置结构

**ToolConfig类**定义完整的工具配置：

```python
from tool_config_manager_demo import ToolConfig, ToolType, SecurityLevel, ToolSecurityConfig

# 创建安全配置
security_config = ToolSecurityConfig(
    security_level=SecurityLevel.RESTRICTED,    # 安全级别：信任、限制、沙箱、不信任
    allowed_commands=["^python$", "^echo.*$"],  # 允许的命令（正则表达式）
    blocked_commands=["^rm ", "^shutdown"],     # 禁止的命令（正则表达式）
    max_execution_time=30.0,                    # 最大执行时间（秒）
    max_memory_mb=100,                          # 最大内存使用（MB）
    network_access=False,                       # 是否允许网络访问
    file_system_access=True,                    # 是否允许文件系统访问
    environment_variables=["PATH", "HOME"]      # 允许访问的环境变量
)

# 创建工具配置
config = ToolConfig(
    tool_id="python-interpreter",               # 工具唯一标识
    tool_type=ToolType.EXTERNAL,                # 工具类型：内置、自定义、MCP、外部、脚本
    name="Python解释器",                         # 工具名称
    description="执行Python代码的外部工具",       # 工具描述
    version="1.0.0",                           # 工具版本
    author="DeerFlow Team",                    # 作者
    command="python",                          # 命令（对于外部工具）
    environment_variables={                     # 环境变量
        "PYTHONPATH": "/usr/local/lib/python3.12",
        "API_KEY": "${OPENAI_API_KEY}"          # 支持环境变量引用
    },
    security_config=security_config,            # 安全配置
    dependencies=[                              # 依赖项
        ToolDependency(tool_id="file-reader", required=False)
    ]
)

# 解析环境变量
env_vars = {"OPENAI_API_KEY": "sk-test123"}
resolved_config = config.resolve_environment_variables(env_vars)
print(f"解析后的命令: {resolved_config.command}")
print(f"解析后的环境变量: {resolved_config.environment_variables}")

# 验证配置
errors = config.validate()
if errors:
    print(f"配置验证失败: {errors}")
else:
    print("配置验证通过")
```

**配置字段说明**：
- **tool_id**：工具唯一标识，用于在系统中引用工具
- **tool_type**：工具类型，决定工具的加载和执行方式
- **name**：工具名称，用于显示和日志
- **description**：工具描述，说明工具的用途和功能
- **version**：工具版本，支持版本管理和升级
- **author**：作者信息，用于追踪和联系
- **entry_point**：入口点（模块路径或函数名），对于内置工具
- **module_path**：模块路径（对于自定义工具），指向工具实现文件
- **class_name**：类名（对于面向对象的工具）
- **function_name**：函数名（对于函数式工具）
- **mcp_server_url**：MCP服务器URL（对于MCP工具）
- **command**：命令（对于外部工具），支持环境变量替换
- **script_content**：脚本内容（对于脚本工具）
- **environment_variables**：环境变量，支持 `${VAR_NAME}` 和 `${VAR_NAME:default}` 格式
- **security_config**：安全配置，定义工具的安全限制和权限
- **dependencies**：依赖项，定义工具间的依赖关系
- **metadata**：元数据，扩展配置信息

### 3. 工具类型系统

**ToolType枚举**定义标准化的工具类型：

```python
from tool_config_manager_demo import ToolType

# 工具类型分类
BUILTIN_TOOLS = ToolType.BUILTIN      # 内置工具：系统自带的工具，如文件操作、数学计算
CUSTOM_TOOLS = ToolType.CUSTOM        # 自定义工具：用户编写的工具，支持Python模块导入
MCP_TOOLS = ToolType.MCP              # MCP工具：Model Context Protocol工具，支持远程调用
EXTERNAL_TOOLS = ToolType.EXTERNAL    # 外部工具：通过API或CLI调用的外部程序
SCRIPT_TOOLS = ToolType.SCRIPT        # 脚本工具：动态执行的脚本，支持多种语言

# 工具类型选择策略
def select_tool_type(use_case: str) -> ToolType:
    """根据使用场景选择工具类型"""
    if use_case == "系统内置功能":
        return ToolType.BUILTIN
    elif use_case == "自定义业务逻辑":
        return ToolType.CUSTOM
    elif use_case == "远程服务调用":
        return ToolType.MCP
    elif use_case == "命令行工具集成":
        return ToolType.EXTERNAL
    elif use_case == "动态脚本执行":
        return ToolType.SCRIPT
    else:
        raise ValueError(f"未知的使用场景: {use_case}")

# 工具类型转换
tool_type = ToolType.from_string("builtin")  # 从字符串转换
print(f"工具类型: {tool_type.value}")
```

**工具类型特点**：
1. **内置工具**：性能最高，安全性最好，但功能有限
2. **自定义工具**：灵活性最高，可以实现任意逻辑，需要代码审查
3. **MCP工具**：可扩展性最好，支持远程服务，需要网络连接
4. **外部工具**：集成现有工具，功能丰富，安全性需要仔细控制
5. **脚本工具**：动态性最强，支持热更新，安全性风险最高

### 4. 安全配置管理

**ToolSecurityConfig类**管理工具安全配置：

```python
from tool_config_manager_demo import ToolSecurityConfig, SecurityLevel

# 创建不同安全级别的配置
trusted_config = ToolSecurityConfig(
    security_level=SecurityLevel.TRUSTED,      # 信任级别：完全信任，无限制
    network_access=True,
    file_system_access=True
)

restricted_config = ToolSecurityConfig(
    security_level=SecurityLevel.RESTRICTED,    # 限制级别：有限制的操作
    allowed_commands=["^python$", "^echo.*$"],
    blocked_commands=["^rm ", "^shutdown"],
    max_execution_time=30.0,
    max_memory_mb=100,
    network_access=False,
    file_system_access=True
)

sandboxed_config = ToolSecurityConfig(
    security_level=SecurityLevel.SANDBOXED,     # 沙箱级别：完全隔离，高度限制
    allowed_commands=["^python$"],
    max_execution_time=10.0,
    max_memory_mb=50,
    network_access=False,
    file_system_access=False,
    environment_variables=["PATH"]  # 仅允许访问PATH环境变量
)

untrusted_config = ToolSecurityConfig(
    security_level=SecurityLevel.UNTRUSTED      # 不信任级别：禁止执行
)

# 命令安全检查
test_commands = ["python script.py", "rm -rf /", "echo hello", "shutdown now"]
for cmd in test_commands:
    allowed = restricted_config.is_command_allowed(cmd)
    status = "✓ 允许" if allowed else "✗ 拒绝"
    print(f"{cmd}: {status}")

# 安全配置验证
errors = restricted_config.validate()
if errors:
    print(f"安全配置错误: {errors}")
else:
    print("安全配置有效")
```

**安全级别说明**：
1. **信任级别 (TRUSTED)**：完全信任，无任何限制，仅用于系统核心工具
2. **限制级别 (RESTRICTED)**：有限制的操作，需要明确授权，适用于大多数工具
3. **沙箱级别 (SANDBOXED)**：完全隔离，高度限制，适用于不可信工具
4. **不信任级别 (UNTRUSTED)**：禁止执行，仅用于记录和审计

**安全策略**：
1. **命令限制**：基于正则表达式的命令白名单和黑名单
2. **资源限制**：执行时间、内存使用、文件描述符等资源限制
3. **权限控制**：网络访问、文件系统访问、环境变量访问等权限控制
4. **沙箱隔离**：进程隔离、文件系统隔离、网络隔离等隔离措施
5. **审计日志**：所有工具执行记录审计日志，便于追踪和调查

### 5. 工具依赖管理

**ToolDependency类**管理工具依赖关系：

```python
from tool_config_manager_demo import ToolDependency

# 创建依赖配置
required_dependency = ToolDependency(
    tool_id="file-reader",    # 依赖的工具ID
    version=">=1.0.0",        # 版本要求（可选）
    required=True             # 是否必需
)

optional_dependency = ToolDependency(
    tool_id="logger",
    version="^2.0.0",         # 语义化版本号
    required=False            # 可选依赖
)

# 依赖解析
class DependencyResolver:
    def __init__(self):
        self.dependency_graph = {}
    
    def add_tool(self, tool_id: str, dependencies: List[ToolDependency]):
        """添加工具及其依赖"""
        self.dependency_graph[tool_id] = [
            dep.tool_id for dep in dependencies if dep.required
        ]
    
    def resolve_order(self) -> List[str]:
        """解析依赖顺序（拓扑排序）"""
        from tool_config_manager_demo import ToolLoader
        loader = ToolLoader()
        return loader._topological_sort(self.dependency_graph)

# 使用示例
resolver = DependencyResolver()
resolver.add_tool("advanced-processor", [required_dependency])
resolver.add_tool("file-reader", [])

try:
    order = resolver.resolve_order()
    print(f"工具初始化顺序: {order}")
except ToolDependencyError as e:
    print(f"循环依赖错误: {e}")
```

**依赖管理功能**：
1. **必需依赖**：工具初始化前必须加载的依赖
2. **可选依赖**：工具可以使用但不强制的依赖
3. **版本约束**：支持语义化版本号约束（>=, ^, ~等）
4. **循环依赖检测**：自动检测和报告循环依赖
5. **拓扑排序**：确定工具初始化顺序

### 6. 工具加载器

**ToolLoader类**负责工具加载和管理：

```python
from tool_config_manager_demo import ToolLoader, ToolConfig
import asyncio

# 创建工具加载器
loader = ToolLoader()

# 1. 从YAML文件加载配置
async def load_from_yaml():
    configs = await loader.load_configs_from_yaml(
        "tools.yaml",
        env_vars={"API_KEY": "sk-test123"}  # 传入环境变量
    )
    print(f"加载了 {len(configs)} 个工具配置")
    return configs

# 2. 加载工具实例
async def load_tools(configs):
    tools = await loader.load_tools(configs)
    print(f"加载了 {len(tools)} 个工具实例")
    return tools

# 3. 初始化所有工具
async def initialize_tools():
    await loader.initialize_all()
    print("所有工具初始化完成")

# 4. 执行工具
async def execute_tool():
    result = await loader.execute_tool(
        "python-interpreter",
        {"args": ["-c", "print('Hello, World!')"]}
    )
    print(f"执行结果: {result}")

# 5. 关闭所有工具
async def shutdown_tools():
    await loader.shutdown_all()
    print("所有工具已关闭")

# 完整使用流程
async def main():
    configs = await load_from_yaml()
    tools = await load_tools(configs)
    await initialize_tools()
    
    # 列出所有工具
    tool_list = loader.list_tools()
    print(f"可用工具: {[tool['name'] for tool in tool_list]}")
    
    # 执行工具
    await execute_tool()
    
    # 安全验证
    errors = loader.validate_security_configs()
    if errors:
        print(f"安全配置问题: {errors}")
    
    await shutdown_tools()

# 运行
asyncio.run(main())
```

**加载器功能**：
1. **配置加载**：从YAML、JSON等格式加载工具配置
2. **环境变量解析**：支持配置中的环境变量动态替换
3. **依赖解析**：自动解析工具依赖关系和初始化顺序
4. **异步加载**：支持异步工具初始化和执行
5. **类型分发**：根据工具类型创建对应的工具实例
6. **安全管理**：验证安全配置，执行安全检查
7. **生命周期管理**：统一的初始化和关闭流程
8. **执行监控**：记录工具使用情况和性能指标

### 7. 工具抽象层

**BaseTool抽象类**定义所有工具的统一接口：

```python
from tool_config_manager_demo import BaseTool, ToolConfig
import asyncio

# 自定义工具实现
class CalculatorTool(BaseTool):
    """计算器工具示例"""
    
    async def initialize(self) -> None:
        """初始化工具"""
        print(f"初始化计算器工具: {self.name}")
        self.memory = 0  # 工具内部状态
        await asyncio.sleep(0.1)  # 模拟初始化延迟
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        operation = input_data.get("operation", "add")
        value = input_data.get("value", 0)
        
        if operation == "add":
            self.memory += value
        elif operation == "subtract":
            self.memory -= value
        elif operation == "multiply":
            self.memory *= value
        elif operation == "divide":
            if value != 0:
                self.memory /= value
            else:
                return {"error": "除以零错误"}
        elif operation == "clear":
            self.memory = 0
        else:
            return {"error": f"未知操作: {operation}"}
        
        self.record_usage()
        return {"success": True, "result": self.memory, "operation": operation}
    
    async def shutdown(self) -> None:
        """关闭工具"""
        print(f"关闭计算器工具: {self.name}")
        self.memory = 0

# 使用工具
async def use_calculator():
    # 创建配置
    config = ToolConfig(
        tool_id="calculator",
        tool_type=ToolType.CUSTOM,
        name="计算器",
        description="简单的计算器工具"
    )
    
    # 创建工具实例
    calculator = CalculatorTool(config)
    
    # 初始化
    await calculator.initialize()
    
    # 执行操作
    result1 = await calculator.execute({"operation": "add", "value": 10})
    print(f"加10: {result1}")
    
    result2 = await calculator.execute({"operation": "multiply", "value": 2})
    print(f"乘2: {result2}")
    
    result3 = await calculator.execute({"operation": "clear"})
    print(f"清零: {result3}")
    
    # 查看使用统计
    stats = calculator.to_dict()
    print(f"工具统计: {stats}")
    
    # 关闭
    await calculator.shutdown()

asyncio.run(use_calculator())
```

**工具接口设计**：
1. **统一接口**：所有工具实现相同的接口，便于管理和调用
2. **异步支持**：支持异步初始化和执行，提高系统并发能力
3. **状态管理**：工具可以维护内部状态，支持有状态工具
4. **使用统计**：自动记录工具使用次数和最后使用时间
5. **输入验证**：提供统一的输入验证机制
6. **安全集成**：集成安全配置检查功能

## 🔧 核心类说明

### ToolConfig
工具配置类，定义单个工具的完整配置信息。

```python
# 创建配置
config = ToolConfig(
    tool_id="http-client",
    tool_type=ToolType.CUSTOM,
    name="HTTP客户端",
    description="发送HTTP请求的自定义工具",
    module_path="/path/to/http_client.py",
    class_name="HttpClient",
    security_config=ToolSecurityConfig(
        security_level=SecurityLevel.RESTRICTED,
        network_access=True,
        max_execution_time=10.0
    ),
    dependencies=[
        ToolDependency(tool_id="logger", required=False)
    ]
)

# 序列化和反序列化
config_dict = config.to_dict()  # 转换为字典
config_from_dict = ToolConfig.from_dict(config_dict)  # 从字典创建

# 环境变量解析
env_vars = {"API_KEY": "sk-123456", "BASE_URL": "https://api.example.com"}
resolved_config = config.resolve_environment_variables(env_vars)

# 依赖管理
required_deps = config.get_required_dependencies()
print(f"必需依赖: {required_deps}")

# 配置验证
errors = config.validate()
if errors:
    print(f"配置错误: {errors}")
```

### ToolSecurityConfig
工具安全配置类，管理安全策略。

```python
# 创建安全配置
security_config = ToolSecurityConfig(
    security_level=SecurityLevel.RESTRICTED,
    allowed_commands=["^python$", "^curl$", "^wget$"],
    blocked_commands=["^rm ", "^dd ", "^shutdown"],
    max_execution_time=30.0,
    max_memory_mb=256,
    network_access=True,
    file_system_access=True,
    environment_variables=["PATH", "HOME", "TEMP"]
)

# 命令安全检查
commands_to_check = ["python script.py", "rm -rf /", "curl https://api.example.com"]
for cmd in commands_to_check:
    allowed = security_config.is_command_allowed(cmd)
    print(f"{cmd}: {'允许' if allowed else '拒绝'}")

# 安全验证
errors = security_config.validate()
if errors:
    print(f"安全配置错误: {errors}")

# 序列化
security_dict = security_config.to_dict()
print(f"安全配置字典: {security_dict}")
```

### ToolLoader
工具加载器，负责工具的生命周期管理。

```python
# 创建加载器
loader = ToolLoader()

# 从YAML加载配置
configs = await loader.load_configs_from_yaml("config/tools.yaml")

# 加载工具实例
tools = await loader.load_tools(configs)

# 初始化所有工具
await loader.initialize_all()

# 执行工具
result = await loader.execute_tool("http-client", {
    "method": "GET",
    "url": "https://api.example.com/data"
})

# 获取工具信息
tool_list = loader.list_tools()
print(f"可用工具: {[tool['name'] for tool in tool_list]}")

# 获取特定工具
tool = loader.get_tool("http-client")
if tool:
    print(f"工具状态: 已初始化={tool.initialized}, 使用次数={tool.usage_count}")

# 安全验证
errors = loader.validate_security_configs()
if errors:
    print(f"安全警告: {errors}")

# 关闭所有工具
await loader.shutdown_all()
```

### BaseTool
工具基类，定义所有工具的通用接口。

```python
# 自定义工具实现
class DatabaseTool(BaseTool):
    """数据库工具示例"""
    
    async def initialize(self) -> None:
        """初始化数据库连接"""
        self.connection = await create_db_connection(self.config)
        self.initialized = True
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行数据库查询"""
        query = input_data.get("query")
        params = input_data.get("params", {})
        
        try:
            result = await self.connection.execute(query, params)
            self.record_usage()
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": f"查询失败: {str(e)}"}
    
    async def shutdown(self) -> None:
        """关闭数据库连接"""
        if self.connection:
            await self.connection.close()
        self.initialized = False
    
    def validate_input(self, input_data: Dict[str, Any]) -> List[str]:
        """验证输入数据"""
        errors = []
        if "query" not in input_data:
            errors.append("缺少query参数")
        return errors

# 使用工具
async def use_database_tool():
    config = ToolConfig(
        tool_id="database",
        tool_type=ToolType.CUSTOM,
        name="数据库工具",
        description="执行数据库查询的工具",
        module_path="tools/database.py",
        class_name="DatabaseTool",
        security_config=ToolSecurityConfig(
            security_level=SecurityLevel.RESTRICTED,
            max_execution_time=5.0
        )
    )
    
    tool = DatabaseTool(config)
    await tool.initialize()
    
    result = await tool.execute({
        "query": "SELECT * FROM users WHERE id = :id",
        "params": {"id": 1}
    })
    
    print(f"查询结果: {result}")
    
    await tool.shutdown()
```

## 📊 测试用例

| 测试 | 说明 | 预期结果 |
|------|------|----------|
| 测试1 | 工具配置创建和序列化 | 配置可正确创建、序列化和反序列化 |
| 测试2 | 环境变量解析 | 环境变量可正确解析，支持默认值和嵌套引用 |
| 测试3 | 安全配置验证 | 安全配置验证功能正常，能检测无效配置 |
| 测试4 | 命令安全检查 | 命令白名单和黑名单功能正常 |
| 测试5 | 工具依赖管理 | 依赖关系能正确解析，能检测循环依赖 |
| 测试6 | 工具类型创建 | 能根据工具类型创建正确的工具实例 |
| 测试7 | 工具加载器配置加载 | 能从YAML文件正确加载配置 |
| 测试8 | 异步工具执行模拟 | 异步工具执行流程正常，错误处理正确 |

## 📝 课后练习

### 基础练习
1. **扩展工具类型系统**：添加新的工具类型（如REST API工具、数据库工具、消息队列工具）
2. **实现配置验证**：添加工具配置的完整验证规则（命令安全性、路径有效性、参数范围）
3. **添加新的安全策略**：实现进程隔离、文件系统沙箱、网络防火墙等安全策略
4. **实现配置热重载**：添加配置文件监视功能，配置变化时自动重新加载工具
5. **增强环境变量支持**：支持嵌套环境变量引用、加密环境变量、环境变量模板

### 进阶练习
1. **实现工具编排引擎**：实现工具执行顺序和依赖关系的编排功能
2. **优化性能监控**：实现工具性能监控、资源使用限制、自动扩缩容
3. **设计工具市场**：设计支持动态安装和卸载的工具市场架构
4. **实现工具版本管理**：支持工具版本控制、灰度发布、回滚机制
5. **添加工具使用审计**：实现完整的工具使用审计日志和异常检测

### 挑战练习
1. **实现智能安全策略**：基于机器学习动态调整工具安全策略
2. **设计跨语言工具支持**：支持JavaScript、Go、Rust等语言编写的工具
3. **实现工具联邦学习**：多个工具间共享知识和经验，提高整体性能
4. **构建工具生态系统**：设计完整的工具开发、测试、部署、运维流程
5. **设计工具安全网关**：添加API密钥管理、请求限流、内容过滤等安全功能

## 🔗 扩展阅读

### 理论知识
1. **安全设计原则**：最小权限原则、防御性编程、安全默认值
2. **配置管理理论**：十二要素应用的配置管理原则
3. **依赖管理理论**：语义化版本控制、依赖解析算法、循环依赖检测
4. **系统可靠性**：容错设计、降级策略、熔断机制在工具管理中的应用
5. **性能工程**：工具性能测试和优化方法

### 工程实践
1. **Docker安全实践**：容器安全配置、镜像扫描、运行时保护
2. **Linux安全模块**：SELinux、AppArmor在工具隔离中的应用
3. **沙箱技术**：Firejail、Bubblewrap、gVisor等沙箱工具的使用
4. **企业工具治理**：企业级工具管理规范和工具链建设
5. **多云工具策略**：跨多个云服务商的工具部署和管理

### 工具推荐
1. **配置管理工具**：Hydra、OmegaConf、Pydantic Settings
2. **安全扫描工具**：Bandit、Safety、Trivy
3. **性能测试工具**：Locust、Apache JMeter、自定义基准测试
4. **部署工具**：Docker、Kubernetes、Helm Charts
5. **监控工具**：Prometheus、Grafana、ELK Stack

## 🛠️ 最佳实践

### 配置设计原则
1. **环境分离**：开发、测试、生产环境使用不同的工具配置
2. **安全第一**：默认使用限制级别，需要显式授权提升权限
3. **版本控制**：工具配置和代码一样进行版本控制和代码审查
4. **文档化**：每个配置项都有详细说明、示例和安全注意事项
5. **验证前置**：配置加载时立即验证，避免运行时安全漏洞

### 安全配置建议
1. **最小权限原则**：只授予工具完成任务所需的最小权限
2. **默认拒绝**：默认禁止所有操作，需要显式允许
3. **深度防御**：多层安全防护，不依赖单一安全机制
4. **审计日志**：记录所有工具执行，便于安全调查
5. **定期审查**：定期审查工具权限和配置，及时调整

### 工具选择策略
1. **内置优先**：优先使用内置工具，安全性最高
2. **自定义适度**：只在必要时使用自定义工具，需要代码审查
3. **外部工具审慎**：仔细评估外部工具的安全性，限制权限
4. **脚本工具限制**：限制脚本工具的使用，避免安全风险
5. **MCP工具验证**：验证MCP服务器的可信度，使用加密通信

### 性能优化建议
1. **懒加载**：按需加载工具，减少启动时间
2. **连接池**：复用工具连接，减少建立连接开销
3. **缓存结果**：缓存工具执行结果，减少重复计算
4. **异步执行**：非实时任务使用异步执行，提高并发能力
5. **监控调优**：持续监控工具性能，根据数据调优配置

## 📈 性能指标目标

### 配置系统性能
- **加载时间**：配置加载 < 50ms，工具初始化 < 200ms
- **查找性能**：工具查找 < 5ms（O(1)复杂度）
- **内存使用**：每个工具实例内存占用 < 10MB
- **并发支持**：支持1000+并发工具执行

### 安全系统可靠性
- **安全检测**：恶意命令拦截率 > 99.9%
- **资源限制**：资源超限检测准确率 > 99.9%
- **隔离效果**：工具隔离逃逸防护率 > 99.9%
- **审计完整性**：工具执行审计覆盖率 100%

### 系统可扩展性
- **工具类型扩展**：添加新工具类型不需要修改核心代码
- **配置格式扩展**：支持JSON、YAML、TOML等多种配置格式
- **安全策略扩展**：支持动态添加新的安全策略
- **性能水平扩展**：支持水平扩展，增加节点提高处理能力

## 🔍 故障排除

### 常见问题
1. **工具加载失败**：检查配置路径、文件权限、依赖关系
2. **安全配置错误**：检查正则表达式、权限设置、资源限制
3. **环境变量未解析**：检查环境变量名称、默认值、嵌套引用
4. **依赖循环错误**：检查工具依赖关系，解决循环依赖
5. **性能下降**：检查资源限制、网络延迟、工具实现

### 调试工具
```bash
# 测试工具配置
python -c "from tool_config_manager_demo import ToolConfig, ToolType; config=ToolConfig(tool_id='test', tool_type=ToolType.BUILTIN, name='测试工具'); print(config.to_dict())"

# 测试安全配置
python -c "from tool_config_manager_demo import ToolSecurityConfig, SecurityLevel; security=ToolSecurityConfig(security_level=SecurityLevel.RESTRICTED); print(security.is_command_allowed('python'))"

# 测试环境变量解析
python -c "from tool_config_manager_demo import ToolConfig, ToolType; config=ToolConfig(tool_id='test', tool_type=ToolType.EXTERNAL, command='echo \${MESSAGE}'); env_vars={'MESSAGE':'Hello'}; resolved=config.resolve_environment_variables(env_vars); print(resolved.command)"

# 性能分析
python -m cProfile -s time tool_config_manager_demo.py --test
```

### 紧急处理
1. **安全漏洞**：立即禁用相关工具，审查安全配置，更新安全策略
2. **工具故障**：立即切换到备用工具或降级方案
3. **配置错误**：回滚到上一个已知正确的配置版本
4. **性能严重下降**：启用限流，增加容量，优化配置
5. **依赖冲突**：暂时移除冲突依赖，使用简化版本

---

**注意**：本演示代码包含完整测试套件，使用`--test`参数运行所有测试确保功能正常。建议在实际项目中使用前根据具体需求调整安全策略和验证规则。