#!/usr/bin/env python3
# 第88节课：监控与指标
from typing import Dict, Any
import time


class MetricsCollector:
    def __init__(self):
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, list] = {}
    
    def inc_counter(self, name: str, value: int = 1):
        self.counters[name] = self.counters.get(name, 0) + value
    
    def set_gauge(self, name: str, value: float):
        self.gauges[name] = value
    
    def observe_histogram(self, name: str, value: float):
        if name not in self.histograms:
            self.histograms[name] = []
        self.histograms[name].append(value)
    
    def get_metrics(self) -> Dict[str, Any]:
        return {
            "counters": self.counters.copy(),
            "gauges": self.gauges.copy(),
            "histograms": {k: sum(v)/len(v) for k, v in self.histograms.items()}
        }


collector = MetricsCollector()
collector.inc_counter("requests_total")
collector.set_gauge("memory_usage", 1024.5)
collector.observe_histogram("response_time", 0.25)
print(collector.get_metrics())
