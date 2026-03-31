#!/usr/bin/env python3
# 第102节课：消息队列集成
import time, threading, json
from typing import Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class MessagePriority(Enum): 
    LOW = 1 
    NORMAL = 2 
    HIGH = 3

@dataclass
class Message:
    id: str
    payload: Any
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)

class MessageQueue:
    def __init__(self, name: str): self.name = name; self.messages: List[Message] = []
    def publish(self, msg: Message) -> None:
        self.messages.append(msg)
        self.messages.sort(key=lambda m: m.priority.value, reverse=True)
    def consume(self) -> Message:
        return self.messages.pop(0) if self.messages else None

class WorkerPool:
    def __init__(self, workers: int): self.workers = workers; self.queue = MessageQueue("pool"); self.running = False
    def start(self, handler: Callable) -> None:
        self.running = True
        for _ in range(self.workers):
            t = threading.Thread(target=self._worker, args=(handler,))
            t.start()
    def _worker(self, handler: Callable) -> None:
        while self.running:
            msg = self.queue.consume()
            if msg: handler(msg)
            time.sleep(0.01)
    def stop(self) -> None:
        self.running = False

def run_demo():
    print("消息队列演示")
    q = MessageQueue("tasks")
    q.publish(Message("1", {"task": "A"}, MessagePriority.HIGH))
    q.publish(Message("2", {"task": "B"}, MessagePriority.LOW))
    q.publish(Message("3", {"task": "C"}, MessagePriority.NORMAL))
    print("消息按优先级消费:")
    while True:
        msg = q.consume()
        if not msg: break
        print(f"  {msg.id}: {msg.payload}")

def run_tests():
    print("测试: 消息队列")
    q = MessageQueue("test")
    q.publish(Message("1", "low", MessagePriority.LOW))
    q.publish(Message("2", "high", MessagePriority.HIGH))
    msg = q.consume()
    assert msg.payload == "high"
    print("✓ 消息队列测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
