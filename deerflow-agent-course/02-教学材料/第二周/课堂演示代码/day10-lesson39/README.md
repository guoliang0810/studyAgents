# Day 10 Lesson 39: SSE事件系统

## 📋 课程信息
- **课程名称**: Day 10 - 第39节课：SSE事件系统
- **授课日期**: 2024年4月3日（周三）
- **上课时间**: 上午11:00-11:45 (45分钟)
- **课时编号**: Day10-Lesson39
- **前置知识**: Python基础、异步编程（asyncio）、HTTP协议基础、第二周任务调度算法课程
- **后续课程**: 第二周 Day 10 第40节课：超时与错误处理

## 🎯 学习目标

### 知识目标
1. 理解实时事件系统在分布式系统中的重要性和应用场景
2. 掌握Server-Sent Events（SSE）协议原理和与WebSocket的区别
3. 了解事件驱动架构在子代理系统中的设计和实现方法

### 技能目标
1. 能够设计和实现基于SSE的事件发布-订阅系统
2. 能够编写事件生产者和消费者，处理实时状态更新
3. 能够实现事件过滤、转换和持久化机制

### 态度目标
1. 培养实时系统设计和事件驱动编程思维
2. 增强对系统可观测性和调试能力的重视
3. 提升解决分布式系统通信问题的实践能力

## 📁 演示代码结构

### 主要文件
- `sse_demo.py`: 完整的SSE事件系统实现和演示代码

### 代码结构概述
本演示代码实现SSE事件系统，包括：

1. **事件数据模型** - TaskEvent事件数据类，支持多种事件类型
2. **事件过滤系统** - 订阅过滤器，支持按类型、来源、数据内容过滤
3. **事件流管理器** - EventStream发布-订阅模式实现
4. **SSE连接管理** - SSEConnection处理HTTP长连接和事件流
5. **测试套件** - 完整的测试验证事件系统正确性

### 依赖和运行要求
```bash
# 运行环境
Python 3.12+（支持完整的类型注解和现代特性）
安装依赖: pip install  # 本演示代码使用标准库，无需额外依赖

# 运行演示
cd /home/guoliang/mydocs/studyAgents/deerflow-agent-course/02-教学材料/第二周/课堂演示代码/day10-lesson39
python sse_demo.py

# 运行测试套件
python sse_demo.py --test

# 运行完整演示
python sse_demo.py --demo
```

## 🔧 技术要点

### 核心概念
1. **事件类型**: TASK_CREATED、TASK_STARTED、TASK_PROGRESS、TASK_COMPLETED等
2. **事件数据模型**: TaskEvent包含event_id、event_type、timestamp、data等字段
3. **订阅过滤器**: EventTypeFilter、SourceFilter、DataFilter等过滤器类
4. **事件流管理器**: EventStream实现发布-订阅模式
5. **SSE连接**: SSEConnection管理HTTP长连接和心跳机制
6. **事件格式**: SSE标准格式`data: message\n\n`
7. **异步处理**: 基于asyncio的异步事件发布和订阅
8. **统计监控**: 事件统计、订阅者管理、性能监控

### 关键技术
- **SSE协议**: 基于HTTP的服务器推送技术
- **发布-订阅模式**: 解耦事件生产者和消费者
- **异步生成器**: 使用async generator实现事件流
- **过滤器模式**: 策略模式实现事件过滤
- **事件序列化**: JSON序列化和SSE格式转换
- **连接管理**: 心跳机制、自动重连、连接状态管理
- **测试驱动**: 完整的单元测试套件
- **性能优化**: 异步分发、批量处理、历史记录管理

## 🚀 快速开始

### 运行演示
```bash
cd /home/guoliang/mydocs/studyAgents/deerflow-agent-course/02-教学材料/第二周/课堂演示代码/day10-lesson39
python sse_demo.py
```

### 核心API使用示例

```python
import asyncio
from sse_demo import EventStream, TaskEvent, EventType, EventTypeFilter

# 创建事件流
event_stream = EventStream()

# 订阅事件
async def event_handler(event):
    print(f"收到事件: {event.event_type.value}")

subscription_id = event_stream.subscribe(event_handler)

# 创建事件
event = TaskEvent.create_task_progress("task_001", 0.5, "处理中")

# 发布事件
asyncio.run(event_stream.publish(event))

# 带过滤器的订阅
filters = [EventTypeFilter({EventType.TASK_PROGRESS})]
filtered_id = event_stream.subscribe(event_handler, filters=filters)

# 清理
event_stream.unsubscribe(subscription_id)
event_stream.unsubscribe(filtered_id)
```

## 📚 教学资源

### 参考链接
- SSE官方规范: https://html.spec.whatwg.org/multipage/server-sent-events.html
- MDN SSE文档: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
- WebSocket对比: https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API
- 事件驱动架构: https://martinfowler.com/articles/201701-event-driven.html

---

**版本**: v1.0  
**教师**: 张老师  
**适用对象**: DeerFlow Python Agent架构师训练营学员