#!/usr/bin/env python3
"""
Day 14 - 第56节课：实战：记忆系统性能优化
========================================

本演示代码实现记忆系统性能优化，包括：
1. MemoryCache - LRU缓存实现
2. MemoryPerformanceMonitor - 性能监控系统
3. 多种优化策略：索引优化、批量操作、异步处理、数据分区
4. 性能测试和调优工具

运行方式:
    python memory_performance_optimization_demo.py          # 运行演示
    python memory_performance_optimization_demo.py --test   # 运行测试
"""

import os
import sys
import time
import json
import math
import random
import statistics
import threading
import asyncio
import queue
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import wraps
from pathlib import Path
from datetime import datetime, timedelta
import heapq
import hashlib
import pickle


# ============================================================================
# 第一部分：缓存系统实现
# ============================================================================

class CacheEntry:
    """缓存条目"""
    
    def __init__(self, key: str, value: Any, timestamp: float = None):
        self.key = key
        self.value = value
        self.timestamp = timestamp or time.time()
        self.access_count = 1
        self.last_access_time = self.timestamp
        self.size = self._calculate_size(value)
    
    def _calculate_size(self, value: Any) -> int:
        """计算值的大小（近似字节数）"""
        try:
            return len(pickle.dumps(value))
        except:
            # 估算大小
            return len(str(value))
    
    def access(self):
        """记录访问"""
        self.access_count += 1
        self.last_access_time = time.time()


class CacheEvictionPolicy(Enum):
    """缓存淘汰策略"""
    LRU = "lru"          # 最近最少使用
    LFU = "lfu"          # 最不经常使用
    FIFO = "fifo"        # 先进先出
    RANDOM = "random"    # 随机淘汰


class MemoryCache:
    """内存缓存系统（支持LRU、LFU、FIFO、RANDOM策略）"""
    
    def __init__(self, max_size: int = 1000, 
                 policy: CacheEvictionPolicy = CacheEvictionPolicy.LRU,
                 enable_statistics: bool = True):
        self.max_size = max_size
        self.policy = policy
        self.enable_statistics = enable_statistics
        
        # 缓存存储
        self.cache = OrderedDict() if policy == CacheEvictionPolicy.LRU else {}
        
        # 辅助数据结构（根据策略不同）
        if policy == CacheEvictionPolicy.LFU:
            self.access_counts = defaultdict(int)  # 键 -> 访问次数
            self.freq_map = defaultdict(list)      # 频率 -> 键列表
            self.min_freq = 0
        
        elif policy == CacheEvictionPolicy.FIFO:
            self.queue = []  # 先进先出队列
        
        # 统计信息
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.total_accesses = 0
        self.total_size = 0
        self.creation_time = time.time()
        
        # 并发控制
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            self.total_accesses += 1
            
            if key in self.cache:
                entry = self.cache[key]
                
                # 更新访问信息
                entry.access()
                
                # 根据策略更新数据结构
                if self.policy == CacheEvictionPolicy.LRU:
                    # 移动到最近使用位置
                    self.cache.move_to_end(key)
                elif self.policy == CacheEvictionPolicy.LFU:
                    # 更新LFU数据结构
                    old_freq = self.access_counts[key]
                    new_freq = old_freq + 1
                    
                    # 从旧频率列表移除
                    if key in self.freq_map[old_freq]:
                        self.freq_map[old_freq].remove(key)
                        if not self.freq_map[old_freq]:
                            del self.freq_map[old_freq]
                            if old_freq == self.min_freq:
                                self.min_freq += 1
                    
                    # 添加到新频率列表
                    self.access_counts[key] = new_freq
                    self.freq_map[new_freq].append(key)
                
                self.hits += 1
                return entry.value
            else:
                self.misses += 1
                return None
    
    def set(self, key: str, value: Any):
        """设置缓存值"""
        with self._lock:
            # 如果键已存在，先移除旧条目
            if key in self.cache:
                old_entry = self.cache[key]
                self.total_size -= old_entry.size
                self._remove_from_auxiliary(key)
            
            # 创建新条目
            entry = CacheEntry(key, value)
            
            # 检查是否需要淘汰
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict()
            
            # 添加新条目
            self.cache[key] = entry
            self.total_size += entry.size
            
            # 添加到辅助数据结构
            self._add_to_auxiliary(key, entry)
    
    def _evict(self):
        """执行淘汰策略"""
        if not self.cache:
            return
        
        evicted_key = None
        
        if self.policy == CacheEvictionPolicy.LRU:
            # LRU: 淘汰最久未使用的
            evicted_key, evicted_entry = self.cache.popitem(last=False)
            
        elif self.policy == CacheEvictionPolicy.LFU:
            # LFU: 淘汰访问频率最低的
            if self.min_freq in self.freq_map and self.freq_map[self.min_freq]:
                evicted_key = self.freq_map[self.min_freq].pop(0)
                if not self.freq_map[self.min_freq]:
                    del self.freq_map[self.min_freq]
                evicted_entry = self.cache[evicted_key]
                del self.cache[evicted_key]
                del self.access_counts[evicted_key]
            
        elif self.policy == CacheEvictionPolicy.FIFO:
            # FIFO: 淘汰最早加入的
            if self.queue:
                evicted_key = self.queue.pop(0)
                evicted_entry = self.cache[evicted_key]
                del self.cache[evicted_key]
            
        elif self.policy == CacheEvictionPolicy.RANDOM:
            # RANDOM: 随机淘汰
            evicted_key = random.choice(list(self.cache.keys()))
            evicted_entry = self.cache[evicted_key]
            del self.cache[evicted_key]
            self._remove_from_auxiliary(evicted_key)
        
        if evicted_key:
            self.evictions += 1
            self.total_size -= evicted_entry.size
    
    def _add_to_auxiliary(self, key: str, entry: CacheEntry):
        """添加到辅助数据结构"""
        if self.policy == CacheEvictionPolicy.LFU:
            freq = 1
            self.access_counts[key] = freq
            self.freq_map[freq].append(key)
            self.min_freq = 1
            
        elif self.policy == CacheEvictionPolicy.FIFO:
            self.queue.append(key)
    
    def _remove_from_auxiliary(self, key: str):
        """从辅助数据结构移除"""
        if self.policy == CacheEvictionPolicy.LFU:
            if key in self.access_counts:
                freq = self.access_counts[key]
                if key in self.freq_map[freq]:
                    self.freq_map[freq].remove(key)
                    if not self.freq_map[freq]:
                        del self.freq_map[freq]
                        if freq == self.min_freq:
                            # 更新最小频率
                            self.min_freq = min(self.freq_map.keys()) if self.freq_map else 0
                del self.access_counts[key]
        
        elif self.policy == CacheEvictionPolicy.FIFO:
            if key in self.queue:
                self.queue.remove(key)
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            if self.policy == CacheEvictionPolicy.LFU:
                self.access_counts.clear()
                self.freq_map.clear()
                self.min_freq = 0
            elif self.policy == CacheEvictionPolicy.FIFO:
                self.queue.clear()
            
            self.hits = 0
            self.misses = 0
            self.evictions = 0
            self.total_accesses = 0
            self.total_size = 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            hit_rate = self.hits / self.total_accesses if self.total_accesses > 0 else 0
            
            return {
                "total_entries": len(self.cache),
                "max_size": self.max_size,
                "hits": self.hits,
                "misses": self.misses,
                "total_accesses": self.total_accesses,
                "hit_rate": hit_rate,
                "evictions": self.evictions,
                "total_size_bytes": self.total_size,
                "average_entry_size": self.total_size / len(self.cache) if self.cache else 0,
                "policy": self.policy.value,
                "uptime_seconds": time.time() - self.creation_time
            }
    
    def resize(self, new_max_size: int):
        """调整缓存大小"""
        with self._lock:
            self.max_size = new_max_size
            
            # 如果当前大小超过新限制，执行淘汰
            while len(self.cache) > self.max_size:
                self._evict()
    
    def prefetch(self, keys: List[str], loader: Callable[[str], Any]):
        """预取多个键到缓存"""
        for key in keys:
            if key not in self.cache:
                value = loader(key)
                if value is not None:
                    self.set(key, value)
    
    def batch_set(self, items: Dict[str, Any]):
        """批量设置缓存值"""
        with self._lock:
            for key, value in items.items():
                self.set(key, value)


class AdaptiveCache(MemoryCache):
    """自适应缓存（根据访问模式动态调整策略）"""
    
    def __init__(self, max_size: int = 1000):
        super().__init__(max_size, CacheEvictionPolicy.LRU)
        self.access_patterns = []
        self.policy_history = []
        self.switch_threshold = 0.1  # 性能下降阈值
        self.monitor_interval = 1000  # 监控间隔（访问次数）
        self.last_check_accesses = 0
        
        # 策略评估器
        self.policy_evaluators = {
            CacheEvictionPolicy.LRU: self._evaluate_lru,
            CacheEvictionPolicy.LFU: self._evaluate_lfu,
            CacheEvictionPolicy.FIFO: self._evaluate_fifo
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值（带自适应调整）"""
        result = super().get(key)
        
        # 记录访问模式
        self.access_patterns.append({
            "key": key,
            "time": time.time(),
            "hit": result is not None
        })
        
        # 定期评估是否需要切换策略
        if self.total_accesses - self.last_check_accesses >= self.monitor_interval:
            self._evaluate_and_adjust()
            self.last_check_accesses = self.total_accesses
        
        return result
    
    def _evaluate_and_adjust(self):
        """评估性能并调整策略"""
        if len(self.access_patterns) < 100:  # 需要足够的数据
            return
        
        # 计算当前策略的命中率
        recent_patterns = self.access_patterns[-1000:]
        current_hits = sum(1 for p in recent_patterns if p["hit"])
        current_hit_rate = current_hits / len(recent_patterns) if recent_patterns else 0
        
        # 评估其他策略的预期命中率
        best_policy = self.policy
        best_hit_rate = current_hit_rate
        
        for policy, evaluator in self.policy_evaluators.items():
            if policy == self.policy:
                continue
            
            expected_hit_rate = evaluator(recent_patterns)
            if expected_hit_rate > best_hit_rate + self.switch_threshold:
                best_policy = policy
                best_hit_rate = expected_hit_rate
        
        # 如果找到更好的策略，切换
        if best_policy != self.policy:
            print(f"自适应缓存: 从 {self.policy.value} 切换到 {best_policy.value} "
                  f"(预期命中率: {best_hit_rate:.2%})")
            self._switch_policy(best_policy)
    
    def _switch_policy(self, new_policy: CacheEvictionPolicy):
        """切换缓存策略"""
        # 保存当前缓存内容
        old_cache = self.cache.copy()
        
        # 更新策略和数据结构
        self.policy = new_policy
        self.cache = OrderedDict() if new_policy == CacheEvictionPolicy.LRU else {}
        
        if new_policy == CacheEvictionPolicy.LFU:
            self.access_counts = defaultdict(int)
            self.freq_map = defaultdict(list)
            self.min_freq = 0
        elif new_policy == CacheEvictionPolicy.FIFO:
            self.queue = []
        
        # 重新添加缓存条目（保持原有顺序）
        for key, entry in old_cache.items():
            self.cache[key] = entry
            self._add_to_auxiliary(key, entry)
        
        # 记录策略切换
        self.policy_history.append({
            "time": time.time(),
            "from": self.policy_history[-1]["to"] if self.policy_history else self.policy.value,
            "to": new_policy.value,
            "reason": "adaptive_adjustment"
        })
    
    def _evaluate_lru(self, patterns: List[Dict[str, Any]]) -> float:
        """评估LRU策略的预期命中率"""
        # 模拟LRU行为：最近访问的模式更适合LRU
        recent_keys = set()
        simulated_hits = 0
        
        for pattern in patterns[-100:]:  # 只看最近100个
            if pattern["key"] in recent_keys:
                simulated_hits += 1
            recent_keys.add(pattern["key"])
            if len(recent_keys) > self.max_size:
                # 移除最旧的（模拟LRU淘汰）
                recent_keys.remove(list(recent_keys)[0])
        
        return simulated_hits / 100 if patterns else 0
    
    def _evaluate_lfu(self, patterns: List[Dict[str, Any]]) -> float:
        """评估LFU策略的预期命中率"""
        # 统计访问频率
        freq_count = defaultdict(int)
        for pattern in patterns:
            freq_count[pattern["key"]] += 1
        
        # 找出高频键
        high_freq_keys = {k for k, v in freq_count.items() if v > 1}
        
        # 模拟LFU：高频键在缓存中
        simulated_hits = 0
        for pattern in patterns[-100:]:
            if pattern["key"] in high_freq_keys:
                simulated_hits += 1
        
        return simulated_hits / 100 if patterns else 0
    
    def _evaluate_fifo(self, patterns: List[Dict[str, Any]]) -> float:
        """评估FIFO策略的预期命中率"""
        # FIFO适合访问模式均匀的场景
        # 这里简单返回一个基准值
        return 0.5  # 假设FIFO有50%命中率


# ============================================================================
# 第二部分：性能监控系统
# ============================================================================

@dataclass
class PerformanceMetric:
    """性能指标"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceSnapshot:
    """性能快照"""
    timestamp: float
    metrics: Dict[str, PerformanceMetric]
    summary: Dict[str, float]
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceAggregator:
    """性能指标聚合器"""
    
    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.metrics_history = defaultdict(list)
        self.aggregation_functions = {
            "avg": statistics.mean,
            "min": min,
            "max": max,
            "sum": sum,
            "std": statistics.stdev,
            "count": len,
            "p50": lambda x: statistics.quantiles(x, n=2)[0],
            "p90": lambda x: statistics.quantiles(x, n=10)[9],
            "p95": lambda x: statistics.quantiles(x, n=20)[19],
            "p99": lambda x: statistics.quantiles(x, n=100)[98]
        }
    
    def add_metric(self, metric: PerformanceMetric):
        """添加指标"""
        self.metrics_history[metric.name].append(metric)
        
        # 保持窗口大小
        if len(self.metrics_history[metric.name]) > self.window_size:
            self.metrics_history[metric.name].pop(0)
    
    def aggregate(self, metric_name: str, 
                  aggregation_types: List[str] = None) -> Dict[str, float]:
        """聚合指标"""
        if metric_name not in self.metrics_history or not self.metrics_history[metric_name]:
            return {}
        
        values = [m.value for m in self.metrics_history[metric_name]]
        
        if aggregation_types is None:
            aggregation_types = ["avg", "min", "max", "std", "count", "p90", "p95"]
        
        results = {}
        for agg_type in aggregation_types:
            if agg_type in self.aggregation_functions:
                try:
                    results[agg_type] = self.aggregation_functions[agg_type](values)
                except (statistics.StatisticsError, ValueError):
                    results[agg_type] = 0.0
        
        return results
    
    def get_trend(self, metric_name: str, 
                  time_window: int = 3600) -> Dict[str, Any]:
        """获取指标趋势"""
        if metric_name not in self.metrics_history:
            return {}
        
        # 过滤时间窗口内的指标
        cutoff_time = time.time() - time_window
        recent_metrics = [
            m for m in self.metrics_history[metric_name]
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        values = [m.value for m in recent_metrics]
        timestamps = [m.timestamp for m in recent_metrics]
        
        # 计算趋势（线性回归斜率）
        try:
            n = len(values)
            if n > 1:
                x_mean = statistics.mean(timestamps)
                y_mean = statistics.mean(values)
                
                numerator = sum((timestamps[i] - x_mean) * (values[i] - y_mean) for i in range(n))
                denominator = sum((timestamps[i] - x_mean) ** 2 for i in range(n))
                
                if denominator != 0:
                    slope = numerator / denominator
                else:
                    slope = 0
                
                trend = "increasing" if slope > 0.01 else "decreasing" if slope < -0.01 else "stable"
            else:
                slope = 0
                trend = "stable"
        except:
            slope = 0
            trend = "unknown"
        
        return {
            "values": values,
            "timestamps": timestamps,
            "slope": slope,
            "trend": trend,
            "current": values[-1] if values else 0,
            "average": statistics.mean(values) if values else 0
        }
    
    def clear(self, metric_name: str = None):
        """清空指标"""
        if metric_name:
            if metric_name in self.metrics_history:
                del self.metrics_history[metric_name]
        else:
            self.metrics_history.clear()


class MemoryPerformanceMonitor:
    """记忆系统性能监控器"""
    
    def __init__(self):
        self.aggregator = PerformanceAggregator(window_size=5000)
        self.metric_definitions = self._create_metric_definitions()
        self.alerts = []
        self.alert_thresholds = self._create_default_thresholds()
        self.start_time = time.time()
        
        # 缓存监控
        self.cache_metrics = {}
        
        # 性能基准
        self.baseline_metrics = {}
        
        # 监控开关
        self.enabled = True
        
        # 数据存储
        self.snapshots = []
        self.max_snapshots = 100
    
    def _create_metric_definitions(self) -> Dict[str, Dict[str, Any]]:
        """创建指标定义"""
        return {
            "extraction_time": {
                "description": "记忆提取时间（毫秒）",
                "unit": "ms",
                "lower_is_better": True,
                "default_threshold": 100.0  # 超过100ms警告
            },
            "injection_time": {
                "description": "记忆注入时间（毫秒）",
                "unit": "ms",
                "lower_is_better": True,
                "default_threshold": 50.0
            },
            "cache_hit_rate": {
                "description": "缓存命中率",
                "unit": "%",
                "lower_is_better": False,
                "default_threshold": 0.7  # 低于70%警告
            },
            "storage_latency": {
                "description": "存储访问延迟（毫秒）",
                "unit": "ms",
                "lower_is_better": True,
                "default_threshold": 20.0
            },
            "memory_usage": {
                "description": "内存使用量（MB）",
                "unit": "MB",
                "lower_is_better": True,
                "default_threshold": 1024.0  # 超过1GB警告
            },
            "throughput": {
                "description": "系统吞吐量（操作/秒）",
                "unit": "ops/s",
                "lower_is_better": False,
                "default_threshold": 100.0  # 低于100ops/s警告
            },
            "error_rate": {
                "description": "错误率",
                "unit": "%",
                "lower_is_better": True,
                "default_threshold": 1.0  # 超过1%警告
            },
            "concurrent_connections": {
                "description": "并发连接数",
                "unit": "count",
                "lower_is_better": False,
                "default_threshold": 1000.0
            }
        }
    
    def _create_default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """创建默认阈值"""
        thresholds = {}
        for metric_name, definition in self.metric_definitions.items():
            thresholds[metric_name] = {
                "warning": definition.get("default_threshold", 0),
                "critical": definition.get("default_threshold", 0) * 2,
                "direction": "above" if definition.get("lower_is_better", True) else "below"
            }
        return thresholds
    
    def record_metric(self, name: str, value: float, 
                     tags: Dict[str, str] = None,
                     metadata: Dict[str, Any] = None):
        """记录性能指标"""
        if not self.enabled:
            return
        
        if name not in self.metric_definitions:
            # 自动注册新指标
            self.metric_definitions[name] = {
                "description": f"自定义指标: {name}",
                "unit": "",
                "lower_is_better": True,
                "default_threshold": 0
            }
            self.alert_thresholds[name] = {
                "warning": 0,
                "critical": 0,
                "direction": "above"
            }
        
        definition = self.metric_definitions[name]
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=definition["unit"],
            tags=tags or {},
            metadata=metadata or {}
        )
        
        self.aggregator.add_metric(metric)
        
        # 检查阈值告警
        self._check_threshold(name, value, tags)
        
        # 定期创建快照
        if len(self.aggregator.metrics_history.get(name, [])) % 100 == 0:
            self._create_snapshot()
    
    def _check_threshold(self, metric_name: str, value: float, tags: Dict[str, str]):
        """检查阈值并触发告警"""
        if metric_name not in self.alert_thresholds:
            return
        
        threshold = self.alert_thresholds[metric_name]
        
        is_warning = False
        is_critical = False
        
        if threshold["direction"] == "above":
            if value >= threshold["critical"]:
                is_critical = True
            elif value >= threshold["warning"]:
                is_warning = True
        else:  # below
            if value <= threshold["critical"]:
                is_critical = True
            elif value <= threshold["warning"]:
                is_warning = True
        
        if is_critical or is_warning:
            alert = {
                "timestamp": time.time(),
                "metric": metric_name,
                "value": value,
                "threshold": threshold["critical"] if is_critical else threshold["warning"],
                "level": "CRITICAL" if is_critical else "WARNING",
                "message": f"{metric_name} {'超过' if threshold['direction'] == 'above' else '低于'} "
                          f"{'严重' if is_critical else '警告'}阈值",
                "tags": tags or {}
            }
            self.alerts.append(alert)
    
    def _create_snapshot(self):
        """创建性能快照"""
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            metrics={},
            summary={}
        )
        
        # 聚合所有指标
        for metric_name in self.metric_definitions.keys():
            agg_results = self.aggregator.aggregate(metric_name)
            if agg_results:
                snapshot.summary[metric_name] = agg_results.get("avg", 0)
        
        self.snapshots.append(snapshot)
        
        # 保持快照数量
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots.pop(0)
    
    def get_performance_report(self, time_window: int = 3600) -> Dict[str, Any]:
        """获取性能报告"""
        report = {
            "timestamp": time.time(),
            "time_window_seconds": time_window,
            "uptime_seconds": time.time() - self.start_time,
            "metrics": {},
            "alerts": [],
            "recommendations": []
        }
        
        # 收集指标数据
        for metric_name, definition in self.metric_definitions.items():
            trend = self.aggregator.get_trend(metric_name, time_window)
            if trend:
                report["metrics"][metric_name] = {
                    "definition": definition,
                    "trend": trend,
                    "aggregations": self.aggregator.aggregate(metric_name)
                }
        
        # 收集告警
        cutoff_time = time.time() - time_window
        report["alerts"] = [a for a in self.alerts if a["timestamp"] >= cutoff_time]
        
        # 生成优化建议
        report["recommendations"] = self._generate_recommendations()
        
        return report
    
    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """生成优化建议"""
        recommendations = []
        
        # 分析缓存命中率
        cache_trend = self.aggregator.get_trend("cache_hit_rate", 3600)
        if cache_trend and cache_trend.get("current", 0) < 0.5:
            recommendations.append({
                "type": "cache_optimization",
                "priority": "high",
                "message": "缓存命中率较低，考虑增加缓存容量或优化缓存策略",
                "suggestion": "增加缓存大小或切换到LFU策略",
                "metric": "cache_hit_rate",
                "current_value": cache_trend.get("current", 0),
                "target_value": 0.7
            })
        
        # 分析内存使用
        memory_trend = self.aggregator.get_trend("memory_usage", 3600)
        if memory_trend and memory_trend.get("current", 0) > 512:  # 512MB
            recommendations.append({
                "type": "memory_optimization",
                "priority": "medium",
                "message": "内存使用较高，考虑优化数据结构或添加内存限制",
                "suggestion": "实施数据压缩或分页加载",
                "metric": "memory_usage",
                "current_value": memory_trend.get("current", 0),
                "target_value": 256.0
            })
        
        # 分析响应时间
        extraction_trend = self.aggregator.get_trend("extraction_time", 3600)
        if extraction_trend and extraction_trend.get("current", 0) > 200:  # 200ms
            recommendations.append({
                "type": "performance_optimization",
                "priority": "high",
                "message": "记忆提取时间过长，考虑添加索引或优化查询",
                "suggestion": "为常用查询字段添加索引或实现查询缓存",
                "metric": "extraction_time",
                "current_value": extraction_trend.get("current", 0),
                "target_value": 100.0
            })
        
        return recommendations
    
    def set_baseline(self, baseline_data: Dict[str, float]):
        """设置性能基准"""
        self.baseline_metrics = baseline_data.copy()
    
    def compare_with_baseline(self) -> Dict[str, Dict[str, Any]]:
        """与基准对比"""
        comparison = {}
        
        for metric_name in self.metric_definitions.keys():
            if metric_name in self.baseline_metrics:
                current_agg = self.aggregator.aggregate(metric_name)
                current_avg = current_agg.get("avg", 0) if current_agg else 0
                baseline = self.baseline_metrics[metric_name]
                
                if baseline != 0:
                    change_pct = ((current_avg - baseline) / baseline) * 100
                else:
                    change_pct = 0
                
                comparison[metric_name] = {
                    "baseline": baseline,
                    "current": current_avg,
                    "change_percent": change_pct,
                    "status": "improved" if change_pct < 0 else "degraded" if change_pct > 0 else "stable",
                    "significance": "significant" if abs(change_pct) > 10 else "moderate" if abs(change_pct) > 5 else "minor"
                }
        
        return comparison


# ============================================================================
# 第三部分：优化策略实现
# ============================================================================

class IndexOptimizer:
    """索引优化器"""
    
    def __init__(self, monitor: MemoryPerformanceMonitor = None):
        self.monitor = monitor
        self.indices = {}  # 字段名 -> 索引数据结构
        self.index_stats = defaultdict(lambda: {"hits": 0, "misses": 0})
        
    def create_index(self, field_name: str, data: List[Dict[str, Any]]):
        """为字段创建索引"""
        if not data:
            return
        
        # 构建索引（倒排索引）
        index = defaultdict(list)
        for i, item in enumerate(data):
            value = item.get(field_name)
            if value is not None:
                if isinstance(value, list):
                    for v in value:
                        index[v].append(i)
                else:
                    index[value].append(i)
        
        self.indices[field_name] = {
            "index": index,
            "size": len(index),
            "created_at": time.time(),
            "data_size": len(data)
        }
        
        if self.monitor:
            self.monitor.record_metric(
                "index_creation_time",
                time.time() - self.indices[field_name]["created_at"],
                tags={"field": field_name}
            )
    
    def query_with_index(self, field_name: str, value: Any, 
                        data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用索引查询"""
        start_time = time.time()
        
        if field_name not in self.indices:
            # 没有索引，回退到线性搜索
            self.index_stats[field_name]["misses"] += 1
            result = [item for item in data if item.get(field_name) == value]
            
            if self.monitor:
                self.monitor.record_metric(
                    "index_query_time",
                    (time.time() - start_time) * 1000,
                    tags={"field": field_name, "indexed": False}
                )
            
            return result
        
        # 使用索引查询
        index = self.indices[field_name]["index"]
        if value in index:
            indices = index[value]
            result = [data[i] for i in indices]
            self.index_stats[field_name]["hits"] += 1
        else:
            result = []
            self.index_stats[field_name]["misses"] += 1
        
        query_time = (time.time() - start_time) * 1000
        
        if self.monitor:
            self.monitor.record_metric(
                "index_query_time",
                query_time,
                tags={"field": field_name, "indexed": True}
            )
            self.monitor.record_metric(
                "index_hit_rate",
                self.index_stats[field_name]["hits"] / max(1, self.index_stats[field_name]["hits"] + self.index_stats[field_name]["misses"]),
                tags={"field": field_name}
            )
        
        return result
    
    def get_index_statistics(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        stats = {}
        for field_name, index_info in self.indices.items():
            field_stats = self.index_stats[field_name]
            total = field_stats["hits"] + field_stats["misses"]
            hit_rate = field_stats["hits"] / total if total > 0 else 0
            
            stats[field_name] = {
                "size": index_info["size"],
                "data_size": index_info["data_size"],
                "created_at": index_info["created_at"],
                "hits": field_stats["hits"],
                "misses": field_stats["misses"],
                "hit_rate": hit_rate,
                "memory_usage_estimate": index_info["size"] * 100  # 粗略估计
            }
        
        return stats


class BatchOperationOptimizer:
    """批量操作优化器"""
    
    def __init__(self, monitor: MemoryPerformanceMonitor = None, 
                 batch_size: int = 100):
        self.monitor = monitor
        self.batch_size = batch_size
        self.batch_queue = []
        self.last_flush_time = time.time()
        self.flush_interval = 1.0  # 1秒
        self.stats = {
            "batches_executed": 0,
            "total_operations": 0,
            "total_saved_time": 0.0,
            "average_batch_size": 0.0
        }
        
    def add_operation(self, operation: Callable, *args, **kwargs):
        """添加操作到批量队列"""
        self.batch_queue.append((operation, args, kwargs))
        
        # 检查是否需要立即执行
        if len(self.batch_queue) >= self.batch_size:
            self.flush()
        elif time.time() - self.last_flush_time >= self.flush_interval:
            self.flush()
    
    def flush(self):
        """执行批量操作"""
        if not self.batch_queue:
            return
        
        start_time = time.time()
        batch_size = len(self.batch_queue)
        
        # 执行所有操作
        results = []
        for operation, args, kwargs in self.batch_queue:
            try:
                result = operation(*args, **kwargs)
                results.append(result)
            except Exception as e:
                results.append(e)
        
        # 清空队列
        self.batch_queue.clear()
        
        # 更新统计
        execution_time = time.time() - start_time
        estimated_individual_time = batch_size * 0.001  # 假设每个操作1ms
        saved_time = max(0, estimated_individual_time - execution_time)
        
        self.stats["batches_executed"] += 1
        self.stats["total_operations"] += batch_size
        self.stats["total_saved_time"] += saved_time
        self.stats["average_batch_size"] = (
            (self.stats["average_batch_size"] * (self.stats["batches_executed"] - 1) + batch_size)
            / self.stats["batches_executed"]
        )
        
        self.last_flush_time = time.time()
        
        if self.monitor:
            self.monitor.record_metric(
                "batch_execution_time",
                execution_time * 1000,  # 转换为毫秒
                tags={"batch_size": str(batch_size)}
            )
            self.monitor.record_metric(
                "batch_saved_time",
                saved_time * 1000,
                tags={"batch_size": str(batch_size)}
            )
            self.monitor.record_metric(
                "batch_efficiency",
                saved_time / estimated_individual_time if estimated_individual_time > 0 else 0,
                tags={"batch_size": str(batch_size)}
            )
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        efficiency = (self.stats["total_saved_time"] / 
                     (self.stats["total_operations"] * 0.001)) if self.stats["total_operations"] > 0 else 0
        
        return {
            **self.stats,
            "efficiency": efficiency,
            "current_queue_size": len(self.batch_queue),
            "time_since_last_flush": time.time() - self.last_flush_time
        }


class AsyncOperationOptimizer:
    """异步操作优化器"""
    
    def __init__(self, monitor: MemoryPerformanceMonitor = None,
                 max_workers: int = 10):
        self.monitor = monitor
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.stats = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_execution_time": 0.0,
            "average_concurrency": 0.0
        }
        self.active_tasks = 0
        self.max_concurrency = 0
        
    async def execute_async(self, operation: Callable, *args, **kwargs):
        """异步执行操作"""
        self.stats["tasks_submitted"] += 1
        self.active_tasks += 1
        self.max_concurrency = max(self.max_concurrency, self.active_tasks)
        
        start_time = time.time()
        
        try:
            # 在线程池中执行阻塞操作
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: operation(*args, **kwargs)
            )
            
            execution_time = time.time() - start_time
            self.stats["tasks_completed"] += 1
            self.stats["total_execution_time"] += execution_time
            
            if self.monitor:
                self.monitor.record_metric(
                    "async_execution_time",
                    execution_time * 1000,
                    tags={"operation": operation.__name__ if hasattr(operation, '__name__') else 'unknown'}
                )
                self.monitor.record_metric(
                    "async_concurrency",
                    self.active_tasks,
                    tags={"max_workers": str(self.max_workers)}
                )
            
            return result
            
        except Exception as e:
            self.stats["tasks_failed"] += 1
            
            if self.monitor:
                self.monitor.record_metric(
                    "async_error_rate",
                    1,  # 计数错误
                    tags={"operation": operation.__name__ if hasattr(operation, '__name__') else 'unknown'}
                )
            
            raise e
            
        finally:
            self.active_tasks -= 1
            # 更新平均并发度
            self.stats["average_concurrency"] = (
                (self.stats["average_concurrency"] * (self.stats["tasks_completed"] + self.stats["tasks_failed"] - 1)
                 + self.active_tasks) / (self.stats["tasks_completed"] + self.stats["tasks_failed"])
            )
    
    def batch_execute_async(self, operations: List[Tuple[Callable, tuple, dict]]):
        """批量异步执行操作"""
        async def run_all():
            tasks = []
            for operation, args, kwargs in operations:
                task = self.execute_async(operation, *args, **kwargs)
                tasks.append(task)
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        return asyncio.run(run_all())
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_tasks = self.stats["tasks_completed"] + self.stats["tasks_failed"]
        avg_time = (self.stats["total_execution_time"] / 
                   self.stats["tasks_completed"] if self.stats["tasks_completed"] > 0 else 0)
        
        return {
            **self.stats,
            "average_execution_time": avg_time,
            "success_rate": self.stats["tasks_completed"] / total_tasks if total_tasks > 0 else 0,
            "current_concurrency": self.active_tasks,
            "max_concurrency_observed": self.max_concurrency,
            "executor_status": "running"
        }
    
    def shutdown(self):
        """关闭执行器"""
        self.executor.shutdown(wait=True)


class DataPartitionOptimizer:
    """数据分区优化器"""
    
    def __init__(self, monitor: MemoryPerformanceMonitor = None,
                 partition_key: str = "id"):
        self.monitor = monitor
        self.partition_key = partition_key
        self.partitions = {}
        self.partition_rules = {}
        self.stats = {
            "partitions_created": 0,
            "total_items": 0,
            "partition_hits": 0,
            "partition_misses": 0,
            "rebalance_operations": 0
        }
        
    def create_partition(self, partition_id: str, 
                        condition: Callable[[Any], bool] = None):
        """创建分区"""
        self.partitions[partition_id] = []
        if condition:
            self.partition_rules[partition_id] = condition
        
        self.stats["partitions_created"] += 1
        
        if self.monitor:
            self.monitor.record_metric(
                "partition_count",
                len(self.partitions),
                tags={"action": "create"}
            )
    
    def add_to_partition(self, item: Dict[str, Any]):
        """添加数据项到合适的分区"""
        self.stats["total_items"] += 1
        
        # 查找匹配的分区
        assigned = False
        for partition_id, condition in self.partition_rules.items():
            if condition(item):
                self.partitions[partition_id].append(item)
                assigned = True
                break
        
        if not assigned:
            # 使用默认分区（基于分区键的哈希）
            if self.partition_key in item:
                partition_id = self._get_partition_id(item[self.partition_key])
                if partition_id not in self.partitions:
                    self.partitions[partition_id] = []
                self.partitions[partition_id].append(item)
            else:
                # 没有分区键，添加到默认分区
                if "default" not in self.partitions:
                    self.partitions["default"] = []
                self.partitions["default"].append(item)
        
        # 检查是否需要重新平衡
        self._check_rebalance()
    
    def _get_partition_id(self, value: Any) -> str:
        """根据值计算分区ID"""
        if isinstance(value, (int, float)):
            # 数值分区（例如：0-99, 100-199）
            partition_num = int(value) // 100
            return f"partition_{partition_num}"
        else:
            # 字符串哈希分区
            hash_val = hashlib.md5(str(value).encode()).hexdigest()
            return f"partition_{int(hash_val[:4], 16) % 10}"
    
    def _check_rebalance(self):
        """检查并执行分区重新平衡"""
        # 计算分区大小
        partition_sizes = {pid: len(items) for pid, items in self.partitions.items()}
        total_items = sum(partition_sizes.values())
        
        if total_items == 0:
            return
        
        avg_size = total_items / len(self.partitions)
        
        # 检查是否需要重新平衡（某个分区大小超过平均值的2倍）
        for partition_id, size in partition_sizes.items():
            if size > avg_size * 2 and size > 10:
                self._rebalance_partition(partition_id)
                self.stats["rebalance_operations"] += 1
                break
    
    def _rebalance_partition(self, partition_id: str):
        """重新平衡分区"""
        if partition_id not in self.partitions:
            return
        
        items = self.partitions[partition_id]
        if len(items) <= 10:
            return
        
        # 将一半的数据移动到新分区
        new_partition_id = f"{partition_id}_split_{int(time.time())}"
        self.partitions[new_partition_id] = items[len(items)//2:]
        self.partitions[partition_id] = items[:len(items)//2]
        
        if self.monitor:
            self.monitor.record_metric(
                "partition_rebalance",
                1,
                tags={"from": partition_id, "to": new_partition_id}
            )
            self.monitor.record_metric(
                "partition_size",
                len(self.partitions[partition_id]),
                tags={"partition": partition_id}
            )
            self.monitor.record_metric(
                "partition_size",
                len(self.partitions[new_partition_id]),
                tags={"partition": new_partition_id}
            )
    
    def query_partition(self, partition_id: str, 
                       condition: Callable[[Dict[str, Any]], bool] = None):
        """查询分区数据"""
        start_time = time.time()
        
        if partition_id not in self.partitions:
            self.stats["partition_misses"] += 1
            return []
        
        items = self.partitions[partition_id]
        
        if condition:
            result = [item for item in items if condition(item)]
        else:
            result = items.copy()
        
        query_time = (time.time() - start_time) * 1000
        self.stats["partition_hits"] += 1
        
        if self.monitor:
            self.monitor.record_metric(
                "partition_query_time",
                query_time,
                tags={"partition": partition_id, "condition": str(condition is not None)}
            )
            hit_rate = self.stats["partition_hits"] / max(1, self.stats["partition_hits"] + self.stats["partition_misses"])
            self.monitor.record_metric(
                "partition_hit_rate",
                hit_rate,
                tags={"partition": partition_id}
            )
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        partition_sizes = {pid: len(items) for pid, items in self.partitions.items()}
        total_size = sum(partition_sizes.values())
        
        return {
            **self.stats,
            "partition_count": len(self.partitions),
            "partition_sizes": partition_sizes,
            "total_size": total_size,
            "average_partition_size": total_size / len(self.partitions) if self.partitions else 0,
            "max_partition_size": max(partition_sizes.values()) if partition_sizes else 0,
            "min_partition_size": min(partition_sizes.values()) if partition_sizes else 0
        }


# ============================================================================
# 第四部分：性能测试和调优工具
# ============================================================================

class PerformanceBenchmark:
    """性能基准测试工具"""
    
    def __init__(self, monitor: MemoryPerformanceMonitor):
        self.monitor = monitor
        self.benchmark_results = {}
        self.test_cases = {}
        
    def register_test_case(self, name: str, 
                          test_func: Callable,
                          description: str = ""):
        """注册测试用例"""
        self.test_cases[name] = {
            "function": test_func,
            "description": description,
            "runs": 0,
            "total_time": 0.0
        }
    
    def run_benchmark(self, test_name: str = None, 
                     iterations: int = 100,
                     warmup_iterations: int = 10):
        """运行基准测试"""
        if test_name:
            test_cases = {test_name: self.test_cases[test_name]}
        else:
            test_cases = self.test_cases
        
        results = {}
        
        for name, test_info in test_cases.items():
            # 预热
            for _ in range(warmup_iterations):
                test_info["function"]()
            
            # 正式测试
            start_time = time.time()
            for i in range(iterations):
                test_info["function"]()
            
            total_time = time.time() - start_time
            avg_time = total_time / iterations
            
            # 更新统计
            test_info["runs"] += iterations
            test_info["total_time"] += total_time
            
            # 记录结果
            results[name] = {
                "iterations": iterations,
                "total_time_seconds": total_time,
                "average_time_seconds": avg_time,
                "operations_per_second": iterations / total_time if total_time > 0 else 0,
                "description": test_info["description"]
            }
            
            # 记录到监控器
            if self.monitor:
                self.monitor.record_metric(
                    "benchmark_time",
                    avg_time * 1000,  # 转换为毫秒
                    tags={"test": name}
                )
                self.monitor.record_metric(
                    "benchmark_throughput",
                    iterations / total_time if total_time > 0 else 0,
                    tags={"test": name}
                )
        
        self.benchmark_results.update(results)
        return results
    
    def compare_benchmarks(self, baseline_name: str, 
                          current_name: str) -> Dict[str, Any]:
        """比较两个基准测试结果"""
        if baseline_name not in self.benchmark_results or current_name not in self.benchmark_results:
            return {}
        
        baseline = self.benchmark_results[baseline_name]
        current = self.benchmark_results[current_name]
        
        time_diff = current["average_time_seconds"] - baseline["average_time_seconds"]
        time_diff_pct = (time_diff / baseline["average_time_seconds"]) * 100 if baseline["average_time_seconds"] > 0 else 0
        
        throughput_diff = current["operations_per_second"] - baseline["operations_per_second"]
        throughput_diff_pct = (throughput_diff / baseline["operations_per_second"]) * 100 if baseline["operations_per_second"] > 0 else 0
        
        return {
            "baseline": baseline,
            "current": current,
            "time_difference_seconds": time_diff,
            "time_difference_percent": time_diff_pct,
            "throughput_difference": throughput_diff,
            "throughput_difference_percent": throughput_diff_pct,
            "performance_change": "improved" if time_diff < 0 else "degraded" if time_diff > 0 else "stable",
            "significance": "significant" if abs(time_diff_pct) > 10 else "moderate" if abs(time_diff_pct) > 5 else "minor"
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """生成基准测试报告"""
        return {
            "timestamp": time.time(),
            "test_cases": len(self.test_cases),
            "total_runs": sum(tc["runs"] for tc in self.test_cases.values()),
            "total_time": sum(tc["total_time"] for tc in self.test_cases.values()),
            "results": self.benchmark_results,
            "summary": self._generate_summary()
        }
    
    def _generate_summary(self) -> Dict[str, Any]:
        """生成摘要"""
        if not self.benchmark_results:
            return {}
        
        avg_times = [r["average_time_seconds"] for r in self.benchmark_results.values()]
        throughputs = [r["operations_per_second"] for r in self.benchmark_results.values()]
        
        return {
            "fastest_test": min(self.benchmark_results.items(), 
                               key=lambda x: x[1]["average_time_seconds"])[0],
            "slowest_test": max(self.benchmark_results.items(), 
                               key=lambda x: x[1]["average_time_seconds"])[0],
            "average_time": statistics.mean(avg_times) if avg_times else 0,
            "median_time": statistics.median(avg_times) if avg_times else 0,
            "average_throughput": statistics.mean(throughputs) if throughputs else 0,
            "total_operations": sum(r["iterations"] for r in self.benchmark_results.values())
        }


class PerformanceTuner:
    """性能调优器"""
    
    def __init__(self, monitor: MemoryPerformanceMonitor):
        self.monitor = monitor
        self.tuning_history = []
        self.parameter_space = {}
        self.best_parameters = {}
        self.best_score = float('-inf')
        
    def define_parameter(self, name: str, 
                        param_type: str,
                        min_value: float = None,
                        max_value: float = None,
                        options: List[Any] = None):
        """定义调优参数"""
        self.parameter_space[name] = {
            "type": param_type,
            "min": min_value,
            "max": max_value,
            "options": options,
            "current_value": None,
            "best_value": None
        }
    
    def tune(self, objective_function: Callable[[Dict[str, Any]], float],
            max_iterations: int = 100,
            method: str = "random_search"):
        """执行参数调优"""
        
        if method == "random_search":
            return self._random_search(objective_function, max_iterations)
        elif method == "grid_search":
            return self._grid_search(objective_function, max_iterations)
        else:
            raise ValueError(f"Unknown tuning method: {method}")
    
    def _random_search(self, objective_function: Callable[[Dict[str, Any]], float],
                      max_iterations: int) -> Dict[str, Any]:
        """随机搜索调优"""
        best_score = float('-inf')
        best_params = {}
        
        for i in range(max_iterations):
            # 生成随机参数
            params = {}
            for name, param_info in self.parameter_space.items():
                if param_info["type"] == "float":
                    min_val = param_info["min"] or 0
                    max_val = param_info["max"] or 1
                    params[name] = random.uniform(min_val, max_val)
                elif param_info["type"] == "int":
                    min_val = param_info["min"] or 0
                    max_val = param_info["max"] or 100
                    params[name] = random.randint(min_val, max_val)
                elif param_info["type"] == "categorical":
                    if param_info["options"]:
                        params[name] = random.choice(param_info["options"])
                    else:
                        params[name] = None
                else:
                    params[name] = None
            
            # 评估目标函数
            score = objective_function(params)
            
            # 记录结果
            self.tuning_history.append({
                "iteration": i,
                "parameters": params.copy(),
                "score": score,
                "timestamp": time.time()
            })
            
            # 更新最佳结果
            if score > best_score:
                best_score = score
                best_params = params.copy()
                
                # 更新参数空间中的最佳值
                for name, value in params.items():
                    self.parameter_space[name]["best_value"] = value
            
            # 记录到监控器
            if self.monitor:
                self.monitor.record_metric(
                    "tuning_score",
                    score,
                    tags={"iteration": str(i), "method": "random_search"}
                )
                self.monitor.record_metric(
                    "tuning_best_score",
                    best_score,
                    tags={"iteration": str(i), "method": "random_search"}
                )
        
        self.best_score = best_score
        self.best_parameters = best_params
        
        return {
            "best_score": best_score,
            "best_parameters": best_params,
            "total_iterations": max_iterations,
            "method": "random_search",
            "history_size": len(self.tuning_history)
        }
    
    def _grid_search(self, objective_function: Callable[[Dict[str, Any]], float],
                    max_iterations: int) -> Dict[str, Any]:
        """网格搜索调优"""
        # 简化实现：对于大量参数，网格搜索不可行
        # 这里只处理最多3个参数的情况
        param_names = list(self.parameter_space.keys())
        if len(param_names) > 3:
            print("警告：参数过多，网格搜索不可行，切换到随机搜索")
            return self._random_search(objective_function, max_iterations)
        
        # 生成参数网格
        param_grids = []
        for name in param_names:
            param_info = self.parameter_space[name]
            
            if param_info["type"] == "float":
                min_val = param_info["min"] or 0
                max_val = param_info["max"] or 1
                # 生成5个等间距点
                values = [min_val + (max_val - min_val) * i / 4 for i in range(5)]
            elif param_info["type"] == "int":
                min_val = param_info["min"] or 0
                max_val = param_info["max"] or 10
                values = list(range(min_val, max_val + 1))
                # 限制数量
                if len(values) > 10:
                    step = len(values) // 10
                    values = values[::step]
            elif param_info["type"] == "categorical":
                values = param_info["options"] or [None]
            else:
                values = [None]
            
            param_grids.append(values)
        
        # 计算总组合数
        total_combinations = 1
        for grid in param_grids:
            total_combinations *= len(grid)
        
        if total_combinations > max_iterations:
            # 太多组合，随机采样
            return self._random_search(objective_function, max_iterations)
        
        # 执行网格搜索
        best_score = float('-inf')
        best_params = {}
        iteration = 0
        
        # 递归生成所有组合
        from itertools import product
        for param_values in product(*param_grids):
            params = dict(zip(param_names, param_values))
            
            # 评估目标函数
            score = objective_function(params)
            
            # 记录结果
            self.tuning_history.append({
                "iteration": iteration,
                "parameters": params.copy(),
                "score": score,
                "timestamp": time.time()
            })
            
            iteration += 1
            
            # 更新最佳结果
            if score > best_score:
                best_score = score
                best_params = params.copy()
                
                # 更新参数空间中的最佳值
                for name, value in params.items():
                    self.parameter_space[name]["best_value"] = value
            
            # 记录到监控器
            if self.monitor:
                self.monitor.record_metric(
                    "tuning_score",
                    score,
                    tags={"iteration": str(iteration), "method": "grid_search"}
                )
        
        self.best_score = best_score
        self.best_parameters = best_params
        
        return {
            "best_score": best_score,
            "best_parameters": best_params,
            "total_iterations": iteration,
            "method": "grid_search",
            "history_size": len(self.tuning_history)
        }
    
    def apply_best_parameters(self, target_object: Any):
        """应用最佳参数到目标对象"""
        for param_name, param_value in self.best_parameters.items():
            if hasattr(target_object, param_name):
                setattr(target_object, param_name, param_value)
            elif hasattr(target_object, f"set_{param_name}"):
                getattr(target_object, f"set_{param_name}")(param_value)
    
    def get_tuning_report(self) -> Dict[str, Any]:
        """获取调优报告"""
        return {
            "best_score": self.best_score,
            "best_parameters": self.best_parameters,
            "parameter_space": self.parameter_space,
            "tuning_history_size": len(self.tuning_history),
            "summary": self._generate_tuning_summary()
        }
    
    def _generate_tuning_summary(self) -> Dict[str, Any]:
        """生成调优摘要"""
        if not self.tuning_history:
            return {}
        
        scores = [entry["score"] for entry in self.tuning_history]
        
        return {
            "score_range": (min(scores), max(scores)) if scores else (0, 0),
            "average_score": statistics.mean(scores) if scores else 0,
            "score_std": statistics.stdev(scores) if len(scores) > 1 else 0,
            "improvement": self.best_score - scores[0] if scores else 0,
            "improvement_percent": ((self.best_score - scores[0]) / abs(scores[0])) * 100 if scores and scores[0] != 0 else 0
        }


# ============================================================================
# 第五部分：测试用例
# ============================================================================

def run_tests():
    """运行所有测试用例"""
    print("🚀 开始运行记忆系统性能优化测试...")
    
    # 初始化监控器
    monitor = MemoryPerformanceMonitor()
    
    # 测试1: 缓存系统
    print("\n🧪 测试1: 缓存系统")
    cache = MemoryCache(max_size=5, policy=CacheEvictionPolicy.LRU)
    
    # 添加数据
    for i in range(10):
        cache.set(f"key_{i}", f"value_{i}")
    
    # 测试命中
    hit_value = cache.get("key_5")
    assert hit_value == "value_5", f"缓存命中测试失败: {hit_value}"
    
    # 测试淘汰（LRU应该淘汰了key_0到key_4）
    miss_value = cache.get("key_0")
    assert miss_value is None, f"缓存淘汰测试失败: {miss_value}"
    
    # 获取统计
    stats = cache.get_statistics()
    assert stats["total_entries"] == 5, f"缓存大小测试失败: {stats['total_entries']}"
    assert stats["evictions"] >= 5, f"缓存淘汰次数测试失败: {stats['evictions']}"
    
    print("✅ 缓存系统测试通过")
    
    # 测试2: 性能监控
    print("\n🧪 测试2: 性能监控")
    
    # 记录一些指标
    for i in range(100):
        monitor.record_metric("extraction_time", random.uniform(10, 200))
        monitor.record_metric("cache_hit_rate", random.uniform(0.5, 0.9))
        monitor.record_metric("memory_usage", random.uniform(100, 1000))
    
    # 获取报告
    report = monitor.get_performance_report(time_window=3600)
    assert "metrics" in report, "性能报告缺少metrics"
    assert "extraction_time" in report["metrics"], "性能报告缺少extraction_time指标"
    
    print("✅ 性能监控测试通过")
    
    # 测试3: 索引优化
    print("\n🧪 测试3: 索引优化")
    optimizer = IndexOptimizer(monitor)
    
    # 创建测试数据
    test_data = [
        {"id": i, "name": f"item_{i}", "category": f"cat_{i % 3}"}
        for i in range(1000)
    ]
    
    # 创建索引
    optimizer.create_index("category", test_data)
    
    # 使用索引查询
    results = optimizer.query_with_index("category", "cat_1", test_data)
    assert len(results) == 334, f"索引查询结果数量错误: {len(results)}"  # 1000/3 ≈ 333.33
    
    # 获取索引统计
    index_stats = optimizer.get_index_statistics()
    assert "category" in index_stats, "索引统计缺少category"
    
    print("✅ 索引优化测试通过")
    
    # 测试4: 批量操作
    print("\n🧪 测试4: 批量操作")
    batch_optimizer = BatchOperationOptimizer(monitor, batch_size=10)
    
    def mock_operation(x):
        time.sleep(0.001)  # 模拟耗时操作
        return x * 2
    
    # 添加操作
    for i in range(25):
        batch_optimizer.add_operation(mock_operation, i)
    
    # 手动触发flush
    results = batch_optimizer.flush()
    assert len(results) == 25, f"批量操作结果数量错误: {len(results)}"
    
    batch_stats = batch_optimizer.get_statistics()
    assert batch_stats["batches_executed"] > 0, "批量操作执行次数错误"
    
    print("✅ 批量操作测试通过")
    
    # 测试5: 数据分区
    print("\n🧪 测试5: 数据分区")
    partition_optimizer = DataPartitionOptimizer(monitor, partition_key="category")
    
    # 创建分区
    partition_optimizer.create_partition("cat_0")
    partition_optimizer.create_partition("cat_1")
    partition_optimizer.create_partition("cat_2")
    
    # 添加数据
    for item in test_data:
        partition_optimizer.add_to_partition(item)
    
    # 查询分区
    cat_0_items = partition_optimizer.query_partition("cat_0")
    assert len(cat_0_items) > 0, "分区查询结果为空"
    
    partition_stats = partition_optimizer.get_statistics()
    assert partition_stats["partition_count"] == 3, f"分区数量错误: {partition_stats['partition_count']}"
    
    print("✅ 数据分区测试通过")
    
    # 测试6: 性能基准测试
    print("\n🧪 测试6: 性能基准测试")
    benchmark = PerformanceBenchmark(monitor)
    
    def test_cache_performance():
        cache = MemoryCache(max_size=100)
        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}")
        for i in range(100):
            cache.get(f"key_{i}")
    
    benchmark.register_test_case("cache_performance", test_cache_performance, "缓存性能测试")
    
    results = benchmark.run_benchmark("cache_performance", iterations=50, warmup_iterations=5)
    assert "cache_performance" in results, "基准测试结果缺少cache_performance"
    assert results["cache_performance"]["iterations"] == 50, "基准测试迭代次数错误"
    
    print("✅ 性能基准测试通过")
    
    # 测试7: 自适应缓存
    print("\n🧪 测试7: 自适应缓存")
    adaptive_cache = AdaptiveCache(max_size=10)
    
    # 模拟访问模式（偏向某些键）
    for i in range(100):
        for j in range(5):  # 频繁访问前5个键
            adaptive_cache.get(f"key_{j % 3}")
        adaptive_cache.set(f"key_{i % 20}", f"value_{i}")
    
    adaptive_stats = adaptive_cache.get_statistics()
    assert adaptive_stats["total_accesses"] > 0, "自适应缓存访问次数错误"
    
    print("✅ 自适应缓存测试通过")
    
    # 测试8: 性能调优
    print("\n🧪 测试8: 性能调优")
    tuner = PerformanceTuner(monitor)
    
    # 定义参数
    tuner.define_parameter("cache_size", "int", min_value=10, max_value=1000)
    tuner.define_parameter("batch_size", "int", min_value=1, max_value=100)
    
    def objective_function(params):
        # 模拟目标函数（缓存命中率）
        cache_size = params["cache_size"]
        batch_size = params["batch_size"]
        
        # 简单的模拟：缓存大小越大，命中率越高；批处理大小适中最好
        hit_rate = min(0.9, cache_size / 2000)
        batch_efficiency = 1 - abs(batch_size - 50) / 100
        
        return hit_rate * 0.7 + batch_efficiency * 0.3
    
    tuning_result = tuner.tune(objective_function, max_iterations=20, method="random_search")
    assert "best_score" in tuning_result, "调优结果缺少best_score"
    assert "best_parameters" in tuning_result, "调优结果缺少best_parameters"
    
    print("✅ 性能调优测试通过")
    
    # 生成最终报告
    final_report = monitor.get_performance_report()
    print(f"\n📊 最终性能报告:")
    print(f"   监控指标数量: {len(final_report['metrics'])}")
    print(f"   告警数量: {len(final_report['alerts'])}")
    print(f"   优化建议: {len(final_report['recommendations'])}")
    
    print("\n🎉 所有测试通过！")
    return True


# ============================================================================
# 主程序
# ============================================================================

def main():
    """主演示程序"""
    print("=" * 80)
    print("🧠 记忆系统性能优化演示")
    print("=" * 80)
    
    # 初始化监控器
    monitor = MemoryPerformanceMonitor()
    
    # 创建缓存系统
    print("\n1. 创建LRU缓存系统 (最大容量: 100)")
    cache = MemoryCache(max_size=100, policy=CacheEvictionPolicy.LRU)
    
    # 模拟数据加载
    print("   加载测试数据...")
    test_data = {}
    for i in range(200):
        key = f"user_{i % 50}_item_{i}"
        value = {
            "id": i,
            "name": f"Item {i}",
            "price": random.uniform(10, 1000),
            "category": f"cat_{i % 5}",
            "timestamp": time.time()
        }
        test_data[key] = value
    
    # 填充缓存
    print("   填充缓存...")
    for key, value in test_data.items():
        cache.set(key, value)
    
    # 模拟访问模式
    print("   模拟访问模式...")
    access_pattern = []
    for _ in range(1000):
        # 80%的访问集中在20%的数据上（帕累托分布）
        if random.random() < 0.8:
            key = f"user_{random.randint(0, 9)}_item_{random.randint(0, 39)}"
        else:
            key = f"user_{random.randint(10, 49)}_item_{random.randint(40, 199)}"
        
        access_pattern.append(key)
        
        # 访问缓存
        start_time = time.time()
        value = cache.get(key)
        access_time = (time.time() - start_time) * 1000  # 毫秒
        
        # 记录性能指标
        monitor.record_metric("cache_access_time", access_time)
        monitor.record_metric("cache_hit", 1 if value is not None else 0)
        
        # 如果未命中，从"存储"加载
        if value is None and key in test_data:
            # 模拟存储访问延迟
            time.sleep(0.001)
            cache.set(key, test_data[key])
    
    # 显示缓存统计
    cache_stats = cache.get_statistics()
    print(f"\n2. 缓存统计:")
    print(f"   总条目数: {cache_stats['total_entries']}")
    print(f"   命中率: {cache_stats['hit_rate']:.2%}")
    print(f"   淘汰次数: {cache_stats['evictions']}")
    print(f"   总访问次数: {cache_stats['total_accesses']}")
    
    # 创建索引优化器
    print("\n3. 创建索引优化器")
    index_optimizer = IndexOptimizer(monitor)
    
    # 创建测试数据
    users = [
        {"id": i, "name": f"User_{i}", "age": random.randint(18, 60), "city": f"City_{i % 10}"}
        for i in range(1000)
    ]
    
    # 为城市字段创建索引
    index_optimizer.create_index("city", users)
    
    # 使用索引查询
    start_time = time.time()
    city_users = index_optimizer.query_with_index("city", "City_5", users)
    index_query_time = (time.time() - start_time) * 1000
    
    print(f"   索引查询时间: {index_query_time:.2f}ms")
    print(f"   查询结果数量: {len(city_users)}")
    
    # 显示索引统计
    index_stats = index_optimizer.get_index_statistics()
    print(f"   索引命中率: {index_stats.get('city', {}).get('hit_rate', 0):.2%}")
    
    # 批量操作演示
    print("\n4. 批量操作优化")
    batch_optimizer = BatchOperationOptimizer(monitor, batch_size=50)
    
    def process_item(item_id):
        # 模拟处理逻辑
        time.sleep(0.0005)
        return f"processed_{item_id}"
    
    # 添加批量操作
    print("   添加1000个处理操作...")
    for i in range(1000):
        batch_optimizer.add_operation(process_item, i)
    
    # 执行剩余操作
    batch_optimizer.flush()
    
    batch_stats = batch_optimizer.get_statistics()
    print(f"   批量执行次数: {batch_stats['batches_executed']}")
    print(f"   总操作数: {batch_stats['total_operations']}")
    print(f"   节省时间: {batch_stats['total_saved_time']:.3f}秒")
    
    # 数据分区演示
    print("\n5. 数据分区优化")
    partition_optimizer = DataPartitionOptimizer(monitor, partition_key="city")
    
    # 自动创建分区
    for user in users:
        partition_optimizer.add_to_partition(user)
    
    partition_stats = partition_optimizer.get_statistics()
    print(f"   分区数量: {partition_stats['partition_count']}")
    print(f"   总数据项: {partition_stats['total_items']}")
    print(f"   分区命中率: {partition_stats['partition_hits'] / max(1, partition_stats['partition_hits'] + partition_stats['partition_misses']):.2%}")
    
    # 性能报告
    print("\n6. 性能分析报告")
    report = monitor.get_performance_report(time_window=300)  # 最近5分钟
    
    # 显示关键指标
    print("   关键性能指标:")
    for metric_name, metric_data in report["metrics"].items():
        if metric_name in ["cache_access_time", "cache_hit_rate", "index_query_time"]:
            current = metric_data["trend"]["current"]
            avg = metric_data["trend"]["average"]
            unit = monitor.metric_definitions.get(metric_name, {}).get("unit", "")
            print(f"     {metric_name}: {current:.2f}{unit} (平均: {avg:.2f}{unit})")
    
    # 显示优化建议
    if report["recommendations"]:
        print("\n   优化建议:")
        for rec in report["recommendations"][:3]:  # 显示前3个建议
            print(f"     [{rec['priority'].upper()}] {rec['message']}")
    
    print("\n" + "=" * 80)
    print("演示完成！使用 --test 参数运行完整测试套件。")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # 运行测试模式
        try:
            success = run_tests()
            sys.exit(0 if success else 1)
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        # 运行演示模式
        main()