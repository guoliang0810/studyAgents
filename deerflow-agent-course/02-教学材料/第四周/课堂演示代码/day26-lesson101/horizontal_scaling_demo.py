#!/usr/bin/env python3
# 第101节课：水平扩展架构
import threading, time, hashlib
from typing import Dict, Any, List
from dataclasses import dataclass, field

class LoadBalancer:
    def __init__(self, strategy: str = "round_robin"):
        self.strategy = strategy
        self.backends: List[str] = []
        self.current_index = 0
        self.requests: Dict[str, int] = {}
    
    def add_backend(self, backend: str) -> None:
        self.backends.append(backend)
        self.requests[backend] = 0
    
    def select(self) -> str:
        if not self.backends: return ""
        if self.strategy == "round_robin":
            backend = self.backends[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.backends)
        elif self.strategy == "least_conn":
            backend = min(self.backends, key=lambda b: self.requests[b])
        else:
            backend = self.backends[0]
        self.requests[backend] += 1
        return backend

class SessionAffinity:
    def __init__(self): self.sessions: Dict[str, str] = {}
    def get_backend(self, session_id: str, backends: List[str]) -> str:
        if session_id in self.sessions:
            return self.sessions[session_id]
        backend = hashlib.md5(session_id.encode()).hexdigest() % len(backends)
        self.sessions[session_id] = backends[backend]
        return self.sessions[session_id]

@dataclass
class ScaleConfig:
    min_replicas: int = 1
    max_replicas: int = 10
    target_cpu_percent: int = 70
    scale_up_cooldown: int = 60
    scale_down_cooldown: int = 300

class AutoScaler:
    def __init__(self, config: ScaleConfig): self.config = config; self.current_replicas = 1
    def calculate_replicas(self, cpu_percent: float) -> int:
        if cpu_percent >= self.config.target_cpu_percent * 1.5:
            return min(self.config.max_replicas, self.current_replicas + 2)
        elif cpu_percent >= self.config.target_cpu_percent:
            return min(self.config.max_replicas, self.current_replicas + 1)
        elif cpu_percent < self.config.target_cpu_percent * 0.3:
            return max(self.config.min_replicas, self.current_replicas - 1)
        return self.current_replicas

def run_demo():
    print("水平扩展架构演示")
    lb = LoadBalancer("round_robin")
    for i in range(3): lb.add_backend(f"backend-{i}")
    for _ in range(5): print(f"请求路由到: {lb.select()}")
    print(f"请求统计: {lb.requests}")
    
    scaler = AutoScaler(ScaleConfig())
    for cpu in [50, 80, 95, 60, 40]:
        replicas = scaler.calculate_replicas(cpu)
        print(f"CPU: {cpu}% -> 副本数: {replicas}")

def run_tests():
    print("测试: 负载均衡")
    lb = LoadBalancer()
    lb.add_backend("a"); lb.add_backend("b")
    assert lb.select() == "a"
    assert lb.select() == "b"
    print("✓ 负载均衡测试通过")
    
    print("测试: 自动扩缩容")
    scaler = AutoScaler(ScaleConfig(min_replicas=1, max_replicas=5))
    assert scaler.calculate_replicas(95) == 2
    assert scaler.calculate_replicas(40) == 1
    print("✓ 自动扩缩容测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
