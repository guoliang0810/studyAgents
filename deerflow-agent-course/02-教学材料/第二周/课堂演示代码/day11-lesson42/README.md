# Day 11 Lesson 42: 子代理注册表

## 📋 课程信息
- **课程名称**: Day 11 - 第42节课：子代理注册表
- **授课日期**: 2024年4月4日（周四）
- **上课时间**: 上午10:00-10:45 (45分钟)
- **课时编号**: Day11-Lesson42
- **前置知识**: Python基础、数据类(dataclass)、上节SubagentConfig配置结构
- **后续课程**: 第43节课：子代理工厂模式

## 🎯 学习目标

### 知识目标
1. 理解注册表模式在软件设计中的作用和价值
2. 掌握子代理注册表的架构设计和核心接口
3. 理解注册表与配置系统的协同工作方式

### 技能目标
1. 能够实现基本的子代理注册表类
2. 能够使用注册表管理子代理的生命周期
3. 能够实现从配置到注册表的自动化注册流程

### 态度目标
1. 培养对设计模式的兴趣和应用能力
2. 增强模块化设计和接口设计意识
3. 提高对系统可扩展性和可维护性的重视

## 📁 演示代码结构

### 主要文件
- `subagent_registry_demo.py`: 完整的子代理注册表实现和演示代码

### 代码结构概述
本演示代码实现子代理注册表系统，包括：

1. **子代理状态** - AgentState枚举定义生命周期状态
2. **子代理信息** - SubagentInfo数据类包含完整子代理信息
3. **注册表核心** - SubagentRegistry实现register、get、list、unregister
4. **生命周期管理** - start_agent、stop_agent、restart_agent方法
5. **事件系统** - 支持on_register、on_state_change事件处理器
6. **测试套件** - RegistryTestSuite验证注册表功能正确性

### 依赖和运行要求
```bash
# 运行环境
Python 3.12+（支持完整的类型注解和现代特性）
安装依赖: 本演示代码使用标准库，无需额外依赖

# 运行演示
cd /home/guoliang/mydocs/studyAgents/deerflow-agent-course/02-教学材料/第二周/课堂演示代码/day11-lesson42
python subagent_registry_demo.py

# 运行测试套件
python subagent_registry_demo.py --test

# 运行异步演示
python subagent_registry_demo.py --demo
```

## 🔧 技术要点

### 核心概念
1. **AgentState**: 子代理状态枚举（CREATED、STARTING、RUNNING、STOPPING、STOPPED、ERROR）
2. **AgentType**: 子代理类型枚举（GENERIC、BASH、SQL、WEB、PYTHON）
3. **SubagentInfo**: 子代理信息数据类，包含名称、类型、状态、能力、指标等
4. **AgentMetrics**: 子代理运行指标，包括任务统计、响应时间等
5. **SubagentRegistry**: 子代理注册表，提供集中管理接口

### 关键技术
- **注册表模式**: 集中管理对象实例，提供统一访问接口
- **线程安全**: 使用Lock确保并发环境下的数据一致性
- **事件驱动**: 支持注册、注销、状态变更事件
- **生命周期管理**: 管理子代理从创建到销毁的完整生命周期
- **状态机**: 明确的状态转换规则，确保状态一致性

## 🚀 快速开始

### 运行演示
```bash
cd /home/guoliang/mydocs/studyAgents/deerflow-agent-course/02-教学材料/第二周/课堂演示代码/day11-lesson42
python subagent_registry_demo.py
```

### 核心API使用示例

```python
from subagent_registry_demo import SubagentRegistry, SubagentInfo, AgentType, AgentState

# 1. 创建注册表
registry = SubagentRegistry()

# 2. 创建子代理信息
agent = SubagentInfo(
    name="python_expert",
    agent_type=AgentType.PYTHON,
    description="Python代码执行专家",
    capabilities=["code_execution", "debugging"],
    config={"timeout": 300}
)

# 3. 注册子代理
if registry.register(agent):
    print("注册成功")

# 4. 查询子代理
found = registry.get("python_expert")
print(f"找到子代理: {found.name} ({found.agent_type.value})")

# 5. 列出所有子代理
all_agents = registry.list_all()
print(f"总共 {len(all_agents)} 个子代理")

# 6. 按类型查询
bash_agents = registry.list_by_type(AgentType.BASH)
print(f"Bash类型: {len(bash_agents)} 个")

# 7. 状态管理
registry.update_state("python_expert", AgentState.RUNNING)
running = registry.list_running()
print(f"运行中: {[a.name for a in running]}")

# 8. 获取统计信息
stats = registry.get_stats()
print(f"统计: {stats}")

# 9. 注销子代理
registry.unregister("python_expert")
```

### 事件处理器示例

```python
# 定义事件处理器
def on_register_handler(agent):
    print(f"子代理已注册: {agent.name}")

def on_state_change_handler(agent, old_state, new_state):
    print(f"状态变更: {agent.name} {old_state.value} -> {new_state.value}")

# 注册事件处理器
registry.on("on_register", on_register_handler)
registry.on("on_state_change", on_state_change_handler)

# 触发事件
registry.register(agent)  # 会触发on_register事件
registry.update_state("test", AgentState.RUNNING)  # 会触发on_state_change事件
```

### 生命周期管理示例

```python
# 启动子代理（异步）
await registry.start_agent("python_expert")

# 停止子代理（异步）
await registry.stop_agent("python_expert")

# 重启子代理（异步）
await registry.restart_agent("python_expert")
```

## 📚 教学资源

### 参考链接
- 注册表模式: https://en.wikipedia.org/wiki/Registry_pattern
- Python threading文档: https://docs.python.org/3/library/threading.html
- Python enum文档: https://docs.python.org/3/library/enum.html
- 状态机设计模式: https://en.wikipedia.org/wiki/State_pattern

---

**版本**: v1.0  
**教师**: 张老师  
**适用对象**: DeerFlow Python Agent架构师训练营学员
