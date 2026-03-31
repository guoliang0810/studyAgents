#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第88节课：监控与指标

本课程介绍DeerFlow Agent系统中的监控与指标系统，包括：
1. 结构化日志系统 - 实现统一的日志格式和级别管理
2. 性能指标收集 - Counter、Gauge、Histogram指标类型
3. 健康检查机制 - 多层次服务可用性检测
4. 告警系统 - 基于阈值的告警触发和通知

作者：DeerFlow架构师训练营
"""

import time
import json
import logging
import threading
import os
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import unittest.mock as unittest


# ============================================================
# 第一部分：结构化日志系统
# ============================================================

class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class StructuredLogger:
    """
    结构化日志记录器
    
    提供统一的日志格式，支持JSON输出，便于日志收集和分析。
    适用于分布式系统的日志聚合场景。
    
    特性：
    - JSON格式输出
    - 上下文信息自动注入
    - 线程安全
    - 多级别支持
    """
    
    def __init__(self, name: str, level: LogLevel = LogLevel.INFO):
        """
        初始化结构化日志记录器
        
        Args:
            name: 日志记录器名称，通常为模块名
            level: 日志级别
        """
        self.name = name
        self.level = level
        self._context: Dict[str, Any] = {}
        self._handlers: List[Callable[[Dict], None]] = []
        self._lock = threading.RLock()
        
    def set_context(self, **kwargs) -> None:
        """
        设置日志上下文
        
        上下文信息会被注入到每条日志中，用于追踪请求、用户等信息。
        """
        with self._lock:
            self._context.update(kwargs)
            
    def clear_context(self) -> None:
        """清空日志上下文"""
        with self._lock:
            self._context.clear()
            
    def add_handler(self, handler: Callable[[Dict], None]) -> None:
        """
        添加日志处理器
        
        Args:
            handler: 接收字典格式日志的函数
        """
        with self._lock:
            self._handlers.append(handler)
            
    def _format_log(self, level: LogLevel, message: str, 
                    extra: Optional[Dict] = None) -> Dict[str, Any]:
        """
        格式化日志为字典
        
        Args:
            level: 日志级别
            message: 日志消息
            extra: 额外字段
            
        Returns:
            格式化的日志字典
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.name,
            "logger": self.name,
            "message": message,
            "context": self._context.copy()
        }
        
        if extra:
            log_entry["extra"] = extra
            
        # 添加线程信息用于调试并发问题
        log_entry["thread"] = {
            "id": threading.current_thread().ident,
            "name": threading.current_thread().name
        }
        
        return log_entry
        
    def _emit(self, level: LogLevel, message: str, 
              extra: Optional[Dict] = None) -> None:
        """
        发送日志到所有处理器
        
        Args:
            level: 日志级别
            message: 日志消息
            extra: 额外字段
        """
        if level.value < self.level.value:
            return
            
        log_entry = self._format_log(level, message, extra)
        
        with self._lock:
            for handler in self._handlers:
                try:
                    handler(log_entry)
                except Exception as e:
                    # 防止handler错误导致主流程中断
                    pass
                    
    def debug(self, message: str, **kwargs) -> None:
        """记录调试级别日志"""
        self._emit(LogLevel.DEBUG, message, kwargs if kwargs else None)
        
    def info(self, message: str, **kwargs) -> None:
        """记录信息级别日志"""
        self._emit(LogLevel.INFO, message, kwargs if kwargs else None)
        
    def warning(self, message: str, **kwargs) -> None:
        """记录警告级别日志"""
        self._emit(LogLevel.WARNING, message, kwargs if kwargs else None)
        
    def error(self, message: str, **kwargs) -> None:
        """记录错误级别日志"""
        self._emit(LogLevel.ERROR, message, kwargs if kwargs else None)
        
    def critical(self, message: str, **kwargs) -> None:
        """记录严重错误日志"""
        self._emit(LogLevel.CRITICAL, message, kwargs if kwargs else None)


class LogAggregator:
    """
    日志聚合器
    
    收集并处理来自多个日志源的日志，支持日志过滤和转发。
    """
    
    def __init__(self, max_memory: int = 10000):
        """
        初始化日志聚合器
        
        Args:
            max_memory: 内存中保存的最大日志数量
        """
        self.max_memory = max_memory
        self._logs: deque = deque(maxlen=max_memory)
        self._lock = threading.RLock()
        self._loggers: Dict[str, StructuredLogger] = {}
        
    def get_logger(self, name: str) -> StructuredLogger:
        """
        获取或创建日志记录器
        
        Args:
            name: 日志记录器名称
            
        Returns:
            StructuredLogger实例
        """
        with self._lock:
            if name not in self._loggers:
                logger = StructuredLogger(name)
                # 添加默认处理器：输出到标准输出
                logger.add_handler(lambda log: print(json.dumps(log, ensure_ascii=False)))
                self._loggers[name] = logger
            return self._loggers[name]
            
    def get_recent_logs(self, count: int = 100, 
                        level: Optional[LogLevel] = None) -> List[Dict]:
        """
        获取最近的日志
        
        Args:
            count: 返回的日志数量
            level: 按日志级别过滤
            
        Returns:
            日志列表
        """
        with self._lock:
            logs = list(self._logs)
            
        if level:
            logs = [l for l in logs if LogLevel[l["level"]].value >= level.value]
            
        return logs[-count:]


# ============================================================
# 第二部分：性能指标系统
# ============================================================

class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"      # 累计值，只能增加
    GAUGE = "gauge"          # 瞬时值，可增可减
    HISTOGRAM = "histogram"  # 直方图，统计分布


@dataclass
class MetricSample:
    """指标样本"""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class Counter:
    """
    计数器指标
    
    用于统计累计发生的事件，如请求数、错误数等。
    只能增加，不能减少。
    """
    
    def __init__(self, name: str, description: str = "", 
                 labels: Optional[Dict[str, str]] = None):
        """
        初始化计数器
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签字典
        """
        self.name = name
        self.description = description
        self.labels = labels or {}
        self._value: float = 0
        self._lock = threading.RLock()
        
    def inc(self, value: float = 1) -> None:
        """
        增加计数器值
        
        Args:
            value: 增加值，默认1
        """
        if value < 0:
            raise ValueError("Counter只能增加，不能减少")
        with self._lock:
            self._value += value
            
    def get_value(self) -> float:
        """获取当前值"""
        with self._lock:
            return self._value
            
    def reset(self) -> None:
        """重置计数器"""
        with self._lock:
            self._value = 0


class Gauge:
    """
    仪表指标
    
    用于表示当前的瞬时值，如内存使用量、连接数等。
    可增可减。
    """
    
    def __init__(self, name: str, description: str = "",
                 labels: Optional[Dict[str, str]] = None):
        """
        初始化仪表
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签字典
        """
        self.name = name
        self.description = description
        self.labels = labels or {}
        self._value: float = 0
        self._lock = threading.RLock()
        
    def set(self, value: float) -> None:
        """
        设置仪表值
        
        Args:
            value: 设置的值
        """
        with self._lock:
            self._value = value
            
    def inc(self, value: float = 1) -> None:
        """增加仪表值"""
        with self._lock:
            self._value += value
            
    def dec(self, value: float = 1) -> None:
        """减少仪表值"""
        with self._lock:
            self._value -= value
            
    def get_value(self) -> float:
        """获取当前值"""
        with self._lock:
            return self._value


class Histogram:
    """
    直方图指标
    
    用于统计值的分布情况，计算平均值、百分位数等。
    适用于响应时间、请求大小等指标。
    """
    
    def __init__(self, name: str, description: str = "",
                 labels: Optional[Dict[str, str]] = None,
                 buckets: Optional[List[float]] = None):
        """
        初始化直方图
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签字典
            buckets: 直方图桶边界
        """
        self.name = name
        self.description = description
        self.labels = labels or {}
        self.buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        
        # 初始化桶计数
        self._bucket_counts: Dict[float, int] = {b: 0 for b in self.buckets}
        self._sum: float = 0
        self._count: int = 0
        self._lock = threading.RLock()
        
    def observe(self, value: float) -> None:
        """
        记录观测值
        
        Args:
            value: 观测到的值
        """
        with self._lock:
            self._sum += value
            self._count += 1
            
            # 更新桶计数
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[bucket] += 1
                    
    def get_stats(self) -> Dict[str, float]:
        """
        获取统计信息
        
        Returns:
            包含sum、count、mean和百分位数的字典
        """
        with self._lock:
            if self._count == 0:
                return {"sum": 0, "count": 0, "mean": 0}
                
            result = {
                "sum": self._sum,
                "count": self._count,
                "mean": self._sum / self._count,
            }
            
            # 计算百分位数
            sorted_values = []
            for bucket in sorted(self.buckets):
                count = self._bucket_counts[bucket]
                for _ in range(count):
                    sorted_values.append(bucket)
                    
            for p in [0.5, 0.75, 0.9, 0.95, 0.99]:
                idx = int(len(sorted_values) * p)
                if idx < len(sorted_values):
                    result[f"p{int(p*100)}"] = sorted_values[idx]
                    
            return result


class MetricsCollector:
    """
    指标收集器
    
    统一管理所有指标，提供注册、查询、导出等功能。
    """
    
    def __init__(self):
        """初始化指标收集器"""
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._lock = threading.RLock()
        
    def register_counter(self, name: str, description: str = "",
                        labels: Optional[Dict[str, str]] = None) -> Counter:
        """
        注册计数器
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签字典
            
        Returns:
            Counter实例
        """
        with self._lock:
            if name in self._counters:
                return self._counters[name]
            counter = Counter(name, description, labels)
            self._counters[name] = counter
            return counter
            
    def register_gauge(self, name: str, description: str = "",
                     labels: Optional[Dict[str, str]] = None) -> Gauge:
        """
        注册仪表
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签字典
            
        Returns:
            Gauge实例
        """
        with self._lock:
            if name in self._gauges:
                return self._gauges[name]
            gauge = Gauge(name, description, labels)
            self._gauges[name] = gauge
            return gauge
            
    def register_histogram(self, name: str, description: str = "",
                         labels: Optional[Dict[str, str]] = None,
                         buckets: Optional[List[float]] = None) -> Histogram:
        """
        注册直方图
        
        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签字典
            buckets: 直方图桶边界
            
        Returns:
            Histogram实例
        """
        with self._lock:
            if name in self._histograms:
                return self._histograms[name]
            histogram = Histogram(name, description, labels, buckets)
            self._histograms[name] = histogram
            return histogram
            
    def get_counter(self, name: str) -> Optional[Counter]:
        """获取计数器"""
        with self._lock:
            return self._counters.get(name)
            
    def get_gauge(self, name: str) -> Optional[Gauge]:
        """获取仪表"""
        with self._lock:
            return self._gauges.get(name)
            
    def get_histogram(self, name: str) -> Optional[Histogram]:
        """获取直方图"""
        with self._lock:
            return self._histograms.get(name)
            
    def export_prometheus(self) -> str:
        """
        导出为Prometheus格式
        
        Returns:
            Prometheus文本格式的指标
        """
        lines = []
        
        with self._lock:
            # 导出计数器
            for counter in self._counters.values():
                labels = ",".join(f'{k}="{v}"' for k, v in counter.labels.items())
                if labels:
                    lines.append(f"# TYPE {counter.name} counter")
                    lines.append(f"{counter.name}{{{labels}}} {counter.get_value()}")
                else:
                    lines.append(f"# TYPE {counter.name} counter")
                    lines.append(f"{counter.name} {counter.get_value()}")
                    
            # 导出仪表
            for gauge in self._gauges.values():
                labels = ",".join(f'{k}="{v}"' for k, v in gauge.labels.items())
                if labels:
                    lines.append(f"# TYPE {gauge.name} gauge")
                    lines.append(f"{gauge.name}{{{labels}}} {gauge.get_value()}")
                else:
                    lines.append(f"# TYPE {gauge.name} gauge")
                    lines.append(f"{gauge.name} {gauge.get_value()}")
                    
            # 导出直方图
            for histogram in self._histograms.values():
                labels = ",".join(f'{k}="{v}"' for k, v in histogram.labels.items())
                suffix = f"{{{labels}}}" if labels else ""
                
                lines.append(f"# TYPE {histogram.name} histogram")
                stats = histogram.get_stats()
                for bucket, count in histogram._bucket_counts.items():
                    bucket_labels = dict(histogram.labels)
                    bucket_labels["le"] = str(bucket)
                    b_labels = ",".join(f'{k}="{v}"' for k, v in bucket_labels.items())
                    lines.append(f"{histogram.name}_bucket{b_labels} {count}")
                    
                # 添加inf bucket
                inf_labels = ",".join(f'{k}="{v}"' for k, v in histogram.labels.items())
                inf_labels += ',le="+Inf"' if inf_labels else 'le="+Inf"'
                lines.append(f"{histogram.name}_bucket{{{inf_labels}}} {stats['count']}")
                lines.append(f"{histogram.name}_sum{ suffix} {stats['sum']}")
                lines.append(f"{histogram.name}_count{ suffix} {stats['count']}")
                
        return "\n".join(lines)


# ============================================================
# 第三部分：健康检查系统
# ============================================================

class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    name: str
    status: HealthStatus
    message: str
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Optional[Dict] = None


class HealthCheck:
    """
    健康检查基类
    
    用于实现各种健康检查逻辑。
    """
    
    def __init__(self, name: str, timeout: float = 5.0):
        """
        初始化健康检查
        
        Args:
            name: 检查名称
            timeout: 超时时间（秒）
        """
        self.name = name
        self.timeout = timeout
        
    def check(self) -> HealthCheckResult:
        """
        执行健康检查
        
        Returns:
            HealthCheckResult实例
        """
        start = time.time()
        try:
            status, message, details = self._do_check()
            duration_ms = (time.time() - start) * 1000
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                duration_ms=duration_ms,
                details=details
            )
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"检查失败: {str(e)}",
                duration_ms=duration_ms,
                details={"error": traceback.format_exc()}
            )
            
    def _do_check(self) -> tuple:
        """
        实现具体的检查逻辑
        
        Returns:
            (status, message, details)元组
        """
        raise NotImplementedError


class DependencyHealthCheck(HealthCheck):
    """
    依赖服务健康检查
    
    检查外部依赖服务的可用性。
    """
    
    def __init__(self, name: str, check_func: Callable[[], bool],
                 timeout: float = 5.0):
        """
        初始化依赖健康检查
        
        Args:
            name: 检查名称
            check_func: 返回布尔值的检查函数
            timeout: 超时时间
        """
        super().__init__(name, timeout)
        self.check_func = check_func
        
    def _do_check(self) -> tuple:
        """执行依赖检查"""
        try:
            result = self.check_func()
            if result:
                return HealthStatus.HEALTHY, "服务正常", {"available": True}
            else:
                return HealthStatus.UNHEALTHY, "服务不可用", {"available": False}
        except Exception as e:
            return HealthStatus.UNHEALTHY, f"服务异常: {str(e)}", {"error": str(e)}


class ResourceHealthCheck(HealthCheck):
    """
    资源健康检查
    
    检查系统资源使用情况。
    """
    
    def __init__(self, name: str, resource_type: str,
                 warning_threshold: float, critical_threshold: float):
        """
        初始化资源健康检查
        
        Args:
            name: 检查名称
            resource_type: 资源类型 (memory, cpu, disk)
            warning_threshold: 警告阈值
            critical_threshold: 严重阈值
        """
        super().__init__(name)
        self.resource_type = resource_type
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        
    def _do_check(self) -> tuple:
        """执行资源检查"""
        # 模拟资源检查
        usage = self._get_usage()
        
        if usage >= self.critical_threshold:
            return (HealthStatus.UNHEALTHY, 
                   f"{self.resource_type}使用率过高: {usage:.1f}%",
                   {"usage": usage, "threshold": self.critical_threshold})
        elif usage >= self.warning_threshold:
            return (HealthStatus.DEGRADED,
                   f"{self.resource_type}使用率偏高: {usage:.1f}%",
                   {"usage": usage, "threshold": self.warning_threshold})
        else:
            return (HealthStatus.HEALTHY,
                   f"{self.resource_type}使用率正常: {usage:.1f}%",
                   {"usage": usage})
                   
    def _get_usage(self) -> float:
        """获取资源使用率（模拟）"""
        import random
        return random.uniform(30, 80)


class HealthCheckManager:
    """
    健康检查管理器
    
    统一管理多个健康检查，提供聚合的健康状态。
    """
    
    def __init__(self):
        """初始化健康检查管理器"""
        self._checks: Dict[str, HealthCheck] = {}
        self._lock = threading.RLock()
        
    def register(self, check: HealthCheck) -> None:
        """
        注册健康检查
        
        Args:
            check: HealthCheck实例
        """
        with self._lock:
            self._checks[check.name] = check
            
    def check_all(self) -> Dict[str, HealthCheckResult]:
        """
        执行所有健康检查
        
        Returns:
            检查结果字典
        """
        results = {}
        threads = []
        
        def run_check(name: str, check: HealthCheck):
            results[name] = check.check()
            
        with self._lock:
            checks = list(self._checks.items())
            
        for name, check in checks:
            thread = threading.Thread(target=run_check, args=(name, check))
            thread.start()
            threads.append(thread)
            
        for thread in threads:
            thread.join()
            
        return results
        
    def get_overall_status(self) -> HealthStatus:
        """
        获取整体健康状态
        
        Returns:
            整体健康状态
        """
        results = self.check_all()
        
        if not results:
            return HealthStatus.HEALTHY
            
        statuses = [r.status for r in results.values()]
        
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            return HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY


# ============================================================
# 第四部分：告警系统
# ============================================================

class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警"""
    id: str
    level: AlertLevel
    title: str
    message: str
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Optional[Dict] = None
    resolved: bool = False


class AlertRule:
    """
    告警规则
    
    定义告警触发条件。
    """
    
    def __init__(self, name: str, condition: Callable[[], bool],
                 level: AlertLevel, message: str):
        """
        初始化告警规则
        
        Args:
            name: 规则名称
            condition: 返回布尔值的条件函数
            level: 告警级别
            message: 告警消息模板
        """
        self.name = name
        self.condition = condition
        self.level = level
        self.message = message
        self._last_triggered: Optional[datetime] = None
        self._cooldown_seconds: int = 60
        
    def should_alert(self) -> bool:
        """
        检查是否应该触发告警
        
        考虑冷却时间，避免告警风暴。
        
        Returns:
            是否应该告警
        """
        if not self.condition():
            self._last_triggered = None
            return False
            
        if self._last_triggered:
            elapsed = (datetime.utcnow() - self._last_triggered).total_seconds()
            if elapsed < self._cooldown_seconds:
                return False
                
        self._last_triggered = datetime.utcnow()
        return True
        
    def create_alert(self, source: str) -> Alert:
        """
        创建告警对象
        
        Args:
            source: 告警来源
            
        Returns:
            Alert实例
        """
        return Alert(
            id=f"{self.name}-{int(time.time())}",
            level=self.level,
            title=self.name,
            message=self.message,
            source=source
        )


class AlertManager:
    """
    告警管理器
    
    管理告警规则、告警历史和通知。
    """
    
    def __init__(self):
        """初始化告警管理器"""
        self._rules: List[AlertRule] = []
        self._alerts: deque = deque(maxlen=1000)
        self._handlers: List[Callable[[Alert], None]] = []
        self._lock = threading.RLock()
        
    def add_rule(self, rule: AlertRule) -> None:
        """
        添加告警规则
        
        Args:
            rule: AlertRule实例
        """
        with self._lock:
            self._rules.append(rule)
            
    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        添加告警处理函数
        
        Args:
            handler: 处理告警的函数
        """
        with self._lock:
            self._handlers.append(handler)
            
    def check_rules(self, source: str) -> List[Alert]:
        """
        检查所有规则，触发符合条件的告警
        
        Args:
            source: 告警来源
            
        Returns:
            触发的告警列表
        """
        triggered = []
        
        with self._lock:
            for rule in self._rules:
                if rule.should_alert():
                    alert = rule.create_alert(source)
                    self._alerts.append(alert)
                    triggered.append(alert)
                    
                    # 调用处理函数
                    for handler in self._handlers:
                        try:
                            handler(alert)
                        except Exception:
                            pass
                            
        return triggered
        
    def get_active_alerts(self) -> List[Alert]:
        """
        获取未解决的告警
        
        Returns:
            活跃告警列表
        """
        with self._lock:
            return [a for a in self._alerts if not a.resolved]
            
    def resolve_alert(self, alert_id: str) -> bool:
        """
        解决告警
        
        Args:
            alert_id: 告警ID
            
        Returns:
            是否成功解决
        """
        with self._lock:
            for alert in self._alerts:
                if alert.id == alert_id:
                    alert.resolved = True
                    return True
        return False


# ============================================================
# 第五部分：集成示例与测试
# ============================================================

class DeerFlowMonitor:
    """
    DeerFlow监控系统的完整集成示例
    
    展示如何将日志、指标、健康检查和告警系统整合在一起。
    """
    
    def __init__(self):
        """初始化监控系统"""
        # 日志系统
        self.logger = LogAggregator()
        
        # 指标收集器
        self.metrics = MetricsCollector()
        
        # 注册常用指标
        self.request_counter = self.metrics.register_counter(
            "deerflow_requests_total", "DeerFlow总请求数"
        )
        self.error_counter = self.metrics.register_counter(
            "deerflow_errors_total", "DeerFlow错误总数"
        )
        self.response_time = self.metrics.register_histogram(
            "deerflow_response_time_seconds", "响应时间分布"
        )
        self.active_connections = self.metrics.register_gauge(
            "deerflow_active_connections", "活跃连接数"
        )
        self.memory_usage = self.metrics.register_gauge(
            "deerflow_memory_usage_bytes", "内存使用量"
        )
        
        # 健康检查管理器
        self.health_manager = HealthCheckManager()
        self.health_manager.register(
            ResourceHealthCheck("memory", "memory", 80, 95)
        )
        self.health_manager.register(
            ResourceHealthCheck("cpu", "cpu", 80, 90)
        )
        
        # 告警管理器
        self.alert_manager = AlertManager()
        self.alert_manager.add_rule(AlertRule(
            "high_error_rate",
            lambda: self.error_counter.get_value() > 10,
            AlertLevel.ERROR,
            "错误率过高"
        ))
        
    def record_request(self, duration: float, is_error: bool = False) -> None:
        """
        记录请求
        
        Args:
            duration: 请求持续时间（秒）
            is_error: 是否为错误请求
        """
        # 记录指标
        self.request_counter.inc()
        self.response_time.observe(duration)
        
        if is_error:
            self.error_counter.inc()
            
        # 检查告警
        self.alert_manager.check_rules("deerflow")
        
        # 记录日志
        logger = self.logger.get_logger("deerflow.requests")
        logger.info(
            "请求完成",
            duration=duration,
            error=is_error
        )
        
    def get_status(self) -> Dict[str, Any]:
        """
        获取系统状态
        
        Returns:
            包含所有监控数据的字典
        """
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metrics": {
                "requests_total": self.request_counter.get_value(),
                "errors_total": self.error_counter.get_value(),
                "response_time": self.response_time.get_stats(),
                "active_connections": self.active_connections.get_value(),
                "memory_usage_bytes": self.memory_usage.get_value()
            },
            "health": {
                "status": self.health_manager.get_overall_status().value,
                "checks": {
                    name: {
                        "status": result.status.value,
                        "message": result.message,
                        "duration_ms": result.duration_ms
                    }
                    for name, result in self.health_manager.check_all().items()
                }
            },
            "alerts": {
                "active": len(self.alert_manager.get_active_alerts()),
                "recent": len(self.alert_manager._alerts)
            }
        }


def run_demo():
    """演示监控系统功能"""
    print("=" * 60)
    print("DeerFlow 监控与指标系统演示")
    print("=" * 60)
    
    # 创建监控系统
    monitor = DeerFlowMonitor()
    
    # 模拟请求
    print("\n1. 模拟正常请求...")
    for i in range(5):
        monitor.record_request(duration=0.1 + i * 0.01, is_error=False)
        
    print("\n2. 模拟错误请求...")
    monitor.record_request(duration=0.5, is_error=True)
    monitor.record_request(duration=0.3, is_error=True)
    
    # 设置资源使用
    monitor.memory_usage.set(1024 * 1024 * 512)  # 512MB
    monitor.active_connections.set(42)
    
    # 获取状态
    print("\n3. 获取系统状态...")
    status = monitor.get_status()
    
    print("\n--- 指标数据 ---")
    print(f"总请求数: {status['metrics']['requests_total']}")
    print(f"错误总数: {status['metrics']['errors_total']}")
    print(f"响应时间: {status['metrics']['response_time']}")
    print(f"活跃连接: {status['metrics']['active_connections']}")
    print(f"内存使用: {status['metrics']['memory_usage_bytes'] / 1024 / 1024:.1f} MB")
    
    print("\n--- 健康检查 ---")
    for name, check in status['health']['checks'].items():
        print(f"  {name}: {check['status']} - {check['message']}")
        
    print("\n--- 告警状态 ---")
    print(f"活跃告警: {status['alerts']['active']}")
    
    # 导出Prometheus格式
    print("\n4. Prometheus格式导出:")
    print("-" * 40)
    print(monitor.metrics.export_prometheus())
    
    print("\n演示完成!")


def run_tests():
    """运行测试"""
    print("\n" + "=" * 60)
    print("运行单元测试")
    print("=" * 60 + "\n")
    
    # 测试日志系统
    print("测试1: 结构化日志系统")
    logger = StructuredLogger("test")
    logger.set_context(request_id="req-123", user_id="user-456")
    logger.info("测试日志消息", extra_field="额外信息")
    logger.clear_context()
    print("✓ 日志系统测试通过\n")
    
    # 测试指标收集器
    print("测试2: 指标收集器")
    collector = MetricsCollector()
    
    counter = collector.register_counter("test_counter", "测试计数器")
    counter.inc(5)
    counter.inc(3)
    assert counter.get_value() == 8, "计数器测试失败"
    print(f"  计数器: {counter.get_value()} (期望: 8)")
    
    gauge = collector.register_gauge("test_gauge", "测试仪表")
    gauge.set(100)
    gauge.inc(50)
    gauge.dec(30)
    assert gauge.get_value() == 120, "仪表测试失败"
    print(f"  仪表: {gauge.get_value()} (期望: 120)")
    
    histogram = collector.register_histogram("test_histogram", "测试直方图")
    histogram.observe(0.1)
    histogram.observe(0.2)
    histogram.observe(0.3)
    stats = histogram.get_stats()
    print(f"  直方图: count={stats['count']}, mean={stats['mean']:.3f}")
    
    print("✓ 指标收集器测试通过\n")
    
    # 测试健康检查
    print("测试3: 健康检查系统")
    health_manager = HealthCheckManager()
    
    # 添加一个简单的健康检查
    def simple_check():
        return True
        
    health_manager.register(DependencyHealthCheck("test_service", simple_check))
    results = health_manager.check_all()
    
    assert "test_service" in results, "健康检查测试失败"
    print(f"  检查结果: {results['test_service'].status.value}")
    print("✓ 健康检查测试通过\n")
    
    # 测试告警系统
    print("测试4: 告警系统")
    alert_manager = AlertManager()
    
    counter = Counter("alert_counter", "告警计数器")
    alert_manager.add_rule(AlertRule(
        "test_alert",
        lambda: counter.get_value() > 5,
        AlertLevel.WARNING,
        "测试告警"
    ))
    
    # 第一次检查 - 不触发
    counter.inc(3)
    alerts = alert_manager.check_rules("test")
    assert len(alerts) == 0, "不应该触发告警"
    print(f"  counter=3, 触发告警数: {len(alerts)}")
    
    # 第二次检查 - 触发
    counter.inc(5)
    alerts = alert_manager.check_rules("test")
    assert len(alerts) > 0, "应该触发告警"
    print(f"  counter=8, 触发告警数: {len(alerts)}")
    print("✓ 告警系统测试通过\n")
    
    # 测试DeerFlowMonitor集成
    print("测试5: DeerFlowMonitor集成")
    monitor = DeerFlowMonitor()
    monitor.record_request(0.5, is_error=False)
    monitor.record_request(0.3, is_error=True)
    status = monitor.get_status()
    
    assert status['metrics']['requests_total'] == 2, "请求计数错误"
    assert status['metrics']['errors_total'] == 1, "错误计数错误"
    print(f"  请求总数: {status['metrics']['requests_total']}")
    print(f"  错误总数: {status['metrics']['errors_total']}")
    print("✓ DeerFlowMonitor集成测试通过\n")
    
    print("=" * 60)
    print("所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if "--test" in sys.argv:
        run_tests()
    else:
        run_demo()
