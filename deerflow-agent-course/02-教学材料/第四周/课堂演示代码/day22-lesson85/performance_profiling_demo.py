#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeerFlow Python Agent架构师训练营 - 第85节课：性能分析工具 演示代码

本课程讲解性能分析工具的使用和性能优化策略。
"""

import cProfile
import pstats
import time
import asyncio
from functools import wraps
from typing import Callable, Any
import io


def timing_decorator(func: Callable) -> Callable:
    """性能计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} 执行时间: {elapsed:.4f}秒")
        return result
    return wrapper


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {}
    
    def record(self, name: str, duration: float) -> None:
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(duration)
    
    def get_stats(self, name: str) -> dict:
        if name not in self.metrics:
            return {}
        
        durations = self.metrics[name]
        return {
            "count": len(durations),
            "total": sum(durations),
            "avg": sum(durations) / len(durations),
            "min": min(durations),
            "max": max(durations)
        }


async def simulate_agent_workflow():
    """模拟Agent工作流程"""
    await asyncio.sleep(0.1)  # LLM调用
    await asyncio.sleep(0.05)  # 工具执行
    await asyncio.sleep(0.02)  # 状态更新
    return {"status": "completed"}


def profile_function(func: Callable, *args, **kwargs) -> None:
    """性能分析函数"""
    profiler = cProfile.Profile()
    profiler.enable()
    
    result = func(*args, **kwargs)
    
    profiler.disable()
    
    s = io.StringIO()
    stats = pstats.Stats(profiler, stream=s)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
    print(s.getvalue())


def main():
    print("=== 性能分析演示 ===")
    
    @timing_decorator
    def slow_function():
        time.sleep(0.1)
        return "完成"
    
    slow_function()
    
    profile_function(slow_function)


if __name__ == "__main__":
    main()
