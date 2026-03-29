# Day 15 - 第60节课：沙箱与技能配置

## 📚 课程概述

本节课讲解现代AI Agent系统中的沙箱和技能配置管理，包括沙箱配置架构、技能配置体系、安全配置原则和配置继承机制。重点掌握多层结构设计、版本管理、依赖解析和安全策略实施，培养安全第一的系统配置思维。

## 🎯 学习目标

1. **掌握沙箱配置架构**：理解沙箱配置的多层结构设计，包括提供者配置、资源限制、环境变量等
2. **掌握技能配置体系**：掌握技能配置的结构设计，包括版本管理、依赖管理、启用状态、配置参数等
3. **掌握安全配置原则**：了解沙箱安全配置的重要性，包括资源限制、网络隔离、权限控制等安全策略
4. **掌握配置继承机制**：理解默认配置与具体提供者配置的继承和覆盖关系，实现灵活配置
5. **培养系统化配置思维**：掌握从配置设计到系统集成的完整流程，建立安全可靠的AI Agent系统配置基础

## 📁 文件结构

```
day15-lesson60/
├── sandbox_skill_config_demo.py    # 主演示代码（包含8个测试）
└── README.md                      # 本文件
```

## 🚀 运行方式

```bash
python sandbox_skill_config_demo.py              # 运行演示示例
python sandbox_skill_config_demo.py --test       # 运行测试（建议）
python sandbox_skill_config_demo.py --demo       # 运行详细演示
python sandbox_skill_config_demo.py --all        # 运行所有演示和测试
python sandbox_skill_config_demo.py --generate-yaml  # 生成YAML示例
```

## 📖 核心概念

### 1. 沙箱配置设计哲学

**安全隔离第一**：
- AI Agent系统需要安全隔离的执行环境，防止恶意代码影响主机系统
- 沙箱提供不同级别的隔离：本地进程、Docker容器、WebAssembly、虚拟机等
- 平衡隔离强度、性能开销和开发便利性

**配置驱动隔离**：
- 通过配置文件定义沙箱的行为和限制
- 支持多种提供者类型，每种提供者有特定的配置参数
- 配置继承机制允许灵活覆盖默认设置

**资源精细控制**：
- CPU、内存、磁盘、网络等资源的精确限制
- 环境变量、文件系统访问、网络访问的细粒度控制
- 执行时间和进程数的安全限制

### 2. 沙箱配置结构

**SandboxConfig类**定义完整的沙箱配置：

```python
from sandbox_skill_config_demo import SandboxConfig, SandboxProviderType, LocalProviderConfig, DockerProviderConfig, AIOProviderConfig, SecurityConfig, SecurityLevel

# 创建安全配置
security_config = SecurityConfig(
    security_level=SecurityLevel.RESTRICTED,    # 安全级别：信任、限制、沙箱、不信任
    cpu_limit_percent=50.0,                     # CPU限制百分比
    memory_limit_mb=512,                        # 内存限制(MB)
    disk_limit_mb=1024,                         # 磁盘限制(MB)
    network_access=False,                       # 是否允许网络访问
    file_system_access=True,                    # 是否允许文件系统访问
    max_execution_time_seconds=30.0,            # 最大执行时间（秒）
    max_process_count=10                        # 最大进程数
)

# 创建本地提供者配置
local_provider = LocalProviderConfig(
    provider_type=SandboxProviderType.LOCAL,    # 提供者类型：本地
    name="local-dev",                           # 提供者名称
    description="开发环境本地沙箱",               # 描述
    work_dir="/tmp/dev",                        # 工作目录
    python_path="/usr/bin/python3",             # Python路径
    environment_variables={                     # 环境变量
        "PYTHONPATH": "/usr/local/lib/python3.12",
        "LOG_LEVEL": "INFO"
    },
    security_config=security_config             # 安全配置
)

# 创建Docker提供者配置
docker_provider = DockerProviderConfig(
    provider_type=SandboxProviderType.DOCKER,   # 提供者类型：Docker
    name="docker-prod",                         # 提供者名称
    description="生产环境Docker沙箱",            # 描述
    image="python",                             # Docker镜像
    tag="3.12-slim",                            # 镜像标签
    volumes=[                                   # 挂载卷
        {"host": "/tmp/data", "container": "/data", "mode": "rw"},
        {"host": "/tmp/logs", "container": "/logs", "mode": "ro"}
    ],
    environment_variables={                     # 环境变量
        "PYTHONUNBUFFERED": "1",
        "API_KEY": "${EXTERNAL_API_KEY}"        # 支持环境变量引用
    },
    network_mode="bridge",                      # 网络模式
    privileged=False,                           # 是否特权模式
    security_config=security_config             # 安全配置
)

# 创建沙箱配置
sandbox_config = SandboxConfig(
    default_provider="local-dev",               # 默认提供者名称
    providers={                                 # 提供者字典
        "local-dev": local_provider,
        "docker-prod": docker_provider
    },
    security_config=security_config,            # 沙箱级别的安全配置
    environment_variables={                     # 沙箱级别的环境变量
        "LOG_LEVEL": "${APP_LOG_LEVEL:INFO}",   # 支持默认值
        "MAX_RETRIES": "3"
    },
    metadata={                                  # 元数据
        "created_by": "SystemAdmin",
        "environment": "development"
    }
)

# 验证配置
errors = sandbox_config.validate()
if errors:
    print(f"配置验证失败: {errors}")
else:
    print("配置验证通过")

# 获取提供者配置
provider = sandbox_config.get_provider("docker-prod")
if provider:
    print(f"提供者类型: {provider.provider_type.value}")
    print(f"安全级别: {provider.security_config.security_level.value}")

# 解析环境变量
env_vars = {"EXTERNAL_API_KEY": "sk-test-123", "APP_LOG_LEVEL": "DEBUG"}
resolved_config = sandbox_config.resolve_environment_variables(env_vars)
print(f"解析后的环境变量: {resolved_config.environment_variables}")
```

**配置字段说明**：
- **default_provider**：默认提供者名称，当未指定提供者时使用
- **providers**：提供者配置字典，键为提供者名称，值为提供者配置对象
- **security_config**：沙箱级别的安全配置，作为所有提供者的默认安全配置
- **environment_variables**：沙箱级别的环境变量，支持 `${VAR_NAME}` 和 `${VAR_NAME:default}` 格式
- **metadata**：元数据，扩展配置信息

**提供者类型**：
1. **LOCAL**：本地进程沙箱，适用于开发和测试环境，性能高，隔离性低
2. **DOCKER**：Docker容器沙箱，适用于生产环境，隔离性好，性能开销适中
3. **AIO**：异步I/O沙箱，适用于高并发场景，支持任务队列和重试机制
4. **WEBASSEMBLY**：WebAssembly沙箱，适用于高安全环境，隔离性最强
5. **VM**：虚拟机沙箱，适用于完全隔离环境，性能开销最大

### 3. 安全配置管理

**SecurityConfig类**管理沙箱和技能的安全配置：

```python
from sandbox_skill_config_demo import SecurityConfig, SecurityLevel

# 创建不同安全级别的配置
trusted_config = SecurityConfig(
    security_level=SecurityLevel.TRUSTED,      # 信任级别：完全信任，无限制
    network_access=True,
    file_system_access=True
)

restricted_config = SecurityConfig(
    security_level=SecurityLevel.RESTRICTED,    # 限制级别：有限制的操作
    cpu_limit_percent=50.0,
    memory_limit_mb=512,
    network_access=False,
    file_system_access=True,
    max_execution_time_seconds=30.0
)

sandboxed_config = SecurityConfig(
    security_level=SecurityLevel.SANDBOXED,     # 沙箱级别：完全隔离，高度限制
    cpu_limit_percent=30.0,
    memory_limit_mb=256,
    network_access=False,
    file_system_access=False,
    read_only_paths=["/usr", "/lib", "/bin"],   # 只读路径
    environment_variables_whitelist=["PATH"]    # 环境变量白名单
)

untrusted_config = SecurityConfig(
    security_level=SecurityLevel.UNTRUSTED      # 不信任级别：禁止执行
)

# 网络访问检查
hosts_to_check = ["api.example.com", "malicious.com", "download.example.com"]
for host in hosts_to_check:
    allowed = restricted_config.is_network_allowed(host)
    status = "✓ 允许" if allowed else "✗ 拒绝"
    print(f"{host}: {status}")

# 安全配置验证
errors = restricted_config.validate()
if errors:
    print(f"安全配置错误: {errors}")
else:
    print("安全配置有效")
```

**安全级别说明**：
1. **信任级别 (TRUSTED)**：完全信任，无任何限制，仅用于系统核心组件
2. **限制级别 (RESTRICTED)**：有限制的操作，需要明确授权，适用于大多数场景
3. **沙箱级别 (SANDBOXED)**：完全隔离，高度限制，适用于不可信代码
4. **不信任级别 (UNTRUSTED)**：禁止执行，仅用于记录和审计

**安全策略**：
1. **资源限制**：CPU、内存、磁盘、进程数等资源限制
2. **网络隔离**：网络访问控制，支持白名单和黑名单（正则表达式）
3. **文件系统控制**：只读路径、可写路径、文件系统访问权限
4. **环境变量控制**：环境变量白名单，限制可访问的环境变量
5. **执行时间限制**：最大执行时间，防止无限循环或死锁

### 4. 技能配置体系

**SkillConfig类**定义单个技能的完整配置：

```python
from sandbox_skill_config_demo import SkillConfig, SkillType, SkillStatus, SkillDependency

# 创建技能依赖
file_reader_dep = SkillDependency(
    skill_id="file-reader",           # 依赖的技能ID
    version_constraint=">=1.0.0",     # 版本约束
    required=True,                    # 是否必需
    description="文件读取技能依赖"      # 依赖描述
)

logger_dep = SkillDependency(
    skill_id="logger",
    version_constraint="^2.0.0",      # 语义化版本号
    required=False,                   # 可选依赖
    description="日志记录技能依赖"
)

# 创建技能配置
skill_config = SkillConfig(
    skill_id="file-converter",        # 技能唯一标识
    name="文件转换器",                 # 技能名称
    description="转换不同文件格式的技能", # 技能描述
    version="2.1.3",                  # 技能版本
    skill_type=SkillType.FILE_CONVERTER,  # 技能类型
    status=SkillStatus.ENABLED,       # 技能状态
    author="Data Tools Team",         # 作者
    license="Apache-2.0",             # 许可证
    tags=["file", "conversion", "format"],  # 标签
    dependencies=[file_reader_dep, logger_dep],  # 依赖项
    parameters={                      # 配置参数
        "supported_formats": ["json", "yaml", "csv", "xml"],
        "max_file_size_mb": 10,
        "enable_compression": True
    },
    sandbox_provider="local",         # 指定沙箱提供者
    metadata={                        # 元数据
        "category": "data",
        "difficulty": "intermediate",
        "last_updated": "2024-03-28"
    }
)

# 验证配置
errors = skill_config.validate()
if errors:
    print(f"技能配置错误: {errors}")
else:
    print("技能配置验证通过")

# 依赖管理
required_deps = skill_config.get_required_dependencies()
optional_deps = skill_config.get_optional_dependencies()
print(f"必需依赖: {[dep.skill_id for dep in required_deps]}")
print(f"可选依赖: {[dep.skill_id for dep in optional_deps]}")

# 版本约束检查
version = "1.5.0"
satisfied = file_reader_dep.is_version_satisfied(version)
print(f"版本 {version} 满足约束 {file_reader_dep.version_constraint}: {satisfied}")
```

**配置字段说明**：
- **skill_id**：技能唯一标识，用于在系统中引用技能
- **name**：技能名称，用于显示和日志
- **description**：技能描述，说明技能的用途和功能
- **version**：技能版本，支持版本管理和升级
- **skill_type**：技能类型，分类管理不同功能的技能
- **status**：技能状态，控制技能的启用和禁用
- **author**：作者信息，用于追踪和联系
- **license**：许可证，说明技能的使用权限
- **tags**：标签，便于搜索和分类
- **dependencies**：依赖项，定义技能间的依赖关系
- **parameters**：配置参数，技能的运行时参数
- **sandbox_provider**：指定沙箱提供者，覆盖系统默认
- **security_config**：安全配置，技能级别的安全策略
- **metadata**：元数据，扩展配置信息
- **created_at**/**updated_at**：创建和更新时间

**技能类型**：
1. **CALCULATOR**：计算器技能，数学计算、统计分析
2. **FILE_CONVERTER**：文件转换技能，格式转换、数据处理
3. **WEB_SCRAPER**：网络爬虫技能，数据抓取、网页解析
4. **DATABASE**：数据库技能，数据查询、事务处理
5. **API_CLIENT**：API客户端技能，外部服务调用
6. **ML_MODEL**：机器学习技能，模型推理、预测
7. **TEXT_PROCESSOR**：文本处理技能，NLP处理、文本分析
8. **IMAGE_PROCESSOR**：图像处理技能，图像分析、处理

**技能状态**：
1. **ENABLED**：已启用，可以正常使用
2. **DISABLED**：已禁用，配置存在但不可用
3. **PENDING**：等待中，等待依赖或条件满足
4. **DEPRECATED**：已弃用，不推荐使用，未来会移除

### 5. 技能系统配置

**SkillSystemConfig类**管理整个技能系统的配置：

```python
from sandbox_skill_config_demo import SkillSystemConfig, SkillConfig, SandboxConfig

# 创建技能配置
calculator_skill = SkillConfig(
    skill_id="calculator",
    name="计算器",
    version="1.2.0",
    skill_type=SkillType.CALCULATOR
)

file_converter_skill = SkillConfig(
    skill_id="file-converter",
    name="文件转换器",
    version="2.1.3",
    skill_type=SkillType.FILE_CONVERTER
)

# 创建沙箱配置
sandbox_config = SandboxConfig(
    default_provider="local",
    providers={...}  # 省略提供者配置
)

# 创建技能系统配置
system_config = SkillSystemConfig(
    default_sandbox_provider="local",      # 默认沙箱提供者
    sandbox_config=sandbox_config,         # 沙箱配置
    skills={                               # 技能字典
        "calculator": calculator_skill,
        "file-converter": file_converter_skill
    },
    auto_resolve_dependencies=True,        # 自动解析依赖
    enable_version_check=True,             # 启用版本检查
    enable_security_check=True,            # 启用安全检查
    metadata={                             # 元数据
        "system_name": "DeerFlow Skill System",
        "version": "1.0.0",
        "environment": "development"
    }
)

# 验证配置
errors = system_config.validate()
if errors:
    print(f"系统配置错误: {errors}")
else:
    print("系统配置验证通过")

# 获取依赖顺序
try:
    dependency_order = system_config.get_dependency_order()
    print(f"技能依赖顺序: {dependency_order}")
except SkillConfigError as e:
    print(f"依赖解析错误: {e}")

# 添加新技能
new_skill = SkillConfig(
    skill_id="web-scraper",
    name="网络爬虫",
    version="3.0.1",
    skill_type=SkillType.WEB_SCRAPER
)
system_config.add_skill(new_skill)

# 获取技能配置
skill = system_config.get_skill("calculator")
if skill:
    print(f"技能名称: {skill.name}, 版本: {skill.version}")
```

**系统配置功能**：
1. **依赖管理**：自动解析技能依赖关系，检测循环依赖
2. **拓扑排序**：确定技能初始化和加载顺序
3. **配置验证**：验证技能配置的完整性和一致性
4. **技能管理**：添加、移除、查询技能配置
5. **沙箱集成**：集成沙箱配置，为技能提供执行环境

### 6. 配置加载器

**SandboxSkillConfigLoader类**负责配置的加载和管理：

```python
from sandbox_skill_config_demo import SandboxSkillConfigLoader
import asyncio

# 创建配置加载器
loader = SandboxSkillConfigLoader(config_dir="/path/to/configs")

# 从YAML文件加载配置
async def load_configs():
    await loader.load_from_yaml(
        sandbox_yaml="sandbox.yaml",
        skills_yaml="skills.yaml",
        env_vars={                          # 环境变量
            "EXTERNAL_API_KEY": "sk-test-123",
            "APP_LOG_LEVEL": "INFO"
        }
    )
    
    # 验证所有配置
    errors = loader.validate_all()
    if errors:
        print(f"配置验证失败: {errors}")
        return
    
    # 获取沙箱提供者
    provider = loader.get_sandbox_provider("docker")
    if provider:
        print(f"提供者名称: {provider.name}")
        print(f"安全级别: {provider.security_config.security_level.value}")
    
    # 获取技能依赖信息
    skill_info = loader.get_skill_with_dependencies("file-converter")
    deps = [dep["skill"]["skill_id"] for dep in skill_info["dependencies"]]
    print(f"file-converter依赖的技能: {deps}")
    
    # 保存配置到YAML文件
    loader.to_yaml_files(
        sandbox_output="sandbox_backup.yaml",
        skills_output="skills_backup.yaml"
    )

# 运行加载器
asyncio.run(load_configs())
```

**加载器功能**：
1. **配置加载**：从YAML、JSON等格式加载配置
2. **环境变量解析**：支持配置中的环境变量动态替换
3. **配置验证**：验证配置的完整性和一致性
4. **依赖解析**：解析技能依赖关系和初始化顺序
5. **配置备份**：保存配置到文件，支持版本控制
6. **错误处理**：详细的错误信息和验证结果

### 7. 配置继承机制

**配置继承设计**：
```python
from sandbox_skill_config_demo import SandboxConfig, SecurityConfig, SecurityLevel

# 默认安全配置（基配置）
default_security = SecurityConfig(
    security_level=SecurityLevel.RESTRICTED,
    cpu_limit_percent=50.0,
    memory_limit_mb=512,
    network_access=False
)

# 沙箱级别的安全配置（继承并覆盖）
sandbox_security = SecurityConfig(
    security_level=SecurityLevel.RESTRICTED,
    cpu_limit_percent=60.0,      # 覆盖：从50%提高到60%
    memory_limit_mb=512,         # 继承：保持不变
    network_access=False,        # 继承：保持不变
    max_execution_time_seconds=45.0  # 新增：添加执行时间限制
)

# 提供者级别的安全配置（进一步覆盖）
provider_security = SecurityConfig(
    security_level=SecurityLevel.SANDBOXED,  # 覆盖：提高安全级别
    cpu_limit_percent=60.0,      # 继承：保持不变
    memory_limit_mb=256,         # 覆盖：降低内存限制
    network_access=True,         # 覆盖：允许网络访问
    max_execution_time_seconds=30.0,  # 覆盖：缩短执行时间
    network_whitelist=[r"^api\.example\.com$"]  # 新增：添加网络白名单
)

# 配置继承规则：
# 1. 提供者配置继承沙箱配置
# 2. 沙箱配置继承默认配置
# 3. 子配置可以覆盖父配置的字段
# 4. 子配置可以新增字段
# 5. 未指定的字段使用父配置的值

print("配置继承示例：")
print(f"默认安全级别: {default_security.security_level.value}")
print(f"沙箱安全级别: {sandbox_security.security_level.value}")
print(f"提供者安全级别: {provider_security.security_level.value}")
print(f"提供者内存限制: {provider_security.memory_limit_mb}MB")
print(f"提供者网络白名单: {provider_security.network_whitelist}")
```

**继承规则**：
1. **层次结构**：默认配置 → 沙箱配置 → 提供者配置 → 技能配置
2. **字段覆盖**：子配置可以覆盖父配置的同名字段
3. **字段新增**：子配置可以添加父配置中没有的字段
4. **合并策略**：列表和字典采用深层合并，而不是简单替换
5. **环境变量优先**：环境变量解析在配置继承之后进行

## 🔧 核心类说明

### SandboxConfig
沙箱配置类，定义整个沙箱系统的配置。

```python
# 创建配置
sandbox_config = SandboxConfig(
    default_provider="local",
    providers={
        "local": LocalProviderConfig(...),
        "docker": DockerProviderConfig(...)
    },
    security_config=SecurityConfig(...),
    environment_variables={
        "LOG_LEVEL": "INFO",
        "API_TIMEOUT": "30"
    }
)

# 验证配置
errors = sandbox_config.validate()
if errors:
    print(f"配置错误: {errors}")

# 获取提供者
provider = sandbox_config.get_provider("docker")
if provider:
    print(f"提供者类型: {provider.provider_type.value}")

# 解析环境变量
env_vars = {"API_KEY": "sk-123456"}
resolved_config = sandbox_config.resolve_environment_variables(env_vars)

# 序列化和反序列化
config_dict = sandbox_config.to_dict()
config_from_dict = SandboxConfig.from_dict(config_dict)
```

### SkillConfig
技能配置类，定义单个技能的完整配置。

```python
# 创建技能配置
skill_config = SkillConfig(
    skill_id="data-processor",
    name="数据处理器",
    description="处理和分析数据的技能",
    version="1.5.0",
    skill_type=SkillType.DATABASE,
    status=SkillStatus.ENABLED,
    dependencies=[
        SkillDependency(skill_id="file-reader", required=True),
        SkillDependency(skill_id="logger", required=False)
    ],
    parameters={
        "batch_size": 100,
        "timeout_seconds": 60
    },
    sandbox_provider="docker"
)

# 验证配置
errors = skill_config.validate()
if errors:
    print(f"技能配置错误: {errors}")

# 依赖管理
required_deps = skill_config.get_required_dependencies()
print(f"必需依赖: {[dep.skill_id for dep in required_deps]}")

# 检查版本兼容性
version = "2.0.0"
for dep in skill_config.dependencies:
    if dep.version_constraint:
        satisfied = dep.is_version_satisfied(version)
        print(f"依赖 {dep.skill_id} 版本 {version} 满足约束 {dep.version_constraint}: {satisfied}")

# 序列化和反序列化
config_dict = skill_config.to_dict()
config_from_dict = SkillConfig.from_dict(config_dict)
```

### SkillSystemConfig
技能系统配置类，管理整个技能系统的配置。

```python
# 创建系统配置
system_config = SkillSystemConfig(
    default_sandbox_provider="local",
    sandbox_config=sandbox_config,
    skills={
        "calculator": calculator_skill,
        "file-converter": file_converter_skill,
        "web-scraper": web_scraper_skill
    },
    auto_resolve_dependencies=True,
    enable_version_check=True
)

# 验证配置
errors = system_config.validate()
if errors:
    print(f"系统配置错误: {errors}")

# 获取依赖顺序
try:
    order = system_config.get_dependency_order()
    print(f"技能初始化顺序: {order}")
except SkillConfigError as e:
    print(f"依赖解析错误: {e}")

# 添加新技能
new_skill = SkillConfig(skill_id="new-skill", name="新技能", version="1.0.0")
system_config.add_skill(new_skill)

# 移除技能
system_config.remove_skill("old-skill")

# 获取技能
skill = system_config.get_skill("calculator")
if skill:
    print(f"技能信息: {skill.name} v{skill.version}")

# 序列化和反序列化
config_dict = system_config.to_dict()
config_from_dict = SkillSystemConfig.from_dict(config_dict)
```

### SandboxSkillConfigLoader
配置加载器，负责配置的加载、验证和管理。

```python
# 创建加载器
loader = SandboxSkillConfigLoader(config_dir="/etc/deerflow")

# 从字典加载配置
await loader.load_from_dict(
    sandbox_data=sandbox_config.to_dict(),
    skills_data=system_config.to_dict(),
    env_vars={
        "API_KEY": "sk-test-789",
        "ENVIRONMENT": "production"
    }
)

# 验证所有配置
errors = loader.validate_all()
if errors:
    print(f"配置验证问题: {errors}")
else:
    print("所有配置验证通过")

# 获取技能依赖信息
skill_info = loader.get_skill_with_dependencies("web-scraper")
print(f"技能 {skill_info['skill']['name']} 的依赖:")
for dep in skill_info["dependencies"]:
    print(f"  - {dep['skill']['skill_id']} ({dep['relationship']})")

# 保存配置到文件
loader.to_yaml_files(
    sandbox_output="config/backup/sandbox_backup.yaml",
    skills_output="config/backup/skills_backup.yaml"
)

# 获取沙箱提供者
provider = loader.get_sandbox_provider()
if provider:
    print(f"默认提供者: {provider.name}")
    print(f"安全级别: {provider.security_config.security_level.value}")
```

### ExampleConfigGenerator
示例配置生成器，用于生成演示和测试用的配置。

```python
# 生成示例配置
generator = ExampleConfigGenerator()

# 生成沙箱配置
sandbox_config = generator.generate_sandbox_config()
print(f"生成的沙箱提供者: {list(sandbox_config.providers.keys())}")

# 生成技能系统配置
system_config = generator.generate_skill_system_config()
print(f"生成的技能: {list(system_config.skills.keys())}")

# 生成YAML示例
sandbox_yaml, skills_yaml = generator.generate_yaml_example()
print(f"沙箱配置YAML大小: {len(sandbox_yaml)} 字节")
print(f"技能配置YAML大小: {len(skills_yaml)} 字节")

# 保存到文件
with open("sandbox_example.yaml", "w") as f:
    f.write(sandbox_yaml)

with open("skills_example.yaml", "w") as f:
    f.write(skills_yaml)
```

## 📊 测试用例

| 测试 | 说明 | 预期结果 |
|------|------|----------|
| 测试1 | 沙箱配置创建和验证 | 配置可正确创建、验证、序列化和反序列化 |
| 测试2 | 技能配置创建和验证 | 技能配置可正确创建、验证、序列化和反序列化 |
| 测试3 | 技能依赖解析 | 依赖关系能正确解析，能确定初始化顺序 |
| 测试4 | 安全配置验证 | 安全配置验证功能正常，能检测无效配置 |
| 测试5 | 环境变量解析 | 环境变量可正确解析，支持默认值和嵌套引用 |
| 测试6 | 配置加载器功能 | 配置加载器能正确加载和验证配置 |
| 测试7 | 循环依赖检测 | 能检测到循环依赖并报告错误 |
| 测试8 | 版本约束检查 | 版本约束检查功能正常，支持语义化版本 |

## 📝 课后练习

### 基础练习
1. **扩展沙箱提供者类型**：添加新的沙箱提供者类型（如WebAssembly沙箱、虚拟机沙箱）
2. **实现配置验证规则**：添加沙箱和技能配置的完整验证规则（资源限制范围、路径有效性、版本格式）
3. **添加新的安全策略**：实现进程隔离、文件系统沙箱、网络防火墙等高级安全策略
4. **实现配置热重载**：添加配置文件监视功能，配置变化时自动重新加载
5. **增强环境变量支持**：支持嵌套环境变量引用、加密环境变量、环境变量模板

### 进阶练习
1. **实现技能编排引擎**：实现技能执行顺序和依赖关系的编排功能
2. **优化性能监控**：实现技能性能监控、资源使用限制、自动扩缩容
3. **设计技能市场架构**：设计支持动态安装和卸载的技能市场系统
4. **实现技能版本管理**：支持技能版本控制、灰度发布、回滚机制
5. **添加技能使用审计**：实现完整的技能使用审计日志和异常检测

### 挑战练习
1. **实现智能安全策略**：基于机器学习动态调整沙箱安全策略
2. **设计跨语言技能支持**：支持JavaScript、Go、Rust等语言编写的技能
3. **实现技能联邦学习**：多个技能间共享知识和经验，提高整体性能
4. **构建技能生态系统**：设计完整的技能开发、测试、部署、运维流程
5. **设计安全配置网关**：添加API密钥管理、请求限流、内容过滤等安全功能

## 🔗 扩展阅读

### 理论知识
1. **安全设计原则**：最小权限原则、防御性编程、安全默认值
2. **配置管理理论**：十二要素应用的配置管理原则
3. **依赖管理理论**：语义化版本控制、依赖解析算法、循环依赖检测
4. **系统可靠性**：容错设计、降级策略、熔断机制在配置管理中的应用
5. **性能工程**：沙箱性能测试和优化方法

### 工程实践
1. **容器安全实践**：Docker安全配置、镜像扫描、运行时保护
2. **Linux安全模块**：SELinux、AppArmor在沙箱隔离中的应用
3. **沙箱技术**：Firejail、Bubblewrap、gVisor等沙箱工具的使用
4. **企业配置治理**：企业级配置管理规范和工具链建设
5. **多云配置策略**：跨多个云服务商的配置部署和管理

### 工具推荐
1. **配置管理工具**：Hydra、OmegaConf、Pydantic Settings
2. **安全扫描工具**：Bandit、Safety、Trivy、Clair
3. **性能测试工具**：Locust、Apache JMeter、自定义基准测试
4. **部署工具**：Docker、Kubernetes、Helm Charts
5. **监控工具**：Prometheus、Grafana、ELK Stack、Jaeger

## 🛠️ 最佳实践

### 配置设计原则
1. **环境分离**：开发、测试、生产环境使用不同的配置
2. **安全第一**：默认使用限制级别，需要显式授权提升权限
3. **版本控制**：配置和代码一样进行版本控制和代码审查
4. **文档化**：每个配置项都有详细说明、示例和安全注意事项
5. **验证前置**：配置加载时立即验证，避免运行时安全漏洞

### 安全配置建议
1. **最小权限原则**：只授予沙箱完成任务所需的最小权限
2. **默认拒绝**：默认禁止所有操作，需要显式允许
3. **深度防御**：多层安全防护，不依赖单一安全机制
4. **审计日志**：记录所有沙箱执行，便于安全调查
5. **定期审查**：定期审查沙箱权限和配置，及时调整

### 技能管理策略
1. **版本控制**：每个技能都有明确的版本号，支持版本回滚
2. **依赖明确**：明确声明技能依赖，避免隐式依赖
3. **测试覆盖**：技能配置需要有完整的测试覆盖
4. **文档完整**：每个技能都有详细的使用文档和示例
5. **安全审查**：新技能上线前需要安全审查和代码审查

### 性能优化建议
1. **懒加载**：按需加载技能和沙箱，减少启动时间
2. **连接池**：复用沙箱连接，减少建立连接开销
3. **缓存配置**：缓存解析后的配置，减少重复解析
4. **异步执行**：非实时任务使用异步执行，提高并发能力
5. **监控调优**：持续监控系统性能，根据数据调优配置

## 📈 性能指标目标

### 配置系统性能
- **加载时间**：配置加载 < 100ms，技能初始化 < 500ms
- **查找性能**：技能查找 < 10ms（O(1)复杂度）
- **内存使用**：每个技能配置内存占用 < 5MB
- **并发支持**：支持1000+并发技能执行

### 安全系统可靠性
- **安全检测**：恶意操作拦截率 > 99.9%
- **资源限制**：资源超限检测准确率 > 99.9%
- **隔离效果**：沙箱隔离逃逸防护率 > 99.9%
- **审计完整性**：技能执行审计覆盖率 100%

### 系统可扩展性
- **提供者类型扩展**：添加新提供者类型不需要修改核心代码
- **技能类型扩展**：添加新技能类型不需要修改核心代码
- **安全策略扩展**：支持动态添加新的安全策略
- **性能水平扩展**：支持水平扩展，增加节点提高处理能力

## 🔍 故障排除

### 常见问题
1. **配置加载失败**：检查配置文件路径、文件权限、格式错误
2. **安全配置错误**：检查资源限制范围、网络访问规则、权限设置
3. **环境变量未解析**：检查环境变量名称、默认值、嵌套引用
4. **依赖循环错误**：检查技能依赖关系，解决循环依赖
5. **性能下降**：检查资源限制、网络延迟、配置复杂度

### 调试工具
```bash
# 测试沙箱配置
python -c "from sandbox_skill_config_demo import SandboxConfig, SandboxProviderType, LocalProviderConfig; config=SandboxConfig(default_provider='local', providers={'local': LocalProviderConfig(provider_type=SandboxProviderType.LOCAL, name='local', work_dir='/tmp')}); print(config.validate())"

# 测试技能配置
python -c "from sandbox_skill_config_demo import SkillConfig, SkillType, SkillStatus; config=SkillConfig(skill_id='test', name='测试技能', skill_type=SkillType.CALCULATOR, status=SkillStatus.ENABLED); print(config.validate())"

# 测试环境变量解析
python -c "from sandbox_skill_config_demo import SandboxConfig; config=SandboxConfig(environment_variables={'LOG_LEVEL': '\${APP_LOG_LEVEL:INFO}'}); env_vars={'APP_LOG_LEVEL':'DEBUG'}; resolved=config.resolve_environment_variables(env_vars); print(resolved.environment_variables)"

# 性能分析
python -m cProfile -s time sandbox_skill_config_demo.py --test
```

### 紧急处理
1. **安全漏洞**：立即禁用相关沙箱，审查安全配置，更新安全策略
2. **配置错误**：回滚到上一个已知正确的配置版本
3. **依赖冲突**：暂时移除冲突依赖，使用简化版本
4. **性能严重下降**：启用限流，增加容量，优化配置
5. **系统崩溃**：启用备用配置，切换到降级模式

---

**注意**：本演示代码包含完整测试套件，使用`--test`参数运行所有测试确保功能正常。建议在实际项目中使用前根据具体需求调整安全策略和验证规则。