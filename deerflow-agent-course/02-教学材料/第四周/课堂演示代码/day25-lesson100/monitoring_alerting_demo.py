#!/usr/bin/env python3
# 第100节课：监控与告警
import time, json, threading
from typing import Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class AlertLevel(Enum):
    INFO = "info" 
    WARNING = "warning" 
    ERROR = "error" 
    CRITICAL = "critical"

@dataclass
class Metric:
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

class MetricsCollector:
    def __init__(self): self.metrics: List[Metric] = []
    def record(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        self.metrics.append(Metric(name=name, value=value, labels=labels or {}))
    def query(self, name: str) -> List[Metric]:
        return [m for m in self.metrics if m.name == name]

class AlertRule:
    def __init__(self, name: str, condition: Callable[[float], bool], level: AlertLevel):
        self.name = name
        self.condition = condition
        self.level = level
    def evaluate(self, value: float) -> bool:
        return self.condition(value)

class AlertManager:
    def __init__(self): self.rules: List[AlertRule] = [] 
    def add_rule(self, rule: AlertRule) -> None:
        self.rules.append(rule)
    def check(self, name: str, value: float) -> List[Dict]:
        triggered = []
        for rule in self.rules:
            if rule.evaluate(value):
                triggered.append({"rule": rule.name, "level": rule.level.value, "value": value})
        return triggered

class PrometheusConfig:
    def __init__(self, job_name: str = "deerflow"):
        self.job_name = job_name
        self.scrape_configs = []
    def add_scrape(self, job_name: str, endpoint: str, interval: int = 15) -> None:
        self.scrape_configs.append({"job_name": job_name, "static_configs": [{"targets": [endpoint]}], "scrape_interval": f"{interval}s"})
    def generate(self) -> str:
        config = {"global": {"scrape_interval": "15s"}, "scrape_configs": self.scrape_configs}
        return json.dumps(config, indent=2)

class GrafanaDashboard:
    def __init__(self, title: str): self.title = title; self.panels = []
    def add_panel(self, title: str, metric: str, unit: str = "short") -> None:
        self.panels.append({"title": title, "targets": [{"expr": metric}], "gridPos": {"h": 8, "w": 12}})
    def generate(self) -> Dict:
        return {"title": self.title, "panels": self.panels}

def run_demo():
    print("监控与告警演示")
    collector = MetricsCollector()
    collector.record("request_count", 100)
    collector.record("request_latency", 0.5)
    print(f"指标: {collector.query('request_count')}")
    
    am = AlertManager()
    am.add_rule(AlertRule("high_error", lambda x: x > 10, AlertLevel.ERROR))
    alerts = am.check("errors", 15)
    print(f"告警: {alerts}")
    
    pc = PrometheusConfig()
    pc.add_scrape("deerflow", "localhost:9090")
    print(f"Prometheus配置:\n{pc.generate()}")

def run_tests():
    print("测试: 指标收集")
    c = MetricsCollector()
    c.record("test", 1.0)
    assert len(c.query("test")) == 1
    print("✓ 指标收集测试通过")
    
    print("测试: 告警规则")
    am = AlertManager()
    am.add_rule(AlertRule("test", lambda x: x > 5, AlertLevel.WARNING))
    alerts = am.check("test", 10)
    assert len(alerts) == 1
    print("✓ 告警测试通过")
    
    print("测试: Prometheus配置")
    pc = PrometheusConfig()
    pc.add_scrape("test", "localhost:9090")
    config = json.loads(pc.generate())
    assert len(config["scrape_configs"]) == 1
    print("✓ Prometheus配置测试通过")
    
    print("测试: Grafana面板")
    gd = GrafanaDashboard("Test")
    gd.add_panel("Requests", "rate(requests_total[5m])")
    assert len(gd.panels) == 1
    print("✓ Grafana测试通过")
    print("所有测试通过!")

if __name__ == "__main__":
    import sys
    run_tests() if "--test" in sys.argv else run_demo()
