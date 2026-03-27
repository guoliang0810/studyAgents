#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 12 Lesson 48: 子代理性能优化 (Subagent Performance Optimization)

本文件演示子代理性能优化系统的设计和实现，包括：
1. 性能监控 - 执行时间、成功率、资源使用监控
2. 优化策略 - 预加载、连接池、缓存、并行执行
3. 性能评分 - 多因素加权评分算法
4. 瓶颈识别 - 自动识别性能瓶颈并建议优化

使用示例:
    python subagent_perf_demo.py          # 运行基本演示
    python subagent_perf_demo.py --test   # 运行测试套件
    python subagent_perf_demo.py --demo   # 运行完整演示
    python subagent_perf_demo.py --help   # 显示帮助信息
"""

import asyncio
import logging
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import hashlib
import json


class MetricType(Enum):
    """指标类型枚举"""
    EXECUTION_TIME = "execution_time"      # 执行时间
    SUCCESS_RATE = "success_rate"          # 成功率
    MEMORY_USAGE = "memory_usage"          # 内存使用
    CPU_USAGE = "cpu_usage"                # CPU使用
    QUEUE_LENGTH = "queue_length"          # 队列长度
    ERROR_COUNT = "error_count"            # 错误计数


class OptimizationStrategy(Enum):
    """优化策略枚举"""
    PRELOAD = "preload"                    # 预加载
    CONNECTION_POOL = "connection_pool"    # 连接池
    CACHING = "caching"                    # 缓存
    PARALLEL = "parallel"                  # 并行执行
    BATCH = "batch"                        # 批量处理
    LAZY_LOAD = "lazy_load"               # 延迟加载


@dataclass
class MetricRecord:
    """指标记录"""
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """性能指标集合"""
    agent_id: str
    execution_times: List[float] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    queue_length: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        total = self.success_count + self.failure_count
        return (self.success_count / total * 100) if total > 0 else 0.0
    
    def get_avg_execution_time(self) -> float:
        """获取平均执行时间"""
        return sum(self.execution_times) / len(self.execution_times) if self.execution_times else 0.0
    
    def get_p95_execution_time(self) -> float:
        """获取P95执行时间"""
        if not self.execution_times:
            return 0.0
        sorted_times = sorted(self.execution_times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[min(index, len(sorted_times) - 1)]


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.metric_history: Dict[str, deque] = {}
        
        # 权重配置
        self.weights = {
            "success_rate": 0.40,       # 成功率权重
            "execution_time": 0.30,     # 执行时间权重
            "memory_usage": 0.15,       # 内存权重
            "queue_efficiency": 0.15,   # 队列效率权重
        }
    
    def register_agent(self, agent_id: str):
        """注册代理"""
        self.metrics[agent_id] = PerformanceMetrics(agent_id=agent_id)
        self.metric_history[agent_id] = deque(maxlen=self.window_size)
        logging.info(f"代理已注册监控: {agent_id}")
    
    def record_execution(self, agent_id: str, execution_time: float, success: bool):
        """记录执行指标"""
        if agent_id not in self.metrics:
            self.register_agent(agent_id)
        
        metrics = self.metrics[agent_id]
        metrics.execution_times.append(execution_time)
        
        # 保持滑动窗口
        if len(metrics.execution_times) > self.window_size:
            metrics.execution_times.pop(0)
        
        if success:
            metrics.success_count += 1
        else:
            metrics.failure_count += 1
        
        metrics.last_updated = datetime.now()
        
        # 记录历史
        self.metric_history[agent_id].append(MetricRecord(
            metric_type=MetricType.EXECUTION_TIME,
            value=execution_time,
            metadata={"success": success}
        ))
    
    def record_resource_usage(self, agent_id: str, memory_mb: float, cpu_percent: float):
        """记录资源使用"""
        if agent_id not in self.metrics:
            self.register_agent(agent_id)
        
        metrics = self.metrics[agent_id]
        metrics.memory_usage_mb = memory_mb
        metrics.cpu_usage_percent = cpu_percent
        metrics.last_updated = datetime.now()
    
    def record_queue_length(self, agent_id: str, length: int):
        """记录队列长度"""
        if agent_id not in self.metrics:
            self.register_agent(agent_id)
        
        self.metrics[agent_id].queue_length = length
    
    def get_performance_score(self, agent_id: str) -> float:
        """
        获取性能综合评分（0-100）
        
        使用加权评分算法:
        - 成功率: 40% (越高越好)
        - 执行时间: 30% (越低越好)
        - 内存使用: 15% (越低越好)
        - 队列效率: 15% (队列越短越好)
        """
        if agent_id not in self.metrics:
            return 0.0
        
        metrics = self.metrics[agent_id]
        
        # 1. 成功率得分（0-100）
        success_score = metrics.get_success_rate()
        
        # 2. 执行时间得分（归一化，时间越短得分越高）
        avg_time = metrics.get_avg_execution_time()
        # 假设基准执行时间为1秒，超过2秒得分为0
        time_score = max(0, min(100, (2.0 - avg_time) * 100))
        
        # 3. 内存使用得分（归一化，内存越少得分越高）
        # 假设基准内存为100MB，超过500MB得分为0
        memory_score = max(0, min(100, (500 - metrics.memory_usage_mb) / 4))
        
        # 4. 队列效率得分（归一化，队列越短得分越高）
        # 假设队列长度为0得100分，超过50得0分
        queue_score = max(0, min(100, (50 - metrics.queue_length) * 2))
        
        # 加权总分
        total_score = (
            self.weights["success_rate"] * success_score +
            self.weights["execution_time"] * time_score +
            self.weights["memory_usage"] * memory_score +
            self.weights["queue_efficiency"] * queue_score
        )
        
        return max(0, min(100, total_score))
    
    def get_agent_report(self, agent_id: str) -> Dict[str, Any]:
        """获取代理性能报告"""
        if agent_id not in self.metrics:
            return {}
        
        metrics = self.metrics[agent_id]
        score = self.get_performance_score(agent_id)
        
        return {
            "agent_id": agent_id,
            "performance_score": round(score, 2),
            "success_rate": round(metrics.get_success_rate(), 2),
            "avg_execution_time": round(metrics.get_avg_execution_time(), 3),
            "p95_execution_time": round(metrics.get_p95_execution_time(), 3),
            "total_executions": metrics.success_count + metrics.failure_count,
            "memory_usage_mb": round(metrics.memory_usage_mb, 2),
            "cpu_usage_percent": round(metrics.cpu_usage_percent, 2),
            "queue_length": metrics.queue_length,
            "last_updated": metrics.last_updated.isoformat()
        }
    
    def get_bottleneck_analysis(self, agent_id: str) -> List[Dict[str, Any]]:
        """分析性能瓶颈"""
        if agent_id not in self.metrics:
            return []
        
        bottlenecks = []
        metrics = self.metrics[agent_id]
        
        # 检查成功率
        success_rate = metrics.get_success_rate()
        if success_rate < 80:
            bottlenecks.append({
                "type": "low_success_rate",
                "severity": "high" if success_rate < 50 else "medium",
                "current_value": f"{success_rate:.1f}%",
                "threshold": "80%",
                "suggestion": "检查错误日志，分析失败原因"
            })
        
        # 检查执行时间
        p95_time = metrics.get_p95_execution_time()
        if p95_time > 5.0:
            bottlenecks.append({
                "type": "high_latency",
                "severity": "high" if p95_time > 10 else "medium",
                "current_value": f"{p95_time:.2f}s",
                "threshold": "5.0s",
                "suggestion": "考虑启用缓存或优化算法"
            })
        
        # 检查内存使用
        if metrics.memory_usage_mb > 400:
            bottlenecks.append({
                "type": "high_memory",
                "severity": "high" if metrics.memory_usage_mb > 800 else "medium",
                "current_value": f"{metrics.memory_usage_mb:.1f}MB",
                "threshold": "400MB",
                "suggestion": "检查内存泄漏，考虑资源池"
            })
        
        # 检查队列长度
        if metrics.queue_length > 20:
            bottlenecks.append({
                "type": "queue_backlog",
                "severity": "high" if metrics.queue_length > 50 else "medium",
                "current_value": str(metrics.queue_length),
                "threshold": "20",
                "suggestion": "增加并行处理能力或优化任务调度"
            })
        
        return bottlenecks
    
    def get_global_report(self) -> Dict[str, Any]:
        """获取全局性能报告"""
        if not self.metrics:
            return {"agents": {}, "summary": {}}
        
        reports = {}
        total_score = 0
        
        for agent_id in self.metrics:
            report = self.get_agent_report(agent_id)
            reports[agent_id] = report
            total_score += report["performance_score"]
        
        avg_score = total_score / len(self.metrics)
        
        return {
            "agents": reports,
            "summary": {
                "total_agents": len(self.metrics),
                "avg_performance_score": round(avg_score, 2),
                "best_agent": max(reports.items(), key=lambda x: x[1]["performance_score"])[0],
                "worst_agent": min(reports.items(), key=lambda x: x[1]["performance_score"])[0]
            }
        }


class ConnectionPool:
    """连接池"""
    
    def __init__(self, max_size: int = 10, timeout: float = 30.0):
        self.max_size = max_size
        self.timeout = timeout
        self._pool: List[Any] = []
        self._in_use: set = set()
        self._created_count = 0
        self._acquire_count = 0
        self._release_count = 0
    
    async def acquire(self) -> Any:
        """获取连接"""
        start_time = time.time()
        
        while (time.time() - start_time) < self.timeout:
            # 尝试从池中获取
            if self._pool:
                conn = self._pool.pop()
                self._in_use.add(id(conn))
                self._acquire_count += 1
                return conn
            
            # 创建新连接
            if len(self._in_use) < self.max_size:
                conn = await self._create_connection()
                self._in_use.add(id(conn))
                self._created_count += 1
                self._acquire_count += 1
                return conn
            
            # 等待释放
            await asyncio.sleep(0.1)
        
        raise Exception("获取连接超时")
    
    async def release(self, conn: Any):
        """释放连接"""
        conn_id = id(conn)
        if conn_id in self._in_use:
            self._in_use.remove(conn_id)
            self._pool.append(conn)
            self._release_count += 1
    
    async def _create_connection(self) -> Any:
        """创建新连接（模拟）"""
        await asyncio.sleep(0.01)  # 模拟连接创建延迟
        return {"connection_id": f"conn_{len(self._pool) + len(self._in_use)}", "created_at": time.time()}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计"""
        return {
            "pool_size": len(self._pool),
            "in_use": len(self._in_use),
            "max_size": self.max_size,
            "created_count": self._created_count,
            "acquire_count": self._acquire_count,
            "release_count": self._release_count,
            "utilization": len(self._in_use) / self.max_size * 100 if self.max_size > 0 else 0
        }


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: float = 300.0):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, timestamp)
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key in self._cache:
            value, timestamp = self._cache[key]
            # 检查是否过期
            if time.time() - timestamp < self.ttl_seconds:
                self._hits += 1
                return value
            else:
                # 过期，删除
                del self._cache[key]
        
        self._misses += 1
        return None
    
    def set(self, key: str, value: Any):
        """设置缓存"""
        # 清理过期条目
        self._cleanup_expired()
        
        # 如果缓存满了，删除最旧的
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        
        self._cache[key] = (value, time.time())
    
    def _cleanup_expired(self):
        """清理过期条目"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp >= self.ttl_seconds
        ]
        for key in expired_keys:
            del self._cache[key]
    
    def invalidate(self, key: str):
        """使缓存失效"""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "ttl_seconds": self.ttl_seconds
        }


class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.connection_pools: Dict[str, ConnectionPool] = {}
        self.caches: Dict[str, CacheManager] = {}
        self.applied_strategies: Dict[str, List[OptimizationStrategy]] = {}
    
    def create_connection_pool(self, pool_name: str, max_size: int = 10) -> ConnectionPool:
        """创建连接池"""
        pool = ConnectionPool(max_size=max_size)
        self.connection_pools[pool_name] = pool
        logging.info(f"连接池已创建: {pool_name} (max_size={max_size})")
        return pool
    
    def create_cache(self, cache_name: str, max_size: int = 1000, ttl: float = 300.0) -> CacheManager:
        """创建缓存"""
        cache = CacheManager(max_size=max_size, ttl_seconds=ttl)
        self.caches[cache_name] = cache
        logging.info(f"缓存已创建: {cache_name} (max_size={max_size}, ttl={ttl}s)")
        return cache
    
    async def execute_with_optimization(self, agent_id: str, task_func: callable,
                                        use_cache: bool = True,
                                        cache_key: Optional[str] = None) -> Any:
        """带优化的执行"""
        start_time = time.time()
        
        # 尝试从缓存获取
        if use_cache and cache_key and agent_id in self.caches:
            cached = self.caches[agent_id].get(cache_key)
            if cached is not None:
                self.monitor.record_execution(agent_id, 0.001, True)
                return cached
        
        try:
            # 执行任务
            result = await task_func()
            execution_time = time.time() - start_time
            
            # 记录成功
            self.monitor.record_execution(agent_id, execution_time, True)
            
            # 更新缓存
            if use_cache and cache_key and agent_id in self.caches:
                self.caches[agent_id].set(cache_key, result)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.monitor.record_execution(agent_id, execution_time, False)
            raise
    
    async def execute_parallel(self, agent_id: str, tasks: List[callable]) -> List[Any]:
        """并行执行多个任务"""
        start_time = time.time()
        
        try:
            results = await asyncio.gather(*[task() for task in tasks])
            execution_time = time.time() - start_time
            self.monitor.record_execution(agent_id, execution_time, True)
            return results
        except Exception as e:
            execution_time = time.time() - start_time
            self.monitor.record_execution(agent_id, execution_time, False)
            raise
    
    def get_optimization_suggestions(self, agent_id: str) -> List[Dict[str, Any]]:
        """获取优化建议"""
        suggestions = []
        
        # 获取瓶颈分析
        bottlenecks = self.monitor.get_bottleneck_analysis(agent_id)
        
        for bottleneck in bottlenecks:
            if bottleneck["type"] == "high_latency":
                suggestions.append({
                    "strategy": OptimizationStrategy.CACHING.value,
                    "reason": "执行时间过长",
                    "expected_improvement": "减少30-50%重复计算时间",
                    "implementation": "启用结果缓存，设置合理的TTL"
                })
            
            elif bottleneck["type"] == "queue_backlog":
                suggestions.append({
                    "strategy": OptimizationStrategy.PARALLEL.value,
                    "reason": "队列积压",
                    "expected_improvement": "提高2-3倍吞吐量",
                    "implementation": "启用并行执行，增加工作线程"
                })
            
            elif bottleneck["type"] == "high_memory":
                suggestions.append({
                    "strategy": OptimizationStrategy.LAZY_LOAD.value,
                    "reason": "内存使用过高",
                    "expected_improvement": "减少30-50%内存占用",
                    "implementation": "启用延迟加载，及时释放资源"
                })
        
        return suggestions
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """获取优化报告"""
        return {
            "monitor": self.monitor.get_global_report(),
            "connection_pools": {
                name: pool.get_stats() for name, pool in self.connection_pools.items()
            },
            "caches": {
                name: cache.get_stats() for name, cache in self.caches.items()
            }
        }


class PerformanceTestSuite:
    """性能测试套件"""
    
    def __init__(self):
        self.tests = []
        self._register_tests()
    
    def _register_tests(self):
        """注册测试用例"""
        self.tests = [
            ("test_performance_monitor", self.test_performance_monitor),
            ("test_connection_pool", self.test_connection_pool),
            ("test_cache_manager", self.test_cache_manager),
            ("test_bottleneck_analysis", self.test_bottleneck_analysis),
            ("test_optimization_suggestions", self.test_optimization_suggestions),
        ]
    
    def test_performance_monitor(self) -> tuple:
        """测试性能监控器"""
        try:
            monitor = PerformanceMonitor()
            monitor.register_agent("test_agent")
            
            # 记录执行指标
            monitor.record_execution("test_agent", 0.5, True)
            monitor.record_execution("test_agent", 0.8, True)
            monitor.record_execution("test_agent", 1.2, False)
            
            # 记录资源使用
            monitor.record_resource_usage("test_agent", 150.0, 35.0)
            
            # 获取性能评分
            score = monitor.get_performance_score("test_agent")
            
            if score <= 0 or score > 100:
                return False, f"性能评分超出范围: {score}"
            
            # 获取报告
            report = monitor.get_agent_report("test_agent")
            
            if report["total_executions"] != 3:
                return False, f"执行次数不正确: {report['total_executions']}"
            
            if report["success_rate"] != 66.67:  # 2/3 * 100
                return False, f"成功率不正确: {report['success_rate']}"
            
            return True, f"性能监控器测试通过 (评分: {score:.2f})"
        except Exception as e:
            return False, f"性能监控器异常: {e}"
    
    def test_connection_pool(self) -> tuple:
        """测试连接池"""
        async def run_test():
            pool = ConnectionPool(max_size=5)
            
            # 获取连接
            conn1 = await pool.acquire()
            conn2 = await pool.acquire()
            
            stats = pool.get_stats()
            
            if stats["in_use"] != 2:
                return False, f"使用中连接数不正确: {stats['in_use']}"
            
            # 释放连接
            await pool.release(conn1)
            await pool.release(conn2)
            
            stats = pool.get_stats()
            
            if stats["pool_size"] != 2:
                return False, f"池大小不正确: {stats['pool_size']}"
            
            # 重新获取（应该复用）
            conn3 = await pool.acquire()
            
            if stats["acquire_count"] != 3:
                return False, f"获取次数不正确: {stats['acquire_count']}"
            
            await pool.release(conn3)
            
            return True, "连接池测试通过"
        
        return asyncio.run(run_test())
    
    def test_cache_manager(self) -> tuple:
        """测试缓存管理器"""
        try:
            cache = CacheManager(max_size=3, ttl_seconds=1.0)
            
            # 设置缓存
            cache.set("key1", "value1")
            cache.set("key2", "value2")
            cache.set("key3", "value3")
            
            # 获取缓存
            value = cache.get("key1")
            if value != "value1":
                return False, f"缓存值不正确: {value}"
            
            # 缓存未命中
            value = cache.get("key4")
            if value is not None:
                return False, f"未存在的key应该返回None: {value}"
            
            # 检查统计
            stats = cache.get_stats()
            
            if stats["hits"] != 1:
                return False, f"命中次数不正确: {stats['hits']}"
            
            if stats["misses"] != 1:
                return False, f"未命中次数不正确: {stats['misses']}"
            
            if stats["hit_rate"] != 50.0:
                return False, f"命中率不正确: {stats['hit_rate']}"
            
            # 测试容量限制
            cache.set("key4", "value4")  # 应该淘汰最旧的
            
            if cache.get("key1") is not None:
                return False, "应该淘汰最旧的key1"
            
            return True, "缓存管理器测试通过"
        except Exception as e:
            return False, f"缓存管理器异常: {e}"
    
    def test_bottleneck_analysis(self) -> tuple:
        """测试瓶颈分析"""
        try:
            optimizer = PerformanceOptimizer()
            optimizer.monitor.register_agent("bottleneck_agent")
            
            # 模拟各种瓶颈场景
            # 1. 低成功率
            for _ in range(8):
                optimizer.monitor.record_execution("bottleneck_agent", 0.5, False)
            for _ in range(2):
                optimizer.monitor.record_execution("bottleneck_agent", 0.5, True)
            
            # 2. 高内存
            optimizer.monitor.record_resource_usage("bottleneck_agent", 600.0, 50.0)
            
            # 3. 队列积压
            optimizer.monitor.record_queue_length("bottleneck_agent", 30)
            
            # 获取瓶颈分析
            bottlenecks = optimizer.monitor.get_bottleneck_analysis("bottleneck_agent")
            
            if len(bottlenecks) < 2:
                return False, f"应该检测到至少2个瓶颈，实际: {len(bottlenecks)}"
            
            # 检查是否检测到低成功率
            success_bottleneck = next((b for b in bottlenecks if b["type"] == "low_success_rate"), None)
            if not success_bottleneck:
                return False, "未检测到低成功率瓶颈"
            
            return True, f"瓶颈分析测试通过，检测到{len(bottlenecks)}个瓶颈"
        except Exception as e:
            return False, f"瓶颈分析异常: {e}"
    
    def test_optimization_suggestions(self) -> tuple:
        """测试优化建议"""
        try:
            optimizer = PerformanceOptimizer()
            optimizer.monitor.register_agent("suggestion_agent")
            
            # 模拟高延迟场景
            for _ in range(10):
                optimizer.monitor.record_execution("suggestion_agent", 6.0, True)
            
            # 获取优化建议
            suggestions = optimizer.get_optimization_suggestions("suggestion_agent")
            
            if len(suggestions) == 0:
                return False, "应该有优化建议"
            
            # 检查是否建议缓存
            cache_suggestion = next((s for s in suggestions if s["strategy"] == "caching"), None)
            if not cache_suggestion:
                return False, "应该建议使用缓存"
            
            return True, f"优化建议测试通过，获得{len(suggestions)}条建议"
        except Exception as e:
            return False, f"优化建议异常: {e}"
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始运行子代理性能优化测试套件...")
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
    print("🎓 Day 12 Lesson 48: 子代理性能优化演示")
    print("=" * 60)
    
    # 1. 创建性能优化器
    optimizer = PerformanceOptimizer()
    
    # 2. 注册代理
    print("\n1. 注册代理到监控:")
    agents = ["python_agent", "bash_agent", "data_agent", "web_agent"]
    for agent in agents:
        optimizer.monitor.register_agent(agent)
        print(f"   ✅ {agent} 已注册")
    
    # 3. 模拟性能数据
    print("\n2. 模拟性能数据:")
    
    # python_agent - 表现良好
    for _ in range(20):
        optimizer.monitor.record_execution("python_agent", 0.3 + random.random() * 0.2, True)
    optimizer.monitor.record_resource_usage("python_agent", 120.0, 25.0)
    optimizer.monitor.record_queue_length("python_agent", 2)
    
    # bash_agent - 表现一般
    for i in range(15):
        success = random.random() > 0.2  # 80%成功率
        optimizer.monitor.record_execution("bash_agent", 0.5 + random.random() * 0.5, success)
    optimizer.monitor.record_resource_usage("bash_agent", 200.0, 40.0)
    optimizer.monitor.record_queue_length("bash_agent", 8)
    
    # data_agent - 有瓶颈
    for i in range(10):
        success = random.random() > 0.3  # 70%成功率
        optimizer.monitor.record_execution("data_agent", 2.0 + random.random() * 2.0, success)
    optimizer.monitor.record_resource_usage("data_agent", 450.0, 60.0)
    optimizer.monitor.record_queue_length("data_agent", 25)
    
    # web_agent - 一般
    for _ in range(12):
        optimizer.monitor.record_execution("web_agent", 0.8 + random.random() * 0.3, True)
    optimizer.monitor.record_resource_usage("web_agent", 180.0, 35.0)
    optimizer.monitor.record_queue_length("web_agent", 5)
    
    print("   ✅ 性能数据已模拟")
    
    # 4. 查看性能报告
    print("\n3. 性能报告:")
    report = optimizer.monitor.get_global_report()
    
    for agent_id, agent_report in report["agents"].items():
        print(f"\n   📊 {agent_id}:")
        print(f"      性能评分: {agent_report['performance_score']:.1f}/100")
        print(f"      成功率: {agent_report['success_rate']:.1f}%")
        print(f"      平均执行时间: {agent_report['avg_execution_time']:.3f}s")
        print(f"      P95执行时间: {agent_report['p95_execution_time']:.3f}s")
    
    print(f"\n   🏆 最佳代理: {report['summary']['best_agent']}")
    print(f"   ⚠️  需改进: {report['summary']['worst_agent']}")
    
    # 5. 瓶颈分析
    print("\n4. 瓶颈分析 (data_agent):")
    bottlenecks = optimizer.monitor.get_bottleneck_analysis("data_agent")
    
    for bottleneck in bottlenecks:
        severity_icon = "🔴" if bottleneck["severity"] == "high" else "🟡"
        print(f"   {severity_icon} {bottleneck['type']}:")
        print(f"      当前值: {bottleneck['current_value']}")
        print(f"      阈值: {bottleneck['threshold']}")
        print(f"      建议: {bottleneck['suggestion']}")
    
    # 6. 优化建议
    print("\n5. 优化建议 (data_agent):")
    suggestions = optimizer.get_optimization_suggestions("data_agent")
    
    for suggestion in suggestions:
        print(f"   💡 策略: {suggestion['strategy']}")
        print(f"      原因: {suggestion['reason']}")
        print(f"      预期提升: {suggestion['expected_improvement']}")
        print(f"      实现: {suggestion['implementation']}")
        print()
    
    # 7. 缓存演示
    print("\n6. 缓存演示:")
    optimizer.create_cache("data_agent", max_size=100, ttl=60.0)
    
    # 模拟缓存命中
    optimizer.caches["data_agent"].set("query:result1", {"data": [1, 2, 3]})
    cached = optimizer.caches["data_agent"].get("query:result1")
    print(f"   缓存命中: {cached}")
    
    cache_stats = optimizer.caches["data_agent"].get_stats()
    print(f"   缓存统计: 命中={cache_stats['hits']}, 未命中={cache_stats['misses']}, 命中率={cache_stats['hit_rate']}%")
    
    # 8. 连接池演示
    print("\n7. 连接池演示:")
    pool = optimizer.create_connection_pool("data_agent", max_size=5)
    
    # 模拟连接使用
    conn1 = await pool.acquire()
    conn2 = await pool.acquire()
    print(f"   获取2个连接")
    
    pool_stats = pool.get_stats()
    print(f"   连接池统计: 池中={pool_stats['pool_size']}, 使用中={pool_stats['in_use']}")
    
    await pool.release(conn1)
    await pool.release(conn2)
    
    conn3 = await pool.acquire()  # 应该复用
    print(f"   复用连接: {pool_stats['acquire_count']}次获取, {pool_stats['created_count']}个创建")
    
    await pool.release(conn3)
    
    print("\n演示完成!")


def run_tests():
    """运行测试套件"""
    test_suite = PerformanceTestSuite()
    report = test_suite.run_all_tests()
    
    summary = report['summary']
    if summary['success_rate'] >= 80.0:
        print("\n🎉 子代理性能优化测试套件验证通过")
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
