# Day 14 - 第53节课：记忆注入与配置

## 📚 课程概述

本节课讲解记忆注入与配置系统，包括记忆注入中间件、配置管理和事实生命周期管理。

## 🎯 学习目标

1. **理解注入机制**：MemoryInjectionMiddleware的设计原理和注入流程
2. **掌握配置管理**：MemoryConfig的多级配置管理和动态覆盖机制  
3. **掌握生命周期管理**：FactLifecycleManager的生命周期管理策略
4. **了解性能优化**：注入缓存的实现和性能监控

## 📁 文件结构

```
day14-lesson53/
├── memory_injection_config_demo.py    # 主演示代码
└── README.md                          # 本文件
```

## 🚀 运行方式

```bash
python memory_injection_config_demo.py        # 运行演示
python memory_injection_config_demo.py --test # 运行测试（可选）
```

## 📖 核心概念

### 1. 配置管理系统

**MemoryConfig类**管理多级配置源，支持优先级覆盖：

```python
config = MemoryConfig()
config.set("injection.max_facts", 5, ConfigSource.ENV)  # 环境变量最高优先级
config.set("injection.max_facts", 10, ConfigSource.FILE) # 文件配置较低优先级

# 获取配置（自动选择最高优先级）
max_facts = config.get("injection.max_facts")  # 返回5（ENV优先级更高）
```

**配置源优先级顺序**：
1. ENV (环境变量) - 最高优先级
2. API (接口配置)
3. DATABASE (数据库配置)
4. FILE (配置文件)
5. DEFAULT (默认值) - 最低优先级

### 2. 事实生命周期管理

**FactLifecycleManager类**管理事实的完整生命周期：

```python
mgr = FactLifecycleManager(config)

# 添加事实
fact = Fact("用户偏好Python", "user", confidence=0.9)
mgr.add_fact(fact)

# 状态管理
mgr.update_status(fact.id, FactStatus.ARCHIVED, "置信度过低")

# 过期检查
expired = mgr.check_expired()

# 归档旧事实
archived = mgr.archive_old_facts()

# 运行维护
result = mgr.run_maintenance()
```

### 3. 记忆注入中间件

**MemoryInjectionMiddleware类**实现三步注入流程：

```python
middleware = MemoryInjectionMiddleware(config, lifecycle_manager)

# 注入记忆
enhanced_query = middleware.inject("如何学习编程？", 
                                   context={"previous_messages": ["你好"]})

# 获取统计
stats = middleware.get_stats()  # 包含缓存命中率、成功率等
```

**注入流程**：
1. **提取相关记忆**：根据查询和策略提取相关事实
2. **筛选高质量记忆**：按置信度阈值筛选
3. **构建增强查询**：组合上下文生成最终查询

## 🔧 核心类说明

### MemoryConfig

多级配置管理类，支持动态配置更新和优先级管理。

```python
# 注册配置源
def load_env_config():
    return {"injection.max_facts": 5}
    
config.register_source(ConfigSource.ENV, load_env_config)

# 加载配置
config.load_all()

# 获取配置
value = config.get("injection.max_facts")
```

### FactLifecycleManager

事实生命周期管理器，管理事实的状态转换和维护任务。

```python
# 统计信息
stats = mgr.get_stats()  # 获取各状态事实数量

# 生命周期日志
log = mgr.get_lifecycle_log()  # 获取状态变更历史
```

### MemoryInjectionMiddleware

记忆注入中间件，实现查询增强和缓存优化。

```python
# 配置项
config.set("injection.cache_ttl", 3600)  # 缓存生存时间
config.set("performance.cache_size", 1000)  # 缓存大小限制

# 清理缓存
middleware.clear_cache()
```

## 📊 测试用例

| 测试 | 说明 | 结果 |
|------|------|------|
| 测试1 | MemoryConfig基本功能 | ✅ |
| 测试2 | 配置优先级 | ✅ |
| 测试3 | FactLifecycleManager状态管理 | ✅ |
| 测试4 | 过期检查 | ✅ |
| 测试5 | 归档功能 | ✅ |
| 测试6 | MemoryInjectionMiddleware基础注入 | ✅ |
| 测试7 | 缓存功能 | ✅ |
| 测试8 | 统计功能 | ✅ |

## 📝 课后练习

1. **实现配置文件加载器**：支持YAML/JSON格式配置文件
2. **添加配置验证**：验证配置值的有效性和类型
3. **实现热重载**：配置文件修改后自动重载
4. **扩展注入策略**：实现自适应注入策略
5. **优化缓存算法**：实现LRU或LFU缓存替换策略
6. **添加监控指标**：实现注入效果的实时监控

## 🔗 扩展阅读

- 配置管理最佳实践
- 缓存策略对比分析
- 系统维护自动化
- 性能监控指标体系