# 🎓 详细教案 - Day 10 第39节课：SSE事件系统

## 📋 课程基本信息
- **课程名称**: SSE事件系统
- **授课日期**: 2024年4月3日（周三）
- **上课时间**: 11:00-11:45（第3节课）
- **授课教师**: 张老师（10年AI系统架构经验，DeerFlow核心贡献者）
- **学生背景**: Python基础一般，已学习任务调度算法，理解异步编程基础
- **教室环境**: 虚拟教室，共享屏幕，10名学员在线

## 🎯 教学目标

### 知识目标（学生将知道/理解）
1. 理解实时事件系统在分布式系统中的重要性和应用场景
2. 掌握Server-Sent Events（SSE）协议原理和与WebSocket的区别
3. 了解事件驱动架构在子代理系统中的设计和实现方法

### 技能目标（学生将能够）
1. 设计和实现基于SSE的事件发布-订阅系统
2. 编写事件生产者和消费者，处理实时状态更新
3. 实现事件过滤、转换和持久化机制

### 情感/态度目标
1. 培养实时系统设计和事件驱动编程思维
2. 增强对系统可观测性和调试能力的重视
3. 提升解决分布式系统通信问题的实践能力

## 📚 教学重点与难点
- **教学重点**: SSE协议原理、事件系统架构、发布-订阅模式实现
- **教学难点**: 事件流管理、连接保持、错误恢复、大规模并发处理
- **突破方法**: 通过实际案例（如股票行情、聊天室）、分步实现、可视化事件流

## 🛠️ 教学资源准备
- **硬件**: 演示用电脑（稳定网络连接）
- **软件**: Python 3.12.0、FastAPI/Starlette、浏览器开发者工具
- **工具**: SSE客户端测试工具、网络抓包工具、事件监控仪表板
- **代码**: SSE服务器示例代码、事件生产者/消费者示例
- **演示材料**: PPT幻灯片、协议流程图、事件时序图
- **学生材料**: 练习手册、API文档、测试脚本

## ⏰ 教学流程（45分钟）

### 阶段1：导入与复习（5分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 0-2分钟 | 课程导入 | 1. 问候学员<br>2. 回顾上节课任务调度算法<br>3. 介绍本节课SSE事件系统主题 | 1. 登录课堂<br>2. 准备学习材料<br>3. 思考事件系统应用 | PPT幻灯片第1-3页 |
| 2-5分钟 | 知识激活 | 1. 提问："如何实时获取子代理任务执行进度？轮询有什么问题？"<br>2. 引导思考实时通信的技术选择<br>3. 连接调度系统与事件系统的关系 | 1. 回答问题<br>2. 参与讨论<br>3. 提出疑问 | 白板、互动问答工具 |

### 阶段2：新知讲解（15分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 5-8分钟 | 事件系统概述 | 1. 讲解事件驱动架构的优势和适用场景<br>2. 对比轮询、WebSocket和SSE技术<br>3. 展示事件系统在子代理中的应用 | 1. 观看演示<br>2. 记录技术对比<br>3. 思考适用场景 | PPT第4-6页，技术对比表 |
| 8-12分钟 | SSE协议原理 | 1. 讲解SSE协议规范和消息格式<br>2. 演示HTTP长连接和事件流<br>3. 介绍SSE客户端和服务端交互 | 1. 学习协议细节<br>2. 理解消息格式<br>3. 记录关键概念 | PPT第7-9页，协议图 |
| 12-15分钟 | 事件数据模型 | 1. 讲解事件类型和数据结构设计<br>2. 演示TaskEvent数据类定义<br>3. 介绍事件元数据和序列化 | 1. 学习事件设计<br>2. 理解字段含义<br>3. 记录数据结构 | VS Code演示，代码示例1 |
| 15-20分钟 | 发布-订阅模式 | 1. 讲解EventStream类设计和实现<br>2. 演示事件发布和订阅流程<br>3. 展示多消费者场景处理 | 1. 跟随代码讲解<br>2. 理解发布订阅机制<br>3. 记录实现要点 | 代码示例2，流程图 |

### 阶段3：互动练习（15分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 20-25分钟 | 练习1：实现事件数据模型 | 1. 布置事件类实现任务<br>2. 巡视并提供指导<br>3. 解答学生疑问 | 1. 设计事件数据结构<br>2. 实现TaskEvent类<br>3. 添加序列化方法 | 练习指导文档，类模板 |
| 25-30分钟 | 练习2：实现事件流管理器 | 1. 指导学生实现EventStream<br>2. 检查常见实现错误<br>3. 演示正确实现方法 | 1. 实现发布订阅逻辑<br>2. 处理连接管理<br>3. 测试事件流转发 | 代码编辑器，测试用例 |
| 30-35分钟 | 练习3：创建SSE服务器 | 1. 指导学生创建SSE端点<br>2. 演示HTTP响应流实现<br>3. 讲解连接保持和超时处理 | 1. 实现SSE HTTP端点<br>2. 编写事件生成器<br>3. 测试客户端连接 | Web框架模板，测试客户端 |

### 阶段4：总结与评估（10分钟）
| 时间 | 教学活动 | 教师活动 | 学生活动 | 教学资源 |
|------|----------|----------|----------|----------|
| 35-38分钟 | 知识总结 | 1. 总结本节课核心事件系统概念<br>2. 强调SSE在实时系统中的优势<br>3. 连接下节课超时与错误处理内容 | 1. 回顾学习内容<br>2. 整理技术要点<br>3. 准备提问 | PPT总结页 |
| 38-42分钟 | 问题解答 | 1. 回答学生疑问<br>2. 澄清协议概念误解<br>3. 提供额外学习资源 | 1. 提出问题<br>2. 参与讨论<br>3. 记录解答 | 问题收集工具 |
| 42-45分钟 | 课后任务布置 | 1. 布置课后作业<br>2. 说明作业要求<br>3. 预告下节课内容 | 1. 记录作业要求<br>2. 明确完成标准<br>3. 准备课后学习 | 作业说明文档 |

## 🗣️ 师生互动设计

### 提问设计（关键问题）
1. **导入问题**："微信消息是如何实时推送到手机的？轮询和推送哪种更好？"
2. **探究问题**："SSE和WebSocket有什么区别？各自适合什么场景？"
3. **应用问题**："如果SSE连接断开，系统应该如何恢复和重连？"
4. **反思问题**："事件系统如何保证消息不丢失和顺序一致性？"

### 互动活动
1. **事件流模拟**：分组模拟事件发布订阅过程，理解流程（4分钟）
2. **协议分析**：分析SSE原始HTTP响应，理解协议格式（3分钟）
3. **设计评审**：互相评审事件系统设计，提出改进建议（5分钟）

### 反馈机制
1. **实时反馈**：通过在线工具收集学生对协议理解程度
2. **代码反馈**：教师实时查看学生事件系统实现并提供优化建议
3. **连接测试反馈**：测试SSE连接稳定性，评估实现质量

## 👥 差异化教学

### 针对基础薄弱学生
1. **简化任务**：提供完整的事件系统框架，只需实现核心逻辑
2. **额外指导**：安排助教一对一指导异步事件处理
3. **分步演示**：将复杂事件流分解为简单步骤，逐步完成

### 针对进阶学生
1. **扩展挑战**：实现事件持久化和重放机制
2. **深度研究**：研究事件溯源（Event Sourcing）模式
3. **创新设计**：设计支持大规模并发的事件分发系统

### 共同支持策略
1. **合作学习**：混合分组，让不同水平学生互相帮助
2. **分层资源**：提供基础、标准、高级三种难度的练习材料
3. **弹性时间**：允许学生在课后继续完成事件系统优化

## 📊 评估方式

### 形成性评估（课堂内）
1. **观察记录**：教师观察学生事件系统实现情况（权重30%）
2. **代码检查**：检查学生编写的事件系统代码质量和正确性（权重40%）
3. **协议理解**：通过提问和讨论评估学生对SSE协议的理解（权重30%）

### 评估标准
- **优秀（85-100分）**：完整实现事件系统，支持完整SSE协议，代码健壮高效，理解深入
- **良好（70-84分）**：基本实现事件功能，代码规范，理解正确，能说明技术选择理由
- **合格（60-69分）**：部分实现事件功能，需要指导完成，基本理解协议概念
- **待改进（<60分）**：未能完成核心事件功能，需要额外辅导

### 反馈方式
1. **即时反馈**：课堂练习时直接提供事件系统实现指导
2. **书面反馈**：课后提供详细的代码评语和优化建议
3. **一对一反馈**：针对困难学生安排单独协议辅导

## 🚨 应急预案

### 技术故障
1. **网络问题**：准备本地模拟环境，不依赖外部网络
2. **浏览器兼容性**：提供多种测试工具和备用方案
3. **异步调试困难**：提供同步简化版本，降低调试难度

### 学生困难
1. **无法理解异步事件流**：使用同步事件队列逐步引入异步概念
2. **HTTP流概念困惑**：使用简单HTTP响应示例，逐步引入流式响应
3. **时间不足**：提供课后扩展练习和协议动画演示

### 内容调整
1. **进度过快**：增加协议细节练习，放慢原理讲解
2. **进度过慢**：跳过高级优化内容，保证核心协议实现完成
3. **兴趣不足**：增加实际应用案例，展示事件系统的威力

## 💭 教学反思（课后填写）

### 学生表现
- 理解程度：
- 参与程度：
- 困难点：

### 教学效果
- 目标达成：
- 时间控制：
- 资源使用：

### 改进建议
- 内容调整：
- 方法优化：
- 资源补充：

## 📝 课后任务

### 必做任务
1. **基础练习**：实现TaskEvent数据类和序列化方法，支持JSON转换
2. **协议实现**：实现EventStream类，支持事件发布和订阅功能
3. **SSE端点**：创建FastAPI/Starlette SSE端点，实时推送任务状态事件

### 选做任务（挑战）
1. **连接管理**：实现SSE连接心跳检测和自动重连机制
2. **事件持久化**：设计事件存储和重放系统，支持历史事件查询
3. **性能优化**：实现事件批量发送和压缩，优化网络传输效率

### 预习任务
1. **阅读材料**：预习下一节"超时与错误处理"的学生讲义
2. **思考问题**："事件系统在错误处理中扮演什么角色？"
3. **准备环境**：确保错误监控工具可用，用于下一课的错误处理实验

## 📎 附录

### 附录1：PPT幻灯片大纲
```
幻灯片1：课程标题与目标
幻灯片2：回顾与导入
幻灯片3：实时通信技术对比
幻灯片4：SSE协议原理
幻灯片5：HTTP事件流格式
幻灯片6：事件数据模型设计
幻灯片7：发布-订阅模式
幻灯片8：EventStream实现
幻灯片9：SSE服务器端实现
幻灯片10：SSE客户端实现
幻灯片11：连接管理和错误处理
幻灯片12：互动练习说明
幻灯片13：知识总结
幻灯片14：课后任务
幻灯片15：Q&A
```

### 附录2：实时通信技术对比
```python
"""
实时通信技术对比：

技术        协议      双向通信  连接方式      复杂度      适用场景
----------  --------  --------  -----------  ----------  -------------------------
轮询        HTTP      单向      短连接       低          更新频率低、实时性要求不高
长轮询      HTTP      单向      长连接       中          中等实时性、服务器推送
SSE         HTTP      单向      长连接       中          服务器到客户端单向实时推送
WebSocket   WS        双向      长连接       高          双向实时通信、互动性高
MQTT        TCP       双向      长连接       高          IoT、移动设备、低带宽

SSE优势：
1. 基于HTTP，无需额外协议
2. 自动重连机制
3. 简单的文本协议
4. 浏览器原生支持
"""
```

### 附录3：事件系统实现代码示例
```python
import asyncio
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, AsyncIterator
from enum import Enum
import uuid

class EventType(Enum):
    """事件类型"""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    SYSTEM_STATUS = "system_status"
    WARNING = "warning"
    ERROR = "error"

@dataclass
class Event:
    """基础事件"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.SYSTEM_STATUS
    source: str = "system"
    timestamp: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_sse_format(self) -> str:
        """转换为SSE格式"""
        event_dict = {
            "id": self.id,
            "type": self.type.value,
            "source": self.source,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata
        }
        
        # SSE格式：event: <type>\ndata: <json>\n\n
        lines = [
            f"event: {self.type.value}",
            f"id: {self.id}",
            f"data: {json.dumps(event_dict)}",
            "",  # 空行表示事件结束
        ]
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

@dataclass
class TaskEvent(Event):
    """任务事件"""
    
    def __init__(self, task_id: str, event_type: EventType, data: Dict[str, Any] = None):
        super().__init__(
            type=event_type,
            source="task_manager",
            data=data or {},
            metadata={"task_id": task_id}
        )

class EventStream:
    """事件流管理器"""
    
    def __init__(self, max_listeners: int = 100):
        self.listeners: List[asyncio.Queue] = []
        self.max_listeners = max_listeners
        self._lock = asyncio.Lock()
        self.event_history: List[Event] = []
        self.max_history = 1000
    
    async def publish(self, event: Event):
        """发布事件"""
        async with self._lock:
            # 添加到历史记录
            self.event_history.append(event)
            if len(self.event_history) > self.max_history:
                self.event_history = self.event_history[-self.max_history:]
            
            # 发送给所有监听者
            dead_listeners = []
            
            for listener in self.listeners:
                try:
                    # 非阻塞put，如果队列满则跳过
                    listener.put_nowait(event)
                except asyncio.QueueFull:
                    # 队列满，标记为死亡
                    dead_listeners.append(listener)
                except Exception:
                    # 其他异常，也标记为死亡
                    dead_listeners.append(listener)
            
            # 清理死亡监听者
            for dead in dead_listeners:
                if dead in self.listeners:
                    self.listeners.remove(dead)
            
            print(f"📢 发布事件: {event.type.value} (监听者: {len(self.listeners)})")
    
    async def subscribe(self, filter_types: List[EventType] = None) -> AsyncIterator[Event]:
        """订阅事件流
        
        Args:
            filter_types: 只接收指定类型的事件，None表示接收所有
            
        Returns:
            事件异步迭代器
        """
        queue = asyncio.Queue(maxsize=100)
        
        async with self._lock:
            if len(self.listeners) >= self.max_listeners:
                raise RuntimeError(f"达到最大监听者限制: {self.max_listeners}")
            
            self.listeners.append(queue)
        
        try:
            print(f"✅ 新订阅者加入 (过滤: {filter_types})")
            
            # 发送历史事件（可选）
            # for event in self.event_history[-10:]:  # 发送最近10个事件
            #     if filter_types is None or event.type in filter_types:
            #         await queue.put(event)
            
            # 持续接收新事件
            while True:
                event = await queue.get()
                
                # 应用过滤
                if filter_types is not None and event.type not in filter_types:
                    continue
                
                yield event
                
        except asyncio.CancelledError:
            # 订阅被取消
            print("订阅被取消")
        finally:
            # 清理
            async with self._lock:
                if queue in self.listeners:
                    self.listeners.remove(queue)
            print("订阅者退出")
    
    def get_recent_events(self, limit: int = 100, filter_types: List[EventType] = None) -> List[Event]:
        """获取最近的事件"""
        events = self.event_history[-limit:] if limit else self.event_history
        
        if filter_types:
            events = [e for e in events if e.type in filter_types]
        
        return events

class EventProducer:
    """事件生产者"""
    
    def __init__(self, event_stream: EventStream):
        self.event_stream = event_stream
    
    async def produce_task_event(self, task_id: str, event_type: EventType, data: Dict = None):
        """产生任务事件"""
        event = TaskEvent(task_id, event_type, data)
        await self.event_stream.publish(event)
    
    async def produce_system_event(self, event_type: EventType, message: str, details: Dict = None):
        """产生系统事件"""
        event = Event(
            type=event_type,
            source="system_monitor",
            data={
                "message": message,
                "details": details or {}
            }
        )
        await self.event_stream.publish(event)

# FastAPI SSE端点示例（使用Starlette）
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

# 全局事件流
global_event_stream = EventStream()

@app.get("/events")
async def event_stream(request: Request):
    """SSE事件流端点"""
    
    async def event_generator():
        """事件生成器"""
        try:
            # 订阅所有事件
            async for event in global_event_stream.subscribe():
                # 检查客户端是否断开连接
                if await request.is_disconnected():
                    break
                
                # 发送SSE格式事件
                yield event.to_sse_format()
                
        except asyncio.CancelledError:
            # 连接被取消
            print("SSE连接被客户端取消")
        except Exception as e:
            print(f"SSE连接异常: {e}")
        finally:
            print("SSE连接关闭")
    
    # 设置SSE响应头
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
    }
    
    return StreamingResponse(
        event_generator(),
        headers=headers,
        media_type="text/event-stream"
    )

@app.post("/events/task/{task_id}")
async def create_task_event(task_id: str, event_type: str, data: Dict = None):
    """创建任务事件"""
    try:
        event_type_enum = EventType(event_type)
    except ValueError:
        return {"error": f"无效的事件类型: {event_type}"}
    
    producer = EventProducer(global_event_stream)
    await producer.produce_task_event(task_id, event_type_enum, data)
    
    return {"success": True, "message": "事件已发布"}

# 客户端测试代码
async def test_event_system():
    """测试事件系统"""
    
    # 创建事件流
    event_stream = EventStream()
    producer = EventProducer(event_stream)
    
    print("测试事件系统...")
    
    # 创建消费者任务
    async def consumer(name: str, filter_types: List[EventType] = None):
        """消费者"""
        print(f"{name}: 开始监听事件...")
        
        count = 0
        async for event in event_stream.subscribe(filter_types):
            print(f"{name}: 收到事件 [{event.type.value}] - {event.data}")
            count += 1
            
            if count >= 3:
                print(f"{name}: 收到3个事件，停止监听")
                break
    
    # 启动消费者
    consumer1 = asyncio.create_task(consumer("消费者1", [EventType.TASK_CREATED, EventType.TASK_COMPLETED]))
    consumer2 = asyncio.create_task(consumer("消费者2"))  # 接收所有事件
    
    # 等待消费者准备
    await asyncio.sleep(0.1)
    
    # 产生事件
    await producer.produce_task_event("task_123", EventType.TASK_CREATED, {"description": "测试任务"})
    await asyncio.sleep(0.1)
    
    await producer.produce_task_event("task_123", EventType.TASK_STARTED, {"worker": "worker_1"})
    await asyncio.sleep(0.1)
    
    await producer.produce_system_event(EventType.SYSTEM_STATUS, "系统运行正常", {"load": 0.5})
    await asyncio.sleep(0.1)
    
    await producer.produce_task_event("task_123", EventType.TASK_COMPLETED, {"result": "success", "time": 2.5})
    
    # 等待消费者完成
    await asyncio.gather(consumer1, consumer2)
    
    # 测试历史事件
    recent = event_stream.get_recent_events(limit=5)
    print(f"\\n最近{len(recent)}个事件:")
    for event in recent:
        print(f"  - {event.type.value}: {event.data}")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_event_system())
```

### 附录4：SSE客户端示例
```html
<!DOCTYPE html>
<html>
<head>
    <title>SSE事件监控客户端</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        h1 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        
        .controls {
            margin: 20px 0;
            display: flex;
            gap: 10px;
        }
        
        button {
            padding: 10px 20px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        
        button:hover {
            background: #45a049;
        }
        
        button.stop {
            background: #f44336;
        }
        
        button.stop:hover {
            background: #da190b;
        }
        
        .status {
            margin: 10px 0;
            padding: 10px;
            border-radius: 4px;
            background: #e8f5e9;
            display: none;
        }
        
        .status.connected {
            background: #e8f5e9;
            color: #2e7d32;
            display: block;
        }
        
        .status.disconnected {
            background: #ffebee;
            color: #c62828;
            display: block;
        }
        
        .events {
            margin-top: 20px;
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 10px;
        }
        
        .event {
            padding: 10px;
            margin: 5px 0;
            border-left: 4px solid #4CAF50;
            background: #f9f9f9;
        }
        
        .event.error {
            border-left-color: #f44336;
            background: #ffebee;
        }
        
        .event.warning {
            border-left-color: #ff9800;
            background: #fff3e0;
        }
        
        .event.info {
            border-left-color: #2196f3;
            background: #e3f2fd;
        }
        
        .event-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
        }
        
        .event-type {
            font-weight: bold;
            color: #333;
        }
        
        .event-time {
            color: #666;
            font-size: 0.9em;
        }
        
        .event-data {
            font-family: monospace;
            white-space: pre-wrap;
            background: white;
            padding: 5px;
            border-radius: 3px;
            border: 1px solid #eee;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>SSE事件监控客户端</h1>
        
        <div class="controls">
            <button id="connectBtn">连接事件流</button>
            <button id="disconnectBtn" class="stop">断开连接</button>
            <button id="clearBtn">清空事件</button>
        </div>
        
        <div id="status" class="status"></div>
        
        <div class="events" id="eventsContainer">
            <!-- 事件将在这里显示 -->
        </div>
    </div>
    
    <script>
        class SSEClient {
            constructor(url) {
                this.url = url;
                this.eventSource = null;
                this.connected = false;
                this.reconnectAttempts = 0;
                this.maxReconnectAttempts = 5;
                this.reconnectDelay = 1000; // 1秒
            }
            
            connect() {
                if (this.connected) {
                    console.log("已经连接");
                    return;
                }
                
                try {
                    this.eventSource = new EventSource(this.url);
                    
                    this.eventSource.onopen = (event) => {
                        console.log("SSE连接已建立");
                        this.connected = true;
                        this.reconnectAttempts = 0;
                        this.onConnected();
                    };
                    
                    this.eventSource.onmessage = (event) => {
                        console.log("收到消息:", event.data);
                        this.onMessage(event);
                    };
                    
                    this.eventSource.onerror = (event) => {
                        console.error("SSE连接错误", event);
                        this.connected = false;
                        this.onError(event);
                        
                        // 尝试重连
                        this.attemptReconnect();
                    };
                    
                    // 监听特定事件类型
                    this.eventSource.addEventListener("task_created", (event) => {
                        this.onEvent("task_created", event);
                    });
                    
                    this.eventSource.addEventListener("task_started", (event) => {
                        this.onEvent("task_started", event);
                    });
                    
                    this.eventSource.addEventListener("task_completed", (event) => {
                        this.onEvent("task_completed", event);
                    });
                    
                    this.eventSource.addEventListener("task_failed", (event) => {
                        this.onEvent("task_failed", event);
                    });
                    
                    this.eventSource.addEventListener("system_status", (event) => {
                        this.onEvent("system_status", event);
                    });
                    
                    this.eventSource.addEventListener("error", (event) => {
                        this.onEvent("error", event);
                    });
                    
                    this.eventSource.addEventListener("warning", (event) => {
                        this.onEvent("warning", event);
                    });
                    
                } catch (error) {
                    console.error("创建EventSource失败:", error);
                    this.onError(error);
                }
            }
            
            attemptReconnect() {
                if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                    console.error("达到最大重连次数，停止重连");
                    this.onMaxReconnectAttempts();
                    return;
                }
                
                this.reconnectAttempts++;
                console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
                
                setTimeout(() => {
                    this.disconnect();
                    this.connect();
                }, this.reconnectDelay * this.reconnectAttempts);
            }
            
            disconnect() {
                if (this.eventSource) {
                    this.eventSource.close();
                    this.eventSource = null;
                }
                this.connected = false;
                this.onDisconnected();
            }
            
            onConnected() {
                // 由外部覆盖
            }
            
            onDisconnected() {
                // 由外部覆盖
            }
            
            onMessage(event) {
                // 由外部覆盖
            }
            
            onEvent(eventType, event) {
                // 由外部覆盖
            }
            
            onError(error) {
                // 由外部覆盖
            }
            
            onMaxReconnectAttempts() {
                // 由外部覆盖
            }
        }
        
        // 使用示例
        document.addEventListener('DOMContentLoaded', function() {
            const eventsContainer = document.getElementById('eventsContainer');
            const statusDiv = document.getElementById('status');
            const connectBtn = document.getElementById('connectBtn');
            const disconnectBtn = document.getElementById('disconnectBtn');
            const clearBtn = document.getElementById('clearBtn');
            
            // 更新状态显示
            function updateStatus(message, type) {
                statusDiv.textContent = message;
                statusDiv.className = 'status';
                
                if (type === 'connected') {
                    statusDiv.classList.add('connected');
                } else if (type === 'disconnected') {
                    statusDiv.classList.add('disconnected');
                }
            }
            
            // 添加事件到界面
            function addEventToUI(eventType, data) {
                const eventDiv = document.createElement('div');
                eventDiv.className = 'event';
                
                // 根据事件类型添加CSS类
                if (eventType.includes('error')) {
                    eventDiv.classList.add('error');
                } else if (eventType.includes('warning')) {
                    eventDiv.classList.add('warning');
                } else {
                    eventDiv.classList.add('info');
                }
                
                const now = new Date();
                const timeStr = now.toLocaleTimeString();
                
                let displayData = data;
                if (typeof data === 'object') {
                    try {
                        displayData = JSON.stringify(data, null, 2);
                    } catch (e) {
                        displayData = String(data);
                    }
                }
                
                eventDiv.innerHTML = `
                    <div class="event-header">
                        <span class="event-type">${eventType}</span>
                        <span class="event-time">${timeStr}</span>
                    </div>
                    <div class="event-data">${displayData}</div>
                `;
                
                eventsContainer.prepend(eventDiv);
                
                // 限制显示数量
                const maxEvents = 50;
                const events = eventsContainer.querySelectorAll('.event');
                if (events.length > maxEvents) {
                    for (let i = maxEvents; i < events.length; i++) {
                        events[i].remove();
                    }
                }
            }
            
            // 创建SSE客户端
            const sseClient = new SSEClient('http://localhost:8000/events');
            
            // 设置回调
            sseClient.onConnected = function() {
                updateStatus('✅ 已连接到事件流', 'connected');
                connectBtn.disabled = true;
                disconnectBtn.disabled = false;
            };
            
            sseClient.onDisconnected = function() {
                updateStatus('❌ 已断开连接', 'disconnected');
                connectBtn.disabled = false;
                disconnectBtn.disabled = true;
            };
            
            sseClient.onMessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    addEventToUI('message', data);
                } catch (e) {
                    addEventToUI('message', event.data);
                }
            };
            
            sseClient.onEvent = function(eventType, event) {
                try {
                    const data = JSON.parse(event.data);
                    addEventToUI(eventType, data);
                } catch (e) {
                    addEventToUI(eventType, event.data);
                }
            };
            
            sseClient.onError = function(error) {
                console.error('SSE错误:', error);
                addEventToUI('connection_error', error);
            };
            
            sseClient.onMaxReconnectAttempts = function() {
                updateStatus('❌ 达到最大重连次数，请手动重连', 'disconnected');
                connectBtn.disabled = false;
                disconnectBtn.disabled = true;
            };
            
            // 按钮事件
            connectBtn.addEventListener('click', function() {
                sseClient.connect();
            });
            
            disconnectBtn.addEventListener('click', function() {
                sseClient.disconnect();
            });
            
            clearBtn.addEventListener('click', function() {
                eventsContainer.innerHTML = '';
            });
            
            // 初始状态
            disconnectBtn.disabled = true;
            updateStatus('准备连接...');
        });
    </script>
</body>
</html>
```

### 附录5：课堂练习检查表
```
学生姓名: ___________    日期: ___________

□ 1. 理解了SSE协议原理和事件驱动架构
□ 2. 成功实现了Event数据类和序列化方法
□ 3. 正确实现了EventStream事件流管理器
□ 4. 创建了SSE HTTP端点，支持事件流
□ 5. 实现了事件发布和订阅功能
□ 6. 编写了事件生产者和消费者代码
□ 7. 测试了SSE连接和事件推送
□ 8. 理解了连接管理和错误恢复机制

教师评语: ____________________________________
评分: ______/100
```

### 附录6：学生反馈表
```
课程名称: SSE事件系统
日期: 2024年4月3日

1. 本节课最难理解的部分是？
   [ ] SSE协议原理
   [ ] 异步事件流处理
   [ ] HTTP流式响应
   [ ] 其他: ________

2. 实现时间是否充足？
   [ ] 非常充足
   [ ] 基本足够
   [ ] 有点紧张
   [ ] 完全不够

3. 协议概念讲解是否清晰？
   [ ] 非常清晰
   [ ] 比较清晰
   [ ] 一般
   [ ] 不够清晰

4. 你对SSE事件系统的理解程度（1-5分）？
   1 [ ] 2 [ ] 3 [ ] 4 [ ] 5 [ ]

5. 有什么建议或问题？
   _________________________________________
   _________________________________________
```

### 附录7：教学观察记录表
```
观察项目              | 观察要点                     | 记录
---------------------|----------------------------|-----------
学生参与度           | 是否积极讨论协议设计         | 
概念理解度           | 能否解释SSE协议原理         | 
代码实现能力         | 能否独立完成事件系统实现     | 
协议实现能力         | 能否正确实现SSE端点          | 
合作学习表现         | 是否愿意分享调试经验         | 
特殊需求             | 需要额外协议指导的学生       | 

总体评价: ____________________________________
跟进建议: ____________________________________
观察教师: ___________    时间: ___________
```

---
**教学提示**: 
1. SSE协议基于HTTP，要强调与WebSocket的区别和适用场景
2. 事件驱动架构是现代化系统重要模式，要结合实际案例讲解
3. 异步事件流处理涉及并发编程，要强调线程安全和状态管理
4. 连接管理和错误恢复是生产系统关键，要引导学生设计健壮方案

**关联知识**:
- HTTP协议：长连接、分块传输、响应流
- 异步编程：asyncio、协程、异步迭代器
- 消息队列：发布-订阅模式、事件总线
- 实时系统：WebSocket、MQTT、gRPC流

**延伸阅读**:
1. Server-Sent Events规范（W3C）
2. FastAPI/Starlette SSE实现文档
3. 事件驱动架构模式（Martin Fowler）
4. 实时Web通信技术对比分析

---
*教案版本: v1.0*
*最后更新: 2024年3月26日*
*教案编写: 张老师（DeerFlow架构师培训团队）*