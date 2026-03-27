#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 12 Lesson 47: 父子代理通信 (Parent-Child Agent Communication)

本文件演示父子代理通信系统的设计和实现，包括：
1. 通信协议 - 消息格式、序列化、消息类型
2. 同步通信 - 请求-响应模式
3. 异步通信 - 回调和事件驱动模式
4. 错误处理 - 错误传播和重试机制

使用示例:
    python parent_child_comm_demo.py          # 运行基本演示
    python parent_child_comm_demo.py --test   # 运行测试套件
    python parent_child_comm_demo.py --demo   # 运行完整演示
    python parent_child_comm_demo.py --help   # 显示帮助信息
"""

import asyncio
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Awaitable
from datetime import datetime
import uuid
import json


class MessageType(Enum):
    """消息类型枚举"""
    INSTRUCTION = "instruction"    # 指令（父→子）
    RESULT = "result"              # 结果（子→父）
    PROGRESS = "progress"          # 进度报告（子→父）
    ERROR = "error"                # 错误（双向）
    HEARTBEAT = "heartbeat"        # 心跳（双向）
    CANCEL = "cancel"              # 取消任务（父→子）
    ACK = "ack"                    # 确认（双向）


class MessageStatus(Enum):
    """消息状态枚举"""
    PENDING = "pending"        # 等待发送
    SENT = "sent"              # 已发送
    DELIVERED = "delivered"    # 已送达
    PROCESSED = "processed"    # 已处理
    FAILED = "failed"          # 失败


class CommunicationMode(Enum):
    """通信模式枚举"""
    SYNC = "sync"              # 同步（请求-响应）
    ASYNC = "async"            # 异步（回调）
    FIRE_AND_FORGET = "fire"   # 发送即忘


@dataclass
class Message:
    """通信消息"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.INSTRUCTION
    sender: str = ""                               # 发送者ID
    receiver: str = ""                             # 接收者ID
    content: Dict[str, Any] = field(default_factory=dict)  # 消息内容
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None           # 关联ID（用于请求-响应）
    reply_to: Optional[str] = None                 # 回复的消息ID
    priority: int = 1                              # 优先级（1-5）
    ttl: float = 300.0                             # 生存时间（秒）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "priority": self.priority,
            "ttl": self.ttl
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建"""
        return cls(
            message_id=data["message_id"],
            message_type=MessageType(data["message_type"]),
            sender=data["sender"],
            receiver=data["receiver"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
            priority=data.get("priority", 1),
            ttl=data.get("ttl", 300.0)
        )
    
    def create_reply(self, content: Dict[str, Any], 
                     message_type: MessageType = MessageType.RESULT) -> "Message":
        """创建回复消息"""
        return Message(
            message_type=message_type,
            sender=self.receiver,
            receiver=self.sender,
            content=content,
            correlation_id=self.correlation_id,
            reply_to=self.message_id,
            priority=self.priority
        )
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        elapsed = (datetime.now() - self.timestamp).total_seconds()
        return elapsed > self.ttl


@dataclass
class MessageEnvelope:
    """消息信封（包含传输元数据）"""
    message: Message
    status: MessageStatus = MessageStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    last_attempt: Optional[datetime] = None
    error: Optional[str] = None


class MessageQueue:
    """消息队列"""
    
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self._queues: Dict[str, List[Message]] = {}  # 按接收者分队列
        self._pending_responses: Dict[str, asyncio.Future] = {}  # 等待响应
    
    async def put(self, message: Message):
        """放入消息"""
        receiver = message.receiver
        if receiver not in self._queues:
            self._queues[receiver] = []
        
        if len(self._queues[receiver]) >= self.capacity:
            raise Exception(f"队列已满: {receiver}")
        
        self._queues[receiver].append(message)
    
    async def get(self, receiver: str, timeout: float = 30.0) -> Optional[Message]:
        """获取消息（带超时）"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            if receiver in self._queues and self._queues[receiver]:
                # 按优先级排序
                messages = self._queues[receiver]
                messages.sort(key=lambda m: m.priority, reverse=True)
                return messages.pop(0)
            
            await asyncio.sleep(0.01)
        
        return None
    
    def register_response_future(self, correlation_id: str, future: asyncio.Future):
        """注册响应Future"""
        self._pending_responses[correlation_id] = future
    
    def resolve_response(self, correlation_id: str, message: Message):
        """解析响应"""
        if correlation_id in self._pending_responses:
            future = self._pending_responses.pop(correlation_id)
            if not future.done():
                future.set_result(message)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计"""
        return {
            "queues_count": len(self._queues),
            "pending_responses": len(self._pending_responses),
            "queue_sizes": {k: len(v) for k, v in self._queues.items()}
        }


class AgentCommunication:
    """代理通信接口"""
    
    def __init__(self, agent_id: str, queue: MessageQueue):
        self.agent_id = agent_id
        self.queue = queue
        self.handlers: Dict[MessageType, Callable] = {}
        self.is_running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self.received_count = 0
        self.sent_count = 0
        self.error_count = 0
    
    def register_handler(self, message_type: MessageType, handler: Callable):
        """注册消息处理器"""
        self.handlers[message_type] = handler
    
    async def send(self, message: Message, mode: CommunicationMode = CommunicationMode.SYNC,
                   timeout: float = 30.0) -> Optional[Message]:
        """
        发送消息
        
        Args:
            message: 要发送的消息
            mode: 通信模式
            timeout: 超时时间（仅SYNC模式有效）
            
        Returns:
            响应消息（仅SYNC模式）
        """
        message.sender = self.agent_id
        self.sent_count += 1
        
        try:
            if mode == CommunicationMode.SYNC:
                return await self._send_sync(message, timeout)
            elif mode == CommunicationMode.ASYNC:
                return await self._send_async(message)
            else:  # FIRE_AND_FORGET
                return await self._send_fire_and_forget(message)
        except Exception as e:
            self.error_count += 1
            raise
    
    async def _send_sync(self, message: Message, timeout: float) -> Optional[Message]:
        """同步发送（等待响应）"""
        # 创建Future等待响应
        future = asyncio.Future()
        correlation_id = message.correlation_id or message.message_id
        message.correlation_id = correlation_id
        
        self.queue.register_response_future(correlation_id, future)
        await self.queue.put(message)
        
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            return None
    
    async def _send_async(self, message: Message) -> None:
        """异步发送（不等待响应）"""
        await self.queue.put(message)
    
    async def _send_fire_and_forget(self, message: Message) -> None:
        """发送即忘"""
        await self.queue.put(message)
    
    async def receive(self, timeout: float = 30.0) -> Optional[Message]:
        """接收消息"""
        message = await self.queue.get(self.agent_id, timeout)
        if message:
            self.received_count += 1
        return message
    
    async def handle_message(self, message: Message) -> Optional[Message]:
        """处理消息"""
        handler = self.handlers.get(message.message_type)
        
        if handler:
            try:
                result = await handler(message)
                
                # 如果是请求消息，发送响应
                if message.message_type == MessageType.INSTRUCTION and result is not None:
                    reply = message.create_reply(
                        content=result,
                        message_type=MessageType.RESULT
                    )
                    await self.send(reply, CommunicationMode.FIRE_AND_FORGET)
                
                return result
            except Exception as e:
                # 发送错误响应
                error_reply = message.create_reply(
                    content={"error": str(e)},
                    message_type=MessageType.ERROR
                )
                await self.send(error_reply, CommunicationMode.FIRE_AND_FORGET)
                raise
        else:
            logging.warning(f"未找到处理器: {message.message_type}")
            return None
    
    async def start(self, heartbeat_interval: float = 10.0):
        """启动通信（开始接收消息）"""
        self.is_running = True
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(heartbeat_interval)
        )
    
    async def stop(self):
        """停止通信"""
        self.is_running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
    
    async def _heartbeat_loop(self, interval: float):
        """心跳循环"""
        while self.is_running:
            try:
                heartbeat = Message(
                    message_type=MessageType.HEARTBEAT,
                    sender=self.agent_id,
                    receiver="system",
                    content={"status": "alive", "agent_id": self.agent_id}
                )
                await self.send(heartbeat, CommunicationMode.FIRE_AND_FORGET)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"心跳发送失败: {e}")
                await asyncio.sleep(interval)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取通信统计"""
        return {
            "agent_id": self.agent_id,
            "received_count": self.received_count,
            "sent_count": self.sent_count,
            "error_count": self.error_count,
            "is_running": self.is_running,
            "registered_handlers": list(self.handlers.keys())
        }


class ParentAgent:
    """父代理"""
    
    def __init__(self, parent_id: str, queue: MessageQueue):
        self.parent_id = parent_id
        self.comm = AgentCommunication(parent_id, queue)
        self.child_tasks: Dict[str, Dict[str, Any]] = {}  # child_id -> task info
        self.results: Dict[str, Any] = {}  # task_id -> result
    
    async def start(self):
        """启动父代理"""
        # 注册处理器
        self.comm.register_handler(MessageType.RESULT, self._handle_result)
        self.comm.register_handler(MessageType.PROGRESS, self._handle_progress)
        self.comm.register_handler(MessageType.ERROR, self._handle_error)
        
        await self.comm.start()
        logging.info(f"父代理已启动: {self.parent_id}")
    
    async def stop(self):
        """停止父代理"""
        await self.comm.stop()
        logging.info(f"父代理已停止: {self.parent_id}")
    
    async def delegate_task(self, child_id: str, task_description: str,
                            parameters: Dict[str, Any] = None) -> str:
        """委派任务给子代理"""
        message = Message(
            message_type=MessageType.INSTRUCTION,
            sender=self.parent_id,
            receiver=child_id,
            content={
                "action": "execute",
                "task_description": task_description,
                "parameters": parameters or {}
            },
            priority=3
        )
        
        # 记录任务
        self.child_tasks[child_id] = {
            "task_id": message.message_id,
            "description": task_description,
            "started_at": datetime.now()
        }
        
        # 同步发送，等待结果
        response = await self.comm.send(message, CommunicationMode.SYNC, timeout=60.0)
        
        if response:
            self.results[message.message_id] = response.content
            return f"任务完成: {response.content.get('result', 'success')}"
        else:
            return "任务超时"
    
    async def broadcast_instruction(self, child_ids: List[str], 
                                    instruction: str) -> Dict[str, str]:
        """广播指令给多个子代理"""
        results = {}
        
        for child_id in child_ids:
            message = Message(
                message_type=MessageType.INSTRUCTION,
                sender=self.parent_id,
                receiver=child_id,
                content={"action": "broadcast", "instruction": instruction}
            )
            await self.comm.send(message, CommunicationMode.FIRE_AND_FORGET)
            results[child_id] = "sent"
        
        return results
    
    async def cancel_task(self, child_id: str, task_id: str):
        """取消子代理任务"""
        message = Message(
            message_type=MessageType.CANCEL,
            sender=self.parent_id,
            receiver=child_id,
            content={"task_id": task_id}
        )
        await self.comm.send(message, CommunicationMode.FIRE_AND_FORGET)
    
    async def _handle_result(self, message: Message) -> Dict[str, Any]:
        """处理结果消息"""
        logging.info(f"收到结果来自 {message.sender}: {message.content}")
        self.results[message.reply_to] = message.content
        return {"status": "acknowledged"}
    
    async def _handle_progress(self, message: Message) -> Dict[str, Any]:
        """处理进度消息"""
        logging.info(f"进度报告来自 {message.sender}: {message.content.get('progress', 0)}%")
        return {"status": "received"}
    
    async def _handle_error(self, message: Message) -> Dict[str, Any]:
        """处理错误消息"""
        logging.error(f"错误来自 {message.sender}: {message.content.get('error', 'unknown')}")
        return {"status": "acknowledged"}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "parent_id": self.parent_id,
            "tasks_delegated": len(self.child_tasks),
            "results_received": len(self.results),
            "communication": self.comm.get_stats()
        }


class ChildAgent:
    """子代理"""
    
    def __init__(self, child_id: str, queue: MessageQueue):
        self.child_id = child_id
        self.comm = AgentCommunication(child_id, queue)
        self.current_task: Optional[str] = None
        self.completed_tasks: List[str] = []
    
    async def start(self):
        """启动子代理"""
        # 注册处理器
        self.comm.register_handler(MessageType.INSTRUCTION, self._handle_instruction)
        self.comm.register_handler(MessageType.CANCEL, self._handle_cancel)
        
        await self.comm.start()
        logging.info(f"子代理已启动: {self.child_id}")
    
    async def stop(self):
        """停止子代理"""
        await self.comm.stop()
        logging.info(f"子代理已停止: {self.child_id}")
    
    async def run_message_loop(self, duration: float = 60.0):
        """运行消息循环"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < duration:
            try:
                message = await self.comm.receive(timeout=1.0)
                if message:
                    await self.comm.handle_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logging.error(f"消息处理错误: {e}")
    
    async def _handle_instruction(self, message: Message) -> Dict[str, Any]:
        """处理指令消息"""
        content = message.content
        action = content.get("action", "")
        
        if action == "execute":
            task_desc = content.get("task_description", "")
            params = content.get("parameters", {})
            
            self.current_task = message.message_id
            
            # 模拟任务执行
            await asyncio.sleep(0.1)
            
            # 发送进度
            progress_msg = Message(
                message_type=MessageType.PROGRESS,
                sender=self.child_id,
                receiver=message.sender,
                content={"task_id": message.message_id, "progress": 50},
                reply_to=message.message_id
            )
            await self.comm.send(progress_msg, CommunicationMode.FIRE_AND_FORGET)
            
            await asyncio.sleep(0.1)
            
            # 完成任务
            self.completed_tasks.append(message.message_id)
            self.current_task = None
            
            return {
                "result": f"任务完成: {task_desc}",
                "task_id": message.message_id,
                "parameters": params
            }
        
        elif action == "broadcast":
            instruction = content.get("instruction", "")
            return {"status": "received", "instruction": instruction}
        
        return {"status": "unknown_action"}
    
    async def _handle_cancel(self, message: Message) -> Dict[str, Any]:
        """处理取消消息"""
        task_id = content.get("task_id") if (content := message.content) else None
        
        if task_id == self.current_task:
            self.current_task = None
            return {"status": "cancelled", "task_id": task_id}
        
        return {"status": "not_found", "task_id": task_id}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "child_id": self.child_id,
            "current_task": self.current_task,
            "completed_tasks": len(self.completed_tasks),
            "communication": self.comm.get_stats()
        }


class CommunicationTestSuite:
    """通信测试套件"""
    
    def __init__(self):
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        """注册测试用例"""
        self.tests = [
            ("test_message_creation", self.test_message_creation),
            ("test_message_serialization", self.test_message_serialization),
            ("test_sync_communication", self.test_sync_communication),
            ("test_async_communication", self.test_async_communication),
            ("test_error_handling", self.test_error_handling),
        ]
    
    def test_message_creation(self) -> tuple:
        """测试消息创建"""
        try:
            msg = Message(
                message_type=MessageType.INSTRUCTION,
                sender="parent",
                receiver="child",
                content={"action": "test"}
            )
            
            if msg.sender != "parent":
                return False, f"发送者不正确: {msg.sender}"
            
            if msg.message_type != MessageType.INSTRUCTION:
                return False, f"消息类型不正确: {msg.message_type}"
            
            if not msg.message_id:
                return False, "消息ID为空"
            
            # 测试创建回复
            reply = msg.create_reply(content={"result": "success"})
            
            if reply.receiver != "parent":
                return False, f"回复接收者不正确: {reply.receiver}"
            
            if reply.reply_to != msg.message_id:
                return False, f"回复关联不正确"
            
            return True, "消息创建测试通过"
        except Exception as e:
            return False, f"消息创建异常: {e}"
    
    def test_message_serialization(self) -> tuple:
        """测试消息序列化"""
        try:
            msg = Message(
                message_type=MessageType.RESULT,
                sender="child",
                receiver="parent",
                content={"data": {"value": 42}}
            )
            
            # 序列化
            data = msg.to_dict()
            
            if data["message_type"] != "result":
                return False, "序列化message_type不正确"
            
            if data["content"]["data"]["value"] != 42:
                return False, "序列化content不正确"
            
            # 反序列化
            restored = Message.from_dict(data)
            
            if restored.message_type != MessageType.RESULT:
                return False, "反序列化message_type不正确"
            
            if restored.content["data"]["value"] != 42:
                return False, "反序列化content不正确"
            
            return True, "消息序列化测试通过"
        except Exception as e:
            return False, f"消息序列化异常: {e}"
    
    def test_sync_communication(self) -> tuple:
        """测试同步通信"""
        async def run_test():
            queue = MessageQueue()
            
            # 创建父代理和子代理
            parent = ParentAgent("parent_1", queue)
            child = ChildAgent("child_1", queue)
            
            await parent.start()
            await child.start()
            
            # 启动子代理消息循环
            child_task = asyncio.create_task(child.run_message_loop(5.0))
            
            # 父代理委派任务
            result = await parent.delegate_task("child_1", "测试任务", {"param": "value"})
            
            # 验证结果
            if "任务完成" not in result:
                return False, f"任务执行失败: {result}"
            
            # 清理
            await parent.stop()
            await child.stop()
            child_task.cancel()
            
            return True, "同步通信测试通过"
        
        return asyncio.run(run_test())
    
    def test_async_communication(self) -> tuple:
        """测试异步通信"""
        async def run_test():
            queue = MessageQueue()
            
            parent_comm = AgentCommunication("parent", queue)
            child_comm = AgentCommunication("child", queue)
            
            # 注册处理器
            results = []
            
            async def handle_instruction(msg: Message) -> Dict[str, Any]:
                results.append(("instruction", msg.content))
                return {"status": "ok"}
            
            child_comm.register_handler(MessageType.INSTRUCTION, handle_instruction)
            
            await parent_comm.start()
            await child_comm.start()
            
            # 异步发送
            message = Message(
                message_type=MessageType.INSTRUCTION,
                content={"action": "test"}
            )
            await parent_comm.send(message, CommunicationMode.ASYNC)
            
            # 等待处理
            await asyncio.sleep(0.2)
            
            # 验证
            if len(results) != 1:
                return False, f"消息未处理: {len(results)}"
            
            await parent_comm.stop()
            await child_comm.stop()
            
            return True, "异步通信测试通过"
        
        return asyncio.run(run_test())
    
    def test_error_handling(self) -> tuple:
        """测试错误处理"""
        async def run_test():
            queue = MessageQueue()
            
            parent = ParentAgent("parent_err", queue)
            child = ChildAgent("child_err", queue)
            
            # 注册错误处理器
            error_received = []
            
            async def handle_error(msg: Message) -> Dict[str, Any]:
                error_received.append(msg.content)
                return {"status": "received"}
            
            parent.comm.register_handler(MessageType.ERROR, handle_error)
            
            await parent.start()
            await child.start()
            
            # 发送会导致错误的消息
            error_msg = Message(
                message_type=MessageType.INSTRUCTION,
                sender="parent_err",
                receiver="child_err",
                content={}  # 空内容可能导致处理错误
            )
            
            try:
                await parent.comm.send(error_msg, CommunicationMode.SYNC, timeout=1.0)
            except:
                pass
            
            await parent.stop()
            await child.stop()
            
            return True, "错误处理测试通过"
        
        return asyncio.run(run_test())
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始运行父子代理通信测试套件...")
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


async def main_demo():
    """主演示函数"""
    print("🎓 Day 12 Lesson 47: 父子代理通信演示")
    print("=" * 60)
    
    # 1. 创建共享消息队列
    queue = MessageQueue()
    
    # 2. 创建父代理和子代理
    print("\n1. 创建代理:")
    parent = ParentAgent("supervisor", queue)
    child1 = ChildAgent("worker_1", queue)
    child2 = ChildAgent("worker_2", queue)
    child3 = ChildAgent("worker_3", queue)
    
    print(f"   ✅ 父代理: {parent.parent_id}")
    print(f"   ✅ 子代理: {child1.child_id}, {child2.child_id}, {child3.child_id}")
    
    # 3. 启动代理
    print("\n2. 启动代理:")
    await parent.start()
    await child1.start()
    await child2.start()
    await child3.start()
    
    # 启动子代理消息循环
    child_tasks = [
        asyncio.create_task(child1.run_message_loop(30.0)),
        asyncio.create_task(child2.run_message_loop(30.0)),
        asyncio.create_task(child3.run_message_loop(30.0))
    ]
    
    print("   ✅ 所有代理已启动")
    
    # 4. 同步通信演示
    print("\n3. 同步通信演示:")
    result = await parent.delegate_task("worker_1", "分析销售数据", {"year": 2024})
    print(f"   任务1结果: {result}")
    
    result = await parent.delegate_task("worker_2", "生成报表", {"format": "PDF"})
    print(f"   任务2结果: {result}")
    
    # 5. 广播演示
    print("\n4. 广播演示:")
    results = await parent.broadcast_instruction(
        ["worker_1", "worker_2", "worker_3"],
        "准备接收新任务"
    )
    print(f"   广播结果: {results}")
    
    # 6. 通信统计
    print("\n5. 通信统计:")
    parent_stats = parent.get_stats()
    print(f"   父代理统计:")
    print(f"     委派任务: {parent_stats['tasks_delegated']}")
    print(f"     接收结果: {parent_stats['results_received']}")
    
    child1_stats = child1.get_stats()
    print(f"   子代理统计:")
    print(f"     完成任务: {child1_stats['completed_tasks']}")
    
    queue_stats = queue.get_stats()
    print(f"   队列统计:")
    print(f"     队列数量: {queue_stats['queues_count']}")
    
    # 7. 消息格式示例
    print("\n6. 消息格式示例:")
    sample_msg = Message(
        message_type=MessageType.INSTRUCTION,
        sender="supervisor",
        receiver="worker_1",
        content={"action": "execute", "task": "test"}
    )
    import json
    print(json.dumps(sample_msg.to_dict(), indent=2, ensure_ascii=False))
    
    # 8. 清理
    print("\n7. 停止代理:")
    await parent.stop()
    await child1.stop()
    await child2.stop()
    await child3.stop()
    
    for task in child_tasks:
        task.cancel()
    
    print("   ✅ 所有代理已停止")
    
    print("\n演示完成!")


def run_tests():
    """运行测试套件"""
    test_suite = CommunicationTestSuite()
    report = test_suite.run_all_tests()
    
    summary = report['summary']
    if summary['success_rate'] >= 80.0:
        print("\n🎉 父子代理通信测试套件验证通过")
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
        asyncio.run(main_demo())
    else:
        asyncio.run(main_demo())
