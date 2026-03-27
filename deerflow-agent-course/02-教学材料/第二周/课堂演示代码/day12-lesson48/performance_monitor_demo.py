#!/usr/bin/env python3
"""
Day 12 - 第48节课：子代理性能优化
==================================

本演示代码实现子代理性能监控和优化系统，包括：
1. PerformanceMonitor - 性能监控器，记录和分析各种指标
2. ConnectionPool - 连接池，复用连接减少开销
3. CacheManager - 缓存管理器，支持TTL和LRU淘汰
4. BottleneckAnalyzer - 瓶颈分析器，识别性能问题
5. OptimizationAdvisor - 优化建议器，提供改进建议

运行方式:
    python performance_monitor_demo.py          # 运行演示
    python performance_monitor_demo.py --test   # 运行测试
"""

import time
import threading
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import heapq
import sys


# ============================================================================
# 第一部分：性能监控核心指标定义
# ============================================================================

class MetricType(Enum):
    """性能指标类型枚举
    
    定义子代理系统需要监控的核心指标类型：
    - EXECUTION_TIME: 任务执行时间（毫秒）
    - MEMORY_USAGE: 内存使用量（MB）
    - SUCCESS_RATE: 成功率（0-1之间的小数）
    - QUEUE_TIME: 队列等待时间（毫秒）
    - THROUGHPUT: 吞吐量（任务/秒）
    """
    EXECUTION_TIME = "execution_time"
    MEMORY_USAGE = "memory_usage"
    SUCCESS_RATE = "success_rate"
    QUEUE_TIME = "queue_time"
    THROUGHPUT = "throughput"


@dataclass
class MetricRecord:
    """单条性能指标记录
    
    包含：
    - value: 指标值
    - timestamp: 记录时间戳
    - metadata: 附加元数据（如任务ID、代理类型等）
    """
    value: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 第二部分：性能监控器实现
# ============================================================================

class PerformanceMonitor:
    """子代理性能监控器
    
    核心功能：
    1. 指标记录 - 记录各种性能指标
    2. 滑动窗口统计 - 只关注最近N条数据
    3. 性能评分 - 综合多指标计算0-100分
    4. 瓶颈识别 - 自动发现性能问题
    
    设计原则：
    - 线程安全：支持并发记录指标
    - 低开销：监控本身不应影响性能
    - 可扩展：支持自定义指标和评分规则
    """
    
    def __init__(self, window_size: int = 100):
        """初始化性能监控器
        
        Args:
            window_size: 滑动窗口大小，只保留最近N条记录
        """
        self.window_size = window_size
        # 存储各指标的历史记录（使用deque实现固定大小的滑动窗口）
        self.metrics: Dict[MetricType, deque] = {
            metric_type: deque(maxlen=window_size)
            for metric_type in MetricType
        }
        # 线程锁，保证并发安全
        self._lock = threading.Lock()
        
        # 性能评分权重配置（总和应为1.0）
        # 成功率权重最高，因为系统可用性最重要
        self.weights = {
            MetricType.SUCCESS_RATE: 0.40,      # 40% - 最重要
            MetricType.EXECUTION_TIME: 0.25,     # 25% - 响应速度
            MetricType.MEMORY_USAGE: 0.20,       # 20% - 资源效率
            MetricType.QUEUE_TIME: 0.10,         # 10% - 队列效率
            MetricType.THROUGHPUT: 0.05,         # 5% - 吞吐量
        }
    
    def record_metric(self, metric_type: MetricType, value: float, 
                      metadata: Optional[Dict] = None) -> None:
        """记录单条性能指标
        
        Args:
            metric_type: 指标类型
            value: 指标值
            metadata: 附加元数据
        """
        with self._lock:
            record = MetricRecord(value=value, metadata=metadata or {})
            self.metrics[metric_type].append(record)
    
    def record_execution(self, duration_ms: float, success: bool,
                         memory_mb: float = 0, queue_time_ms: float = 0) -> None:
        """记录一次完整的任务执行
        
        便捷方法，同时记录多个相关指标
        
        Args:
            duration_ms: 执行时长（毫秒）
            success: 是否成功
            memory_mb: 内存使用（MB）
            queue_time_ms: 队列等待时间（毫秒）
        """
        self.record_metric(MetricType.EXECUTION_TIME, duration_ms)
        self.record_metric(MetricType.SUCCESS_RATE, 1.0 if success else 0.0)
        if memory_mb > 0:
            self.record_metric(MetricType.MEMORY_USAGE, memory_mb)
        if queue_time_ms > 0:
            self.record_metric(MetricType.QUEUE_TIME, queue_time_ms)
    
    def get_recent_metrics(self, metric_type: MetricType, 
                          count: Optional[int] = None) -> List[float]:
        """获取最近的指标值列表
        
        Args:
            metric_type: 指标类型
            count: 要获取的数量，None表示全部
            
        Returns:
            指标值列表（从旧到新）
        """
        with self._lock:
            records = list(self.metrics[metric_type])
            if count is not None:
                records = records[-count:]
            return [r.value for r in records]
    
    def calculate_average(self, metric_type: MetricType) -> float:
        """计算指标平均值
        
        Args:
            metric_type: 指标类型
            
        Returns:
            平均值，无数据时返回0
        """
        values = self.get_recent_metrics(metric_type)
        return sum(values) / len(values) if values else 0.0
    
    def calculate_percentile(self, metric_type: MetricType, 
                            percentile: float) -> float:
        """计算指标百分位数
        
        用于分析尾部延迟等极端情况
        
        Args:
            metric_type: 指标类型
            percentile: 百分位（0-100）
            
        Returns:
            百分位数值
        """
        values = self.get_recent_metrics(metric_type)
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]
    
    def normalize_value(self, value: float, metric_type: MetricType) -> float:
        """归一化指标值到0-100分
        
        不同指标需要不同的归一化策略：
        - 越高越好的指标（成功率、吞吐量）：直接映射
        - 越低越好的指标（执行时间、内存）：反向映射
        
        Args:
            value: 原始值
            metric_type: 指标类型
            
        Returns:
            归一化后的分数（0-100）
        """
        # 定义各指标的参考范围
        ranges = {
            MetricType.SUCCESS_RATE: (0, 1),       # 0-1之间
            MetricType.EXECUTION_TIME: (10, 1000),  # 10ms-1000ms
            MetricType.MEMORY_USAGE: (10, 500),     # 10MB-500MB
            MetricType.QUEUE_TIME: (0, 500),        # 0ms-500ms
            MetricType.THROUGHPUT: (1, 100),        # 1-100任务/秒
        }
        
        min_val, max_val = ranges.get(metric_type, (0, 100))
        
        # 越低越好的指标需要反向处理
        if metric_type in [MetricType.EXECUTION_TIME, MetricType.MEMORY_USAGE, 
                          MetricType.QUEUE_TIME]:
            # 反向：值越小，分数越高
            if value <= min_val:
                return 100.0
            elif value >= max_val:
                return 0.0
            else:
                return 100.0 * (1 - (value - min_val) / (max_val - min_val))
        else:
            # 正向：值越大，分数越高
            if value <= min_val:
                return 0.0
            elif value >= max_val:
                return 100.0
            else:
                return 100.0 * (value - min_val) / (max_val - min_val)
    
    def get_performance_score(self) -> float:
        """计算综合性能评分（0-100分）
        
        使用加权平均计算各指标的综合得分：
        Score = Σ(weight_i × normalized_value_i)
        
        Returns:
            综合性能评分（0-100）
        """
        total_score = 0.0
        total_weight = 0.0
        
        for metric_type, weight in self.weights.items():
            avg_value = self.calculate_average(metric_type)
            if avg_value > 0 or metric_type == MetricType.SUCCESS_RATE:
                normalized = self.normalize_value(avg_value, metric_type)
                total_score += weight * normalized
                total_weight += weight
        
        # 避免除零
        if total_weight == 0:
            return 0.0
        
        # normalize_value already returns 0-100, so just divide by total_weight
        return total_score / total_weight
    
    def get_bottleneck_analysis(self) -> Dict[str, Any]:
        """分析性能瓶颈
        
        识别低于阈值的指标，提供优化建议
        
        Returns:
            包含瓶颈信息和建议的字典
        """
        bottlenecks = []
        suggestions = []
        
        # 各指标的健康阈值
        thresholds = {
            MetricType.EXECUTION_TIME: {"max": 200, "unit": "ms"},
            MetricType.MEMORY_USAGE: {"max": 200, "unit": "MB"},
            MetricType.QUEUE_TIME: {"max": 100, "unit": "ms"},
            MetricType.SUCCESS_RATE: {"min": 0.95, "unit": ""},
            MetricType.THROUGHPUT: {"min": 10, "unit": "tasks/s"},
        }
        
        for metric_type, threshold in thresholds.items():
            avg_value = self.calculate_average(metric_type)
            
            # 检查是否超过阈值
            if "max" in threshold and avg_value > threshold["max"]:
                bottlenecks.append({
                    "metric": metric_type.value,
                    "current": avg_value,
                    "threshold": threshold["max"],
                    "severity": "high" if avg_value > threshold["max"] * 1.5 else "medium"
                })
                # 根据指标类型提供优化建议
                if metric_type == MetricType.EXECUTION_TIME:
                    suggestions.append("考虑使用缓存或预加载优化执行时间")
                elif metric_type == MetricType.MEMORY_USAGE:
                    suggestions.append("检查内存泄漏，考虑对象池或连接池")
                elif metric_type == MetricType.QUEUE_TIME:
                    suggestions.append("增加处理并发度或优化任务调度")
            
            # 检查是否低于最小值
            if "min" in threshold and 0 < avg_value < threshold["min"]:
                bottlenecks.append({
                    "metric": metric_type.value,
                    "current": avg_value,
                    "threshold": threshold["min"],
                    "severity": "high" if avg_value < threshold["min"] * 0.5 else "medium"
                })
                if metric_type == MetricType.SUCCESS_RATE:
                    suggestions.append("检查错误处理和重试机制")
                elif metric_type == MetricType.THROUGHPUT:
                    suggestions.append("考虑并行执行或负载均衡")
        
        return {
            "has_bottleneck": len(bottlenecks) > 0,
            "bottlenecks": bottlenecks,
            "suggestions": suggestions,
            "overall_score": self.get_performance_score()
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能监控摘要
        
        Returns:
            包含所有关键指标统计的字典
        """
        return {
            "sample_count": {mt.value: len(self.metrics[mt]) for mt in MetricType},
            "averages": {mt.value: self.calculate_average(mt) for mt in MetricType},
            "p95": {mt.value: self.calculate_percentile(mt, 95) for mt in MetricType},
            "p99": {mt.value: self.calculate_percentile(mt, 99) for mt in MetricType},
            "performance_score": self.get_performance_score(),
            "bottleneck_analysis": self.get_bottleneck_analysis()
        }


# ============================================================================
# 第三部分：连接池实现
# ============================================================================

class Connection:
    """模拟连接对象"""
    
    def __init__(self, connection_id: int):
        self.id = connection_id
        self.is_active = True
        self.created_at = time.time()
        self.last_used_at = time.time()
    
    def execute(self, query: str) -> str:
        """执行查询（模拟）"""
        if not self.is_active:
            raise RuntimeError("Connection is closed")
        self.last_used_at = time.time()
        time.sleep(0.01)  # 模拟网络延迟
        return f"Result of: {query}"


class ConnectionPool:
    """连接池管理器
    
    实现连接复用，减少创建/销毁开销：
    1. 预创建一定数量的连接
    2. 获取连接时优先复用空闲连接
    3. 释放连接时返回池中而非关闭
    4. 支持最大连接数限制
    5. 支持空闲连接自动回收
    
    使用方式：
        pool = ConnectionPool(max_size=10)
        conn = pool.acquire()  # 获取连接
        try:
            result = conn.execute("SELECT ...")
        finally:
            pool.release(conn)  # 释放连接
    """
    
    def __init__(self, max_size: int = 10, idle_timeout: float = 60.0):
        """初始化连接池
        
        Args:
            max_size: 最大连接数
            idle_timeout: 空闲连接超时时间（秒）
        """
        self.max_size = max_size
        self.idle_timeout = idle_timeout
        
        # 空闲连接队列
        self._available: List[Connection] = []
        # 正在使用的连接集合
        self._in_use: Dict[int, Connection] = {}
        # 连接计数器
        self._connection_counter = 0
        # 线程锁
        self._lock = threading.Lock()
        
        # 性能统计
        self.stats = {
            "created": 0,
            "reused": 0,
            "timeouts": 0,
            "acquire_time_total": 0.0
        }
    
    def _create_connection(self) -> Connection:
        """创建新连接（内部方法）"""
        self._connection_counter += 1
        self.stats["created"] += 1
        return Connection(self._connection_counter)
    
    def acquire(self, timeout: float = 5.0) -> Connection:
        """获取连接
        
        Args:
            timeout: 获取超时时间（秒）
            
        Returns:
            可用的连接对象
            
        Raises:
            TimeoutError: 超时无法获取连接
        """
        start_time = time.time()
        
        with self._lock:
            # 清理过期的空闲连接
            self._cleanup_idle_connections()
            
            # 尝试复用空闲连接
            if self._available:
                conn = self._available.pop()
                self._in_use[conn.id] = conn
                self.stats["reused"] += 1
                self.stats["acquire_time_total"] += time.time() - start_time
                return conn
            
            # 检查是否可以创建新连接
            total_connections = len(self._available) + len(self._in_use)
            if total_connections < self.max_size:
                conn = self._create_connection()
                self._in_use[conn.id] = conn
                self.stats["acquire_time_total"] += time.time() - start_time
                return conn
        
        # 等待其他连接释放
        deadline = start_time + timeout
        while time.time() < deadline:
            time.sleep(0.01)
            with self._lock:
                if self._available:
                    conn = self._available.pop()
                    self._in_use[conn.id] = conn
                    self.stats["reused"] += 1
                    self.stats["acquire_time_total"] += time.time() - start_time
                    return conn
        
        self.stats["timeouts"] += 1
        raise TimeoutError("Failed to acquire connection within timeout")
    
    def release(self, conn: Connection) -> None:
        """释放连接回池中
        
        Args:
            conn: 要释放的连接
        """
        with self._lock:
            if conn.id in self._in_use:
                del self._in_use[conn.id]
                if conn.is_active:
                    self._available.append(conn)
    
    def _cleanup_idle_connections(self) -> None:
        """清理过期的空闲连接"""
        current_time = time.time()
        active_connections = []
        
        for conn in self._available:
            if current_time - conn.last_used_at < self.idle_timeout:
                active_connections.append(conn)
        
        self._available = active_connections
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        with self._lock:
            return {
                "max_size": self.max_size,
                "available": len(self._available),
                "in_use": len(self._in_use),
                "total_created": self._connection_counter,
                "created": self.stats["created"],
                "reused": self.stats["reused"],
                "reuse_rate": self.stats["reused"] / max(1, self.stats["created"] + self.stats["reused"]),
                "timeouts": self.stats["timeouts"],
                "avg_acquire_time": self.stats["acquire_time_total"] / max(1, self.stats["created"] + self.stats["reused"])
            }
    
    def shutdown(self) -> None:
        """关闭连接池，释放所有连接"""
        with self._lock:
            for conn in self._available:
                conn.is_active = False
            for conn in self._in_use.values():
                conn.is_active = False
            self._available.clear()
            self._in_use.clear()


# ============================================================================
# 第四部分：缓存管理器实现
# ============================================================================

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: float = 300.0  # 默认5分钟过期
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() - self.created_at > self.ttl
    
    def access(self) -> None:
        """记录访问"""
        self.last_accessed_at = time.time()
        self.access_count += 1


class CacheManager:
    """缓存管理器
    
    实现高性能缓存，支持：
    1. TTL（Time To Live）过期机制
    2. LRU（Least Recently Used）淘汰策略
    3. 命中率统计
    4. 线程安全
    
    使用场景：
    - 缓存子代理的执行结果
    - 缓存配置信息
    - 缓存频繁查询的数据
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        """初始化缓存管理器
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        
        # 缓存存储
        self._cache: Dict[str, CacheEntry] = {}
        # LRU链表（使用有序字典模拟）
        self._access_order: List[str] = []
        # 线程锁
        self._lock = threading.Lock()
        
        # 统计信息
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，不存在或已过期返回None
        """
        with self._lock:
            if key not in self._cache:
                self.stats["misses"] += 1
                return None
            
            entry = self._cache[key]
            
            # 检查是否过期
            if entry.is_expired:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self.stats["expirations"] += 1
                self.stats["misses"] += 1
                return None
            
            # 更新访问记录
            entry.access()
            self._update_access_order(key)
            self.stats["hits"] += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None使用默认值
        """
        with self._lock:
            # 如果已存在，先删除旧条目
            if key in self._cache:
                self._access_order.remove(key)
            
            # 检查是否需要淘汰
            while len(self._cache) >= self.max_size:
                self._evict_one()
            
            # 添加新条目
            entry = CacheEntry(
                key=key,
                value=value,
                ttl=ttl if ttl is not None else self.default_ttl
            )
            self._cache[key] = entry
            self._access_order.append(key)
    
    def _evict_one(self) -> None:
        """淘汰一个最近最少使用的条目"""
        if self._access_order:
            lru_key = self._access_order.pop(0)
            if lru_key in self._cache:
                del self._cache[lru_key]
                self.stats["evictions"] += 1
    
    def _update_access_order(self, key: str) -> None:
        """更新访问顺序（将key移到最后）"""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def delete(self, key: str) -> bool:
        """删除缓存条目
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def cleanup_expired(self) -> int:
        """清理所有过期条目
        
        Returns:
            清理的条目数
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            self.stats["expirations"] += len(expired_keys)
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "hit_rate": self.stats["hits"] / max(1, total_requests),
                "evictions": self.stats["evictions"],
                "expirations": self.stats["expirations"]
            }


# ============================================================================
# 第五部分：优化建议器
# ============================================================================

class OptimizationAdvisor:
    """优化建议器
    
    基于性能监控数据，自动提供优化建议：
    1. 分析瓶颈指标
    2. 匹配优化策略
    3. 估算优化效果
    4. 生成实施建议
    """
    
    # 优化策略库
    STRATEGIES = {
        "cache": {
            "name": "缓存优化",
            "description": "缓存频繁访问的结果，减少重复计算",
            "applicable_metrics": ["execution_time", "success_rate"],
            "expected_improvement": "执行时间减少30-70%"
        },
        "preload": {
            "name": "预加载",
            "description": "预先加载常用资源，避免首次访问延迟",
            "applicable_metrics": ["execution_time", "queue_time"],
            "expected_improvement": "首次响应时间减少50-80%"
        },
        "connection_pool": {
            "name": "连接池",
            "description": "复用连接，减少创建销毁开销",
            "applicable_metrics": ["execution_time", "memory_usage"],
            "expected_improvement": "连接相关延迟减少60-90%"
        },
        "parallel": {
            "name": "并行执行",
            "description": "同时处理多个独立任务，提高吞吐量",
            "applicable_metrics": ["throughput", "queue_time"],
            "expected_improvement": "吞吐量提升100-400%"
        },
        "load_balance": {
            "name": "负载均衡",
            "description": "将任务均匀分配到多个处理单元",
            "applicable_metrics": ["execution_time", "queue_time", "memory_usage"],
            "expected_improvement": "整体延迟减少20-50%"
        }
    }
    
    @classmethod
    def analyze_and_recommend(cls, monitor: PerformanceMonitor) -> Dict[str, Any]:
        """分析性能数据并生成优化建议
        
        Args:
            monitor: 性能监控器实例
            
        Returns:
            包含分析结果和建议的字典
        """
        analysis = monitor.get_bottleneck_analysis()
        recommendations = []
        
        for bottleneck in analysis.get("bottlenecks", []):
            metric = bottleneck["metric"]
            
            # 匹配适用的优化策略
            for strategy_id, strategy in cls.STRATEGIES.items():
                if metric in strategy["applicable_metrics"]:
                    recommendations.append({
                        "strategy": strategy_id,
                        "name": strategy["name"],
                        "description": strategy["description"],
                        "target_metric": metric,
                        "current_value": bottleneck["current"],
                        "expected_improvement": strategy["expected_improvement"],
                        "priority": bottleneck["severity"]
                    })
        
        # 去重并排序
        seen_strategies = set()
        unique_recommendations = []
        for rec in sorted(recommendations, key=lambda x: x["priority"], reverse=True):
            if rec["strategy"] not in seen_strategies:
                seen_strategies.add(rec["strategy"])
                unique_recommendations.append(rec)
        
        return {
            "overall_score": analysis["overall_score"],
            "has_bottleneck": analysis["has_bottleneck"],
            "bottlenecks": analysis["bottlenecks"],
            "recommendations": unique_recommendations,
            "quick_wins": [r for r in unique_recommendations if r["priority"] == "medium"],
            "critical_improvements": [r for r in unique_recommendations if r["priority"] == "high"]
        }


# ============================================================================
# 第六部分：测试套件
# ============================================================================

def run_tests():
    """运行所有测试"""
    print("🧪 运行子代理性能优化测试套件")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 6
    
    # 测试1: PerformanceMonitor基本功能
    print("\n📊 测试1: PerformanceMonitor基本功能")
    try:
        monitor = PerformanceMonitor(window_size=10)
        
        # 记录一些指标
        monitor.record_execution(100, True, 50, 20)
        monitor.record_execution(150, True, 60, 30)
        monitor.record_execution(200, False, 70, 40)
        
        # 验证数据已记录
        exec_times = monitor.get_recent_metrics(MetricType.EXECUTION_TIME)
        assert len(exec_times) == 3, f"Expected 3 records, got {len(exec_times)}"
        
        # 验证平均值计算
        avg_exec = monitor.calculate_average(MetricType.EXECUTION_TIME)
        assert 145 <= avg_exec <= 155, f"Expected avg ~150, got {avg_exec}"
        
        print("   ✅ 基本记录和查询功能正常")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试2: 性能评分计算
    print("\n📊 测试2: 性能评分计算")
    try:
        monitor = PerformanceMonitor()
        
        # 模拟良好性能
        for _ in range(10):
            monitor.record_execution(50, True, 30, 10)
        
        score = monitor.get_performance_score()
        assert 70 <= score <= 100, f"Expected high score (70-100), got {score}"
        
        # 模拟糟糕性能
        monitor2 = PerformanceMonitor()
        for _ in range(10):
            monitor2.record_execution(800, False, 400, 400)
        
        score2 = monitor2.get_performance_score()
        assert score2 < score, f"Bad performance score ({score2}) should be lower than good ({score})"
        
        print(f"   ✅ 评分计算正常 (良好={score:.1f}, 糟糕={score2:.1f})")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试3: 瓶颈分析
    print("\n📊 测试3: 瓶颈分析")
    try:
        monitor = PerformanceMonitor()
        
        # 模拟高执行时间
        for _ in range(10):
            monitor.record_execution(500, True, 30, 10)
        
        analysis = monitor.get_bottleneck_analysis()
        assert analysis["has_bottleneck"], "Should detect bottleneck for high execution time"
        assert len(analysis["bottlenecks"]) > 0, "Should have at least one bottleneck"
        assert len(analysis["suggestions"]) > 0, "Should have suggestions"
        
        print(f"   ✅ 瓶颈分析正常 (检测到{len(analysis['bottlenecks'])}个瓶颈)")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试4: ConnectionPool连接复用
    print("\n📊 测试4: ConnectionPool连接复用")
    try:
        pool = ConnectionPool(max_size=5)
        
        # 获取并释放连接
        conn1 = pool.acquire()
        conn1_id = conn1.id
        pool.release(conn1)
        
        # 再次获取，应该是同一个连接
        conn2 = pool.acquire()
        assert conn2.id == conn1_id, f"Expected reused connection {conn1_id}, got {conn2.id}"
        
        stats = pool.get_stats()
        assert stats["reused"] >= 1, f"Should have reused at least 1 connection"
        
        pool.shutdown()
        print(f"   ✅ 连接复用正常 (创建={stats['created']}, 复用={stats['reused']})")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试5: CacheManager TTL过期
    print("\n📊 测试5: CacheManager TTL过期")
    try:
        cache = CacheManager(max_size=100, default_ttl=0.5)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1", "Should get value immediately"
        
        # 等待过期
        time.sleep(0.6)
        assert cache.get("key1") is None, "Should return None after TTL expired"
        
        stats = cache.get_stats()
        assert stats["expirations"] >= 1, "Should have recorded expiration"
        
        print(f"   ✅ TTL过期正常 (命中率={stats['hit_rate']:.2f})")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试6: CacheManager LRU淘汰
    print("\n📊 测试6: CacheManager LRU淘汰")
    try:
        cache = CacheManager(max_size=3)  # 小容量便于测试
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # 访问key1，使其最近使用
        cache.get("key1")
        
        # 添加第4个，应该淘汰key2（最近最少使用）
        cache.set("key4", "value4")
        
        assert cache.get("key1") == "value1", "key1 should still exist"
        assert cache.get("key4") == "value4", "key4 should exist"
        assert cache.get("key2") is None, "key2 should be evicted (LRU)"
        
        stats = cache.get_stats()
        print(f"   ✅ LRU淘汰正常 (大小={stats['size']}, 淘汰次数={stats['evictions']})")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试总结
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {tests_passed}/{tests_total} 通过")
    
    if tests_passed == tests_total:
        print("🎉 所有测试通过！")
    else:
        print(f"⚠️  有 {tests_total - tests_passed} 个测试失败")
    
    return tests_passed == tests_total


# ============================================================================
# 第七部分：演示主程序
# ============================================================================

def run_demo():
    """运行性能优化演示"""
    print("🚀 Day 12 - 第48节课：子代理性能优化演示")
    print("=" * 60)
    
    # 1. 演示性能监控
    print("\n📊 演示1: 性能监控器")
    print("-" * 40)
    
    monitor = PerformanceMonitor(window_size=100)
    
    # 模拟不同质量的任务执行
    print("模拟30次任务执行...")
    for i in range(30):
        # 前10次：良好性能
        if i < 10:
            duration = random.uniform(30, 80)
            success = random.random() > 0.05
            memory = random.uniform(20, 50)
        # 中间10次：一般性能
        elif i < 20:
            duration = random.uniform(100, 200)
            success = random.random() > 0.1
            memory = random.uniform(50, 100)
        # 后10次：糟糕性能
        else:
            duration = random.uniform(300, 500)
            success = random.random() > 0.3
            memory = random.uniform(150, 300)
        
        monitor.record_execution(duration, success, memory, duration * 0.2)
    
    # 显示性能摘要
    summary = monitor.get_summary()
    print(f"\n📈 性能摘要:")
    print(f"   综合评分: {summary['performance_score']:.1f}/100")
    print(f"   平均执行时间: {summary['averages']['execution_time']:.1f}ms")
    print(f"   平均内存使用: {summary['averages']['memory_usage']:.1f}MB")
    print(f"   平均成功率: {summary['averages']['success_rate']:.2%}")
    
    # 瓶颈分析
    print(f"\n🔍 瓶颈分析:")
    analysis = summary['bottleneck_analysis']
    if analysis['has_bottleneck']:
        for bottleneck in analysis['bottlenecks']:
            print(f"   ⚠️  {bottleneck['metric']}: {bottleneck['current']:.1f} (阈值: {bottleneck['threshold']}, 严重度: {bottleneck['severity']})")
        print(f"\n💡 优化建议:")
        for suggestion in analysis['suggestions']:
            print(f"   - {suggestion}")
    else:
        print("   ✅ 未检测到明显瓶颈")
    
    # 2. 演示连接池
    print("\n\n📊 演示2: 连接池")
    print("-" * 40)
    
    pool = ConnectionPool(max_size=5)
    
    print("模拟数据库连接使用...")
    results = []
    for i in range(10):
        conn = pool.acquire()
        result = conn.execute(f"SELECT * FROM table WHERE id = {i}")
        results.append(result)
        pool.release(conn)
        print(f"   请求 {i+1}: 使用连接 #{conn.id}")
    
    stats = pool.get_stats()
    print(f"\n📈 连接池统计:")
    print(f"   创建连接数: {stats['created']}")
    print(f"   复用连接数: {stats['reused']}")
    print(f"   复用率: {stats['reuse_rate']:.2%}")
    print(f"   平均获取时间: {stats['avg_acquire_time']*1000:.2f}ms")
    
    pool.shutdown()
    
    # 3. 演示缓存管理器
    print("\n\n📊 演示3: 缓存管理器")
    print("-" * 40)
    
    cache = CacheManager(max_size=5, default_ttl=2.0)
    
    print("模拟缓存使用场景...")
    # 设置一些缓存
    cache.set("user:1", {"name": "Alice", "role": "admin"})
    cache.set("user:2", {"name": "Bob", "role": "user"})
    cache.set("config:timeout", 30)
    
    # 多次访问
    for _ in range(5):
        cache.get("user:1")
        cache.get("config:timeout")
    
    cache.get("user:2")  # 访问较少
    cache.get("user:3")  # 未命中
    
    # 添加更多条目触发淘汰
    cache.set("user:4", {"name": "David"})
    cache.set("user:5", {"name": "Eve"})
    cache.set("user:6", {"name": "Frank"})  # 应该淘汰user:2
    
    stats = cache.get_stats()
    print(f"\n📈 缓存统计:")
    print(f"   当前大小: {stats['size']}/{stats['max_size']}")
    print(f"   命中次数: {stats['hits']}")
    print(f"   未命中次数: {stats['misses']}")
    print(f"   命中率: {stats['hit_rate']:.2%}")
    print(f"   淘汰次数: {stats['evictions']}")
    
    # 4. 演示优化建议
    print("\n\n📊 演示4: 优化建议系统")
    print("-" * 40)
    
    recommendations = OptimizationAdvisor.analyze_and_recommend(monitor)
    
    print(f"综合评分: {recommendations['overall_score']:.1f}/100")
    print(f"\n推荐的优化策略:")
    for rec in recommendations.get('recommendations', []):
        print(f"   🎯 {rec['name']} (优先级: {rec['priority']})")
        print(f"      目标指标: {rec['target_metric']}")
        print(f"      预期效果: {rec['expected_improvement']}")
        print()
    
    print("=" * 60)
    print("✅ 演示完成！")


if __name__ == "__main__":
    if "--test" in sys.argv:
        success = run_tests()
        sys.exit(0 if success else 1)
    else:
        run_demo()
