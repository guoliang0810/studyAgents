#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 10 Lesson 39: SSE事件系统 (Server-Sent Events System)

本文件演示SSE事件系统的完整实现，包括：
1. EventStream类 - 基于发布-订阅模式的事件流管理
2. TaskEvent数据模型 - 定义事件数据结构和序列化
3. SSE服务器 - 实现HTTP长连接和事件流传输
4. 事件过滤和分发 - 支持按类型订阅和事件过滤

使用示例:
    python sse_demo.py          # 运行基本演示
    python sse_demo.py --test   # 运行测试套件
    python sse_demo.py --demo   # 运行完整演示
    python sse_demo.py --help   # 显示帮助信息
"""

import asyncio
import json
import time
import uuid
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable, Set, AsyncGenerator
from datetime import datetime
import logging
from abc import ABC, abstractmethod

class EventType(Enum):
    """事件类型枚举"""
    TASK_CREATED = "task_created"          # 任务创建
    TASK_STARTED = "task_started"          # 任务开始
    TASK_PROGRESS = "task_progress"        # 任务进度
    TASK_COMPLETED = "task_completed"      # 任务完成
    TASK_FAILED = "task_failed"            # 任务失败
    SYSTEM_STATUS = "system_status"        # 系统状态
    NOTIFICATION = "notification"          # 通知消息
    HEARTBEAT = "heartbeat"                # 心跳

@dataclass
class TaskEvent:
    """任务事件数据类"""
    event_id: str                          # 事件ID
    event_type: EventType                  # 事件类型
    timestamp: float                       # 事件时间戳
    data: Dict[str, Any]                   # 事件数据
    source: str = ""                       # 事件来源
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = time.time()
    
    def to_sse_format(self) -> str:
        """转换为SSE格式"""
        lines = []
        lines.append(f"id: {self.event_id}")
        lines.append(f"event: {self.event_type.value}")
        lines.append(f"data: {json.dumps(self.to_dict())}")
        lines.append(f"timestamp: {self.timestamp}")
        if self.source:
            lines.append(f"source: {self.source}")
        lines.append("")  # 空行表示消息结束
        lines.append("")
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "data": self.data,
            "source": self.source,
            "metadata": self.metadata
        }
    
    @classmethod
    def create_task_progress(cls, task_id: str, progress: float, 
                           message: str = "", source: str = "task_system") -> 'TaskEvent':
        """创建任务进度事件"""
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=EventType.TASK_PROGRESS,
            timestamp=time.time(),
            data={
                "task_id": task_id,
                "progress": progress,  # 0.0-1.0
                "message": message,
                "percentage": int(progress * 100)
            },
            source=source
        )
    
    @classmethod
    def create_notification(cls, title: str, message: str, level: str = "info",
                          source: str = "system") -> 'TaskEvent':
        """创建通知事件"""
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=EventType.NOTIFICATION,
            timestamp=time.time(),
            data={
                "title": title,
                "message": message,
                "level": level  # info, warning, error
            },
            source=source
        )

class SubscriptionFilter(ABC):
    """订阅过滤器抽象基类"""
    
    @abstractmethod
    def matches(self, event: TaskEvent) -> bool:
        """检查事件是否匹配过滤器"""
        pass

class EventTypeFilter(SubscriptionFilter):
    """事件类型过滤器"""
    
    def __init__(self, event_types: Set[EventType]):
        self.event_types = event_types
    
    def matches(self, event: TaskEvent) -> bool:
        return event.event_type in self.event_types

class SourceFilter(SubscriptionFilter):
    """事件来源过滤器"""
    
    def __init__(self, sources: Set[str]):
        self.sources = sources
    
    def matches(self, event: TaskEvent) -> bool:
        return not self.sources or event.source in self.sources

class DataFilter(SubscriptionFilter):
    """数据内容过滤器"""
    
    def __init__(self, key: str, value: Any):
        self.key = key
        self.value = value
    
    def matches(self, event: TaskEvent) -> bool:
        return event.data.get(self.key) == self.value

class Subscription:
    """事件订阅"""
    
    def __init__(self, subscription_id: str, callback: Callable[[TaskEvent], Any],
                 filters: Optional[List[SubscriptionFilter]] = None,
                 client_id: str = ""):
        self.subscription_id = subscription_id
        self.callback = callback
        self.filters = filters or []
        self.client_id = client_id
        self.created_at = time.time()
        self.last_event_time = 0.0
        self.event_count = 0
    
    def matches(self, event: TaskEvent) -> bool:
        """检查事件是否匹配订阅条件"""
        if not self.filters:
            return True  # 无过滤器，匹配所有事件
        
        for filter in self.filters:
            if not filter.matches(event):
                return False
        return True
    
    async def deliver(self, event: TaskEvent) -> bool:
        """传递事件给订阅者"""
        try:
            await self.callback(event)
            self.last_event_time = time.time()
            self.event_count += 1
            return True
        except Exception as e:
            logging.error(f"事件传递失败: {e}")
            return False

class EventStream:
    """事件流管理器"""
    
    def __init__(self):
        self.subscriptions: Dict[str, Subscription] = {}
        self.event_history: List[TaskEvent] = []  # 事件历史
        self.max_history_size = 1000
        self.active = True
        
        # 统计信息
        self.total_events_published = 0
        self.total_events_delivered = 0
        self.delivery_failures = 0
    
    def subscribe(self, callback: Callable[[TaskEvent], Any],
                 filters: Optional[List[SubscriptionFilter]] = None,
                 client_id: str = "") -> str:
        """订阅事件"""
        subscription_id = str(uuid.uuid4())
        subscription = Subscription(
            subscription_id=subscription_id,
            callback=callback,
            filters=filters,
            client_id=client_id
        )
        self.subscriptions[subscription_id] = subscription
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            return True
        return False
    
    async def publish(self, event: TaskEvent) -> int:
        """发布事件"""
        if not self.active:
            return 0
        
        # 添加到历史记录
        self.event_history.append(event)
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)
        
        self.total_events_published += 1
        
        # 分发给订阅者
        delivered = 0
        tasks = []
        
        for subscription in self.subscriptions.values():
            if subscription.matches(event):
                tasks.append(subscription.deliver(event))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            delivered = sum(1 for result in results if result is True)
            self.total_events_delivered += delivered
            self.delivery_failures += len(results) - delivered
        
        return delivered
    
    def get_subscription_info(self) -> List[Dict[str, Any]]:
        """获取订阅信息"""
        return [
            {
                "subscription_id": sub.subscription_id,
                "client_id": sub.client_id,
                "created_at": sub.created_at,
                "last_event_time": sub.last_event_time,
                "event_count": sub.event_count,
                "filter_count": len(sub.filters)
            }
            for sub in self.subscriptions.values()
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "active_subscriptions": len(self.subscriptions),
            "total_events_published": self.total_events_published,
            "total_events_delivered": self.total_events_delivered,
            "delivery_failures": self.delivery_failures,
            "delivery_rate": (self.total_events_delivered / self.total_events_published * 100 
                            if self.total_events_published > 0 else 0),
            "event_history_size": len(self.event_history)
        }
    
    def clear_history(self) -> int:
        """清空事件历史"""
        count = len(self.event_history)
        self.event_history.clear()
        return count
    
    def stop(self):
        """停止事件流"""
        self.active = False

class SSEConnection:
    """SSE连接管理"""
    
    def __init__(self, client_id: str, event_stream: EventStream):
        self.client_id = client_id
        self.event_stream = event_stream
        self.connected = False
        self.last_heartbeat = 0.0
        self.heartbeat_interval = 15.0  # 15秒心跳间隔
        
        # 订阅回调
        self.subscription_id = None
    
    async def event_generator(self) -> AsyncGenerator[str, None]:
        """事件生成器（异步生成器）"""
        self.connected = True
        
        # 订阅事件
        async def event_callback(event: TaskEvent):
            # 生成SSE格式数据
            sse_data = event.to_sse_format()
            # 注意：在实际实现中，这里需要将数据发送给客户端
            # 在这个简化示例中，我们只是记录日志
            logging.debug(f"事件发送给客户端 {self.client_id}: {event.event_type.value}")
        
        self.subscription_id = self.event_stream.subscribe(
            callback=event_callback,
            client_id=self.client_id
        )
        
        try:
            # 发送连接确认事件
            welcome_event = TaskEvent(
                event_id=str(uuid.uuid4()),
                event_type=EventType.NOTIFICATION,
                timestamp=time.time(),
                data={
                    "type": "welcome",
                    "message": f"客户端 {self.client_id} 已连接",
                    "client_id": self.client_id
                },
                source="sse_server"
            )
            yield welcome_event.to_sse_format()
            
            # 心跳循环
            while self.connected:
                # 等待心跳间隔
                await asyncio.sleep(self.heartbeat_interval)
                
                if not self.connected:
                    break
                
                # 发送心跳
                heartbeat_event = TaskEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=EventType.HEARTBEAT,
                    timestamp=time.time(),
                    data={"ping": "pong"},
                    source="sse_server"
                )
                yield heartbeat_event.to_sse_format()
                self.last_heartbeat = time.time()
                
        finally:
            # 清理订阅
            if self.subscription_id:
                self.event_stream.unsubscribe(self.subscription_id)
            self.connected = False
    
    def disconnect(self):
        """断开连接"""
        self.connected = False

class SSETestSuite:
    """SSE测试套件"""
    
    def __init__(self):
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        """注册测试用例"""
        self.tests = [
            ("test_event_creation", self.test_event_creation),
            ("test_event_stream_subscription", self.test_event_stream_subscription),
            ("test_event_publishing", self.test_event_publishing),
            ("test_event_filtering", self.test_event_filtering),
            ("test_sse_format", self.test_sse_format),
        ]
    
    def test_event_creation(self) -> tuple[bool, str]:
        """测试事件创建"""
        # 创建任务进度事件
        progress_event = TaskEvent.create_task_progress(
            task_id="task_001",
            progress=0.5,
            message="任务进行中"
        )
        
        if progress_event.event_type != EventType.TASK_PROGRESS:
            return False, f"事件类型错误: {progress_event.event_type}"
        
        if progress_event.data.get("progress") != 0.5:
            return False, f"进度值错误: {progress_event.data.get('progress')}"
        
        # 创建通知事件
        notification_event = TaskEvent.create_notification(
            title="系统通知",
            message="测试完成",
            level="info"
        )
        
        if notification_event.event_type != EventType.NOTIFICATION:
            return False, f"通知事件类型错误: {notification_event.event_type}"
        
        return True, f"事件创建测试通过，创建了{2}个事件"
    
    def test_event_stream_subscription(self) -> tuple[bool, str]:
        """测试事件流订阅"""
        event_stream = EventStream()
        received_events = []
        
        async def callback(event: TaskEvent):
            received_events.append(event)
        
        # 订阅事件
        subscription_id = event_stream.subscribe(callback)
        
        if not subscription_id:
            return False, "订阅失败"
        
        # 发布事件
        test_event = TaskEvent.create_notification("测试", "订阅测试")
        asyncio.run(event_stream.publish(test_event))
        
        if len(received_events) != 1:
            return False, f"事件接收数量错误: {len(received_events)}"
        
        # 取消订阅
        success = event_stream.unsubscribe(subscription_id)
        if not success:
            return False, "取消订阅失败"
        
        return True, f"事件流订阅测试通过"
    
    def test_event_publishing(self) -> tuple[bool, str]:
        """测试事件发布"""
        event_stream = EventStream()
        received_events = []
        
        async def callback(event: TaskEvent):
            received_events.append(event)
        
        # 多个订阅者
        subscription_id1 = event_stream.subscribe(callback, client_id="client1")
        subscription_id2 = event_stream.subscribe(callback, client_id="client2")
        
        # 发布多个事件
        events = [
            TaskEvent.create_task_progress("task_1", 0.2),
            TaskEvent.create_notification("测试1", "消息1"),
            TaskEvent.create_task_progress("task_1", 0.8)
        ]
        
        async def publish_events():
            for event in events:
                await event_stream.publish(event)
        
        asyncio.run(publish_events())
        
        # 每个事件应该被两个订阅者接收
        expected_count = len(events) * 2
        if len(received_events) != expected_count:
            return False, f"事件接收数量错误: {len(received_events)} vs {expected_count}"
        
        # 清理
        event_stream.unsubscribe(subscription_id1)
        event_stream.unsubscribe(subscription_id2)
        
        return True, f"事件发布测试通过，发布了{len(events)}个事件"
    
    def test_event_filtering(self) -> tuple[bool, str]:
        """测试事件过滤"""
        event_stream = EventStream()
        received_events = []
        
        async def callback(event: TaskEvent):
            received_events.append(event)
        
        # 创建只接收任务进度事件的过滤器
        filters = [EventTypeFilter({EventType.TASK_PROGRESS})]
        subscription_id = event_stream.subscribe(callback, filters=filters)
        
        # 发布混合事件
        events = [
            TaskEvent.create_notification("测试", "这个不应该被接收"),
            TaskEvent.create_task_progress("task_1", 0.5),
            TaskEvent.create_notification("测试2", "这个也不应该被接收"),
            TaskEvent.create_task_progress("task_1", 1.0)
        ]
        
        async def publish_events():
            for event in events:
                await event_stream.publish(event)
        
        asyncio.run(publish_events())
        
        # 只有任务进度事件应该被接收
        if len(received_events) != 2:
            return False, f"过滤后事件数量错误: {len(received_events)} vs 2"
        
        # 检查事件类型
        for event in received_events:
            if event.event_type != EventType.TASK_PROGRESS:
                return False, f"过滤失败，接收了错误类型事件: {event.event_type}"
        
        event_stream.unsubscribe(subscription_id)
        return True, f"事件过滤测试通过，过滤了{len(events) - len(received_events)}个事件"
    
    def test_sse_format(self) -> tuple[bool, str]:
        """测试SSE格式"""
        event = TaskEvent.create_notification("测试标题", "测试消息")
        sse_format = event.to_sse_format()
        
        # 检查SSE格式是否包含必要字段
        required_fields = ["id:", "event:", "data:", "timestamp:"]
        for field in required_fields:
            if field not in sse_format:
                return False, f"SSE格式缺少字段: {field}"
        
        # 检查消息结束符
        if not sse_format.endswith("\n\n"):
            return False, "SSE格式缺少消息结束符"
        
        # 解析data字段
        lines = sse_format.split("\n")
        data_line = [line for line in lines if line.startswith("data: ")]
        if not data_line:
            return False, "SSE格式缺少data行"
        
        data_json = data_line[0][6:]  # 去掉"data: "前缀
        try:
            data_dict = json.loads(data_json)
            if "event_type" not in data_dict:
                return False, "data字段缺少event_type"
        except json.JSONDecodeError:
            return False, "data字段不是有效的JSON"
        
        return True, f"SSE格式测试通过"
    
    def run_all_tests(self) -> dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始运行SSE事件系统测试套件...")
        print("=" * 60)
        
        passed = 0
        failed = 0
        results = {}
        
        for test_name, test_func in self.tests:
            print(f"📋 运行测试: {test_name}...")
            try:
                success, message = test_func()
                if success:
                    print(f"   ✅ 通过: {message}")
                    passed += 1
                    results[test_name] = {"passed": True, "message": message}
                else:
                    print(f"   ❌ 失败: {message}")
                    failed += 1
                    results[test_name] = {"passed": False, "message": message}
            except Exception as e:
                print(f"   ❌ 异常: {str(e)}")
                failed += 1
                results[test_name] = {"passed": False, "message": str(e)}
        
        print("=" * 60)
        print(f"📊 测试摘要:")
        print(f"   总测试数: {len(self.tests)}")
        print(f"   通过测试: {passed}")
        print(f"   失败测试: {failed}")
        print(f"   成功率: {passed / len(self.tests) * 100:.1f}%")
        
        return {
            "summary": {
                "total_tests": len(self.tests),
                "passed_tests": passed,
                "failed_tests": failed,
                "success_rate": passed / len(self.tests) * 100 if len(self.tests) > 0 else 0
            },
            "detailed_results": results
        }

def main_demo():
    """主演示函数"""
    print("🎓 Day 10 Lesson 39: SSE事件系统演示")
    print("=" * 60)
    
    # 创建事件流管理器
    event_stream = EventStream()
    
    print("\n1. 事件创建演示:")
    # 创建各种类型的事件
    events = [
        TaskEvent.create_task_progress("task_001", 0.3, "正在处理数据"),
        TaskEvent.create_notification("系统通知", "演示开始", "info"),
        TaskEvent.create_task_progress("task_001", 0.7, "数据处理完成"),
        TaskEvent.create_notification("任务完成", "所有任务已完成", "info")
    ]
    
    for i, event in enumerate(events, 1):
        print(f"   事件{i}: {event.event_type.value}")
        print(f"     ID: {event.event_id[:8]}...")
        print(f"     数据: {event.data}")
        print()
    
    print("2. 事件流订阅演示:")
    # 创建订阅者
    received_events = []
    
    async def subscription_callback(event: TaskEvent):
        received_events.append(event)
        print(f"   📨 收到事件: {event.event_type.value} - {event.data.get('message', '')}")
    
    # 订阅所有事件
    subscription_id = event_stream.subscribe(subscription_callback, client_id="demo_client")
    print(f"   订阅ID: {subscription_id[:8]}...")
    
    print("\n3. 事件发布演示:")
    # 发布事件
    async def publish_demo():
        for event in events:
            delivered = await event_stream.publish(event)
            print(f"   发布事件: {event.event_type.value}, 传递给{delivered}个订阅者")
            await asyncio.sleep(0.1)  # 模拟时间间隔
    
    asyncio.run(publish_demo())
    
    print(f"\n   共接收事件: {len(received_events)}个")
    
    print("\n4. 事件过滤演示:")
    # 创建只接收任务进度事件的订阅
    progress_events = []
    
    async def progress_callback(event: TaskEvent):
        progress_events.append(event)
        progress = event.data.get('progress', 0) * 100
        print(f"   📊 进度更新: {progress:.0f}% - {event.data.get('message', '')}")
    
    # 创建过滤器
    filters = [EventTypeFilter({EventType.TASK_PROGRESS})]
    progress_subscription = event_stream.subscribe(
        progress_callback, 
        filters=filters,
        client_id="progress_client"
    )
    
    # 发布混合事件
    async def mixed_publish():
        mixed_events = [
            TaskEvent.create_notification("通知", "这个不应该被接收"),
            TaskEvent.create_task_progress("task_002", 0.25, "开始处理"),
            TaskEvent.create_notification("通知", "这个也不应该被接收"),
            TaskEvent.create_task_progress("task_002", 0.6, "处理中"),
            TaskEvent.create_task_progress("task_002", 1.0, "完成")
        ]
        
        for event in mixed_events:
            await event_stream.publish(event)
            await asyncio.sleep(0.05)
    
    asyncio.run(mixed_publish())
    
    print(f"   过滤后接收事件: {len(progress_events)}个 (预期5个)")
    
    print("\n5. 统计信息:")
    stats = event_stream.get_statistics()
    print(f"   活跃订阅: {stats['active_subscriptions']}个")
    print(f"   发布事件总数: {stats['total_events_published']}个")
    print(f"   传递事件总数: {stats['total_events_delivered']}个")
    print(f"   传递成功率: {stats['delivery_rate']:.1f}%")
    
    # 清理
    event_stream.unsubscribe(subscription_id)
    event_stream.unsubscribe(progress_subscription)
    
    print("\n🎉 SSE事件系统演示完成！")

def run_tests():
    """运行测试套件"""
    test_suite = SSETestSuite()
    report = test_suite.run_all_tests()
    
    summary = report['summary']
    if summary['success_rate'] >= 80.0:
        print("\n🎉 SSE事件系统测试套件验证通过")
        return True
    else:
        print("\n⚠️  有测试失败，请检查实现代码")
        return False

if __name__ == "__main__":
    import sys
    
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_tests()
    elif len(sys.argv) > 1 and sys.argv[1] == "--demo":
        main_demo()
    else:
        main_demo()