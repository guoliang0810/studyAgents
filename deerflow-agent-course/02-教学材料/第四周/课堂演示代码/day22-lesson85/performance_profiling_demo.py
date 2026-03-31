#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能分析工具 - 演示代码

本模块展示AI Agent系统的性能分析工具和优化策略。
包含：cProfile性能分析、火焰图生成、性能监控上下文管理器。

本代码是DeerFlow架构师训练营第85节课的演示代码，
帮助学员掌握性能分析的核心技能。

作者: DeerFlow架构师训练营
"""

import cProfile
import pstats
import time
import asyncio
from functools import wraps
from typing import Callable, Any, Dict, List, Optional
from dataclasses import dataclass, field
from contextlib import contextmanager
from pathlib import Path
import io
import sys


# ============================================================================
# 第一部分：性能指标定义
# ============================================================================

@dataclass
class PerformanceMetrics:
    """性能指标数据类
    
    存储系统性能相关的各项指标
    """
    response_time: float           # 响应时间（毫秒）
    throughput: float              # 吞吐量（请求/秒）
    error_rate: float              # 错误率
    cpu_usage: float               # CPU使用率
    memory_usage: float            # 内存使用（MB）
    latency_p50: float             # P50延迟
    latency_p95: float             # P95延迟
    latency_p99: float             # P99延迟
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            "response_time_ms": self.response_time,
            "throughput_rps": self.throughput,
            "error_rate": self.error_rate,
            "cpu_usage_pct": self.cpu_usage,
            "memory_usage_mb": self.memory_usage,
            "latency_p50_ms": self.latency_p50,
            "latency_p95_ms": self.latency_p95,
            "latency_p99_ms": self.latency_p99
        }


class AgentPerformanceBottleneck:
    """AI Agent性能瓶颈分类
    
    识别AI Agent系统中的常见性能瓶颈
    """
    
    # 瓶颈类型及其特征
    BOTTLENECK_TYPES = {
        "llm_api": {
            "name": "LLM API调用",
            "symptoms": ["网络延迟高", "API限流", "Token消耗大"],
            "optimization": ["缓存响应", "批量请求", "流式处理"]
        },
        "tool_execution": {
            "name": "工具执行",
            "symptoms": ["执行时间长", "并发受限", "资源占用高"],
            "optimization": ["异步执行", "连接池", "超时控制"]
        },
        "state_management": {
            "name": "状态管理",
            "symptoms": ["内存增长", "序列化慢", "状态丢失"],
            "optimization": ["增量更新", "压缩存储", "定期清理"]
        },
        "middleware_chain": {
            "name": "中间件链",
            "symptoms": ["链路延迟", "顺序阻塞", "重复处理"],
            "optimization": ["并行执行", "短路优化", "结果复用"]
        },
        "vector_database": {
            "name": "向量数据库",
            "symptoms": ["查询慢", "索引大", "召回率低"],
            "optimization": ["索引优化", "分层检索", "近似搜索"]
        }
    }
    
    @classmethod
    def get_bottleneck_info(cls, bottleneck_type: str) -> Optional[Dict]:
        """获取瓶颈类型信息"""
        return cls.BOTTLENECK_TYPES.get(bottleneck_type)


# ============================================================================
# 第二部分：性能分析工具
# ============================================================================

def timing_decorator(func: Callable) -> Callable:
    """性能计时装饰器
    
    自动测量函数执行时间并打印结果
    
    使用示例:
        @timing_decorator
        def my_function():
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"[性能] {func.__name__} 执行时间: {elapsed*1000:.2f}毫秒")
        return result
    return wrapper


class PerformanceMonitor:
    """性能监控器
    
    收集和统计性能指标，支持多次调用
    
    使用示例:
        monitor = PerformanceMonitor()
        
        with monitor.measure("operation1"):
            # 执行操作
            pass
        
        stats = monitor.get_stats()
        print(stats)
    """
    
    def __init__(self):
        self.measurements: Dict[str, List[float]] = {}
    
    @contextmanager
    def measure(self, operation_name: str):
        """上下文管理器，测量操作执行时间
        
        Args:
            operation_name: 操作名称
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = (time.perf_counter() - start) * 1000  # 转换为毫秒
            if operation_name not in self.measurements:
                self.measurements[operation_name] = []
            self.measurements[operation_name].append(duration)
    
    def record(self, operation_name: str, duration_ms: float):
        """手动记录执行时间
        
        Args:
            operation_name: 操作名称
            duration_ms: 执行时间（毫秒）
        """
        if operation_name not in self.measurements:
            self.measurements[operation_name] = []
        self.measurements[operation_name].append(duration_ms)
    
    def get_stats(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息
        
        Args:
            operation_name: 操作名称，None表示所有操作
            
        Returns:
            统计信息字典
        """
        if operation_name:
            durations = self.measurements.get(operation_name, [])
            return self._calculate_stats(operation_name, durations)
        
        return {
            name: self._calculate_stats(name, durations)
            for name, durations in self.measurements.items()
        }
    
    def _calculate_stats(self, name: str, durations: List[float]) -> Dict[str, Any]:
        """计算统计数据"""
        if not durations:
            return {}
        
        sorted_durations = sorted(durations)
        n = len(sorted_durations)
        
        return {
            "count": n,
            "total_ms": sum(durations),
            "avg_ms": sum(durations) / n,
            "min_ms": min(durations),
            "max_ms": max(durations),
            "p50_ms": sorted_durations[int(n * 0.5)],
            "p95_ms": sorted_durations[int(n * 0.95)] if n > 1 else sorted_durations[0],
            "p99_ms": sorted_durations[int(n * 0.99)] if n > 1 else sorted_durations[0]
        }
    
    def print_report(self):
        """打印性能报告"""
        print("\n" + "=" * 70)
        print("性能分析报告")
        print("=" * 70)
        
        stats = self.get_stats()
        for operation, data in stats.items():
            print(f"\n操作: {operation}")
            print(f"  调用次数: {data['count']}")
            print(f"  平均耗时: {data['avg_ms']:.2f}毫秒")
            print(f"  最小耗时: {data['min_ms']:.2f}毫秒")
            print(f"  最大耗时: {data['max_ms']:.2f}毫秒")
            print(f"  P50延迟: {data['p50_ms']:.2f}毫秒")
            print(f"  P95延迟: {data['p95_ms']:.2f}毫秒")
            print(f"  P99延迟: {data['p99_ms']:.2f}毫秒")
        
        print("\n" + "=" * 70)


class ProfilerContext:
    """性能分析上下文管理器
    
    使用cProfile进行性能分析，支持输出控制
    
    使用示例:
        with ProfilerContext() as profiler:
            # 执行待分析的代码
            pass
        
        profiler.print_stats(20)
    """
    
    def __init__(self, sort_by: str = 'cumulative', limit: int = 20):
        self.profiler = cProfile.Profile()
        self.sort_by = sort_by
        self.limit = limit
        self.output = io.StringIO()
    
    def __enter__(self):
        self.profiler.enable()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.profiler.disable()
        return False
    
    def print_stats(self, limit: Optional[int] = None):
        """打印性能统计
        
        Args:
            limit: 显示的函数数量
        """
        stats = pstats.Stats(self.profiler, stream=self.output)
        stats.sort_stats(self.sort_by)
        stats.print_stats(limit or self.limit)
        print(self.output.getvalue())
    
    def save_stats(self, filename: str):
        """保存性能数据到文件
        
        Args:
            filename: 文件路径
        """
        stats = pstats.Stats(self.profiler)
        stats.dump_stats(filename)
        print(f"性能数据已保存到: {filename}")


# ============================================================================
# 第三部分：异步性能分析
# ============================================================================

class AsyncPerformanceMonitor:
    """异步性能监控器
    
    专门用于监控异步操作的性能
    """
    
    def __init__(self):
        self.tasks: Dict[str, float] = {}
    
    @contextmanager
    async def track(self, task_name: str):
        """跟踪异步任务执行时间
        
        Args:
            task_name: 任务名称
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self.tasks[task_name] = duration
    
    def get_task_time(self, task_name: str) -> Optional[float]:
        """获取任务执行时间"""
        return self.tasks.get(task_name)
    
    def get_all_tasks(self) -> Dict[str, float]:
        """获取所有任务执行时间"""
        return self.tasks.copy()


async def simulate_llm_call(prompt: str) -> str:
    """模拟LLM API调用
    
    Args:
        prompt: 输入提示词
        
    Returns:
        LLM响应文本
    """
    await asyncio.sleep(0.1)  # 模拟网络延迟
    return f"响应: {prompt}"


async def simulate_tool_execution(tool_name: str) -> dict:
    """模拟工具执行
    
    Args:
        tool_name: 工具名称
        
    Returns:
        工具执行结果
    """
    await asyncio.sleep(0.05)  # 模拟工具执行
    return {"status": "success", "tool": tool_name}


async def simulate_state_update(state: dict) -> dict:
    """模拟状态更新
    
    Args:
        state: 状态字典
        
    Returns:
        更新后的状态
    """
    await asyncio.sleep(0.02)  # 模拟状态更新
    state["timestamp"] = time.time()
    return state


async def agent_workflow(monitor: AsyncPerformanceMonitor):
    """模拟Agent工作流程
    
    展示异步性能监控的使用
    """
    # LLM调用
    async with monitor.track("llm_call"):
        response = await simulate_llm_call("你好")
    
    # 工具执行
    async with monitor.track("tool_execution"):
        tool_result = await simulate_tool_execution("search")
    
    # 状态更新
    async with monitor.track("state_update"):
        state = await simulate_state_update({"response": response})
    
    return state


# ============================================================================
# 第四部分：性能优化示例
# ============================================================================

class PerformanceOptimizer:
    """性能优化器
    
    提供常见的性能优化策略和实现
    """
    
    @staticmethod
    def optimize_with_cache(cache: Dict, key_func: Callable = None):
        """缓存优化装饰器
        
        Args:
            cache: 缓存字典
            key_func: 缓存键生成函数
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成缓存键
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = str(args) + str(kwargs)
                
                # 检查缓存
                if cache_key in cache:
                    return cache[cache_key]
                
                # 执行函数
                result = func(*args, **kwargs)
                
                # 保存到缓存
                cache[cache_key] = result
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def optimize_with_batch(batch_size: int = 10):
        """批量处理优化装饰器
        
        Args:
            batch_size: 批处理大小
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 简化实现，实际应使用队列
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    async def optimize_async_parallel(tasks: List[Callable]):
        """异步并行执行优化
        
        Args:
            tasks: 异步任务列表
            
        Returns:
            所有任务的结果列表
        """
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results


# ============================================================================
# 演示代码
# ============================================================================

def run_performance_demo():
    """运行性能分析演示"""
    print("=" * 70)
    print("DeerFlow性能分析工具演示")
    print("=" * 70)
    
    # 1. 性能监控器演示
    print("\n### 1. 性能监控器演示")
    monitor = PerformanceMonitor()
    
    # 模拟多次操作
    for i in range(10):
        with monitor.measure("llm_call"):
            time.sleep(0.01)  # 模拟LLM调用
    
    for i in range(5):
        with monitor.measure("tool_execution"):
            time.sleep(0.005)  # 模拟工具执行
    
    monitor.print_report()
    
    # 2. cProfile演示
    print("\n### 2. cProfile性能分析演示")
    
    def sample_function():
        """示例函数"""
        result = []
        for i in range(1000):
            result.append(i * i)
        return sum(result)
    
    with ProfilerContext(sort_by='cumulative', limit=15) as profiler:
        for _ in range(100):
            sample_function()
    
    profiler.print_stats(10)
    
    # 3. 异步性能监控演示
    print("\n### 3. 异步性能监控演示")
    
    async def run_async_demo():
        monitor = AsyncPerformanceMonitor()
        
        # 运行多次工作流
        for _ in range(3):
            await agent_workflow(monitor)
        
        # 打印结果
        print("\n异步任务执行时间:")
        for task, duration in monitor.get_all_tasks().items():
            print(f"  {task}: {duration*1000:.2f}毫秒")
    
    asyncio.run(run_async_demo())
    
    # 4. 性能瓶颈识别演示
    print("\n### 4. AI Agent性能瓶颈识别")
    
    bottleneck = AgentPerformanceBottleneck()
    for bottleneck_type, info in AgentPerformanceBottleneck.BOTTLENECK_TYPES.items():
        print(f"\n瓶颈类型: {info['name']}")
        print(f"  症状: {', '.join(info['symptoms'])}")
        print(f"  优化: {', '.join(info['optimization'])}")
    
    print("\n" + "=" * 70)
    print("演示完成")
    print("=" * 70)


if __name__ == "__main__":
    run_performance_demo()
