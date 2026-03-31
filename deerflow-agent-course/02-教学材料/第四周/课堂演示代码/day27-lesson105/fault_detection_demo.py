#!/usr/bin/env python3
# 第105节课：故障检测与恢复
import time, threading
from typing import Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheck:
    name: str
    check_fn: Callable[[], bool]
    interval: int = 30
    timeout: int = 5
    failure_threshold: int = 3

class HealthMonitor:
    def __init__(self):
        self.checks: dict = {}
        self.failures: dict = {}
        self.statuses: dict = {}
    def register(self, check: HealthCheck) -> None:
        self.checks[check.name] = check
        self.failures[check.name] = 0
    def check(self, name: str) -> HealthStatus:
        if name not in self.checks: return HealthStatus.UNHEALTHY
        try:
            result = self.checks[name].check_fn()
            if result:
                self.failures[name] = 0
                self.statuses[name] = HealthStatus.HEALTHY
            else:
                self.failures[name] += 1
                self.statuses[name] = HealthStatus.UNHEALTHY
        except:
            self.failures[name] += 1
            self.statuses[name] = HealthStatus.UNHEALTHY
        return self.statuses[name]
    def get_status(self) -> dict:
        return {name: status.value for name, status in self.statuses.items()}

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"
    def call(self, fn: Callable, *args, **kwargs) -> Any:
        if self.state == "open":
            if self.last_failure_time and datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = "half-open"
            else:
                raise RuntimeError("Circuit breaker is OPEN")
        try:
            result = fn(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = datetime.now()
            if self.failures >= self.failure_threshold:
                self.state = "open"
            raise

def run_demo():
    print("故障检测演示")
    monitor = HealthMonitor()
    monitor.register(HealthCheck("service_a", lambda: True))
    monitor.register(HealthCheck("service_b", lambda: False))
    print(f"检查结果: {monitor.get_status()}")
    
    cb = CircuitBreaker(failure_threshold=3)
    for i in range(5):
        try:
            cb.call(lambda: (_ for _ in ()).throw(Exception("fail")))
        except:
            print(f"调用{i+1}失败, 状态: {cb.state}")

def run_tests():
    print("测试: 健康监控")
    m = HealthMonitor()
    m.register(HealthCheck("test", lambda: True))
    assert m.check("test") == HealthStatus.HEALTHY
    m.register(HealthCheck("fail", lambda: False))
    m.check("fail")
    assert m.check("fail") == HealthStatus.UNHEALTHY
    print("✓ 健康监控测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
