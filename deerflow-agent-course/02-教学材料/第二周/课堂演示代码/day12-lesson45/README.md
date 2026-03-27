# Day 12 Lesson 45: task工具实现

## 📋 课程信息
- **课程名称**: Day 12 - 第45节课：task工具实现
- **授课日期**: 2024年4月5日（周五）
- **上课时间**: 上午9:00-9:45 (45分钟)
- **课时编号**: Day12-Lesson45
- **前置知识**: Python基础、装饰器、异步编程、上周子代理系统
- **后续课程**: 第46节课：工具注册与发现

## 🎯 学习目标

### 知识目标
1. 理解任务工具在AI Agent系统中的作用和设计目标
2. 掌握task工具的定义、参数设计和返回格式
3. 理解任务工具与子代理执行器的集成方式

### 技能目标
1. 能够使用@tool装饰器定义任务工具
2. 能够实现任务创建和提交到执行器的完整流程
3. 能够配置任务工具的异步执行和回调机制

### 态度目标
1. 培养对工具化设计的理解和应用能力
2. 增强对API设计和用户体验的重视
3. 提高对系统集成和接口设计的重视

## 📁 演示代码结构

### 主要文件
- `task_tool_demo.py`: 完整的task工具实现和演示代码

### 代码结构概述
本演示代码实现任务工具系统，包括：

1. **工具参数** - ToolParameter定义工具参数
2. **任务定义** - TaskDefinition定义任务结构
3. **工具注册表** - ToolRegistry管理所有工具
4. **工具装饰器** - @tool装饰器注册工具函数
5. **执行函数** - execute_tool执行工具并返回结果
6. **示例工具** - 预定义的示例工具函数

### 依赖和运行要求
```bash
# 运行环境
Python 3.12+（支持完整的类型注解和现代特性）
安装依赖: 本演示代码使用标准库，无需额外依赖

# 运行演示
cd /home/guoliang/mydocs/studyAgents/deerflow-agent-course/02-教学材料/第二周/课堂演示代码/day12-lesson45
python task_tool_demo.py

# 运行测试套件
python task_tool_demo.py --test

# 运行完整演示
python task_tool_demo.py --demo
```

## 🔧 技术要点

### 核心概念
1. **ToolParameter**: 工具参数定义，包含类型、描述、默认值
2. **TaskDefinition**: 任务定义，包含名称、描述、参数列表、处理函数
3. **TaskResult**: 任务执行结果，包含状态、结果、错误、执行时间
4. **ToolRegistry**: 工具注册表，管理工具的注册和查找
5. **@tool**: 工具装饰器，将函数注册为可调用工具
6. **execute_tool**: 执行工具函数，处理参数验证和异步执行

### 关键技术
- **装饰器模式**: 使用@tool装饰器简化工具注册
- **参数验证**: Pydantic风格的参数验证和类型转换
- **JSON Schema**: 自动生成工具参数的JSON Schema
- **异步执行**: 支持async/await异步工具
- **超时控制**: 防止工具无限期执行

## 🚀 快速开始

### 运行演示
```bash
cd /home/guoliang/mydocs/studyAgents/deerflow-agent-course/02-教学材料/第二周/课堂演示代码/day12-lesson45
python task_tool_demo.py
```

### 核心API使用示例

```python
import asyncio
from task_tool_demo import tool, execute_tool, _global_registry

# 1. 使用装饰器定义工具
@tool(name="my_tool", description="我的自定义工具", timeout=60.0)
async def my_tool(input_text: str, count: int = 1) -> str:
    """我的工具描述"""
    await asyncio.sleep(0.1)
    return f"处理结果: {input_text} x {count}"

# 2. 调用工具
result = await execute_tool("my_tool", input_text="hello", count=3)
print(f"状态: {result.status.value}")
print(f"结果: {result.result}")

# 3. 列出所有工具
tool_names = _global_registry.list_names()
print(f"已注册工具: {tool_names}")

# 4. 获取工具模式
schemas = _global_registry.get_schemas()
print(f"my_tool模式: {schemas['my_tool']}")

# 5. 错误处理
result = await execute_tool("unknown_tool")
print(f"错误: {result.error}")
```

### 工具装饰器详解

```python
@tool(
    name="analyze_code",          # 工具名称
    description="分析代码质量",   # 工具描述
    timeout=120.0                 # 超时时间（秒）
)
async def analyze_code(
    code: str,                    # 必填参数：代码内容
    language: str = "python",     # 可选参数：编程语言
    check_style: bool = True      # 可选参数：是否检查风格
) -> Dict[str, Any]:
    """
    分析代码质量并返回报告
    
    Args:
        code: 要分析的代码内容
        language: 编程语言（python, javascript等）
        check_style: 是否检查代码风格
    
    Returns:
        包含分析结果的字典
    """
    # 实现代码...
    return {"score": 85, "issues": []}
```

## 📚 教学资源

### 参考链接
- Python装饰器: https://docs.python.org/3/glossary.html#decorator
- Python inspect模块: https://docs.python.org/3/library/inspect.html
- LangChain工具: https://python.langchain.com/docs/modules/agents/tools/
- JSON Schema: https://json-schema.org/learn/

---

**版本**: v1.0  
**教师**: 张老师  
**适用对象**: DeerFlow Python Agent架构师训练营学员
