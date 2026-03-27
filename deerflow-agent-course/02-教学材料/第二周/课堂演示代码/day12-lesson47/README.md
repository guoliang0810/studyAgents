# Day 12 Lesson 47: 父子代理通信

## 📋 课程信息
- **课程名称**: Day 12 - 第47节课：父子代理通信
- **授课日期**: 2024年4月5日（周五）
- **上课时间**: 上午11:00-11:45 (45分钟)
- **课时编号**: Day12-Lesson47
- **前置知识**: Python基础、异步编程、消息队列、上节任务委派决策
- **后续课程**: 第三周课程

## 🎯 学习目标

### 知识目标
1. 理解父子代理通信在分布式AI系统中的重要性和设计原则
2. 掌握父子代理通信协议的设计和消息格式
3. 理解不同通信模式的适用场景和实现方式

### 技能目标
1. 能够设计并实现父子代理通信协议
2. 能够实现同步和异步两种通信模式
3. 能够构建可靠的错误传播和恢复机制

### 态度目标
1. 培养对分布式系统通信设计的理解和兴趣
2. 增强对系统可靠性和容错性的重视
3. 提高对通信协议标准化和文档化的认识

## 📁 演示代码结构

### 主要文件
- `parent_child_comm_demo.py`: 完整的父子代理通信系统实现和演示代码

### 代码结构概述
本演示代码实现父子代理通信系统，包括：

1. **消息类型** - MessageType枚举定义各种消息类型
2. **消息格式** - Message数据类定义消息结构
3. **消息队列** - MessageQueue实现异步消息传递
4. **代理通信** - AgentCommunication实现发送/接收接口
5. **父代理** - ParentAgent实现任务委派和结果收集
6. **子代理** - ChildAgent实现任务执行和进度报告

### 依赖和运行要求
```bash
# 运行环境
Python 3.12+（支持完整的类型注解和现代特性）
安装依赖: 本演示代码使用标准库，无需额外依赖

# 运行演示
cd /home/guoliang/mydocs/studyAgents/deerflow-agent-course/02-教学材料/第二周/课堂演示代码/day12-lesson47
python parent_child_comm_demo.py

# 运行测试套件
python parent_child_comm_demo.py --test

# 运行完整演示
python parent_child_comm_demo.py --demo
```

## 🔧 技术要点

### 核心概念
1. **MessageType**: 消息类型枚举（INSTRUCTION、RESULT、PROGRESS、ERROR、CANCEL等）
2. **Message**: 消息数据类，包含ID、类型、发送者、接收者、内容等
3. **MessageQueue**: 消息队列，实现按接收者分队列和优先级排序
4. **AgentCommunication**: 代理通信接口，支持同步/异步/发送即忘三种模式
5. **ParentAgent**: 父代理，实现任务委派、广播、结果收集
6. **ChildAgent**: 子代理，实现消息循环、任务执行、进度报告

### 关键技术
- **消息队列**: 按接收者分队列，支持优先级排序
- **同步通信**: 请求-响应模式，使用Future等待响应
- **异步通信**: 回调模式，消息处理器自动处理
- **心跳机制**: 定期发送心跳消息，检测代理存活
- **错误处理**: 错误消息传播和自动重试

## 🚀 快速开始

### 运行演示
```bash
cd /home/guoliang/mydocs/studyAgents/deerflow-agent-course/02-教学材料/第二周/课堂演示代码/day12-lesson47
python parent_child_comm_demo.py
```

### 核心API使用示例

```python
import asyncio
from parent_child_comm_demo import (
    MessageQueue, ParentAgent, ChildAgent, Message, MessageType
)

async def main():
    # 1. 创建共享消息队列
    queue = MessageQueue()
    
    # 2. 创建父代理和子代理
    parent = ParentAgent("supervisor", queue)
    child = ChildAgent("worker_1", queue)
    
    # 3. 启动代理
    await parent.start()
    await child.start()
    
    # 4. 启动子代理消息循环
    child_task = asyncio.create_task(child.run_message_loop(60.0))
    
    # 5. 父代理委派任务（同步等待结果）
    result = await parent.delegate_task(
        "worker_1", 
        "分析数据", 
        {"data": [1, 2, 3, 4, 5]}
    )
    print(f"任务结果: {result}")
    
    # 6. 广播指令
    await parent.broadcast_instruction(
        ["worker_1", "worker_2"],
        "准备接收新任务"
    )
    
    # 7. 获取统计
    stats = parent.get_stats()
    print(f"统计: {stats}")
    
    # 8. 清理
    await parent.stop()
    await child.stop()
    child_task.cancel()

asyncio.run(main())
```

### 消息格式示例

```python
# 创建消息
message = Message(
    message_type=MessageType.INSTRUCTION,
    sender="parent",
    receiver="child",
    content={
        "action": "execute",
        "task": "分析数据",
        "params": {"year": 2024}
    },
    priority=3,
    ttl=60.0
)

# 序列化
data = message.to_dict()

# 反序列化
restored = Message.from_dict(data)

# 创建回复
reply = message.create_reply(
    content={"result": "success"},
    message_type=MessageType.RESULT
)
```

## 📚 教学资源

### 参考链接
- 消息队列: https://en.wikipedia.org/wiki/Message_queue
- Actor模型: https://en.wikipedia.org/wiki/Actor_model
- 异步编程: https://docs.python.org/3/library/asyncio.html
- 分布式通信: https://en.wikipedia.org/wiki/Message_passing

---

**版本**: v1.0  
**教师**: 张老师  
**适用对象**: DeerFlow Python Agent架构师训练营学员
