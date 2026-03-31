#!/usr/bin/env python3
# 第108节课：性能与成本优化
import time, random
from typing import Dict, Any, List
from dataclasses import dataclass, field

@dataclass
class ResourceMetrics:
    cpu_percent: float
    memory_mb: float
    timestamp: float = field(default_factory=time.time)

class ResourceMonitor:
    def __init__(self):
        self.metrics: List[ResourceMetrics] = []
    
    def collect(self) -> ResourceMetrics:
        m = ResourceMetrics(
            cpu_percent=random.uniform(10, 50),
            memory_mb=random.uniform(256, 1024)
        )
        self.metrics.append(m)
        return m
    
    def get_average(self) -> Dict[str, float]:
        if not self.metrics:
            return {"cpu": 0, "memory": 0}
        return {
            "cpu": sum(m.cpu_percent for m in self.metrics) / len(self.metrics),
            "memory": sum(m.memory_mb for m in self.metrics) / len(self.metrics)
        }

class CostOptimizer:
    def __init__(self):
        self.strategies: List[Dict] = []
    
    def add_strategy(self, name: str, condition: callable, action: callable):
        self.strategies.append({"name": name, "condition": condition, "action": action})
    
    def optimize(self, metrics: Dict[str, float]) -> List[str]:
        actions_taken = []
        for s in self.strategies:
            if s["condition"](metrics):
                s["action"]()
                actions_taken.append(s["name"])
        return actions_taken

def run_demo():
    print("性能与成本优化演示")
    monitor = ResourceMonitor()
    for _ in range(3):
        m = monitor.collect()
        print(f"CPU: {m.cpu_percent:.1f}%, 内存: {m.memory_mb:.1f}MB")
        time.sleep(0.1)
    avg = monitor.get_average()
    print(f"平均: CPU: {avg['cpu']:.1f}%, 内存: {avg['memory']:.1f}MB")
    
    optimizer = CostOptimizer()
    optimizer.add_strategy("scale_down", lambda m: m["cpu"] < 20, lambda: print("缩减资源"))
    optimizer.add_strategy("use_cache", lambda m: m["cpu"] > 50, lambda: print("启用缓存"))
    actions = optimizer.optimize({"cpu": 15, "memory": 500})
    print(f"执行优化: {actions}")

def run_tests():
    print("测试: 资源监控")
    monitor = ResourceMonitor()
    m = monitor.collect()
    assert m.cpu_percent >= 0
    print("✓ 资源监控测试通过")
    
    print("测试: 成本优化")
    optimizer = CostOptimizer()
    triggered = []
    optimizer.add_strategy("test", lambda x: x["value"] > 10, lambda: triggered.append(True))
    optimizer.optimize({"value": 20})
    assert len(triggered) == 1
    print("✓ 成本优化测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
