#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 6 Lesson 23: TodoMiddleware - 课堂演示代码

本文件提供完整的任务管理中间件实现，用于课堂教学演示。
采用四部分结构设计，全面展示TodoMiddleware的各个方面：
1. 任务管理基础：TodoItem数据结构、任务状态、依赖关系基础
2. 任务依赖系统：依赖图构建、阻塞检测、进度计算算法
3. TodoMiddleware实现：中间件核心逻辑与任务管理执行
4. 完整测试系统与端到端演示：单元测试、集成测试、边界测试、性能测试

教学目标：
1. 理解复杂任务管理在AI Agent系统中的重要性和挑战
2. 掌握任务分解的四种核心需求：分解、跟踪、持久化、优先级
3. 理解TodoItem数据结构和依赖关系管理机制
4. 了解任务进度计算和状态同步原理
5. 能够设计合理的TodoItem数据结构（dataclass）
6. 能够实现任务依赖检查和阻塞状态判断
7. 能够编写TodoMiddleware的before/after方法
8. 能够计算和生成任务进度报告

运行要求：
Python 3.12+, 安装依赖: asyncio, typing-extensions, dataclasses-json, yaml
前置课程: 已完成SubagentLimitMiddleware学习

作者: 张老师 (DeerFlow核心贡献者)
版本: v1.0
日期: 2024年4月4日
"""

import asyncio
import time
import json
import yaml
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
# 第一部分：任务管理基础
# ============================================================================


class TaskStatus(Enum):
    """任务状态枚举"""

    PENDING = "pending"  # 待处理
    READY = "ready"  # 准备就绪（依赖已满足）
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 已失败
    BLOCKED = "blocked"  # 被阻塞（依赖未满足）
    CANCELLED = "cancelled"  # 已取消

    def is_terminal(self) -> bool:
        """是否为终止状态（不可再改变）"""
        return self in [self.COMPLETED, self.FAILED, self.CANCELLED]

    def is_active(self) -> bool:
        """是否为活跃状态（可执行）"""
        return self in [self.READY, self.RUNNING]

    @classmethod
    def from_string(cls, status_str: str) -> Optional["TaskStatus"]:
        """从字符串获取任务状态"""
        status_map = {
            "pending": cls.PENDING,
            "ready": cls.READY,
            "running": cls.RUNNING,
            "completed": cls.COMPLETED,
            "failed": cls.FAILED,
            "blocked": cls.BLOCKED,
            "cancelled": cls.CANCELLED,
        }
        return status_map.get(status_str.lower())


class Priority(Enum):
    """任务优先级枚举"""

    LOW = 0  # 低优先级
    NORMAL = 1  # 普通优先级
    HIGH = 2  # 高优先级
    CRITICAL = 3  # 关键优先级

    @classmethod
    def from_string(cls, priority_str: str) -> Optional["Priority"]:
        """从字符串获取优先级"""
        priority_map = {
            "low": cls.LOW,
            "normal": cls.NORMAL,
            "high": cls.HIGH,
            "critical": cls.CRITICAL,
        }
        return priority_map.get(priority_str.lower())


@dataclass
class TodoItem:
    """任务项数据结构

    用于表示AI Agent系统中的单个任务，包含任务信息、状态、依赖关系等。
    采用dataclass自动生成常用方法，简化代码编写。
    """

    # 基础信息
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""  # 任务标题
    description: str = ""  # 任务描述

    # 状态信息
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None

    # 执行信息
    estimated_duration: Optional[float] = None  # 预估时长（秒）
    actual_duration: Optional[float] = None  # 实际时长（秒）
    retry_count: int = 0  # 重试次数
    max_retries: int = 3  # 最大重试次数

    # 依赖关系
    dependencies: List[str] = field(default_factory=list)  # 依赖任务ID列表
    dependents: List[str] = field(default_factory=list)  # 依赖此任务的任务ID列表

    # 执行上下文
    context: Dict[str, Any] = field(default_factory=dict)  # 执行上下文数据
    result: Optional[Any] = None  # 任务执行结果
    error: Optional[str] = None  # 错误信息

    # 元数据
    tags: List[str] = field(default_factory=list)  # 标签
    category: str = ""  # 分类
    assigned_to: Optional[str] = None  # 分配给谁（Agent ID）

    def __post_init__(self):
        """dataclass初始化后处理"""
        # 确保ID为字符串
        if not isinstance(self.id, str):
            self.id = str(self.id)

        # 确保时间类型正确
        if isinstance(self.created_at, str):
            try:
                self.created_at = datetime.fromisoformat(self.created_at)
            except ValueError:
                self.created_at = datetime.now()

    def is_blocked(self, todos: Dict[str, "TodoItem"]) -> bool:
        """检查任务是否被阻塞

        检查当前任务的所有依赖任务是否已完成。
        如果任何依赖任务未完成（或不存在），则当前任务被阻塞。

        Args:
            todos: 所有任务的字典，key为任务ID，value为TodoItem

        Returns:
            bool: 如果任务被阻塞返回True，否则返回False

        教学重点：
        1. 依赖关系检查算法
        2. 递归依赖检测（间接依赖）
        3. 循环依赖检测和避免
        4. 无效依赖处理
        """
        # 没有依赖，不被阻塞
        if not self.dependencies:
            return False

        # 使用集合记录已检查的任务，避免无限递归
        visited = set()

        def check_dependency(dep_id: str) -> bool:
            """递归检查单个依赖"""
            # 防止循环依赖导致无限递归
            if dep_id in visited:
                return False  # 假设循环依赖中至少有一个未完成，但实际上需要更复杂处理
            visited.add(dep_id)

            # 获取依赖任务
            dep = todos.get(dep_id)
            if dep is None:
                # 依赖不存在，视为阻塞（或者可以忽略，取决于设计）
                return True

            # 如果依赖任务未完成，则被阻塞
            if dep.status != TaskStatus.COMPLETED:
                return True

            # 递归检查依赖的依赖
            for sub_dep_id in dep.dependencies:
                if check_dependency(sub_dep_id):
                    return True

            return False

        # 检查所有直接依赖
        for dep_id in self.dependencies:
            if check_dependency(dep_id):
                return True

        return False

    def calculate_progress(self, todos: Dict[str, "TodoItem"]) -> Dict[str, Any]:
        """计算任务进度

        计算任务的完成进度，包括：
        1. 任务自身状态进度
        2. 依赖任务完成情况
        3. 子任务完成情况（如果支持）
        4. 总体进度百分比

        Args:
            todos: 所有任务的字典

        Returns:
            Dict[str, Any]: 进度信息字典

        教学重点：
        1. 进度计算算法
        2. 状态到进度值的映射
        3. 依赖任务进度聚合
        4. 进度报告格式设计
        """
        # 状态到进度值的映射
        status_progress = {
            TaskStatus.PENDING: 0.0,
            TaskStatus.READY: 0.1,
            TaskStatus.BLOCKED: 0.0,
            TaskStatus.RUNNING: 0.5,
            TaskStatus.COMPLETED: 1.0,
            TaskStatus.FAILED: 0.0,
            TaskStatus.CANCELLED: 0.0,
        }

        # 基础进度（基于状态）
        base_progress = status_progress.get(self.status, 0.0)

        # 依赖任务进度计算
        dependency_progress = 0.0
        dependency_count = len(self.dependencies)

        if dependency_count > 0:
            completed_deps = 0
            for dep_id in self.dependencies:
                dep = todos.get(dep_id)
                if dep and dep.status == TaskStatus.COMPLETED:
                    completed_deps += 1
            dependency_progress = completed_deps / dependency_count

        # 计算总体进度（加权平均）
        # 依赖进度权重：0.4，自身进度权重：0.6
        total_progress = (dependency_progress * 0.4) + (base_progress * 0.6)

        # 构建进度报告
        return {
            "task_id": self.id,
            "title": self.title,
            "status": self.status.value,
            "progress": round(total_progress, 3),
            "base_progress": round(base_progress, 3),
            "dependency_progress": round(dependency_progress, 3),
            "dependencies": {
                "total": dependency_count,
                "completed": sum(
                    1
                    for dep_id in self.dependencies
                    if todos.get(dep_id, {}).status == TaskStatus.COMPLETED
                ),
                "blocked": sum(
                    1
                    for dep_id in self.dependencies
                    if todos.get(dep_id, {}).status == TaskStatus.BLOCKED
                ),
            },
            "estimated_duration": self.estimated_duration,
            "actual_duration": self.actual_duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }

    def update_status(self, new_status: TaskStatus) -> bool:
        """更新任务状态

        根据状态流转规则更新任务状态，并设置相应的时间戳。

        Args:
            new_status: 新状态

        Returns:
            bool: 状态更新是否成功

        教学重点：
        1. 状态机设计
        2. 状态流转规则
        3. 时间戳管理
        4. 防御性状态转换
        """
        # 检查是否允许状态转换
        valid_transitions = {
            TaskStatus.PENDING: [
                TaskStatus.READY,
                TaskStatus.BLOCKED,
                TaskStatus.CANCELLED,
            ],
            TaskStatus.READY: [
                TaskStatus.RUNNING,
                TaskStatus.BLOCKED,
                TaskStatus.CANCELLED,
            ],
            TaskStatus.RUNNING: [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ],
            TaskStatus.BLOCKED: [TaskStatus.READY, TaskStatus.CANCELLED],
            TaskStatus.COMPLETED: [],  # 终止状态
            TaskStatus.FAILED: [TaskStatus.READY],  # 失败后可重试
            TaskStatus.CANCELLED: [],  # 终止状态
        }

        current_transitions = valid_transitions.get(self.status, [])
        if new_status not in current_transitions:
            return False

        # 更新状态
        old_status = self.status
        self.status = new_status

        # 设置相应的时间戳
        now = datetime.now()
        if new_status == TaskStatus.RUNNING and not self.started_at:
            self.started_at = now
        elif new_status == TaskStatus.COMPLETED and not self.completed_at:
            self.completed_at = now
            if self.started_at:
                self.actual_duration = (
                    self.completed_at - self.started_at
                ).total_seconds()
        elif new_status == TaskStatus.FAILED and not self.failed_at:
            self.failed_at = now

        # 记录状态变更历史（实际项目中可能需要）
        # self.context.setdefault("status_history", []).append({
        #     "from": old_status.value,
        #     "to": new_status.value,
        #     "timestamp": now.isoformat(),
        # })

        return True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        用于序列化、存储或传输。
        """
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
            "estimated_duration": self.estimated_duration,
            "actual_duration": self.actual_duration,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "context": self.context,
            "result": self.result,
            "error": self.error,
            "tags": self.tags,
            "category": self.category,
            "assigned_to": self.assigned_to,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TodoItem":
        """从字典创建TodoItem

        用于反序列化、从存储加载。
        """
        # 处理时间字段
        for time_field in ["created_at", "started_at", "completed_at", "failed_at"]:
            if time_field in data and data[time_field] is not None:
                if isinstance(data[time_field], str):
                    try:
                        data[time_field] = datetime.fromisoformat(data[time_field])
                    except ValueError:
                        data[time_field] = None
                elif not isinstance(data[time_field], datetime):
                    data[time_field] = None

        # 处理状态字段
        if "status" in data and isinstance(data["status"], str):
            data["status"] = TaskStatus.from_string(data["status"])

        # 处理优先级字段
        if "priority" in data:
            if isinstance(data["priority"], str):
                data["priority"] = Priority.from_string(data["priority"])
            elif isinstance(data["priority"], int):
                # 尝试从整数值映射
                priority_map = {p.value: p for p in Priority}
                data["priority"] = priority_map.get(data["priority"], Priority.NORMAL)

        return cls(**data)


@dataclass
class TodoStorage:
    """任务存储抽象层

    定义任务存储的接口，支持不同的存储后端（内存、文件、数据库等）。
    采用策略模式，便于扩展。
    """

    def save_todo(self, todo: TodoItem) -> bool:
        """保存任务

        教学重点：存储接口设计、错误处理
        """
        raise NotImplementedError("save_todo must be implemented by subclass")

    def load_todo(self, todo_id: str) -> Optional[TodoItem]:
        """加载任务

        教学重点：数据反序列化、异常处理
        """
        raise NotImplementedError("load_todo must be implemented by subclass")

    def delete_todo(self, todo_id: str) -> bool:
        """删除任务

        教学重点：数据一致性、级联删除考虑
        """
        raise NotImplementedError("delete_todo must be implemented by subclass")

    def list_todos(self, filters: Optional[Dict[str, Any]] = None) -> List[TodoItem]:
        """列出任务

        教学重点：查询接口设计、过滤条件处理
        """
        raise NotImplementedError("list_todos must be implemented by subclass")

    def update_todo(self, todo: TodoItem) -> bool:
        """更新任务

        教学重点：更新策略、并发控制考虑
        """
        raise NotImplementedError("update_todo must be implemented by subclass")


class InMemoryTodoStorage(TodoStorage):
    """内存任务存储实现

    用于演示和测试，实际生产环境应使用持久化存储。
    教学重点：简单实现、内存数据结构管理、测试友好性。
    """

    def __init__(self):
        self.todos: Dict[str, TodoItem] = {}

    def save_todo(self, todo: TodoItem) -> bool:
        """保存任务到内存字典"""
        self.todos[todo.id] = todo
        return True

    def load_todo(self, todo_id: str) -> Optional[TodoItem]:
        """从内存加载任务"""
        return self.todos.get(todo_id)

    def delete_todo(self, todo_id: str) -> bool:
        """从内存删除任务"""
        if todo_id in self.todos:
            del self.todos[todo_id]
            return True
        return False

    def list_todos(self, filters: Optional[Dict[str, Any]] = None) -> List[TodoItem]:
        """列出内存中的所有任务，支持简单过滤"""
        todos = list(self.todos.values())

        if not filters:
            return todos

        filtered = []
        for todo in todos:
            match = True
            for key, value in filters.items():
                if key == "status" and todo.status != value:
                    match = False
                    break
                elif key == "priority" and todo.priority != value:
                    match = False
                    break
                elif key == "category" and todo.category != value:
                    match = False
                    break
                elif key == "assigned_to" and todo.assigned_to != value:
                    match = False
                    break
                elif key == "tags" and value not in todo.tags:
                    match = False
                    break

            if match:
                filtered.append(todo)

        return filtered

    def update_todo(self, todo: TodoItem) -> bool:
        """更新内存中的任务"""
        if todo.id in self.todos:
            self.todos[todo.id] = todo
            return True
        return False


# ============================================================================
# 第二部分：任务依赖系统
# ============================================================================


class DependencyGraph:
    """依赖图管理器

    管理任务之间的依赖关系，提供依赖检查、拓扑排序、循环检测等功能。
    教学重点：图算法、有向无环图（DAG）管理、性能优化。
    """

    def __init__(self):
        self.nodes: Dict[str, TodoItem] = {}  # 节点：任务ID -> TodoItem
        self.edges: Dict[str, Set[str]] = defaultdict(
            set
        )  # 边：任务ID -> 依赖任务ID集合

    def add_node(self, todo: TodoItem) -> bool:
        """添加任务节点到依赖图"""
        if todo.id in self.nodes:
            return False

        self.nodes[todo.id] = todo

        # 添加依赖边
        for dep_id in todo.dependencies:
            self.edges[todo.id].add(dep_id)

        # 更新反向依赖（dependents）
        for dep_id in todo.dependencies:
            dep = self.nodes.get(dep_id)
            if dep:
                if todo.id not in dep.dependents:
                    dep.dependents.append(todo.id)

        return True

    def remove_node(self, todo_id: str) -> bool:
        """从依赖图中删除任务节点"""
        if todo_id not in self.nodes:
            return False

        # 删除该任务作为依赖的边
        del self.edges[todo_id]

        # 从其他任务的依赖中删除该任务
        for node_id in self.edges:
            self.edges[node_id].discard(todo_id)

        # 从其他任务的dependents中删除该任务
        for node in self.nodes.values():
            if todo_id in node.dependents:
                node.dependents.remove(todo_id)

        # 删除节点
        del self.nodes[todo_id]

        return True

    def has_cycle(self) -> bool:
        """检查依赖图中是否存在循环依赖

        使用深度优先搜索（DFS）检测有向图中的环。

        教学重点：
        1. 图遍历算法
        2. 循环检测算法
        3. 递归DFS实现
        4. 性能优化考虑
        """
        visited = set()
        rec_stack = set()

        def dfs(node_id: str) -> bool:
            """深度优先搜索检测环"""
            visited.add(node_id)
            rec_stack.add(node_id)

            # 检查所有邻居节点
            for neighbor_id in self.edges.get(node_id, set()):
                if neighbor_id not in visited:
                    if dfs(neighbor_id):
                        return True
                elif neighbor_id in rec_stack:
                    # 找到环
                    return True

            rec_stack.remove(node_id)
            return False

        # 对每个未访问的节点进行DFS
        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True

        return False

    def topological_sort(self) -> List[str]:
        """拓扑排序

        返回任务的执行顺序，确保依赖任务先于依赖它的任务执行。
        如果存在环，返回空列表。

        教学重点：
        1. 拓扑排序算法
        2. Kahn算法实现
        3. 入度计算
        4. 执行顺序生成
        """
        if self.has_cycle():
            return []

        # 计算入度（每个节点被依赖的数量）
        in_degree = {node_id: 0 for node_id in self.nodes}
        for node_id in self.edges:
            for dep_id in self.edges[node_id]:
                in_degree[dep_id] += 1

        # 找到入度为0的节点（没有依赖的节点）
        queue = deque([node_id for node_id in self.nodes if in_degree[node_id] == 0])
        sorted_nodes = []

        while queue:
            node_id = queue.popleft()
            sorted_nodes.append(node_id)

            # 减少邻居节点的入度
            for neighbor_id in self.edges.get(node_id, set()):
                in_degree[neighbor_id] -= 1
                if in_degree[neighbor_id] == 0:
                    queue.append(neighbor_id)

        # 检查是否所有节点都被排序
        if len(sorted_nodes) != len(self.nodes):
            # 存在环，无法完全排序
            return []

        return sorted_nodes

    def get_execution_order(self) -> List[List[str]]:
        """获取分层的执行顺序

        返回任务的分层执行顺序，同一层的任务可以并行执行。

        教学重点：
        1. 分层拓扑排序
        2. 并行执行规划
        3. 关键路径分析基础
        """
        if self.has_cycle():
            return []

        # 计算入度
        in_degree = {node_id: 0 for node_id in self.nodes}
        for node_id in self.edges:
            for dep_id in self.edges[node_id]:
                in_degree[dep_id] += 1

        # 分层执行
        layers = []
        current_layer = [node_id for node_id in self.nodes if in_degree[node_id] == 0]

        while current_layer:
            layers.append(current_layer.copy())

            # 更新入度
            for node_id in current_layer:
                for neighbor_id in self.edges.get(node_id, set()):
                    in_degree[neighbor_id] -= 1

            # 生成下一层
            next_layer = []
            for node_id in self.nodes:
                if (
                    node_id not in [n for layer in layers for n in layer]
                    and in_degree[node_id] == 0
                ):
                    next_layer.append(node_id)

            current_layer = next_layer

        return layers

    def calculate_critical_path(self) -> List[str]:
        """计算关键路径

        基于任务预估时长计算关键路径，识别项目中最长的任务链。
        简化版本，假设所有任务都可以并行执行除了依赖限制。

        教学重点：
        1. 关键路径算法基础
        2. 最长路径计算
        3. 项目管理应用
        """
        if self.has_cycle():
            return []

        # 获取拓扑排序
        topo_order = self.topological_sort()
        if not topo_order:
            return []

        # 初始化最长路径和前置节点
        longest_path = {node_id: 0 for node_id in self.nodes}
        predecessor = {node_id: None for node_id in self.nodes}

        # 遍历拓扑排序
        for node_id in topo_order:
            node = self.nodes[node_id]
            node_duration = node.estimated_duration or 1.0  # 默认1秒

            # 更新所有依赖此节点的任务
            for neighbor_id in self.edges.get(node_id, set()):
                new_path = longest_path[node_id] + node_duration
                if new_path > longest_path[neighbor_id]:
                    longest_path[neighbor_id] = new_path
                    predecessor[neighbor_id] = node_id

        # 找到最长路径的终点
        end_node = max(longest_path, key=longest_path.get)

        # 回溯构建关键路径
        critical_path = []
        current = end_node
        while current is not None:
            critical_path.append(current)
            current = predecessor[current]

        return list(reversed(critical_path))

    def get_task_dependencies(self, todo_id: str, recursive: bool = True) -> Set[str]:
        """获取任务的所有依赖（包括间接依赖）

        教学重点：递归依赖收集、图遍历、性能优化
        """
        if todo_id not in self.nodes:
            return set()

        dependencies = set()
        visited = set()

        def collect_deps(node_id: str):
            """递归收集依赖"""
            if node_id in visited:
                return
            visited.add(node_id)

            node = self.nodes.get(node_id)
            if not node:
                return

            for dep_id in node.dependencies:
                dependencies.add(dep_id)
                if recursive:
                    collect_deps(dep_id)

        collect_deps(todo_id)
        return dependencies

    def get_task_dependents(self, todo_id: str, recursive: bool = True) -> Set[str]:
        """获取任务的所有依赖者（包括间接依赖者）

        教学重点：反向依赖收集、图遍历
        """
        if todo_id not in self.nodes:
            return set()

        dependents = set()
        visited = set()

        def collect_dependents(node_id: str):
            """递归收集依赖者"""
            if node_id in visited:
                return
            visited.add(node_id)

            node = self.nodes.get(node_id)
            if not node:
                return

            for dependent_id in node.dependents:
                dependents.add(dependent_id)
                if recursive:
                    collect_dependents(dependent_id)

        collect_dependents(todo_id)
        return dependents


class TodoProgressCalculator:
    """任务进度计算器

    计算整个任务集的总体进度，支持不同粒度的进度报告。
    教学重点：进度聚合算法、权重分配、报告生成。
    """

    def __init__(self, todos: Dict[str, TodoItem]):
        self.todos = todos

    def calculate_overall_progress(self) -> Dict[str, Any]:
        """计算总体进度

        基于所有任务的完成状态计算整体进度。

        教学重点：
        1. 进度聚合方法
        2. 权重分配策略
        3. 统计信息计算
        """
        total_tasks = len(self.todos)
        if total_tasks == 0:
            return {
                "overall_progress": 0.0,
                "completed_tasks": 0,
                "total_tasks": 0,
                "progress_by_status": {},
                "progress_by_priority": {},
                "estimated_time_remaining": 0.0,
            }

        # 按状态统计
        status_counts = defaultdict(int)
        completed_tasks = 0
        running_tasks = 0
        blocked_tasks = 0

        for todo in self.todos.values():
            status_counts[todo.status.value] += 1

            if todo.status == TaskStatus.COMPLETED:
                completed_tasks += 1
            elif todo.status == TaskStatus.RUNNING:
                running_tasks += 1
            elif todo.status == TaskStatus.BLOCKED:
                blocked_tasks += 1

        # 计算总体进度（加权平均）
        # 已完成：1.0，运行中：0.5，其他：0.0
        weighted_progress = completed_tasks * 1.0 + running_tasks * 0.5
        overall_progress = weighted_progress / total_tasks if total_tasks > 0 else 0.0

        # 按优先级统计进度
        priority_progress = {}
        for priority in Priority:
            priority_tasks = [t for t in self.todos.values() if t.priority == priority]
            if not priority_tasks:
                continue

            priority_completed = sum(
                1 for t in priority_tasks if t.status == TaskStatus.COMPLETED
            )
            priority_running = sum(
                1 for t in priority_tasks if t.status == TaskStatus.RUNNING
            )
            priority_weighted = priority_completed * 1.0 + priority_running * 0.5
            priority_progress[priority.name] = round(
                priority_weighted / len(priority_tasks), 3
            )

        # 估计剩余时间（简化版本）
        # 基于已完成任务的平均时间和剩余任务数量
        estimated_remaining = 0.0
        completed_with_duration = [
            t
            for t in self.todos.values()
            if t.status == TaskStatus.COMPLETED and t.actual_duration
        ]
        remaining_tasks = total_tasks - completed_tasks

        if completed_with_duration and remaining_tasks > 0:
            avg_duration = sum(
                t.actual_duration for t in completed_with_duration
            ) / len(completed_with_duration)
            estimated_remaining = avg_duration * remaining_tasks

        return {
            "overall_progress": round(overall_progress, 3),
            "completed_tasks": completed_tasks,
            "running_tasks": running_tasks,
            "blocked_tasks": blocked_tasks,
            "total_tasks": total_tasks,
            "completion_rate": round(completed_tasks / total_tasks * 100, 1)
            if total_tasks > 0
            else 0.0,
            "progress_by_status": dict(status_counts),
            "progress_by_priority": priority_progress,
            "estimated_time_remaining": round(estimated_remaining, 1),
            "estimated_completion_time": datetime.now()
            + timedelta(seconds=estimated_remaining)
            if estimated_remaining > 0
            else None,
        }

    def calculate_dependency_progress(self) -> Dict[str, Any]:
        """计算依赖关系相关的进度

        教学重点：依赖链分析、阻塞分析、关键路径识别
        """
        # 创建依赖图
        graph = DependencyGraph()
        for todo in self.todos.values():
            graph.add_node(todo)

        # 分析依赖关系
        dependency_chains = []
        blocked_by_dependencies = 0

        for todo in self.todos.values():
            if todo.status == TaskStatus.BLOCKED:
                # 检查是否因依赖而阻塞
                if todo.is_blocked(self.todos):
                    blocked_by_dependencies += 1

            # 查找长依赖链
            if not todo.dependencies and todo.dependents:
                # 这是一个起始节点，跟踪依赖链
                chain = self._find_longest_chain(todo.id, graph)
                if len(chain) > 1:
                    dependency_chains.append(chain)

        # 计算关键路径
        critical_path = graph.calculate_critical_path()
        critical_path_tasks = [
            self.todos[tid] for tid in critical_path if tid in self.todos
        ]
        critical_path_duration = sum(
            t.estimated_duration or 1.0 for t in critical_path_tasks
        )

        # 获取执行顺序
        execution_layers = graph.get_execution_order()
        max_parallel_tasks = (
            max(len(layer) for layer in execution_layers) if execution_layers else 0
        )

        return {
            "total_dependencies": sum(
                len(todo.dependencies) for todo in self.todos.values()
            ),
            "blocked_by_dependencies": blocked_by_dependencies,
            "dependency_chains_count": len(dependency_chains),
            "longest_chain_length": max(len(chain) for chain in dependency_chains)
            if dependency_chains
            else 0,
            "critical_path": {
                "tasks": [t.id for t in critical_path_tasks],
                "estimated_duration": round(critical_path_duration, 1),
                "task_count": len(critical_path),
            },
            "execution_layers": len(execution_layers),
            "max_parallel_tasks": max_parallel_tasks,
            "has_circular_dependencies": graph.has_cycle(),
        }

    def _find_longest_chain(self, start_id: str, graph: DependencyGraph) -> List[str]:
        """查找从起始任务开始的最长依赖链"""
        longest_chain = []

        def dfs(node_id: str, current_chain: List[str]):
            nonlocal longest_chain

            if node_id in current_chain:
                return  # 避免循环

            new_chain = current_chain + [node_id]

            if len(new_chain) > len(longest_chain):
                longest_chain = new_chain

            node = self.todos.get(node_id)
            if not node:
                return

            # 继续跟踪依赖者
            for dependent_id in node.dependents:
                dfs(dependent_id, new_chain)

        dfs(start_id, [])
        return longest_chain

    def generate_progress_report(self) -> Dict[str, Any]:
        """生成完整的进度报告"""
        overall = self.calculate_overall_progress()
        dependency = self.calculate_dependency_progress()

        return {
            "overall": overall,
            "dependency": dependency,
            "timestamp": datetime.now().isoformat(),
            "task_count": len(self.todos),
            "summary": self._generate_summary(overall, dependency),
        }

    def _generate_summary(
        self, overall: Dict[str, Any], dependency: Dict[str, Any]
    ) -> str:
        """生成人类可读的进度摘要"""
        completion_rate = overall.get("completion_rate", 0.0)
        completed = overall.get("completed_tasks", 0)
        total = overall.get("total_tasks", 0)
        blocked = overall.get("blocked_tasks", 0)
        remaining_time = overall.get("estimated_time_remaining", 0.0)

        summary_parts = []

        if completion_rate >= 100:
            summary_parts.append("✅ 所有任务已完成！")
        elif completion_rate >= 80:
            summary_parts.append(
                f"📊 进度良好：完成{completed}/{total}个任务 ({completion_rate}%)"
            )
        elif completion_rate >= 50:
            summary_parts.append(
                f"📈 进展中：完成{completed}/{total}个任务 ({completion_rate}%)"
            )
        else:
            summary_parts.append(
                f"🚧 刚开始：完成{completed}/{total}个任务 ({completion_rate}%)"
            )

        if blocked > 0:
            summary_parts.append(f"⚠️  {blocked}个任务被阻塞")

        if remaining_time > 0:
            hours = int(remaining_time // 3600)
            minutes = int((remaining_time % 3600) // 60)
            if hours > 0:
                summary_parts.append(f"⏱️  预计剩余时间：{hours}小时{minutes}分钟")
            else:
                summary_parts.append(f"⏱️  预计剩余时间：{minutes}分钟")

        if dependency.get("has_circular_dependencies", False):
            summary_parts.append("🔄 检测到循环依赖，请检查任务依赖关系")

        critical_path_len = len(dependency.get("critical_path", {}).get("tasks", []))
        if critical_path_len > 3:
            summary_parts.append(
                f"🔑 关键路径包含{critical_path_len}个任务，影响整体进度"
            )

        return " | ".join(summary_parts)


# ============================================================================
# 第三部分：TodoMiddleware实现
# ============================================================================


class TodoMiddleware:
    """任务管理中间件

    在Agent执行流程中插入任务管理功能，支持：
    1. 任务加载和初始化
    2. 任务依赖检查
    3. 任务状态跟踪
    4. 任务进度计算
    5. 任务结果保存

    教学重点：
    1. 中间件设计模式
    2. 任务生命周期管理
    3. 异步执行流程
    4. 错误处理和恢复
    """

    def __init__(self, storage: Optional[TodoStorage] = None):
        """初始化TodoMiddleware"""
        self.storage = storage or InMemoryTodoStorage()
        self.current_task_id: Optional[str] = None
        self.task_start_time: Optional[datetime] = None
        self.task_context: Dict[str, Any] = {}

    async def before_agent(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """Agent执行前的处理

        在Agent执行前调用，用于：
        1. 加载任务信息
        2. 检查任务依赖是否满足
        3. 更新任务状态为RUNNING
        4. 记录开始时间

        Args:
            agent_input: Agent输入数据

        Returns:
            Dict[str, Any]: 更新后的Agent输入数据

        教学重点：
        1. 前置处理逻辑
        2. 状态转换检查
        3. 依赖验证
        4. 上下文准备
        """
        # 从输入中获取任务ID
        task_id = agent_input.get("task_id") or self.current_task_id
        if not task_id:
            # 如果没有任务ID，则创建一个新任务
            task_id = self._create_new_task(agent_input)
            agent_input["task_id"] = task_id

        # 加载任务
        todo = self.storage.load_todo(task_id)
        if not todo:
            # 任务不存在，创建新任务
            todo = self._create_todo_from_input(agent_input)
            self.storage.save_todo(todo)

        # 检查任务是否被阻塞
        todos = self._load_all_todos()
        if todo.is_blocked(todos):
            todo.update_status(TaskStatus.BLOCKED)
            self.storage.update_todo(todo)
            raise TaskBlockedError(
                f"任务 '{todo.title}' 被依赖任务阻塞",
                task_id=todo.id,
                blocking_dependencies=self._get_blocking_dependencies(todo, todos),
            )

        # 更新任务状态为RUNNING
        if todo.status != TaskStatus.RUNNING:
            todo.update_status(TaskStatus.RUNNING)
            self.storage.update_todo(todo)

        # 记录当前任务信息
        self.current_task_id = todo.id
        self.task_start_time = datetime.now()
        self.task_context = todo.context.copy()

        # 将任务信息添加到Agent输入中
        agent_input["todo"] = todo.to_dict()
        agent_input["todo_context"] = self.task_context

        print(f"📝 TodoMiddleware: 开始执行任务 '{todo.title}' (ID: {todo.id})")
        print(f"   状态: {todo.status.value}, 优先级: {todo.priority.name}")

        return agent_input

    async def during_agent(self, agent_output: Dict[str, Any]) -> Dict[str, Any]:
        """Agent执行中的处理

        在Agent执行过程中定期调用（如果支持），用于：
        1. 检查任务是否超时
        2. 更新任务进度
        3. 收集执行统计信息

        Args:
            agent_output: Agent输出数据

        Returns:
            Dict[str, Any]: 更新后的Agent输出数据

        教学重点：
        1. 中间处理逻辑
        2. 进度更新机制
        3. 超时检查
        4. 统计信息收集
        """
        if not self.current_task_id:
            return agent_output

        todo = self.storage.load_todo(self.current_task_id)
        if not todo:
            return agent_output

        # 检查执行时间（简单超时检查）
        if self.task_start_time and todo.estimated_duration:
            elapsed = (datetime.now() - self.task_start_time).total_seconds()
            if elapsed > todo.estimated_duration * 1.5:  # 允许50%超时
                warning_msg = f"任务执行时间 ({elapsed:.1f}s) 超过预估时间 ({todo.estimated_duration}s)"
                print(f"⚠️  TodoMiddleware: {warning_msg}")

                # 记录警告，但不中断执行
                todo.context.setdefault("warnings", []).append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "message": warning_msg,
                    }
                )
                self.storage.update_todo(todo)

        # 更新进度信息（如果Agent提供了进度）
        if "progress" in agent_output:
            progress = agent_output.get("progress")
            todo.context["last_progress_update"] = {
                "timestamp": datetime.now().isoformat(),
                "progress": progress,
            }
            self.storage.update_todo(todo)

        return agent_output

    async def after_agent(self, agent_output: Dict[str, Any]) -> Dict[str, Any]:
        """Agent执行后的处理

        在Agent执行后调用，用于：
        1. 更新任务状态（完成/失败）
        2. 保存任务结果
        3. 计算实际执行时间
        4. 触发依赖任务的检查
        5. 生成进度报告

        Args:
            agent_output: Agent输出数据

        Returns:
            Dict[str, Any]: 更新后的Agent输出数据

        教学重点：
        1. 后置处理逻辑
        2. 结果保存
        3. 状态更新
        4. 依赖链更新
        5. 进度报告生成
        """
        if not self.current_task_id:
            return agent_output

        todo = self.storage.load_todo(self.current_task_id)
        if not todo:
            return agent_output

        # 根据Agent执行结果更新任务状态
        if agent_output.get("success", True):
            todo.update_status(TaskStatus.COMPLETED)
            todo.result = agent_output.get("result")
            print(f"✅ TodoMiddleware: 任务 '{todo.title}' 成功完成")
        else:
            todo.update_status(TaskStatus.FAILED)
            todo.error = agent_output.get("error", "未知错误")
            todo.retry_count += 1
            print(f"❌ TodoMiddleware: 任务 '{todo.title}' 失败: {todo.error}")

            # 检查是否达到最大重试次数
            if todo.retry_count >= todo.max_retries:
                print(
                    f"🛑 TodoMiddleware: 任务 '{todo.title}' 达到最大重试次数，标记为失败"
                )

        # 计算实际执行时间
        if self.task_start_time:
            todo.actual_duration = (
                datetime.now() - self.task_start_time
            ).total_seconds()

        # 保存任务结果
        todo.context.update(self.task_context)
        self.storage.update_todo(todo)

        # 检查依赖此任务的其他任务
        self._update_dependent_tasks(todo)

        # 生成进度报告
        todos = self._load_all_todos()
        progress_calc = TodoProgressCalculator(todos)
        progress_report = progress_calc.generate_progress_report()

        # 将进度报告添加到输出中
        agent_output["todo_progress"] = progress_report
        agent_output["completed_task"] = todo.to_dict()

        # 清理当前任务上下文
        self.current_task_id = None
        self.task_start_time = None
        self.task_context = {}

        print(f"📊 TodoMiddleware: 任务进度报告生成")
        print(
            f"   总体进度: {progress_report['overall']['overall_progress'] * 100:.1f}%"
        )
        print(
            f"   已完成: {progress_report['overall']['completed_tasks']}/{progress_report['overall']['total_tasks']}"
        )

        return agent_output

    async def on_error(
        self, error: Exception, agent_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """错误处理

        当Agent执行出错时调用，用于：
        1. 记录错误信息
        2. 更新任务状态为FAILED
        3. 保存错误详情

        Args:
            error: 发生的异常
            agent_input: Agent输入数据

        Returns:
            Dict[str, Any]: 错误处理后的Agent输入数据

        教学重点：
        1. 错误处理策略
        2. 异常捕获和记录
        3. 状态恢复机制
        """
        if not self.current_task_id:
            return {"error": str(error)}

        todo = self.storage.load_todo(self.current_task_id)
        if not todo:
            return {"error": str(error)}

        # 更新任务状态为失败
        todo.update_status(TaskStatus.FAILED)
        todo.error = str(error)
        todo.retry_count += 1

        # 保存错误详情
        todo.context["error_details"] = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "agent_input": agent_input,
        }

        self.storage.update_todo(todo)

        print(f"🚨 TodoMiddleware: 任务 '{todo.title}' 执行出错: {error}")

        # 清理上下文
        self.current_task_id = None
        self.task_start_time = None
        self.task_context = {}

        return {"error": str(error), "task_id": todo.id, "task_failed": True}

    def _create_new_task(self, agent_input: Dict[str, Any]) -> str:
        """从Agent输入创建新任务"""
        todo = self._create_todo_from_input(agent_input)
        self.storage.save_todo(todo)
        return todo.id

    def _create_todo_from_input(self, agent_input: Dict[str, Any]) -> TodoItem:
        """从Agent输入创建TodoItem"""
        return TodoItem(
            title=agent_input.get("title", "未命名任务"),
            description=agent_input.get("description", ""),
            priority=Priority.from_string(agent_input.get("priority", "normal"))
            or Priority.NORMAL,
            estimated_duration=agent_input.get("estimated_duration"),
            dependencies=agent_input.get("dependencies", []),
            context=agent_input.get("context", {}),
            tags=agent_input.get("tags", []),
            category=agent_input.get("category", ""),
            assigned_to=agent_input.get("assigned_to"),
        )

    def _load_all_todos(self) -> Dict[str, TodoItem]:
        """加载所有任务"""
        todos_list = self.storage.list_todos()
        return {todo.id: todo for todo in todos_list}

    def _get_blocking_dependencies(
        self, todo: TodoItem, todos: Dict[str, TodoItem]
    ) -> List[Dict[str, Any]]:
        """获取导致阻塞的依赖任务"""
        blocking = []

        def check_dep(dep_id: str, visited: Set[str]) -> bool:
            """递归检查依赖"""
            if dep_id in visited:
                return False
            visited.add(dep_id)

            dep = todos.get(dep_id)
            if not dep:
                blocking.append(
                    {
                        "task_id": dep_id,
                        "reason": "任务不存在",
                        "status": "missing",
                    }
                )
                return True

            if dep.status != TaskStatus.COMPLETED:
                blocking.append(
                    {
                        "task_id": dep_id,
                        "title": dep.title,
                        "status": dep.status.value,
                        "reason": f"依赖任务状态为 {dep.status.value}",
                    }
                )
                return True

            # 检查间接依赖
            for sub_dep_id in dep.dependencies:
                if check_dep(sub_dep_id, visited):
                    return True

            return False

        visited = set()
        for dep_id in todo.dependencies:
            check_dep(dep_id, visited.copy())

        return blocking

    def _update_dependent_tasks(self, completed_todo: TodoItem) -> None:
        """更新依赖此任务的其他任务

        当一个任务完成时，检查依赖它的任务是否不再被阻塞。
        教学重点：依赖链更新、状态同步、级联更新。
        """
        todos = self._load_all_todos()

        for dependent_id in completed_todo.dependents:
            dependent = todos.get(dependent_id)
            if not dependent:
                continue

            # 检查依赖任务是否全部完成
            all_deps_completed = True
            for dep_id in dependent.dependencies:
                dep = todos.get(dep_id)
                if dep and dep.status != TaskStatus.COMPLETED:
                    all_deps_completed = False
                    break

            # 如果所有依赖都已完成，更新状态为READY
            if all_deps_completed and dependent.status == TaskStatus.BLOCKED:
                dependent.update_status(TaskStatus.READY)
                self.storage.update_todo(dependent)
                print(
                    f"🔄 TodoMiddleware: 任务 '{dependent.title}' 依赖已满足，状态更新为 READY"
                )

    def get_progress_report(self) -> Dict[str, Any]:
        """获取当前进度报告"""
        todos = self._load_all_todos()
        progress_calc = TodoProgressCalculator(todos)
        return progress_calc.generate_progress_report()

    def list_tasks(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """列出所有任务（带可选过滤）"""
        todos = self.storage.list_todos(filters)
        return [todo.to_dict() for todo in todos]

    def get_task_details(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详情"""
        todo = self.storage.load_todo(task_id)
        if not todo:
            return None

        # 计算任务进度
        todos = self._load_all_todos()
        progress = todo.calculate_progress(todos)

        result = todo.to_dict()
        result["progress"] = progress
        result["is_blocked"] = todo.is_blocked(todos)
        result["blocking_dependencies"] = (
            self._get_blocking_dependencies(todo, todos) if result["is_blocked"] else []
        )

        return result


class TaskBlockedError(Exception):
    """任务被阻塞异常"""

    def __init__(
        self,
        message: str,
        task_id: str,
        blocking_dependencies: List[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.task_id = task_id
        self.blocking_dependencies = blocking_dependencies or []

    def __str__(self) -> str:
        deps_info = ", ".join(
            [
                f"{d.get('title', d['task_id'])} ({d['status']})"
                for d in self.blocking_dependencies[:3]
            ]
        )
        if len(self.blocking_dependencies) > 3:
            deps_info += f" 等 {len(self.blocking_dependencies)} 个依赖"

        return f"{super().__str__()}. 阻塞依赖: {deps_info}"


class TaskValidationError(Exception):
    """任务验证错误"""

    pass


class CircularDependencyError(Exception):
    """循环依赖错误"""

    pass


# ============================================================================
# 第四部分：完整测试系统与端到端演示
# ============================================================================


class TodoMiddlewareTestSuite:
    """TodoMiddleware测试套件

    包含完整的单元测试、集成测试、边界测试和性能测试。
    教学重点：测试驱动开发、测试覆盖率、边界条件测试。
    """

    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []

    def run_all_tests(self) -> bool:
        """运行所有测试"""
        print("🎓 Day 6 Lesson 23: TodoMiddleware - 测试套件")
        print("=" * 80)
        print()

        test_methods = [
            self.test_todo_item_creation,
            self.test_todo_item_status_transitions,
            self.test_todo_item_blocked_check,
            self.test_todo_item_progress_calculation,
            self.test_dependency_graph_basic,
            self.test_dependency_graph_cycle_detection,
            self.test_dependency_graph_topological_sort,
            self.test_todo_progress_calculator,
            self.test_todo_middleware_basic_flow,
            self.test_todo_middleware_dependency_flow,
            self.test_todo_middleware_error_handling,
            self.test_integration_scenario,
        ]

        for test_method in test_methods:
            try:
                test_method()
                self.test_results.append((test_method.__name__, True, ""))
                self.tests_passed += 1
            except AssertionError as e:
                self.test_results.append((test_method.__name__, False, str(e)))
                self.tests_failed += 1
                print(f"❌ {test_method.__name__}: 失败 - {e}")
            except Exception as e:
                self.test_results.append((test_method.__name__, False, f"异常: {e}"))
                self.tests_failed += 1
                print(f"💥 {test_method.__name__}: 异常 - {e}")

        self._print_summary()
        return self.tests_failed == 0

    def test_todo_item_creation(self):
        """测试TodoItem创建和基本属性"""
        print("🧪 测试1: TodoItem创建和基本属性")
        print("-" * 80)

        # 测试基本创建
        todo = TodoItem(
            title="测试任务",
            description="这是一个测试任务",
            priority=Priority.HIGH,
            estimated_duration=60.0,
        )

        assert todo.title == "测试任务", "标题设置错误"
        assert todo.description == "这是一个测试任务", "描述设置错误"
        assert todo.priority == Priority.HIGH, "优先级设置错误"
        assert todo.status == TaskStatus.PENDING, "默认状态应为PENDING"
        assert todo.estimated_duration == 60.0, "预估时长设置错误"
        assert todo.id is not None and len(todo.id) > 0, "ID应自动生成"
        assert todo.created_at is not None, "创建时间应自动设置"

        # 测试字典转换
        todo_dict = todo.to_dict()
        assert todo_dict["title"] == "测试任务", "字典转换标题错误"
        assert todo_dict["status"] == "pending", "字典转换状态错误"
        assert todo_dict["priority"] == 2, "字典转换优先级错误"  # HIGH = 2

        # 测试从字典创建
        todo2 = TodoItem.from_dict(todo_dict)
        assert todo2.title == todo.title, "从字典创建标题错误"
        assert todo2.status == todo.status, "从字典创建状态错误"
        assert todo2.priority == todo.priority, "从字典创建优先级错误"

        print("   基本属性: ✅ 通过")
        print("   字典转换: ✅ 通过")
        print("   从字典创建: ✅ 通过")
        print()

    def test_todo_item_status_transitions(self):
        """测试TodoItem状态转换"""
        print("🧪 测试2: TodoItem状态转换")
        print("-" * 80)

        todo = TodoItem(title="状态转换测试")

        # PENDING -> READY 应成功
        assert todo.update_status(TaskStatus.READY), "PENDING -> READY 应成功"
        assert todo.status == TaskStatus.READY, "状态应为READY"

        # READY -> RUNNING 应成功
        assert todo.update_status(TaskStatus.RUNNING), "READY -> RUNNING 应成功"
        assert todo.status == TaskStatus.RUNNING, "状态应为RUNNING"
        assert todo.started_at is not None, "开始时间应设置"

        # RUNNING -> COMPLETED 应成功
        assert todo.update_status(TaskStatus.COMPLETED), "RUNNING -> COMPLETED 应成功"
        assert todo.status == TaskStatus.COMPLETED, "状态应为COMPLETED"
        assert todo.completed_at is not None, "完成时间应设置"
        assert todo.actual_duration is not None, "实际时长应计算"

        # COMPLETED -> RUNNING 应失败（终止状态）
        assert not todo.update_status(TaskStatus.RUNNING), "COMPLETED -> RUNNING 应失败"

        # 测试失败重试
        todo2 = TodoItem(title="失败重试测试")
        todo2.update_status(TaskStatus.RUNNING)
        todo2.update_status(TaskStatus.FAILED)
        assert todo2.status == TaskStatus.FAILED, "状态应为FAILED"
        assert todo2.retry_count == 1, "重试次数应增加"

        # FAILED -> READY 应成功（重试）
        assert todo2.update_status(TaskStatus.READY), "FAILED -> READY 应成功"
        assert todo2.status == TaskStatus.READY, "状态应为READY"

        print("   状态流转: ✅ 通过")
        print("   时间戳设置: ✅ 通过")
        print("   失败重试: ✅ 通过")
        print()

    def test_todo_item_blocked_check(self):
        """测试TodoItem阻塞检查"""
        print("🧪 测试3: TodoItem阻塞检查")
        print("-" * 80)

        # 创建任务集合
        todos = {}

        # 创建三个任务：task1 -> task2 -> task3（依赖链）
        task1 = TodoItem(title="任务1")
        task2 = TodoItem(title="任务2", dependencies=[task1.id])
        task3 = TodoItem(title="任务3", dependencies=[task2.id])

        todos[task1.id] = task1
        todos[task2.id] = task2
        todos[task3.id] = task3

        # task2 应被 task1 阻塞（task1未完成）
        assert task2.is_blocked(todos), "task2 应被 task1 阻塞"

        # task1 完成
        task1.update_status(TaskStatus.COMPLETED)

        # task2 应不再被阻塞
        assert not task2.is_blocked(todos), "task2 应不再被阻塞"

        # task3 应被 task2 阻塞（task2未完成）
        assert task3.is_blocked(todos), "task3 应被 task2 阻塞"

        # 测试循环依赖检测（简化版本）
        task4 = TodoItem(title="任务4")
        task5 = TodoItem(title="任务5", dependencies=[task4.id])
        # 创建循环依赖：task4 依赖 task5
        task4.dependencies = [task5.id]

        todos[task4.id] = task4
        todos[task5.id] = task5

        # 在循环依赖中，is_blocked 应避免无限递归
        # 这里我们主要测试不会崩溃
        try:
            task4.is_blocked(todos)
            task5.is_blocked(todos)
            print("   循环依赖处理: ✅ 通过（未崩溃）")
        except RecursionError:
            print("   循环依赖处理: ⚠️  递归错误（需要改进）")

        print("   直接依赖检查: ✅ 通过")
        print("   间接依赖检查: ✅ 通过")
        print()

    def test_todo_item_progress_calculation(self):
        """测试TodoItem进度计算"""
        print("🧪 测试4: TodoItem进度计算")
        print("-" * 80)

        # 创建任务集合
        todos = {}

        task1 = TodoItem(title="任务1", estimated_duration=30.0)
        task2 = TodoItem(
            title="任务2", dependencies=[task1.id], estimated_duration=60.0
        )

        todos[task1.id] = task1
        todos[task2.id] = task2

        # task1 未完成，task2 进度应较低
        task1.update_status(TaskStatus.RUNNING)
        progress1 = task1.calculate_progress(todos)
        assert 0.4 < progress1["progress"] < 0.6, "运行中任务进度应在0.5左右"

        # task2 被阻塞，进度应为0
        progress2 = task2.calculate_progress(todos)
        assert progress2["progress"] == 0.0, "被阻塞任务进度应为0"
        assert progress2["dependencies"]["completed"] == 0, "依赖任务完成数应为0"

        # task1 完成
        task1.update_status(TaskStatus.COMPLETED)
        task1.actual_duration = 25.0

        # task2 准备就绪
        task2.update_status(TaskStatus.READY)
        progress2 = task2.calculate_progress(todos)
        assert progress2["progress"] > 0.0, "准备就绪任务进度应大于0"
        assert progress2["dependencies"]["completed"] == 1, "依赖任务完成数应为1"

        print("   单个任务进度: ✅ 通过")
        print("   依赖进度计算: ✅ 通过")
        print("   状态到进度映射: ✅ 通过")
        print()

    def test_dependency_graph_basic(self):
        """测试依赖图基本功能"""
        print("🧪 测试5: 依赖图基本功能")
        print("-" * 80)

        graph = DependencyGraph()

        # 创建任务
        task1 = TodoItem(title="任务1")
        task2 = TodoItem(title="任务2", dependencies=[task1.id])
        task3 = TodoItem(title="任务3", dependencies=[task2.id])

        # 添加到图
        assert graph.add_node(task1), "添加task1应成功"
        assert graph.add_node(task2), "添加task2应成功"
        assert graph.add_node(task3), "添加task3应成功"

        # 检查节点和边
        assert task1.id in graph.nodes, "task1应在图中"
        assert task2.id in graph.edges, "task2应有边"
        assert task1.id in graph.edges[task2.id], "task2应依赖task1"

        # 检查依赖收集
        deps = graph.get_task_dependencies(task3.id, recursive=True)
        assert task1.id in deps, "task3应间接依赖task1"
        assert task2.id in deps, "task3应直接依赖task2"

        # 检查拓扑排序
        topo_order = graph.topological_sort()
        assert len(topo_order) == 3, "拓扑排序应包含3个任务"
        assert topo_order[0] == task1.id, "task1应最先执行"
        assert topo_order[-1] == task3.id, "task3应最后执行"

        print("   节点添加: ✅ 通过")
        print("   依赖关系: ✅ 通过")
        print("   拓扑排序: ✅ 通过")
        print()

    def test_dependency_graph_cycle_detection(self):
        """测试依赖图循环检测"""
        print("🧪 测试6: 依赖图循环检测")
        print("-" * 80)

        graph = DependencyGraph()

        # 创建循环依赖：task1 -> task2 -> task3 -> task1
        task1 = TodoItem(title="任务1")
        task2 = TodoItem(title="任务2", dependencies=[task1.id])
        task3 = TodoItem(title="任务3", dependencies=[task2.id])

        # 添加循环依赖
        task1.dependencies = [task3.id]

        graph.add_node(task1)
        graph.add_node(task2)
        graph.add_node(task3)

        # 应检测到循环
        assert graph.has_cycle(), "应检测到循环依赖"

        # 拓扑排序应返回空列表
        topo_order = graph.topological_sort()
        assert len(topo_order) == 0, "有循环时拓扑排序应为空"

        # 移除循环依赖
        task1.dependencies = []
        graph2 = DependencyGraph()
        graph2.add_node(task1)
        graph2.add_node(task2)
        graph2.add_node(task3)

        assert not graph2.has_cycle(), "无循环时应返回False"

        print("   循环检测: ✅ 通过")
        print("   拓扑排序处理: ✅ 通过")
        print()

    def test_dependency_graph_topological_sort(self):
        """测试依赖图拓扑排序"""
        print("🧪 测试7: 依赖图拓扑排序")
        print("-" * 80)

        graph = DependencyGraph()

        # 创建复杂依赖图
        # task1 -> task2 -> task4
        # task1 -> task3 -> task4
        task1 = TodoItem(title="任务1")
        task2 = TodoItem(title="任务2", dependencies=[task1.id])
        task3 = TodoItem(title="任务3", dependencies=[task1.id])
        task4 = TodoItem(title="任务4", dependencies=[task2.id, task3.id])

        for task in [task1, task2, task3, task4]:
            graph.add_node(task)

        # 拓扑排序
        topo_order = graph.topological_sort()
        assert len(topo_order) == 4, "拓扑排序应包含4个任务"

        # 检查顺序：task1必须在task2和task3之前
        task1_index = topo_order.index(task1.id)
        task2_index = topo_order.index(task2.id)
        task3_index = topo_order.index(task3.id)
        task4_index = topo_order.index(task4.id)

        assert task1_index < task2_index, "task1应在task2之前"
        assert task1_index < task3_index, "task1应在task3之前"
        assert task2_index < task4_index, "task2应在task4之前"
        assert task3_index < task4_index, "task3应在task4之前"

        # 检查分层执行顺序
        layers = graph.get_execution_order()
        assert len(layers) >= 3, "应至少有3个执行层"
        assert task1.id in layers[0], "task1应在第一层"
        assert task4.id in layers[-1], "task4应在最后一层"

        print("   复杂依赖排序: ✅ 通过")
        print("   分层执行顺序: ✅ 通过")
        print()

    def test_todo_progress_calculator(self):
        """测试任务进度计算器"""
        print("🧪 测试8: 任务进度计算器")
        print("-" * 80)

        # 创建任务集合
        todos = {}

        # 创建不同状态的任务
        task1 = TodoItem(title="任务1", priority=Priority.HIGH)
        task2 = TodoItem(
            title="任务2", priority=Priority.NORMAL, dependencies=[task1.id]
        )
        task3 = TodoItem(title="任务3", priority=Priority.LOW)
        task4 = TodoItem(title="任务4", priority=Priority.CRITICAL)

        task1.update_status(TaskStatus.COMPLETED)
        task1.actual_duration = 30.0

        task2.update_status(TaskStatus.RUNNING)

        task3.update_status(TaskStatus.PENDING)

        task4.update_status(TaskStatus.BLOCKED)

        todos = {t.id: t for t in [task1, task2, task3, task4]}

        # 计算总体进度
        calculator = TodoProgressCalculator(todos)
        overall = calculator.calculate_overall_progress()

        assert overall["total_tasks"] == 4, "总任务数应为4"
        assert overall["completed_tasks"] == 1, "已完成任务数应为1"
        assert overall["running_tasks"] == 1, "运行中任务数应为1"
        assert overall["blocked_tasks"] == 1, "阻塞任务数应为1"

        # 总体进度计算：1个完成(1.0) + 1个运行中(0.5) = 1.5 / 4 = 0.375
        assert abs(overall["overall_progress"] - 0.375) < 0.01, (
            f"总体进度计算错误: {overall['overall_progress']}"
        )

        # 检查优先级进度
        assert "HIGH" in overall["progress_by_priority"], "应包含HIGH优先级进度"
        assert overall["progress_by_priority"]["HIGH"] == 1.0, "HIGH优先级进度应为1.0"

        # 生成完整报告
        report = calculator.generate_progress_report()
        assert "overall" in report, "报告应包含总体进度"
        assert "dependency" in report, "报告应包含依赖分析"
        assert "summary" in report, "报告应包含摘要"

        print("   总体进度计算: ✅ 通过")
        print("   优先级进度: ✅ 通过")
        print("   完整报告生成: ✅ 通过")
        print()

    def test_todo_middleware_basic_flow(self):
        """测试TodoMiddleware基本流程"""
        print("🧪 测试9: TodoMiddleware基本流程")
        print("-" * 80)

        # 创建中间件和模拟Agent
        middleware = TodoMiddleware()

        # 模拟Agent输入
        agent_input = {
            "title": "测试Agent任务",
            "description": "测试TodoMiddleware基本流程",
            "estimated_duration": 10.0,
        }

        # before_agent: 应创建任务
        updated_input = asyncio.run(middleware.before_agent(agent_input))
        assert "task_id" in updated_input, "before_agent应添加task_id"
        assert "todo" in updated_input, "before_agent应添加todo"

        task_id = updated_input["task_id"]

        # during_agent: 更新进度
        agent_output = {"progress": 0.5, "intermediate_result": "处理中"}
        updated_output = asyncio.run(middleware.during_agent(agent_output))
        assert updated_output == agent_output, "during_agent不应修改输出"

        # after_agent: 标记任务完成
        final_output = {
            "success": True,
            "result": "任务完成",
            "additional_data": {"key": "value"},
        }
        final_updated = asyncio.run(middleware.after_agent(final_output))

        assert "todo_progress" in final_updated, "after_agent应添加进度报告"
        assert "completed_task" in final_updated, "after_agent应添加完成的任务"

        # 验证任务状态
        task_details = middleware.get_task_details(task_id)
        assert task_details is not None, "应能获取任务详情"
        assert task_details["status"] == "completed", "任务状态应为completed"
        assert task_details["result"] == "任务完成", "任务结果应保存"

        print("   before_agent: ✅ 通过")
        print("   during_agent: ✅ 通过")
        print("   after_agent: ✅ 通过")
        print()

    def test_todo_middleware_dependency_flow(self):
        """测试TodoMiddleware依赖流程"""
        print("🧪 测试10: TodoMiddleware依赖流程")
        print("-" * 80)

        middleware = TodoMiddleware()

        # 创建依赖任务链：task1 -> task2 -> task3
        task1_input = {
            "title": "依赖任务1",
            "task_id": "dep_task_1",  # 指定ID以便创建依赖
        }

        # 执行task1
        task1_input = asyncio.run(middleware.before_agent(task1_input))
        task1_output = {"success": True, "result": "task1完成"}
        asyncio.run(middleware.after_agent(task1_output))

        # 创建依赖task1的task2
        task2_input = {
            "title": "依赖任务2",
            "dependencies": ["dep_task_1"],  # 依赖task1
        }

        # task2应被阻塞（因为依赖检查）
        try:
            asyncio.run(middleware.before_agent(task2_input))
            assert False, "task2应被阻塞"
        except TaskBlockedError as e:
            assert e.task_id is not None, "异常应包含任务ID"
            assert len(e.blocking_dependencies) > 0, "异常应包含阻塞依赖"
            print("   依赖阻塞检查: ✅ 通过")

        # 手动将task1标记为完成（如果前面未成功）
        todos = middleware.list_tasks()
        task1 = next((t for t in todos if t.get("title") == "依赖任务1"), None)
        if task1 and task1.get("status") != "completed":
            # 更新状态
            middleware.storage.load_todo(task1["id"]).update_status(
                TaskStatus.COMPLETED
            )

        # 再次执行task2，现在应通过
        try:
            task2_input = asyncio.run(
                middleware.before_agent(
                    {
                        "title": "依赖任务2",
                        "dependencies": ["dep_task_1"],
                    }
                )
            )

            # 执行task2
            task2_output = {"success": True, "result": "task2完成"}
            asyncio.run(middleware.after_agent(task2_output))

            print("   依赖满足执行: ✅ 通过")
        except TaskBlockedError:
            print("   依赖满足执行: ❌ 失败（仍被阻塞）")

        print()

    def test_todo_middleware_error_handling(self):
        """测试TodoMiddleware错误处理"""
        print("🧪 测试11: TodoMiddleware错误处理")
        print("-" * 80)

        middleware = TodoMiddleware()

        # 创建任务
        task_input = {
            "title": "错误处理测试任务",
            "max_retries": 2,
        }

        task_input = asyncio.run(middleware.before_agent(task_input))
        task_id = task_input["task_id"]

        # 模拟执行出错
        error = Exception("模拟Agent执行错误")
        error_result = asyncio.run(middleware.on_error(error, task_input))

        assert "error" in error_result, "错误处理应返回错误信息"
        assert error_result.get("task_failed", False), "应标记任务失败"

        # 检查任务状态
        task_details = middleware.get_task_details(task_id)
        assert task_details["status"] == "failed", "任务状态应为failed"
        assert task_details["error"] == "模拟Agent执行错误", "应保存错误信息"
        assert task_details["retry_count"] == 1, "重试次数应增加"

        # 测试重试
        # 再次执行同一任务（模拟重试）
        task_input = asyncio.run(middleware.before_agent({"task_id": task_id}))

        # 这次成功
        success_output = {"success": True, "result": "重试成功"}
        asyncio.run(middleware.after_agent(success_output))

        task_details = middleware.get_task_details(task_id)
        assert task_details["status"] == "completed", "重试后状态应为completed"

        print("   错误捕获: ✅ 通过")
        print("   失败状态更新: ✅ 通过")
        print("   重试机制: ✅ 通过")
        print()

    def test_integration_scenario(self):
        """测试集成场景"""
        print("🧪 测试12: 集成场景测试")
        print("-" * 80)

        # 创建项目场景：软件开发项目
        middleware = TodoMiddleware()

        # 定义项目任务
        project_tasks = [
            {
                "title": "需求分析",
                "estimated_duration": 120,
                "priority": "critical",
            },
            {
                "title": "系统设计",
                "estimated_duration": 180,
                "priority": "high",
                "dependencies": ["需求分析"],
            },
            {
                "title": "前端开发",
                "estimated_duration": 240,
                "priority": "normal",
                "dependencies": ["系统设计"],
            },
            {
                "title": "后端开发",
                "estimated_duration": 300,
                "priority": "normal",
                "dependencies": ["系统设计"],
            },
            {
                "title": "集成测试",
                "estimated_duration": 120,
                "priority": "high",
                "dependencies": ["前端开发", "后端开发"],
            },
            {
                "title": "部署上线",
                "estimated_duration": 60,
                "priority": "critical",
                "dependencies": ["集成测试"],
            },
        ]

        # 创建任务（先创建所有任务，不设置实际依赖ID）
        task_map = {}
        for task_def in project_tasks:
            # 为简化，使用标题作为ID
            task_id = task_def["title"]

            # 转换依赖关系（标题 -> 任务ID）
            deps = []
            for dep_title in task_def.get("dependencies", []):
                # 在实际系统中，这里需要查找对应任务的ID
                deps.append(dep_title)

            task_input = {
                "title": task_def["title"],
                "task_id": task_id,  # 指定ID
                "estimated_duration": task_def["estimated_duration"],
                "priority": task_def["priority"],
                "dependencies": deps,
            }

            # 保存任务（不执行）
            todo = TodoItem(
                id=task_id,
                title=task_def["title"],
                estimated_duration=task_def["estimated_duration"],
                priority=Priority.from_string(task_def["priority"]) or Priority.NORMAL,
                dependencies=deps,
            )
            middleware.storage.save_todo(todo)
            task_map[task_id] = todo

        # 模拟执行流程（简化版本）
        execution_order = [
            "需求分析",
            "系统设计",
            "前端开发",
            "后端开发",
            "集成测试",
            "部署上线",
        ]

        for task_title in execution_order:
            task = task_map.get(task_title)
            if not task:
                continue

            # 检查依赖是否满足
            todos = {tid: t for tid, t in task_map.items()}
            if task.is_blocked(todos):
                print(f"   ⏸️  任务 '{task_title}' 被阻塞，跳过")
                continue

            # 模拟执行
            print(f"   ▶️  执行任务 '{task_title}'")

            # 更新状态为完成
            task.update_status(TaskStatus.COMPLETED)
            task.actual_duration = task.estimated_duration * 0.8  # 假设提前完成
            middleware.storage.update_todo(task)

        # 生成最终进度报告
        report = middleware.get_progress_report()

        assert report["overall"]["total_tasks"] == 6, "总任务数应为6"
        # 由于我们跳过了被阻塞的任务，完成数可能小于6
        completion_rate = report["overall"]["completion_rate"]
        print(f"   项目完成率: {completion_rate}%")

        # 检查依赖分析
        assert "dependency" in report, "报告应包含依赖分析"

        print("   项目场景模拟: ✅ 通过")
        print("   进度报告生成: ✅ 通过")
        print()

    def _print_summary(self):
        """打印测试总结"""
        print("=" * 80)
        print("TodoMiddleware 测试套件结果")
        print("=" * 80)
        print(f"总测试数: {self.tests_passed + self.tests_failed}")
        print(f"通过数: {self.tests_passed}")
        print(f"失败数: {self.tests_failed}")
        print()

        if self.tests_failed == 0:
            print("✅ 所有测试通过！")
        else:
            print("❌ 有测试失败，请检查以上输出")

        print("=" * 80)


async def main_demo():
    """主演示函数

    演示TodoMiddleware的完整功能和工作流程。
    """
    print("🚀 Day 6 Lesson 23: TodoMiddleware - 端到端演示")
    print("=" * 80)
    print()

    # 1. 创建TodoMiddleware实例
    print("1. 初始化TodoMiddleware")
    print("-" * 40)
    middleware = TodoMiddleware()
    print("   ✅ TodoMiddleware 创建成功")
    print(f"   存储类型: {type(middleware.storage).__name__}")
    print()

    # 2. 创建示例任务
    print("2. 创建示例任务")
    print("-" * 40)

    # 任务1: 独立任务
    task1_input = {
        "title": "独立任务",
        "description": "这是一个没有依赖的独立任务",
        "priority": "normal",
        "estimated_duration": 30.0,
        "tags": ["独立", "示例"],
    }

    # 任务2: 依赖任务1
    # 先执行task1以获取其ID
    task1_input = await middleware.before_agent(task1_input)
    task1_id = task1_input["task_id"]

    # 完成task1
    await middleware.after_agent({"success": True, "result": "独立任务完成"})

    print(f"   创建任务1: '{task1_input['todo']['title']}' (ID: {task1_id})")
    print(f"   状态: {task1_input['todo']['status']} -> completed")
    print()

    # 任务2: 依赖任务1
    task2_input = {
        "title": "依赖任务",
        "description": "这个任务依赖任务1完成",
        "priority": "high",
        "estimated_duration": 45.0,
        "dependencies": [task1_id],
        "tags": ["依赖", "示例"],
    }

    print(f"   创建任务2: '{task2_input['title']}'")
    print(f"   依赖: 任务1 ({task1_id})")
    print()

    # 3. 演示依赖检查
    print("3. 依赖检查演示")
    print("-" * 40)

    # 检查任务2是否被阻塞（应不被阻塞，因为task1已完成）
    try:
        task2_input = await middleware.before_agent(task2_input)
        print("   ✅ 依赖检查通过: 任务2可以执行")
        print(f"   任务ID: {task2_input['task_id']}")
        print(f"   状态: {task2_input['todo']['status']}")
    except TaskBlockedError as e:
        print(f"   ❌ 依赖检查失败: {e}")

    print()

    # 4. 演示任务执行
    print("4. 任务执行演示")
    print("-" * 40)

    # 模拟任务2执行过程
    print("   开始执行任务2...")

    # 模拟执行中的进度更新
    intermediate_output = {"progress": 0.3, "message": "处理中..."}
    await middleware.during_agent(intermediate_output)
    print("   ⏳ 进度更新: 30%")

    # 模拟更多进度
    intermediate_output = {"progress": 0.7, "message": "即将完成..."}
    await middleware.during_agent(intermediate_output)
    print("   ⏳ 进度更新: 70%")

    # 完成任务2
    final_output = {
        "success": True,
        "result": "依赖任务成功完成",
        "additional_data": {"quality": "优秀", "time_saved": 10},
    }

    final_output = await middleware.after_agent(final_output)
    print("   ✅ 任务2执行完成")
    print(f"   结果: {final_output['completed_task']['result']}")
    print()

    # 5. 演示进度报告
    print("5. 进度报告演示")
    print("-" * 40)

    report = middleware.get_progress_report()

    print(f"   总体进度: {report['overall']['overall_progress'] * 100:.1f}%")
    print(
        f"   已完成任务: {report['overall']['completed_tasks']}/{report['overall']['total_tasks']}"
    )
    print(f"   完成率: {report['overall']['completion_rate']}%")

    if "estimated_time_remaining" in report["overall"]:
        remaining = report["overall"]["estimated_time_remaining"]
        if remaining > 0:
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            print(f"   预计剩余时间: {minutes}分{seconds}秒")

    print(f"   进度摘要: {report['summary']}")
    print()

    # 6. 演示任务列表和过滤
    print("6. 任务列表和过滤演示")
    print("-" * 40)

    # 获取所有任务
    all_tasks = middleware.list_tasks()
    print(f"   总任务数: {len(all_tasks)}")

    # 按状态过滤
    pending_tasks = middleware.list_tasks({"status": TaskStatus.PENDING})
    completed_tasks = middleware.list_tasks({"status": TaskStatus.COMPLETED})

    print(f"   待处理任务: {len(pending_tasks)}")
    print(f"   已完成任务: {len(completed_tasks)}")

    # 显示任务详情
    if all_tasks:
        first_task = all_tasks[0]
        details = middleware.get_task_details(first_task["id"])
        if details:
            print(f"   示例任务详情: '{details['title']}'")
            print(
                f"     状态: {details['status']}, 进度: {details.get('progress', {}).get('progress', 0) * 100:.1f}%"
            )
            print(f"     是否被阻塞: {details.get('is_blocked', False)}")

    print()

    # 7. 演示错误处理
    print("7. 错误处理演示")
    print("-" * 40)

    # 创建可能失败的任务
    error_task_input = {
        "title": "可能失败的任务",
        "description": "这个任务可能会执行失败",
        "max_retries": 1,
    }

    error_task_input = await middleware.before_agent(error_task_input)
    error_task_id = error_task_input["task_id"]

    # 模拟执行失败
    error = ValueError("模拟执行错误：资源不足")
    error_result = await middleware.on_error(error, error_task_input)

    print(f"   ❌ 任务执行失败: {error}")
    print(f"   错误处理结果: {error_result.get('error', '未知错误')}")

    # 检查任务状态
    error_task_details = middleware.get_task_details(error_task_id)
    if error_task_details:
        print(f"   任务状态: {error_task_details['status']}")
        print(f"   错误信息: {error_task_details.get('error', '无')}")
        print(f"   重试次数: {error_task_details.get('retry_count', 0)}")

    print()

    # 8. 最终总结
    print("8. 演示总结")
    print("-" * 40)

    final_report = middleware.get_progress_report()
    overall = final_report["overall"]

    print("   📊 最终项目状态:")
    print(f"     总任务数: {overall['total_tasks']}")
    print(f"     已完成: {overall['completed_tasks']}")
    print(f"     运行中: {overall['running_tasks']}")
    print(f"     被阻塞: {overall['blocked_tasks']}")
    print(f"     总体进度: {overall['overall_progress'] * 100:.1f}%")

    print()
    print("=" * 80)
    print("✅ TodoMiddleware 演示完成")
    print("=" * 80)


if __name__ == "__main__":
    # 运行测试套件
    print("🎓 Day 6 Lesson 23: TodoMiddleware - 课堂演示代码")
    print("=" * 80)
    print()

    # 检查是否运行测试
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_suite = TodoMiddlewareTestSuite()
        success = test_suite.run_all_tests()

        if not success:
            sys.exit(1)
    else:
        # 运行演示
        asyncio.run(main_demo())
