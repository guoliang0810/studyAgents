# Day 14 - 第54节课：提示词记忆注入

## 📚 课程概述

本节课讲解提示词记忆注入系统，包括PromptTemplate扩展、上下文注入、参数化记忆和模板变量系统。

## 🎯 学习目标

1. **掌握模板扩展**：理解PromptTemplate的三种扩展方法（继承、组合、装饰器）
2. **掌握上下文注入**：掌握记忆上下文到提示词的智能注入技术
3. **掌握参数化记忆**：理解参数化记忆的数据结构和模板变量设计
4. **掌握模板变量系统**：实现模板变量的定义、验证和替换

## 📁 文件结构

```
day14-lesson54/
├── memory_prompt_template_demo.py    # 主演示代码
└── README.md                          # 本文件
```

## 🚀 运行方式

```bash
python memory_prompt_template_demo.py        # 运行演示
python memory_prompt_template_demo.py --test # 运行测试（可选）
```

## 📖 核心概念

### 1. 模板扩展方法

**三种扩展模式**：

```python
# 继承扩展（本课程采用）
class MemoryPromptTemplate(BasePromptTemplate):
    def __init__(self, template: str, template_type: TemplateType = TemplateType.SIMPLE):
        super().__init__(template, template_type)
        # 添加记忆相关功能

# 组合扩展
class MemoryPromptTemplate:
    def __init__(self, base_template: BasePromptTemplate):
        self.base_template = base_template
        # 添加记忆相关功能

# 装饰器扩展
def memory_injection_decorator(template_func):
    def wrapper(*args, **kwargs):
        # 在模板生成前后注入记忆
        return template_func(*args, **kwargs)
    return wrapper
```

### 2. 模板变量系统

**TemplateVariableSystem类**管理模板变量：

```python
var_system = TemplateVariableSystem()
var_system.register_variable(
    TemplateVariable("username", VariableType.STRING, required=True)
)
var_system.set_value("username", "Alice")
result = var_system.interpolate("Hello, {{username}}!")
```

**变量类型支持**：
- STRING：字符串类型
- INTEGER：整数类型
- FLOAT：浮点数类型
- BOOLEAN：布尔类型
- LIST：列表类型
- DICT：字典类型
- ANY：任意类型

### 3. 上下文注入器

**ContextInjector类**实现四种注入模式：

```python
injector = ContextInjector(InjectionMode.PREPEND)
facts = [Fact("Python是流行语言", "system", confidence=0.9)]
prompt = "如何学习编程？"
result = injector.inject_context(prompt, facts)
```

**注入模式**：
1. **PREPEND**：前置注入（上下文在前，提示在后）
2. **APPEND**：后置注入（提示在前，上下文在后）
3. **INTERLEAVE**：交错注入（上下文插入到提示中间）
4. **CONDITIONAL**：条件注入（基于置信度阈值决定是否注入）

### 4. 记忆提示词模板

**MemoryPromptTemplate类**整合所有功能：

```python
template = MemoryPromptTemplate("问题: {{query}}", InjectionMode.PREPEND)
template.add_variable(TemplateVariable("query", VariableType.STRING, required=True))

# 添加记忆
template.add_memory(Fact("Python适合数据分析", "expert", confidence=0.8))

# 格式化（自动搜索和注入记忆）
result = template.format("数据分析用什么语言？", query="数据分析")
```

## 🔧 核心类说明

### BasePromptTemplate

基础提示词模板类（抽象基类），提供模板变量管理基础功能。

```python
# 定义模板
template = BasePromptTemplate("Hello, {{name}}! Today is {{day}}.")

# 添加变量
template.add_variable(TemplateVariable("name", VariableType.STRING, required=True))
template.add_variable(TemplateVariable("day", VariableType.STRING, default="Monday"))

# 编译模板
result = template.compile_template({"name": "Alice"})
```

### TemplateVariableSystem

模板变量系统，支持变量注册、验证、插值和历史记录。

```python
# 变量验证
errors = var_system.validate_all()  # 返回所有验证错误

# 获取变量历史
history = var_system._variable_history  # 变量值变更历史
```

### ContextInjector

上下文注入器，支持多种注入模式和内容格式化。

```python
# 关键词提取
keywords = injector.extract_keywords("如何学习Python编程？")
# 返回: ["学习", "python", "编程"]

# 条件注入配置
injector = ContextInjector(InjectionMode.CONDITIONAL)
```

### MemoryPromptTemplate

记忆提示词模板（扩展类），整合模板、变量、注入和记忆功能。

```python
# 参数化记忆
fact = template.add_parameterized_memory(
    "{{language}}适合{{domain}}开发",
    {"language": "Python", "domain": "Web"}
)

# 模板信息
info = template.get_template_info()  # 获取模板统计信息

# 记忆搜索
context = template.search_memory("数据分析", limit=3)  # 搜索相关记忆
```

## 📊 测试用例

| 测试 | 说明 | 结果 |
|------|------|------|
| 测试1 | 基础模板变量替换 | ✅ |
| 测试2 | 变量验证 | ✅ |
| 测试3 | 模板变量系统 | ✅ |
| 测试4 | 上下文注入 | ✅ |
| 测试5 | MemoryPromptTemplate基础功能 | ✅ |
| 测试6 | 记忆搜索和注入 | ✅ |
| 测试7 | 参数化记忆 | ✅ |
| 测试8 | 模板信息获取 | ✅ |

## 📝 课后练习

1. **实现条件注入增强**：基于查询复杂度和上下文相关性的智能条件注入
2. **添加模板变量类型转换**：支持自动类型转换和格式化
3. **实现模板缓存优化**：使用LRU缓存存储已编译模板
4. **扩展注入策略**：实现基于上下文的动态注入策略选择
5. **添加模板验证**：检查模板语法和变量引用完整性
6. **实现模板性能监控**：记录模板编译、注入、渲染各阶段性能

## 🔗 扩展阅读

- 设计模式：装饰器模式、模板方法模式
- 模板引擎原理：Jinja2、Django Templates
- 变量系统设计：类型系统、验证机制
- 上下文感知系统：内容相关性计算、优先级调度