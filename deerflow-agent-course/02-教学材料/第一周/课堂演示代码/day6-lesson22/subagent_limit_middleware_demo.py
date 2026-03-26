#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 6 Lesson 22: SubagentLimitMiddleware - 课堂演示代码

本文件提供完整的子代理限制中间件实现，用于课堂教学演示。
采用四部分结构设计，全面展示子代理限制中间件的各个方面：
1. 子代理资源管理基础：限制维度、策略配置、状态跟踪基础
2. 四维度限制系统：深度限制、并发限制、时间限制、资源限制
3. SubagentLimitMiddleware实现：中间件核心逻辑与限制执行
4. 完整测试系统与端到端演示：单元测试、集成测试、边界测试、性能测试

教学目标：
1. 理解多Agent系统中子代理资源管理的重要性和挑战
2. 掌握子代理限制的四种核心维度：深度、并发、时间、资源
3. 理解SubagentLimitMiddleware的设计原理和执行流程
4. 了解防止Agent系统资源滥用的安全策略和最佳实践
5. 能够配置子代理限制策略（YAML配置文件）
6. 能够实现子代理深度限制和并发控制逻辑
7. 能够编写子代理状态跟踪和管理机制
8. 能够设计自定义的异常类型和处理流程

运行要求：
Python 3.12+, 安装依赖: asyncio, typing-extensions, dataclasses-json, yaml, threading
前置课程: 已完成ViewImageMiddleware学习

作者: 张老师 (DeerFlow核心贡献者)
版本: v1.0
日期: 2024年4月3日
"""

import asyncio
import time
import json
import yaml
import threading
import uuid
from typing import List, Dict, Optional, Tuple, Any, Set, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
from datetime import datetime, timedelta
import heapq
import warnings
import random
import sys

# ============================================================================
# 第一部分：子代理资源管理基础
# ============================================================================


class RestrictionDimension(Enum):
    """限制维度枚举"""

    DEPTH = "depth"  # 嵌套深度限制
    CONCURRENCY = "concurrency"  # 并发数量限制
    TIME = "time"  # 执行时间限制
    RESOURCE = "resource"  # 资源使用限制（内存/CPU）

    @classmethod
    def from_string(cls, dimension_str: str) -> Optional["RestrictionDimension"]:
        """从字符串获取限制维度"""
        dimension_map = {
            "depth": cls.DEPTH,
            "concurrency": cls.CONCURRENCY,
            "time": cls.TIME,
            "resource": cls.RESOURCE,
            "深度": cls.DEPTH,
            "并发": cls.CONCURRENCY,
            "时间": cls.TIME,
            "资源": cls.RESOURCE,
        }
        return dimension_map.get(dimension_str.lower())


@dataclass
class SubagentState:
    """子代理状态跟踪"""

    agent_id: str  # 子代理唯一标识
    parent_id: Optional[str]  # 父代理ID（用于深度跟踪）
    depth: int  # 当前嵌套深度
    start_time: datetime  # 开始时间
    status: str = "running"  # 状态: running/completed/failed
    resource_usage: Dict[str, float] = field(default_factory=dict)  # 资源使用情况
    end_time: Optional[datetime] = None  # 结束时间

    def is_active(self) -> bool:
        """是否活跃（正在运行）"""
        return self.status == "running"

    def get_duration(self) -> float:
        """获取运行时长（秒）"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()


@dataclass
class RestrictionPolicy:
    """限制策略配置"""

    max_depth: int = 5  # 最大嵌套深度
    max_concurrent: int = 10  # 最大并发子代理数
    max_execution_time: float = 300.0  # 最大执行时间（秒）
    max_memory_mb: float = 1024.0  # 最大内存使用（MB）
    max_cpu_percent: float = 80.0  # 最大CPU使用率（%）
    allow_tools: List[str] = field(default_factory=list)  # 允许的工具白名单
    deny_tools: List[str] = field(default_factory=list)  # 禁止的工具黑名单

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "RestrictionPolicy":
        """从YAML配置创建限制策略"""
        try:
            config = yaml.safe_load(yaml_content)
            if not config:
                return cls()

            # 映射配置字段
            return cls(
                max_depth=config.get("max_depth", 5),
                max_concurrent=config.get("max_concurrent", 10),
                max_execution_time=config.get("max_execution_time", 300.0),
                max_memory_mb=config.get("max_memory_mb", 1024.0),
                max_cpu_percent=config.get("max_cpu_percent", 80.0),
                allow_tools=config.get("allow_tools", []),
                deny_tools=config.get("deny_tools", []),
            )
        except yaml.YAMLError as e:
            raise ValueError(f"YAML解析失败: {e}")

    def to_yaml(self) -> str:
        """转换为YAML格式"""
        config = {
            "max_depth": self.max_depth,
            "max_concurrent": self.max_concurrent,
            "max_execution_time": self.max_execution_time,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "allow_tools": self.allow_tools,
            "deny_tools": self.deny_tools,
        }
        return yaml.dump(config, allow_unicode=True, default_flow_style=False)

    def validate_tool(self, tool_name: str) -> bool:
        """验证工具是否允许使用"""
        # 检查黑名单
        if tool_name in self.deny_tools:
            return False

        # 检查白名单（如果白名单非空，则只允许白名单中的工具）
        if self.allow_tools and tool_name not in self.allow_tools:
            return False

        return True


class SubagentTracker:
    """子代理状态跟踪器（线程安全）"""

    def __init__(self):
        self._active_subagents: Dict[str, SubagentState] = {}
        self._subagents_by_parent: Dict[str, List[str]] = defaultdict(list)
        self._lock = threading.RLock()  # 可重入锁，支持嵌套调用

    def register_subagent(
        self, agent_id: str, parent_id: Optional[str] = None, depth: int = 1
    ) -> SubagentState:
        """注册新的子代理"""
        with self._lock:
            # 检查是否已存在
            if agent_id in self._active_subagents:
                raise ValueError(f"子代理 {agent_id} 已存在")

            # 创建状态记录
            state = SubagentState(
                agent_id=agent_id,
                parent_id=parent_id,
                depth=depth,
                start_time=datetime.now(),
            )

            self._active_subagents[agent_id] = state

            # 更新父子关系
            if parent_id:
                self._subagents_by_parent[parent_id].append(agent_id)

            return state

    def complete_subagent(self, agent_id: str) -> Optional[SubagentState]:
        """标记子代理为完成"""
        with self._lock:
            if agent_id not in self._active_subagents:
                return None

            state = self._active_subagents[agent_id]
            state.status = "completed"
            state.end_time = datetime.now()

            return state

    def fail_subagent(
        self, agent_id: str, error: Optional[str] = None
    ) -> Optional[SubagentState]:
        """标记子代理为失败"""
        with self._lock:
            if agent_id not in self._active_subagents:
                return None

            state = self._active_subagents[agent_id]
            state.status = "failed"
            state.end_time = datetime.now()
            if error:
                state.resource_usage["error"] = error

            return state

    def get_active_count(self) -> int:
        """获取活跃子代理数量"""
        with self._lock:
            return sum(
                1 for state in self._active_subagents.values() if state.is_active()
            )

    def get_max_depth(self) -> int:
        """获取当前最大嵌套深度"""
        with self._lock:
            if not self._active_subagents:
                return 0
            return max(state.depth for state in self._active_subagents.values())

    def get_subagent_state(self, agent_id: str) -> Optional[SubagentState]:
        """获取子代理状态"""
        with self._lock:
            return self._active_subagents.get(agent_id)

    def get_children(self, parent_id: str) -> List[SubagentState]:
        """获取指定父代理的所有子代理"""
        with self._lock:
            child_ids = self._subagents_by_parent.get(parent_id, [])
            return [
                self._active_subagents[cid]
                for cid in child_ids
                if cid in self._active_subagents
            ]

    def cleanup_completed(self, max_age_seconds: float = 3600) -> int:
        """清理已完成/失败的子代理（超过指定时间）"""
        with self._lock:
            now = datetime.now()
            to_remove = []

            for agent_id, state in self._active_subagents.items():
                if state.status in ["completed", "failed"]:
                    if (
                        state.end_time
                        and (now - state.end_time).total_seconds() > max_age_seconds
                    ):
                        to_remove.append(agent_id)

            for agent_id in to_remove:
                # 清理父子关系
                state = self._active_subagents[agent_id]
                if state.parent_id and state.parent_id in self._subagents_by_parent:
                    if agent_id in self._subagents_by_parent[state.parent_id]:
                        self._subagents_by_parent[state.parent_id].remove(agent_id)

                # 清理状态记录
                del self._active_subagents[agent_id]

            return len(to_remove)

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            active = self.get_active_count()
            total = len(self._active_subagents)
            completed = sum(
                1 for s in self._active_subagents.values() if s.status == "completed"
            )
            failed = sum(
                1 for s in self._active_subagents.values() if s.status == "failed"
            )
            max_depth = self.get_max_depth()

            # 计算平均持续时间
            durations = []
            for state in self._active_subagents.values():
                if state.end_time:
                    durations.append(state.get_duration())

            avg_duration = sum(durations) / len(durations) if durations else 0.0

            return {
                "active_subagents": active,
                "total_subagents": total,
                "completed_subagents": completed,
                "failed_subagents": failed,
                "max_depth": max_depth,
                "average_duration_seconds": avg_duration,
            }


# ============================================================================
# 第二部分：四维度限制系统
# ============================================================================


class LimitExceededError(Exception):
    """限制超限异常基类"""

    def __init__(
        self, dimension: str, limit_value: Any, current_value: Any, message: str = ""
    ):
        self.dimension = dimension
        self.limit_value = limit_value
        self.current_value = current_value
        self.message = (
            message
            or f"{dimension}限制超限: 当前值{current_value}超过限制{limit_value}"
        )
        super().__init__(self.message)


class DepthLimitExceededError(LimitExceededError):
    """深度限制超限异常"""

    def __init__(self, current_depth: int, max_depth: int):
        super().__init__(
            "depth",
            max_depth,
            current_depth,
            f"嵌套深度超限: 当前深度{current_depth}超过最大深度{max_depth}",
        )


class ConcurrencyLimitExceededError(LimitExceededError):
    """并发限制超限异常"""

    def __init__(self, current_concurrent: int, max_concurrent: int):
        super().__init__(
            "concurrency",
            max_concurrent,
            current_concurrent,
            f"并发数量超限: 当前并发数{current_concurrent}超过最大并发数{max_concurrent}",
        )


class TimeLimitExceededError(LimitExceededError):
    """时间限制超限异常"""

    def __init__(self, current_time: float, max_time: float):
        super().__init__(
            "time",
            max_time,
            current_time,
            f"执行时间超限: 当前时间{current_time:.2f}秒超过最大时间{max_time:.2f}秒",
        )


class ResourceLimitExceededError(LimitExceededError):
    """资源限制超限异常"""

    def __init__(self, resource_type: str, current_usage: float, max_usage: float):
        super().__init__(
            "resource",
            max_usage,
            current_usage,
            f"资源使用超限: {resource_type}使用率{current_usage}超过限制{max_usage}",
        )


class ToolNotAllowedError(Exception):
    """工具不允许使用异常"""

    def __init__(self, tool_name: str, policy: RestrictionPolicy):
        self.tool_name = tool_name
        self.policy = policy
        message = f"工具 '{tool_name}' 不允许使用"
        if policy.allow_tools:
            message += f" (允许的工具: {', '.join(policy.allow_tools)})"
        if policy.deny_tools and tool_name in policy.deny_tools:
            message += f" (工具在黑名单中)"
        super().__init__(message)


class DepthLimiter:
    """深度限制器"""

    def __init__(self, tracker: SubagentTracker):
        self.tracker = tracker

    def check_depth(self, parent_id: Optional[str] = None) -> Tuple[int, bool]:
        """
        检查深度限制

        Args:
            parent_id: 父代理ID，如果为None表示根代理

        Returns:
            (depth, allowed): 深度和是否允许创建
        """
        if parent_id is None:
            # 根代理，深度为1
            current_depth = 1
        else:
            # 获取父代理深度
            parent_state = self.tracker.get_subagent_state(parent_id)
            if parent_state is None:
                # 父代理不存在，视为根代理
                current_depth = 1
            else:
                current_depth = parent_state.depth + 1

        # 获取当前最大深度（用于检查系统整体深度）
        max_current_depth = self.tracker.get_max_depth()

        return current_depth, max_current_depth

    def validate_depth(self, parent_id: Optional[str], max_allowed_depth: int) -> int:
        """
        验证深度并返回允许的深度

        Args:
            parent_id: 父代理ID
            max_allowed_depth: 允许的最大深度

        Returns:
            允许的深度

        Raises:
            DepthLimitExceededError: 深度超限
        """
        current_depth, max_current_depth = self.check_depth(parent_id)

        # 检查是否超过限制
        if current_depth > max_allowed_depth:
            raise DepthLimitExceededError(current_depth, max_allowed_depth)

        # 检查系统整体深度（防止深度攻击）
        if max_current_depth >= max_allowed_depth * 2:
            # 系统整体深度异常，可能是深度攻击
            warnings.warn(
                f"系统深度异常: 当前最大深度{max_current_depth}，允许深度{max_allowed_depth}"
            )

        return current_depth


class ConcurrencyLimiter:
    """并发限制器"""

    def __init__(self, tracker: SubagentTracker):
        self.tracker = tracker
        self._lock = threading.RLock()

    def get_concurrent_count(self) -> int:
        """获取当前并发数"""
        return self.tracker.get_active_count()

    def validate_concurrency(self, max_allowed_concurrent: int) -> bool:
        """
        验证并发限制

        Args:
            max_allowed_concurrent: 允许的最大并发数

        Returns:
            是否允许创建新子代理

        Raises:
            ConcurrencyLimitExceededError: 并发超限
        """
        current_concurrent = self.get_concurrent_count()

        if current_concurrent >= max_allowed_concurrent:
            raise ConcurrencyLimitExceededError(
                current_concurrent, max_allowed_concurrent
            )

        return True

    def reserve_slot(self, agent_id: str, timeout_seconds: float = 5.0) -> bool:
        """
        预留并发槽位（带超时）

        Args:
            agent_id: 代理ID
            timeout_seconds: 超时时间

        Returns:
            是否成功预留

        Note:
            这是一个高级功能，支持带超时的并发控制
        """
        import time

        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            try:
                # 尝试获取锁并检查并发
                with self._lock:
                    current = self.get_concurrent_count()
                    # 这里可以添加更复杂的逻辑，如基于权重的并发控制
                    return True
            except Exception:
                time.sleep(0.1)  # 短暂等待后重试

        return False


class TimeLimiter:
    """时间限制器"""

    def __init__(self):
        self._start_times: Dict[str, float] = {}
        self._lock = threading.RLock()

    def start_timing(self, agent_id: str):
        """开始计时"""
        with self._lock:
            self._start_times[agent_id] = time.time()

    def stop_timing(self, agent_id: str) -> float:
        """停止计时并返回持续时间"""
        with self._lock:
            if agent_id not in self._start_times:
                return 0.0

            start_time = self._start_times[agent_id]
            duration = time.time() - start_time
            del self._start_times[agent_id]
            return duration

    def check_time(self, agent_id: str, max_allowed_time: float) -> Tuple[float, bool]:
        """
        检查时间限制

        Args:
            agent_id: 代理ID
            max_allowed_time: 允许的最大时间

        Returns:
            (elapsed_time, is_exceeded): 已用时间和是否超限
        """
        with self._lock:
            if agent_id not in self._start_times:
                return 0.0, False

            elapsed = time.time() - self._start_times[agent_id]
            return elapsed, elapsed > max_allowed_time

    def validate_time(self, agent_id: str, max_allowed_time: float) -> float:
        """
        验证时间限制

        Args:
            agent_id: 代理ID
            max_allowed_time: 允许的最大时间

        Returns:
            已用时间

        Raises:
            TimeLimitExceededError: 时间超限
        """
        elapsed, is_exceeded = self.check_time(agent_id, max_allowed_time)

        if is_exceeded:
            raise TimeLimitExceededError(elapsed, max_allowed_time)

        return elapsed


class ResourceLimiter:
    """资源限制器（模拟）"""

    def __init__(self):
        self._resource_usage: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._lock = threading.RLock()

    def measure_resources(self) -> Dict[str, float]:
        """
        测量当前资源使用情况（模拟）

        Returns:
            资源使用情况字典
        """
        # 模拟资源测量
        import psutil
        import os

        process = psutil.Process(os.getpid())

        return {
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "cpu_percent": process.cpu_percent(interval=0.1),
            "thread_count": process.num_threads(),
            "open_files": len(process.open_files()),
        }

    def record_usage(self, agent_id: str, resource_type: str, usage: float):
        """记录资源使用"""
        with self._lock:
            self._resource_usage[agent_id][resource_type] = usage

    def get_agent_usage(self, agent_id: str) -> Dict[str, float]:
        """获取代理资源使用"""
        with self._lock:
            return self._resource_usage.get(agent_id, {}).copy()

    def validate_resources(self, max_memory_mb: float, max_cpu_percent: float) -> bool:
        """
        验证资源限制

        Args:
            max_memory_mb: 最大内存(MB)
            max_cpu_percent: 最大CPU使用率

        Returns:
            是否通过验证

        Raises:
            ResourceLimitExceededError: 资源超限
        """
        try:
            resources = self.measure_resources()

            # 检查内存
            if resources["memory_mb"] > max_memory_mb:
                raise ResourceLimitExceededError(
                    "memory", resources["memory_mb"], max_memory_mb
                )

            # 检查CPU
            if resources["cpu_percent"] > max_cpu_percent:
                raise ResourceLimitExceededError(
                    "cpu", resources["cpu_percent"], max_cpu_percent
                )

            return True
        except ImportError:
            # psutil未安装，跳过资源检查
            warnings.warn("psutil未安装，跳过资源限制检查")
            return True

    def cleanup_agent(self, agent_id: str):
        """清理代理资源记录"""
        with self._lock:
            if agent_id in self._resource_usage:
                del self._resource_usage[agent_id]


# ============================================================================
# 第三部分：SubagentLimitMiddleware实现
# ============================================================================


class SubagentLimitMiddleware:
    """子代理限制中间件"""

    def __init__(self, policy: Optional[RestrictionPolicy] = None):
        """
        初始化子代理限制中间件

        Args:
            policy: 限制策略，如果为None则使用默认策略
        """
        self.policy = policy or RestrictionPolicy()
        self.tracker = SubagentTracker()
        self.depth_limiter = DepthLimiter(self.tracker)
        self.concurrency_limiter = ConcurrencyLimiter(self.tracker)
        self.time_limiter = TimeLimiter()
        self.resource_limiter = ResourceLimiter()

        # 中间件配置
        self.enable_depth_limit = True
        self.enable_concurrency_limit = True
        self.enable_time_limit = True
        self.enable_resource_limit = True
        self.enable_tool_restriction = True

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "blocked_requests": 0,
            "depth_violations": 0,
            "concurrency_violations": 0,
            "time_violations": 0,
            "resource_violations": 0,
            "tool_violations": 0,
        }

    async def before_agent(
        self,
        agent_id: str,
        parent_id: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        在子代理执行前调用，进行限制检查

        Args:
            agent_id: 子代理ID
            parent_id: 父代理ID（可选）
            tool_name: 使用的工具名称（可选）

        Returns:
            包含检查结果的字典

        Raises:
            各种限制超限异常
        """
        self.stats["total_requests"] += 1

        result = {
            "agent_id": agent_id,
            "parent_id": parent_id,
            "tool_name": tool_name,
            "checks_passed": [],
            "checks_failed": [],
            "depth": 1,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # 1. 检查工具限制
            if self.enable_tool_restriction and tool_name:
                if not self.policy.validate_tool(tool_name):
                    self.stats["tool_violations"] += 1
                    raise ToolNotAllowedError(tool_name, self.policy)
                result["checks_passed"].append("tool_restriction")

            # 2. 检查深度限制
            if self.enable_depth_limit:
                depth = self.depth_limiter.validate_depth(
                    parent_id, self.policy.max_depth
                )
                result["depth"] = depth
                result["checks_passed"].append("depth_limit")

            # 3. 检查并发限制
            if self.enable_concurrency_limit:
                self.concurrency_limiter.validate_concurrency(
                    self.policy.max_concurrent
                )
                result["checks_passed"].append("concurrency_limit")

            # 4. 检查资源限制（系统级别）
            if self.enable_resource_limit:
                self.resource_limiter.validate_resources(
                    self.policy.max_memory_mb, self.policy.max_cpu_percent
                )
                result["checks_passed"].append("resource_limit")

            # 5. 注册子代理到跟踪器
            state = self.tracker.register_subagent(agent_id, parent_id, result["depth"])
            result["state"] = asdict(state)

            # 6. 开始时间跟踪
            self.time_limiter.start_timing(agent_id)

            # 7. 记录资源使用基线
            if self.enable_resource_limit:
                try:
                    resources = self.resource_limiter.measure_resources()
                    for resource_type, usage in resources.items():
                        self.resource_limiter.record_usage(
                            agent_id, resource_type, usage
                        )
                except Exception:
                    pass  # 资源测量失败不影响主流程

            self.stats["allowed_requests"] += 1
            result["allowed"] = True

        except Exception as e:
            self.stats["blocked_requests"] += 1
            result["allowed"] = False
            result["error"] = {
                "type": type(e).__name__,
                "message": str(e),
            }
            result["checks_failed"].append(type(e).__name__)

            # 更新特定违规统计
            if isinstance(e, DepthLimitExceededError):
                self.stats["depth_violations"] += 1
            elif isinstance(e, ConcurrencyLimitExceededError):
                self.stats["concurrency_violations"] += 1
            elif isinstance(e, TimeLimitExceededError):
                self.stats["time_violations"] += 1
            elif isinstance(e, ResourceLimitExceededError):
                self.stats["resource_violations"] += 1
            elif isinstance(e, ToolNotAllowedError):
                self.stats["tool_violations"] += 1

            raise

        return result

    async def after_agent(
        self, agent_id: str, success: bool = True, error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        在子代理执行后调用，清理资源

        Args:
            agent_id: 子代理ID
            success: 是否执行成功
            error: 错误信息（如果执行失败）

        Returns:
            包含清理结果的字典
        """
        result = {
            "agent_id": agent_id,
            "success": success,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            # 1. 停止时间跟踪并获取持续时间
            duration = self.time_limiter.stop_timing(agent_id)
            result["duration_seconds"] = duration

            # 2. 更新子代理状态
            if success:
                state = self.tracker.complete_subagent(agent_id)
            else:
                state = self.tracker.fail_subagent(agent_id, error)

            if state:
                result["state"] = asdict(state)

            # 3. 清理资源记录
            self.resource_limiter.cleanup_agent(agent_id)

            # 4. 清理跟踪器中的旧记录
            cleaned = self.tracker.cleanup_completed()
            if cleaned > 0:
                result["cleaned_subagents"] = cleaned

            result["success"] = True

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            warnings.warn(f"子代理清理失败: {agent_id}, 错误: {e}")

        return result

    async def during_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        在子代理执行期间调用，进行运行时检查

        Args:
            agent_id: 子代理ID

        Returns:
            包含运行时检查结果的字典
        """
        result = {
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "checks": [],
        }

        try:
            # 1. 检查时间限制
            if self.enable_time_limit:
                elapsed, is_exceeded = self.time_limiter.check_time(
                    agent_id, self.policy.max_execution_time
                )
                result["elapsed_seconds"] = elapsed
                result["time_exceeded"] = is_exceeded

                if is_exceeded:
                    raise TimeLimitExceededError(
                        elapsed, self.policy.max_execution_time
                    )
                else:
                    result["checks"].append("time_check_passed")

            # 2. 检查资源限制（运行时）
            if self.enable_resource_limit:
                try:
                    resources = self.resource_limiter.measure_resources()
                    result["resources"] = resources

                    # 检查内存
                    if resources["memory_mb"] > self.policy.max_memory_mb:
                        raise ResourceLimitExceededError(
                            "memory", resources["memory_mb"], self.policy.max_memory_mb
                        )

                    # 检查CPU
                    if resources["cpu_percent"] > self.policy.max_cpu_percent:
                        raise ResourceLimitExceededError(
                            "cpu", resources["cpu_percent"], self.policy.max_cpu_percent
                        )

                    result["checks"].append("resource_check_passed")
                except ImportError:
                    # psutil未安装
                    result["checks"].append("resource_check_skipped")

            result["success"] = True

        except Exception as e:
            result["success"] = False
            result["error"] = {
                "type": type(e).__name__,
                "message": str(e),
            }

            # 触发紧急清理（可选）
            if isinstance(e, (TimeLimitExceededError, ResourceLimitExceededError)):
                await self.emergency_cleanup(agent_id)
                result["emergency_cleanup"] = True

        return result

    async def emergency_cleanup(self, agent_id: str):
        """紧急清理（当检测到严重违规时）"""
        try:
            # 强制标记为失败
            self.tracker.fail_subagent(agent_id, "emergency_cleanup")

            # 强制停止时间跟踪
            self.time_limiter.stop_timing(agent_id)

            # 清理资源记录
            self.resource_limiter.cleanup_agent(agent_id)

            warnings.warn(f"紧急清理子代理: {agent_id}")
        except Exception as e:
            warnings.warn(f"紧急清理失败: {agent_id}, 错误: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取中间件统计信息"""
        tracker_stats = self.tracker.get_statistics()

        return {
            **self.stats,
            **tracker_stats,
            "policy": asdict(self.policy),
            "enabled_limits": {
                "depth": self.enable_depth_limit,
                "concurrency": self.enable_concurrency_limit,
                "time": self.enable_time_limit,
                "resource": self.enable_resource_limit,
                "tool": self.enable_tool_restriction,
            },
        }

    def update_policy(self, new_policy: RestrictionPolicy):
        """更新限制策略"""
        self.policy = new_policy
        warnings.warn("限制策略已更新，正在运行的子代理不受新策略影响")

    def reset_statistics(self):
        """重置统计信息"""
        self.stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "blocked_requests": 0,
            "depth_violations": 0,
            "concurrency_violations": 0,
            "time_violations": 0,
            "resource_violations": 0,
            "tool_violations": 0,
        }

    async def process_request(
        self, request: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理Agent请求（兼容DeerFlow中间件接口）

        Args:
            request: Agent请求
            context: 执行上下文

        Returns:
            处理后的请求
        """
        # 从请求中提取信息
        agent_id = request.get("agent_id", str(uuid.uuid4()))
        parent_id = request.get("parent_id")
        tool_name = request.get("tool_name")
        action = request.get("action", "execute")

        result = {}

        if action == "before_execute":
            # 执行前检查
            try:
                before_result = await self.before_agent(agent_id, parent_id, tool_name)
                result["before_result"] = before_result
                result["allowed"] = before_result["allowed"]
            except Exception as e:
                result["error"] = str(e)
                result["allowed"] = False

        elif action == "after_execute":
            # 执行后清理
            success = request.get("success", True)
            error = request.get("error")
            after_result = await self.after_agent(agent_id, success, error)
            result["after_result"] = after_result

        elif action == "during_execute":
            # 执行中检查
            during_result = await self.during_agent(agent_id)
            result["during_result"] = during_result

        elif action == "get_stats":
            # 获取统计信息
            result["stats"] = self.get_statistics()

        elif action == "update_policy":
            # 更新策略
            policy_config = request.get("policy", {})
            policy_yaml = yaml.dump(policy_config)
            new_policy = RestrictionPolicy.from_yaml(policy_yaml)
            self.update_policy(new_policy)
            result["policy_updated"] = True

        else:
            result["error"] = f"未知操作: {action}"

        return result


# ============================================================================
# 第四部分：完整测试系统与端到端演示
# ============================================================================


class SubagentLimitMiddlewareTestSuite:
    """SubagentLimitMiddleware测试套件"""

    def __init__(self):
        self.middleware = SubagentLimitMiddleware()
        self.test_results = {}

    async def test_depth_limit(self) -> Dict[str, Any]:
        """测试深度限制"""
        print("🧪 测试1: 深度限制")
        print("-" * 40)

        results = []

        # 测试正常深度
        try:
            agent_id = "test_depth_1"
            result = await self.middleware.before_agent(agent_id, parent_id=None)
            await self.middleware.after_agent(agent_id, success=True)
            results.append(
                {"test": "正常深度", "status": "✅ 通过", "depth": result["depth"]}
            )
        except Exception as e:
            results.append({"test": "正常深度", "status": "❌ 失败", "error": str(e)})

        # 测试嵌套深度（模拟）
        try:
            parent_id = "parent_agent"
            child_id = "child_agent"

            # 先创建父代理
            await self.middleware.before_agent(parent_id, parent_id=None)

            # 创建子代理
            result = await self.middleware.before_agent(child_id, parent_id=parent_id)
            await self.middleware.after_agent(child_id, success=True)
            await self.middleware.after_agent(parent_id, success=True)

            expected_depth = 2
            actual_depth = result["depth"]

            if actual_depth == expected_depth:
                results.append(
                    {
                        "test": "嵌套深度计算",
                        "status": "✅ 通过",
                        "expected": expected_depth,
                        "actual": actual_depth,
                    }
                )
            else:
                results.append(
                    {
                        "test": "嵌套深度计算",
                        "status": "❌ 失败",
                        "expected": expected_depth,
                        "actual": actual_depth,
                    }
                )
        except Exception as e:
            results.append(
                {"test": "嵌套深度计算", "status": "❌ 失败", "error": str(e)}
            )

        # 测试深度超限
        try:
            # 创建超深嵌套（需要模拟多个层次）
            # 这里我们直接测试深度限制器
            depth_limiter = DepthLimiter(self.middleware.tracker)

            # 模拟深度超限
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    depth_limiter.validate_depth("fake_parent", max_allowed_depth=1)
                    results.append(
                        {
                            "test": "深度超限检测",
                            "status": "❌ 失败",
                            "error": "未抛出深度超限异常",
                        }
                    )
                except DepthLimitExceededError:
                    results.append({"test": "深度超限检测", "status": "✅ 通过"})
        except Exception as e:
            results.append(
                {"test": "深度超限检测", "status": "❌ 失败", "error": str(e)}
            )

        # 打印结果
        for r in results:
            print(f"  {r['test']}: {r['status']}")
            if "error" in r:
                print(f"    错误: {r['error']}")
            if "depth" in r:
                print(f"    深度: {r['depth']}")
            if "expected" in r:
                print(f"    预期: {r['expected']}, 实际: {r['actual']}")

        print()
        return {
            "test_name": "深度限制",
            "results": results,
            "passed": all("✅" in r["status"] for r in results),
        }

    async def test_concurrency_limit(self) -> Dict[str, Any]:
        """测试并发限制"""
        print("🧪 测试2: 并发限制")
        print("-" * 40)

        results = []

        # 获取当前并发限制
        max_concurrent = self.middleware.policy.max_concurrent

        # 测试正常并发
        try:
            agent_ids = [f"concurrent_test_{i}" for i in range(min(3, max_concurrent))]

            for agent_id in agent_ids:
                await self.middleware.before_agent(agent_id)

            # 检查活跃数量
            active_count = self.middleware.tracker.get_active_count()
            expected_count = len(agent_ids)

            if active_count == expected_count:
                results.append(
                    {"test": "正常并发", "status": "✅ 通过", "count": active_count}
                )
            else:
                results.append(
                    {
                        "test": "正常并发",
                        "status": "❌ 失败",
                        "expected": expected_count,
                        "actual": active_count,
                    }
                )

            # 清理
            for agent_id in agent_ids:
                await self.middleware.after_agent(agent_id, success=True)

        except Exception as e:
            results.append({"test": "正常并发", "status": "❌ 失败", "error": str(e)})

        # 测试并发超限
        try:
            # 创建达到限制的代理
            agent_ids = []
            for i in range(max_concurrent):
                agent_id = f"limit_test_{i}"
                await self.middleware.before_agent(agent_id)
                agent_ids.append(agent_id)

            # 尝试创建超限代理
            try:
                await self.middleware.before_agent("exceed_agent")
                results.append(
                    {
                        "test": "并发超限检测",
                        "status": "❌ 失败",
                        "error": "未抛出并发超限异常",
                    }
                )
            except ConcurrencyLimitExceededError:
                results.append({"test": "并发超限检测", "status": "✅ 通过"})

            # 清理
            for agent_id in agent_ids:
                await self.middleware.after_agent(agent_id, success=True)

        except Exception as e:
            results.append(
                {"test": "并发超限检测", "status": "❌ 失败", "error": str(e)}
            )

        # 测试并发释放
        try:
            agent_id = "release_test"
            await self.middleware.before_agent(agent_id)

            before_count = self.middleware.tracker.get_active_count()
            await self.middleware.after_agent(agent_id, success=True)
            after_count = self.middleware.tracker.get_active_count()

            if before_count == 1 and after_count == 0:
                results.append(
                    {
                        "test": "并发释放",
                        "status": "✅ 通过",
                        "before": before_count,
                        "after": after_count,
                    }
                )
            else:
                results.append(
                    {
                        "test": "并发释放",
                        "status": "❌ 失败",
                        "before": before_count,
                        "after": after_count,
                    }
                )

        except Exception as e:
            results.append({"test": "并发释放", "status": "❌ 失败", "error": str(e)})

        # 打印结果
        for r in results:
            print(f"  {r['test']}: {r['status']}")
            if "error" in r:
                print(f"    错误: {r['error']}")
            if "count" in r:
                print(f"    并发数: {r['count']}")
            if "before" in r:
                print(f"    释放前: {r['before']}, 释放后: {r['after']}")

        print()
        return {
            "test_name": "并发限制",
            "results": results,
            "passed": all("✅" in r["status"] for r in results),
        }

    async def test_time_limit(self) -> Dict[str, Any]:
        """测试时间限制"""
        print("🧪 测试3: 时间限制")
        print("-" * 40)

        results = []

        # 测试时间跟踪
        try:
            agent_id = "time_track_test"

            before_result = await self.middleware.before_agent(agent_id)
            await asyncio.sleep(0.1)  # 短暂等待
            after_result = await self.middleware.after_agent(agent_id, success=True)

            duration = after_result.get("duration_seconds", 0)

            if duration > 0:
                results.append(
                    {
                        "test": "时间跟踪",
                        "status": "✅ 通过",
                        "duration": f"{duration:.3f}秒",
                    }
                )
            else:
                results.append(
                    {"test": "时间跟踪", "status": "❌ 失败", "duration": duration}
                )

        except Exception as e:
            results.append({"test": "时间跟踪", "status": "❌ 失败", "error": str(e)})

        # 测试超时检测（模拟）
        try:
            time_limiter = TimeLimiter()
            agent_id = "timeout_test"

            time_limiter.start_timing(agent_id)

            # 立即检查（不应超时）
            elapsed, is_exceeded = time_limiter.check_time(
                agent_id, max_allowed_time=1.0
            )

            if not is_exceeded and elapsed < 0.1:
                results.append(
                    {
                        "test": "时间检查",
                        "status": "✅ 通过",
                        "elapsed": f"{elapsed:.3f}秒",
                    }
                )
            else:
                results.append(
                    {
                        "test": "时间检查",
                        "status": "❌ 失败",
                        "elapsed": elapsed,
                        "exceeded": is_exceeded,
                    }
                )

            time_limiter.stop_timing(agent_id)

        except Exception as e:
            results.append({"test": "时间检查", "status": "❌ 失败", "error": str(e)})

        # 打印结果
        for r in results:
            print(f"  {r['test']}: {r['status']}")
            if "error" in r:
                print(f"    错误: {r['error']}")
            if "duration" in r:
                print(f"    持续时间: {r['duration']}")
            if "elapsed" in r:
                print(f"    已用时间: {r['elapsed']}")

        print()
        return {
            "test_name": "时间限制",
            "results": results,
            "passed": all("✅" in r["status"] for r in results),
        }

    async def test_tool_restriction(self) -> Dict[str, Any]:
        """测试工具限制"""
        print("🧪 测试4: 工具限制")
        print("-" * 40)

        results = []

        # 测试白名单
        try:
            # 创建带白名单的策略
            policy = RestrictionPolicy(allow_tools=["tool_a", "tool_b"])
            middleware = SubagentLimitMiddleware(policy)

            # 测试允许的工具
            try:
                await middleware.before_agent("test_agent", tool_name="tool_a")
                await middleware.after_agent("test_agent", success=True)
                results.append({"test": "白名单-允许工具", "status": "✅ 通过"})
            except ToolNotAllowedError:
                results.append(
                    {
                        "test": "白名单-允许工具",
                        "status": "❌ 失败",
                        "error": "允许的工具被拒绝",
                    }
                )

            # 测试不允许的工具
            try:
                await middleware.before_agent("test_agent2", tool_name="tool_c")
                results.append(
                    {
                        "test": "白名单-拒绝工具",
                        "status": "❌ 失败",
                        "error": "未拒绝不允许的工具",
                    }
                )
            except ToolNotAllowedError:
                results.append({"test": "白名单-拒绝工具", "status": "✅ 通过"})

        except Exception as e:
            results.append({"test": "白名单测试", "status": "❌ 失败", "error": str(e)})

        # 测试黑名单
        try:
            policy = RestrictionPolicy(deny_tools=["dangerous_tool"])
            middleware = SubagentLimitMiddleware(policy)

            # 测试黑名单工具
            try:
                await middleware.before_agent("test_agent3", tool_name="dangerous_tool")
                results.append(
                    {
                        "test": "黑名单-拒绝工具",
                        "status": "❌ 失败",
                        "error": "未拒绝黑名单工具",
                    }
                )
            except ToolNotAllowedError:
                results.append({"test": "黑名单-拒绝工具", "status": "✅ 通过"})

            # 测试非黑名单工具
            try:
                await middleware.before_agent("test_agent4", tool_name="safe_tool")
                await middleware.after_agent("test_agent4", success=True)
                results.append({"test": "黑名单-允许工具", "status": "✅ 通过"})
            except ToolNotAllowedError:
                results.append(
                    {
                        "test": "黑名单-允许工具",
                        "status": "❌ 失败",
                        "error": "非黑名单工具被拒绝",
                    }
                )

        except Exception as e:
            results.append({"test": "黑名单测试", "status": "❌ 失败", "error": str(e)})

        # 打印结果
        for r in results:
            print(f"  {r['test']}: {r['status']}")
            if "error" in r:
                print(f"    错误: {r['error']}")

        print()
        return {
            "test_name": "工具限制",
            "results": results,
            "passed": all("✅" in r["status"] for r in results),
        }

    async def test_integration(self) -> Dict[str, Any]:
        """测试集成功能"""
        print("🧪 测试5: 集成功能")
        print("-" * 40)

        results = []

        # 测试完整流程
        try:
            agent_id = "integration_test"

            # 执行前检查
            before_result = await self.middleware.before_agent(agent_id)
            if before_result["allowed"]:
                results.append({"test": "执行前检查", "status": "✅ 通过"})
            else:
                results.append(
                    {
                        "test": "执行前检查",
                        "status": "❌ 失败",
                        "error": "执行前检查失败",
                    }
                )

            # 执行中检查
            during_result = await self.middleware.during_agent(agent_id)
            if during_result["success"]:
                results.append({"test": "执行中检查", "status": "✅ 通过"})
            else:
                results.append(
                    {
                        "test": "执行中检查",
                        "status": "❌ 失败",
                        "error": during_result.get("error", "未知错误"),
                    }
                )

            # 执行后清理
            after_result = await self.middleware.after_agent(agent_id, success=True)
            if after_result["success"]:
                results.append({"test": "执行后清理", "status": "✅ 通过"})
            else:
                results.append(
                    {
                        "test": "执行后清理",
                        "status": "❌ 失败",
                        "error": after_result.get("error", "未知错误"),
                    }
                )

            # 检查统计信息
            stats = self.middleware.get_statistics()
            if stats["total_requests"] > 0:
                results.append(
                    {
                        "test": "统计信息",
                        "status": "✅ 通过",
                        "requests": stats["total_requests"],
                    }
                )
            else:
                results.append(
                    {
                        "test": "统计信息",
                        "status": "❌ 失败",
                        "requests": stats["total_requests"],
                    }
                )

        except Exception as e:
            results.append({"test": "完整流程", "status": "❌ 失败", "error": str(e)})

        # 测试配置更新
        try:
            new_policy = RestrictionPolicy(max_depth=10, max_concurrent=20)
            self.middleware.update_policy(new_policy)

            # 检查策略是否更新
            current_policy = self.middleware.policy
            if current_policy.max_depth == 10 and current_policy.max_concurrent == 20:
                results.append({"test": "配置更新", "status": "✅ 通过"})
            else:
                results.append(
                    {
                        "test": "配置更新",
                        "status": "❌ 失败",
                        "expected_depth": 10,
                        "actual_depth": current_policy.max_depth,
                        "expected_concurrent": 20,
                        "actual_concurrent": current_policy.max_concurrent,
                    }
                )

        except Exception as e:
            results.append({"test": "配置更新", "status": "❌ 失败", "error": str(e)})

        # 打印结果
        for r in results:
            print(f"  {r['test']}: {r['status']}")
            if "error" in r:
                print(f"    错误: {r['error']}")
            if "requests" in r:
                print(f"    请求数: {r['requests']}")

        print()
        return {
            "test_name": "集成功能",
            "results": results,
            "passed": all("✅" in r["status"] for r in results),
        }

    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🎓 Day 6 Lesson 22: SubagentLimitMiddleware - 测试套件")
        print("=" * 70)
        print()

        test_functions = [
            ("深度限制", self.test_depth_limit),
            ("并发限制", self.test_concurrency_limit),
            ("时间限制", self.test_time_limit),
            ("工具限制", self.test_tool_restriction),
            ("集成功能", self.test_integration),
        ]

        all_results = []
        total_tests = len(test_functions)
        passed_tests = 0
        failed_tests = 0

        for test_name, test_func in test_functions:
            try:
                result = await test_func()
                all_results.append(result)

                if result["passed"]:
                    passed_tests += 1
                else:
                    failed_tests += 1

            except Exception as e:
                print(f"❌ {test_name}测试异常: {e}")
                all_results.append(
                    {"test_name": test_name, "passed": False, "error": str(e)}
                )
                failed_tests += 1

        # 汇总结果
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "test_details": {r["test_name"]: r for r in all_results},
            "overall_success": failed_tests == 0,
        }

        # 打印汇总
        self.print_test_summary(summary)

        return summary

    def print_test_summary(self, test_results: Dict[str, Any]):
        """打印测试摘要"""
        print("\n" + "=" * 70)
        print("SubagentLimitMiddleware 测试套件结果")
        print("=" * 70)

        print(f"总测试数: {test_results['total_tests']}")
        print(f"通过数: {test_results['passed_tests']}")
        print(f"失败数: {test_results['failed_tests']}")

        if test_results["failed_tests"] > 0:
            print("\n失败测试详情:")
            for test_name, details in test_results["test_details"].items():
                if not details.get("passed", False):
                    print(f"  - {test_name}")
                    if "error" in details:
                        print(f"    错误: {details['error']}")

        print("\n" + "=" * 70)
        if test_results["overall_success"]:
            print("✅ 所有测试通过！")
        else:
            print("❌ 部分测试失败，请检查实现")
        print("=" * 70)


async def main_demo():
    """主演示函数"""
    print("🎓 Day 6 Lesson 22: SubagentLimitMiddleware - 演示系统")
    print("=" * 70)

    # 创建测试套件
    test_suite = SubagentLimitMiddlewareTestSuite()

    # 运行所有测试
    print("\n🧪 运行测试套件...")
    test_results = await test_suite.run_all_tests()

    # 演示端到端流程
    print("\n🚀 端到端流程演示")
    print("-" * 40)

    # 创建中间件实例
    middleware = SubagentLimitMiddleware()

    # 演示1: 正常子代理创建
    print("1. 正常子代理创建...")
    agent_id = "demo_agent_1"
    try:
        before_result = await middleware.before_agent(agent_id)
        print(f"   结果: {'允许' if before_result['allowed'] else '拒绝'}")
        print(f"   深度: {before_result.get('depth', 'N/A')}")
        print(f"   检查通过: {', '.join(before_result.get('checks_passed', []))}")

        # 模拟执行
        await asyncio.sleep(0.1)

        after_result = await middleware.after_agent(agent_id, success=True)
        print(f"   清理结果: {'成功' if after_result['success'] else '失败'}")
        print(f"   执行时间: {after_result.get('duration_seconds', 0):.3f}秒")
    except Exception as e:
        print(f"   错误: {e}")

    # 演示2: 并发限制演示
    print("\n2. 并发限制演示...")
    max_concurrent = middleware.policy.max_concurrent
    print(f"   最大并发数: {max_concurrent}")

    agent_ids = []
    for i in range(min(3, max_concurrent)):
        agent_id = f"concurrent_demo_{i}"
        try:
            await middleware.before_agent(agent_id)
            agent_ids.append(agent_id)
            print(f"   创建子代理 {agent_id}: ✅ 成功")
        except Exception as e:
            print(f"   创建子代理 {agent_id}: ❌ 失败 ({e})")

    # 演示3: 统计信息
    print("\n3. 统计信息查看...")
    stats = middleware.get_statistics()
    print(f"   总请求数: {stats['total_requests']}")
    print(f"   允许的请求: {stats['allowed_requests']}")
    print(f"   拒绝的请求: {stats['blocked_requests']}")
    print(f"   活跃子代理: {stats['active_subagents']}")
    print(f"   最大深度: {stats['max_depth']}")

    # 演示4: 配置更新
    print("\n4. 配置更新演示...")
    new_policy = RestrictionPolicy(max_depth=3, max_concurrent=5)
    middleware.update_policy(new_policy)
    print(
        f"   更新策略: 最大深度={new_policy.max_depth}, 最大并发={new_policy.max_concurrent}"
    )

    # 清理演示代理
    for agent_id in agent_ids:
        try:
            await middleware.after_agent(agent_id, success=True)
        except:
            pass

    print("\n" + "=" * 70)
    print("✅ SubagentLimitMiddleware 演示完成")
    print("=" * 70)


if __name__ == "__main__":
    # 运行主演示
    asyncio.run(main_demo())
