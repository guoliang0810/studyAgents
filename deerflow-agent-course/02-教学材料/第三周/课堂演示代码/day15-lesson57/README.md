# Day 15 - 第57节课：AppConfig加载流程

## 📚 课程概述

本节课讲解配置系统的设计哲学和加载流程，包括多源配置加载、深度合并算法、配置验证、模板渲染等核心技术。重点掌握"约定优于配置"的设计理念和分层覆盖的实现方法，培养配置驱动的系统设计思维。

## 🎯 学习目标

1. **掌握配置系统设计哲学**：理解约定优于配置和分层覆盖原则
2. **掌握多源配置加载**：能够实现默认配置、YAML文件、环境变量、命令行参数的多源加载
3. **掌握深度合并算法**：能够实现嵌套配置字典的递归合并，支持多种数组合并策略
4. **掌握配置验证技术**：能够实现配置的类型检查、必需字段验证、值范围验证等
5. **掌握配置模板渲染**：能够实现配置模板和变量替换，支持环境变量和默认值
6. **培养工程思维**：掌握从设计原则到具体实现的完整配置系统构建流程

## 📁 文件结构

```
day15-lesson57/
├── app_config_loader_demo.py    # 主演示代码（包含8个测试）
└── README.md                    # 本文件
```

## 🚀 运行方式

```bash
python app_config_loader_demo.py              # 运行演示示例
python app_config_loader_demo.py --test       # 运行测试（建议）
python app_config_loader_demo.py --example    # 运行完整使用示例
python app_config_loader_demo.py --config config.yaml --config-key database.host  # 加载配置并查看特定键
```

## 📖 核心概念

### 1. 配置系统设计哲学

**约定优于配置（Convention over Configuration）**：
- 提供合理的默认值，减少用户配置工作量
- 通过命名约定自动推断配置，而非显式指定
- 平衡灵活性和易用性

**分层覆盖原则**：
- 配置源按优先级分层：默认配置 < 文件配置 < 环境变量 < 命令行参数 < 运行时配置
- 高优先级配置覆盖低优先级配置
- 支持灵活的配置覆盖和组合

### 2. 多源配置加载

**ConfigLoader类**支持四种配置源：

```python
from app_config_loader_demo import ConfigLoader

# 创建配置加载器
loader = ConfigLoader(
    env_prefix="APP_",          # 环境变量前缀
    cli_prefix="--config-",     # 命令行参数前缀
    array_merge_strategy=DeepMerger.ArrayMergeStrategy.EXTEND
)

# 从多个源加载配置
config = loader.load(
    config_file="config.yaml",           # YAML配置文件
    default_config={"app": {"name": "MyApp"}},  # 默认配置
    env_vars={"APP_DATABASE_HOST": "localhost"},  # 环境变量
    cli_args=["--config-app.debug=true"]          # 命令行参数
)
```

**配置加载顺序**：
1. **默认配置**：代码中定义的默认值，最低优先级
2. **YAML配置文件**：结构化配置文件，支持嵌套配置
3. **环境变量**：操作系统环境变量，便于容器化部署
4. **命令行参数**：运行时临时覆盖，最高优先级

### 3. 深度合并算法

**DeepMerger类**实现递归的深度合并：

```python
from app_config_loader_demo import DeepMerger

merger = DeepMerger(DeepMerger.ArrayMergeStrategy.EXTEND)

base_config = {
    "database": {
        "host": "localhost",
        "port": 5432,
        "pool": {
            "max_size": 10,
            "min_size": 1
        }
    }
}

override_config = {
    "database": {
        "host": "prod.db.example.com",
        "pool": {
            "max_size": 20
        }
    },
    "cache": {
        "enabled": True
    }
}

# 深度合并：override覆盖base，嵌套字典递归合并
result = merger.merge(base_config, override_config)
# result["database"]["host"] = "prod.db.example.com"（覆盖）
# result["database"]["port"] = 5432（保留）
# result["database"]["pool"]["max_size"] = 20（覆盖）
# result["database"]["pool"]["min_size"] = 1（保留）
# result["cache"]["enabled"] = True（新增）
```

**数组合并策略**：
- `REPLACE`：完全替换（默认）
- `APPEND`：追加到末尾
- `EXTEND`：展平后追加（支持嵌套列表）
- `UNIQUE`：去重后追加
- `INTERSECT`：只保留交集

### 4. 配置验证

**ConfigValidator类**提供全面的配置验证：

```python
from app_config_loader_demo import ConfigValidator

validator = ConfigValidator()

# 必需字段验证
validator.add_required_fields(["database.host", "database.port", "app.name"])

# 类型验证
validator.add_type_rule("database.port", int)
validator.add_type_rule("app.debug", bool)
validator.add_type_rule("server.timeout", float)

# 值范围验证
validator.add_range_rule("database.port", min_val=1, max_val=65535)
validator.add_range_rule("server.timeout", min_val=0.1, max_val=300.0)

# 正则表达式验证
validator.add_regex_rule("database.host", r"^[a-zA-Z0-9.-]+$")
validator.add_regex_rule("app.email", r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# 自定义验证器
def validate_database_config(config):
    errors = []
    if config.get("database", {}).get("max_connections", 0) < config.get("database", {}).get("min_connections", 0):
        errors.append("最大连接数不能小于最小连接数")
    return errors

validator.add_custom_validator(validate_database_config)

# 执行验证
config = {"database": {"host": "localhost", "port": 5432}, "app": {"name": "MyApp"}}
errors = validator.validate(config)
if errors:
    print(f"配置验证失败: {errors}")
else:
    print("配置验证通过")
```

### 5. 配置模板渲染

**ConfigTemplateEngine类**支持变量替换和模板功能：

```python
from app_config_loader_demo import ConfigTemplateEngine

engine = ConfigTemplateEngine()

# 设置环境变量
import os
os.environ["DB_HOST"] = "production-db.example.com"
os.environ["DB_PORT"] = "5432"

# 定义配置模板
template = {
    "database": {
        "host": "${DB_HOST:localhost}",      # 使用环境变量，默认值localhost
        "port": "${DB_PORT:5432}",           # 使用环境变量，默认值5432
        "url": "postgresql://${DB_USER:admin}:${DB_PASS:secret}@${DB_HOST}:${DB_PORT}/${DB_NAME:appdb}"
    },
    "feature": {
        "enabled": "${FEATURE_FLAG:false}",  # 布尔值转换
        "max_items": "${MAX_ITEMS:100}"      # 整数转换
    }
}

# 渲染模板
context = {"DB_USER": "app_user", "DB_NAME": "myapp_db"}
config = engine.render(template, context)

# 结果：
# config["database"]["host"] = "production-db.example.com"（来自环境变量）
# config["database"]["port"] = 5432（整数，来自环境变量）
# config["database"]["url"] = "postgresql://app_user:secret@production-db.example.com:5432/myapp_db"
# config["feature"]["enabled"] = False（布尔值，使用默认值）
# config["feature"]["max_items"] = 100（整数，使用默认值）
```

**支持的变量语法**：
- `${VAR_NAME}`：引用变量
- `${VAR_NAME:default_value}`：带默认值的变量引用
- `${ENV_VAR_NAME}`：引用环境变量
- `${function(arg)}`：函数调用（支持upper、lower、int、float、bool、env等）

### 6. 应用程序配置类

**AppConfig类**提供类型安全的配置访问接口：

```python
from app_config_loader_demo import AppConfig

# 创建应用程序配置
app_config = AppConfig()

# 加载配置
app_config.load(
    config_file="config.yaml",
    default_config={
        "server": {
            "host": "0.0.0.0",
            "port": 8080,
            "timeout": 30.0
        }
    }
)

# 类型安全的配置访问
server_host = app_config.get("server.host", "localhost")          # 字符串
server_port = app_config.get_int("server.port", 8080)             # 整数
server_timeout = app_config.get_float("server.timeout", 30.0)     # 浮点数
debug_mode = app_config.get_bool("app.debug", False)              # 布尔值
features = app_config.get_list("app.features", [])                # 列表
database_config = app_config.get_dict("database", {})             # 字典

# 运行时配置修改
app_config.set("server.port", 9090)
app_config.set("app.features", ["auth", "logging", "cache"])

# 重新加载配置（热更新）
app_config.reload()
```

## 🔧 核心类说明

### ConfigLoader
配置加载器，支持多源配置加载和合并。

```python
# 创建配置加载器
loader = ConfigLoader(
    env_prefix="MYAPP_",      # 环境变量前缀
    cli_prefix="--config-",   # 命令行参数前缀
    array_merge_strategy=DeepMerger.ArrayMergeStrategy.EXTEND
)

# 加载配置
config = loader.load(
    config_file="config/production.yaml",
    default_config={
        "app": {
            "name": "MyApplication",
            "version": "1.0.0",
            "environment": "production"
        }
    }
)

# 获取加载元数据
metadata = loader.get_metadata()
for meta in metadata:
    print(f"来源: {meta.source.value}, 路径: {meta.path}, 优先级: {meta.priority}")

# 监视配置变化（简化版）
def on_config_changed(new_config):
    print(f"配置已更新: {new_config['app']['name']}")

checker = loader.watch_and_reload("config/production.yaml", on_config_changed)
```

**关键特性**：
1. **多源支持**：默认配置、YAML文件、环境变量、命令行参数
2. **优先级管理**：清晰的配置覆盖规则
3. **模板渲染**：支持变量替换和默认值
4. **验证集成**：加载后自动验证配置
5. **元数据追踪**：记录配置来源和优先级

### DeepMerger
深度合并器，实现递归的配置合并算法。

```python
# 创建合并器（使用不同策略）
merger_replace = DeepMerger(DeepMerger.ArrayMergeStrategy.REPLACE)
merger_append = DeepMerger(DeepMerger.ArrayMergeStrategy.APPEND)
merger_extend = DeepMerger(DeepMerger.ArrayMergeStrategy.EXTEND)
merger_unique = DeepMerger(DeepMerger.ArrayMergeStrategy.UNIQUE)
merger_intersect = DeepMerger(DeepMerger.ArrayMergeStrategy.INTERSECT)

# 示例：数组合并策略对比
base = {"items": [1, 2, 3]}
override = {"items": [3, 4, [5, 6]]}

print(merger_replace.merge(base, override))   # {"items": [3, 4, [5, 6]]}
print(merger_append.merge(base, override))    # {"items": [1, 2, 3, 3, 4, [5, 6]]}
print(merger_extend.merge(base, override))    # {"items": [1, 2, 3, 3, 4, 5, 6]}
print(merger_unique.merge(base, override))    # {"items": [1, 2, 3, 4, 5, 6]}
print(merger_intersect.merge(base, override)) # {"items": [3]}

# 嵌套字典合并
nested_base = {
    "database": {
        "host": "localhost",
        "credentials": {
            "username": "admin",
            "password": "secret"
        }
    }
}

nested_override = {
    "database": {
        "host": "prod.db",
        "credentials": {
            "password": "newsecret"
        },
        "pool_size": 20
    }
}

result = merger_replace.merge(nested_base, nested_override)
# result = {
#     "database": {
#         "host": "prod.db",                    # 覆盖
#         "credentials": {
#             "username": "admin",              # 保留
#             "password": "newsecret"           # 覆盖
#         },
#         "pool_size": 20                       # 新增
#     }
# }
```

**算法特点**：
1. **递归合并**：深度遍历嵌套字典
2. **类型感知**：根据类型选择合并策略
3. **策略灵活**：支持多种数组合并策略
4. **性能优化**：O(n)时间复杂度，避免深度复制开销

### ConfigValidator
配置验证器，确保配置的完整性和正确性。

```python
# 创建验证器
validator = ConfigValidator()

# 1. 必需字段验证
validator.add_required_fields([
    "app.name",
    "app.version", 
    "database.host",
    "database.port",
    "server.port"
])

# 2. 类型验证
validator.add_type_rule("app.debug", bool)
validator.add_type_rule("app.version", str)
validator.add_type_rule("database.port", int)
validator.add_type_rule("server.timeout", (int, float))  # 多种类型
validator.add_type_rule("app.features", list)

# 3. 值范围验证
validator.add_range_rule("database.port", min_val=1, max_val=65535)
validator.add_range_rule("server.timeout", min_val=0.1, max_val=300.0)
validator.add_range_rule("cache.max_size", min_val=1, max_val=10000)

# 4. 正则表达式验证
validator.add_regex_rule("app.name", r"^[a-zA-Z][a-zA-Z0-9_-]{1,49}$")
validator.add_regex_rule("database.host", r"^[a-zA-Z0-9.-]+$")
validator.add_regex_rule("app.email", r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# 5. 自定义验证器
def validate_app_config(config):
    errors = []
    app_config = config.get("app", {})
    
    # 业务规则：版本号格式
    version = app_config.get("version", "")
    if version and not re.match(r"^\d+\.\d+\.\d+$", version):
        errors.append("app.version 必须符合语义化版本格式 (x.y.z)")
    
    # 业务规则：功能依赖
    features = app_config.get("features", [])
    if "advanced_search" in features and "basic_search" not in features:
        errors.append("启用 advanced_search 必须先启用 basic_search")
    
    return errors

validator.add_custom_validator(validate_app_config)

# 执行验证
config = {
    "app": {
        "name": "MyApp-1",
        "version": "1.0.0",
        "debug": False,
        "features": ["auth", "logging"]
    },
    "database": {
        "host": "localhost",
        "port": 5432
    },
    "server": {
        "port": 8080,
        "timeout": 30.0
    }
}

errors = validator.validate(config)
if errors:
    print("配置验证失败:")
    for error in errors:
        print(f"  - {error}")
else:
    print("配置验证通过")
```

**验证能力**：
1. **必需性检查**：确保关键配置项存在
2. **类型检查**：验证配置值类型是否符合预期
3. **范围检查**：数值范围、字符串长度等
4. **格式检查**：正则表达式匹配
5. **业务规则**：自定义验证逻辑
6. **依赖检查**：配置项间的依赖关系

### ConfigTemplateEngine
配置模板引擎，支持动态变量替换。

```python
# 创建模板引擎
engine = ConfigTemplateEngine()

# 定义模板函数
engine.functions["base64"] = lambda x: base64.b64encode(x.encode()).decode()
engine.functions["md5"] = lambda x: hashlib.md5(x.encode()).hexdigest()
engine.functions["timestamp"] = lambda: str(int(time.time()))

# 复杂模板示例
template = {
    "app": {
        "name": "${APP_NAME:MyApp}",
        "version": "${APP_VERSION:1.0.0}",
        "build_id": "${timestamp()}",  # 函数调用
        "secret_hash": "${md5(${APP_SECRET:default_secret})}"  # 嵌套函数
    },
    "database": {
        "connection_string": "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}",
        "pool": {
            "min_size": "${DB_POOL_MIN:1}",
            "max_size": "${DB_POOL_MAX:10}",
            "timeout": "${DB_POOL_TIMEOUT:30.0}"
        }
    },
    "api": {
        "base_url": "${API_BASE_URL:https://api.example.com}",
        "timeout": "${API_TIMEOUT:30}",
        "retries": "${API_RETRIES:3}",
        "headers": {
            "Authorization": "Bearer ${API_TOKEN}",
            "X-Request-ID": "${uuid()}"  # 假设有uuid函数
        }
    }
}

# 设置环境变量
os.environ["APP_NAME"] = "ProductionApp"
os.environ["DB_USER"] = "prod_user"
os.environ["DB_PASSWORD"] = "prod_password"
os.environ["DB_HOST"] = "db.production.example.com"
os.environ["DB_PORT"] = "5432"
os.environ["DB_NAME"] = "production_db"

# 渲染模板
config = engine.render(template)

# 结果包含：
# - 环境变量替换的值
# - 函数调用的结果
# - 类型转换（字符串转整数、浮点数、布尔值）
# - 嵌套变量引用
```

**模板特性**：
1. **变量替换**：`${VAR_NAME}` 和 `${VAR_NAME:default}`
2. **环境变量**：自动从环境变量读取
3. **函数调用**：支持自定义函数
4. **类型转换**：自动转换字符串到适当类型
5. **嵌套引用**：支持变量嵌套引用
6. **条件表达式**：支持简单条件逻辑

### AppConfig
应用程序配置类，提供便捷的类型安全接口。

```python
# 创建应用程序配置
config = AppConfig()

# 1. 加载配置
config.load("config/production.yaml")

# 2. 类型安全访问
# 字符串值
app_name = config.get("app.name", "DefaultApp")
# 整数值（自动转换）
port = config.get_int("server.port", 8080)
# 浮点值（自动转换）
timeout = config.get_float("server.timeout", 30.0)
# 布尔值（自动转换）
debug = config.get_bool("app.debug", False)
# 列表值
features = config.get_list("app.features", [])
# 字典值
db_config = config.get_dict("database", {})

# 3. 嵌套访问
db_host = config.get("database.connection.host", "localhost")
db_port = config.get_int("database.connection.port", 5432)

# 4. 运行时修改
config.set("app.debug", True)
config.set("server.port", 9090)
config.set("app.features", ["auth", "cache", "monitoring"])

# 5. 批量操作
config.update({
    "app": {
        "name": "UpdatedApp",
        "version": "2.0.0"
    },
    "server": {
        "host": "0.0.0.0",
        "port": 8081
    }
})

# 6. 配置监听（简化版）
def on_config_change(key, old_value, new_value):
    print(f"配置变更: {key} = {old_value} -> {new_value}")

# 注意：实际实现需要事件系统
```

**主要方法**：
1. `load()`：从文件加载配置
2. `get()`：获取配置值（支持默认值）
3. `get_int()`、`get_float()`、`get_bool()`：类型安全获取
4. `get_list()`、`get_dict()`：获取集合类型
5. `set()`：设置配置值（运行时修改）
6. `update()`：批量更新配置
7. `reload()`：重新加载配置文件

## 📊 测试用例

| 测试 | 说明 | 预期结果 |
|------|------|----------|
| 测试1 | DeepMerger基础功能 | 字典合并、嵌套合并、数组合并功能正常 |
| 测试2 | 数组合并策略 | REPLACE、APPEND、EXTEND、UNIQUE、INTERSECT策略正确工作 |
| 测试3 | ConfigValidator验证 | 必需字段、类型、范围、正则验证功能正常 |
| 测试4 | ConfigTemplateEngine模板渲染 | 变量替换、环境变量、函数调用、类型转换功能正常 |
| 测试5 | ConfigLoader多源加载 | 默认配置、YAML文件、环境变量、命令行参数正确加载和合并 |
| 测试6 | 配置优先级 | 命令行参数 > 环境变量 > YAML文件 > 默认配置 |
| 测试7 | AppConfig类型安全访问 | get_int、get_float、get_bool等类型安全方法正确工作 |
| 测试8 | 错误处理 | 配置文件不存在、YAML解析错误、验证失败等场景正确处理 |

## 📝 课后练习

### 基础练习
1. **实现配置热更新**：添加配置文件监视功能，文件变化时自动重新加载
2. **扩展配置源**：添加JSON配置文件、INI配置文件、远程配置中心（HTTP API）支持
3. **增强模板引擎**：添加条件表达式 `${condition ? true_value : false_value}` 支持
4. **添加配置加密**：支持敏感配置项（密码、密钥）的加密存储和解密加载
5. **实现配置导出**：将当前配置导出为YAML、JSON、环境变量等格式

### 进阶练习
1. **实现配置版本控制**：记录配置变更历史，支持配置回滚和差异对比
2. **设计配置Schema**：使用JSON Schema定义配置结构，实现强类型验证
3. **实现配置依赖注入**：根据配置动态创建和注入组件依赖
4. **添加配置性能分析**：监控配置加载、合并、验证的性能，优化热点路径
5. **实现配置可视化**：Web界面展示配置结构、来源、值和验证状态

### 挑战练习
1. **实现配置智能提示**：根据配置Schema提供代码补全和类型提示
2. **设计分布式配置同步**：多节点配置自动同步和一致性保证
3. **实现配置机器学习**：基于历史配置数据预测最优配置参数
4. **集成配置测试**：配置变更前自动运行测试，确保配置正确性
5. **实现配置治理**：配置访问控制、审计日志、合规检查

## 🔗 扩展阅读

### 理论知识
1. **配置管理理论**：十二要素应用配置原则、配置即代码理念
2. **设计模式**：工厂模式、建造者模式、策略模式在配置系统中的应用
3. **数据格式**：YAML、JSON、TOML、HCL等配置格式比较
4. **验证理论**：契约测试、属性测试在配置验证中的应用
5. **安全实践**：配置加密、密钥管理、秘密管理最佳实践

### 工程实践
1. **Spring Boot配置**：Java生态的配置管理最佳实践
2. **Dotenv原理**：环境变量管理库的设计和实现
3. **Consul配置中心**：分布式配置管理的架构设计
4. **Kubernetes ConfigMap**：容器化环境的配置管理
5. **AWS Parameter Store**：云原生配置管理服务

### 工具推荐
1. **Python配置库**：pydantic、attrs、dataclasses用于配置验证
2. **模板引擎**：Jinja2、Mako、Chameleon用于配置模板
3. **配置管理工具**：Ansible、Chef、Puppet、Terraform
4. **秘密管理工具**：HashiCorp Vault、AWS Secrets Manager、Azure Key Vault
5. **配置验证工具**：JSON Schema验证器、Cerberus、Voluptuous

## 🛠️ 最佳实践

### 配置设计原则
1. **分层设计**：默认配置 → 环境配置 → 部署配置 → 运行时配置
2. **环境分离**：开发、测试、预生产、生产环境使用不同配置
3. **敏感信息保护**：密码、密钥等敏感配置加密存储，不提交到版本控制
4. **配置即代码**：配置和代码一样进行版本控制、代码审查、自动化测试
5. **最小权限**：配置访问权限最小化，按需分配

### 配置加载策略
1. **失败快速**：配置加载失败时立即报错，避免使用错误配置
2. **合理默认**：提供合理的默认值，减少必需配置项
3. **明确优先级**：清晰的配置覆盖规则，避免歧义
4. **完整验证**：加载后全面验证配置，提前发现问题
5. **详细日志**：记录配置加载过程和决策，便于调试

### 配置维护建议
1. **文档化**：每个配置项都有详细说明和示例
2. **版本化**：配置变更记录版本，支持回滚
3. **测试化**：配置变更前运行测试，确保兼容性
4. **监控化**：监控配置使用情况和效果
5. **定期审查**：定期审查配置，清理无用配置项

## 📈 性能指标目标

### 配置加载性能
- **加载时间**：< 100ms（小型配置），< 1s（大型配置）
- **内存使用**：配置内存占用 < 总内存的1%
- **并发加载**：支持多线程并发加载，无竞争条件
- **缓存效率**：配置缓存命中率 > 95%
- **启动时间**：配置加载不成为应用启动瓶颈

### 配置系统可靠性
- **可用性**：配置系统可用性 > 99.99%
- **正确性**：配置验证覆盖率 > 90%
- **一致性**：多节点配置一致性延迟 < 1s
- **可恢复性**：配置错误时自动回滚到上一个有效版本
- **可审计性**：所有配置变更可追溯、可审计

## 🔍 故障排除

### 常见问题
1. **配置加载失败**：检查文件权限、格式、编码、路径是否正确
2. **配置合并冲突**：检查配置优先级，明确覆盖规则
3. **配置验证失败**：查看验证错误信息，检查配置值是否符合要求
4. **环境变量未生效**：检查环境变量名称、前缀、格式是否正确
5. **配置热更新不工作**：检查文件监视权限、回调函数注册、重新加载逻辑

### 调试工具
```bash
# 查看配置加载详情
python -c "from app_config_loader_demo import ConfigLoader; loader=ConfigLoader(); config=loader.load('config.yaml'); print(loader.get_metadata())"

# 验证配置文件
python -c "from app_config_loader_demo import ConfigValidator; import yaml; validator=ConfigValidator(); validator.add_required_fields(['app.name']); config=yaml.safe_load(open('config.yaml')); errors=validator.validate(config); print('验证通过' if not errors else errors)"

# 测试模板渲染
python -c "from app_config_loader_demo import ConfigTemplateEngine; import os; os.environ['TEST_VAR']='test_value'; engine=ConfigTemplateEngine(); template={'key':'${TEST_VAR:default}'}; print(engine.render(template))"

# 性能分析
python -m cProfile -s time app_config_loader_demo.py --test
```

### 紧急处理
1. **配置错误导致服务不可用**：立即回滚到上一个已知正确的配置版本
2. **敏感信息泄露**：立即轮换所有泄露的密钥和密码
3. **配置不一致**：使用配置同步工具强制同步所有节点
4. **配置加载性能问题**：启用配置缓存，优化验证逻辑
5. **配置系统故障**：降级到本地配置文件，禁用远程配置中心

---

**注意**：本演示代码包含完整测试套件，使用`--test`参数运行所有测试确保功能正常。建议在实际项目中使用前根据具体需求调整配置策略和验证规则。