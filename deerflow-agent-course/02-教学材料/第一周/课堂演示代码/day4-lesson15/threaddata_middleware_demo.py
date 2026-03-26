#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 4 Lesson 15: ThreadDataMiddleware深度分析 - 课堂演示代码

本文件提供ThreadDataMiddleware的完整实现和演示，涵盖：
1. 线程状态管理架构与核心机制
2. 线程存储抽象层与多后端实现
3. 状态合并策略与并发处理
4. 工程化集成与生产级实践

适用对象: DeerFlow Python Agent架构师训练营学员
教师: 张老师（10年AI系统架构经验，DeerFlow核心贡献者）
版本: v1.0
日期: 2024年3月28日

课程目标:
1. 理解ThreadDataMiddleware在AI Agent架构中的核心地位和作用
2. 掌握线程状态管理的基本原理和设计模式
3. 了解线程存储抽象层的设计思路和实现方式
4. 理解状态合并策略的重要性和实现机制

依赖安装:
pip install asyncio typing-extensions dataclasses-json redis (用于Redis存储后端)
可选: pip install aiohttp (用于模拟HTTP请求)

运行方式:
python threaddata_middleware_demo.py
"""

import asyncio
import json
import uuid
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Union, Callable, TypeVar, Generic
from collections import defaultdict

# 为教学目的添加详细注释，帮助初学者理解复杂的状态管理概念
# 这些注释对于基础较差的学生至关重要，能够帮助他们理解抽象层设计和状态管理原理

# ============================================================================
# 第一部分：线程状态管理架构与核心机制
# ============================================================================


class ThreadStatus(Enum):
    """
    线程状态枚举 - 教学注释:

    线程状态管理是AI Agent对话系统的核心，定义了对话线程的完整生命周期。
    这个枚举类型定义了线程可能处于的所有状态，每个状态都对应特定的业务含义：

    1. CREATED: 线程刚刚创建，还未开始处理
    2. PROCESSING: 线程正在处理用户请求
    3. WAITING: 线程等待外部输入或异步操作完成
    4. COMPLETED: 线程已成功完成处理
    5. FAILED: 线程处理过程中发生错误
    6. CANCELLED: 线程被用户或系统取消

    设计思考:
    - 状态枚举要覆盖对话线程的完整生命周期
    - 状态转移要符合业务逻辑，防止非法状态转移
    - 要考虑状态持久化和恢复的需求
    """

    CREATED = auto()  # 已创建
    PROCESSING = auto()  # 处理中
    WAITING = auto()  # 等待中
    COMPLETED = auto()  # 已完成
    FAILED = auto()  # 已失败
    CANCELLED = auto()  # 已取消


@dataclass
class Message:
    """
    消息模型 - 教学注释:

    在AI Agent对话系统中，消息是状态的核心组成部分。这个模型定义了
    对话中的一条消息，包含消息内容、发送者、时间戳等元数据。

    设计要点:
    - 消息ID: 唯一标识符，用于消息去重和引用
    - 角色: 区分用户、助理、系统等不同消息来源
    - 内容: 消息的文本内容
    - 时间戳: 消息创建时间，用于时序分析和状态恢复
    - 元数据: 扩展字段，用于存储消息相关的额外信息

    实际应用中的考虑:
    - 消息可能需要支持富文本、附件等扩展
    - 消息可能需要进行内容安全检查或敏感信息过滤
    - 消息可能需要支持引用、回复等交互模式
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "user"  # user, assistant, system, tool
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """将消息转换为字典格式，用于序列化"""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建消息实例，用于反序列化"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=datetime.fromisoformat(
                data.get("timestamp", datetime.now().isoformat())
            ),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ThreadState:
    """
    线程状态模型 - 教学注释:

    这是ThreadDataMiddleware管理的核心数据结构，表示一个AI Agent对话线程的完整状态。
    线程状态包含消息历史、元数据、配置信息等所有对话相关的数据。

    关键设计决策:
    1. 状态ID: 全局唯一标识符，用于状态查找和关联
    2. 状态枚举: 线程当前的生命周期状态
    3. 消息列表: 对话历史，按时间顺序排列
    4. 元数据: 扩展字段，存储线程级别的额外信息
    5. 创建时间和更新时间: 用于监控和审计

    状态管理挑战:
    - 状态可能很大（长时间对话历史）
    - 状态需要支持并发更新
    - 状态需要持久化到不同存储后端
    - 状态恢复需要保证一致性
    """

    thread_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ThreadStatus = ThreadStatus.CREATED
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = 1  # 状态版本，用于乐观锁和冲突检测

    def add_message(self, message: Message) -> None:
        """添加消息到线程状态，并更新状态"""
        self.messages.append(message)
        self.updated_at = datetime.now()
        self.version += 1

    def update_status(self, new_status: ThreadStatus) -> None:
        """更新线程状态，记录状态转移"""
        self.status = new_status
        self.updated_at = datetime.now()
        self.version += 1

    def to_dict(self) -> Dict[str, Any]:
        """将线程状态转换为字典格式，用于序列化"""
        return {
            "thread_id": self.thread_id,
            "status": self.status.name,
            "messages": [msg.to_dict() for msg in self.messages],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThreadState":
        """从字典创建线程状态实例，用于反序列化"""
        return cls(
            thread_id=data.get("thread_id", str(uuid.uuid4())),
            status=ThreadStatus[data.get("status", "CREATED")],
            messages=[Message.from_dict(msg) for msg in data.get("messages", [])],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now().isoformat())
            ),
            updated_at=datetime.fromisoformat(
                data.get("updated_at", datetime.now().isoformat())
            ),
            version=data.get("version", 1),
        )


class ThreadStateLifecycleManager:
    """
    线程状态生命周期管理器 - 教学注释:

    负责管理线程状态的完整生命周期，包括状态验证、状态转移控制、
    状态历史记录等功能。这是状态管理系统的协调者。

    设计模式:
    - 状态模式: 管理线程状态的状态转移
    - 观察者模式: 监听状态变化事件
    - 策略模式: 支持不同的状态验证策略

    核心职责:
    1. 状态转移验证: 确保状态转移符合业务规则
    2. 状态历史记录: 记录状态变化历史，支持回滚
    3. 状态事件发布: 发布状态变化事件，供其他组件响应
    4. 状态一致性保证: 确保状态变化前后的数据一致性
    """

    # 允许的状态转移矩阵
    ALLOWED_TRANSITIONS = {
        ThreadStatus.CREATED: [ThreadStatus.PROCESSING, ThreadStatus.CANCELLED],
        ThreadStatus.PROCESSING: [
            ThreadStatus.WAITING,
            ThreadStatus.COMPLETED,
            ThreadStatus.FAILED,
            ThreadStatus.CANCELLED,
        ],
        ThreadStatus.WAITING: [
            ThreadStatus.PROCESSING,
            ThreadStatus.COMPLETED,
            ThreadStatus.FAILED,
            ThreadStatus.CANCELLED,
        ],
        ThreadStatus.COMPLETED: [],  # 完成状态是终态
        ThreadStatus.FAILED: [ThreadStatus.PROCESSING],  # 失败后可以重试
        ThreadStatus.CANCELLED: [],  # 取消状态是终态
    }

    def __init__(self):
        self.state_history: Dict[str, List[ThreadState]] = defaultdict(list)
        self.event_listeners: List[
            Callable[[str, ThreadStatus, ThreadStatus], None]
        ] = []

    def can_transition(self, current: ThreadStatus, target: ThreadStatus) -> bool:
        """检查状态转移是否允许"""
        return target in self.ALLOWED_TRANSITIONS.get(current, [])

    def transition(
        self, thread_id: str, current_state: ThreadState, new_status: ThreadStatus
    ) -> bool:
        """执行状态转移，返回是否成功"""
        if not self.can_transition(current_state.status, new_status):
            logging.warning(f"非法状态转移: {current_state.status} -> {new_status}")
            return False

        # 记录状态历史
        self.state_history[thread_id].append(current_state)

        # 更新状态
        old_status = current_state.status
        current_state.update_status(new_status)

        # 发布状态变化事件
        self._notify_listeners(thread_id, old_status, new_status)

        logging.info(f"线程 {thread_id} 状态转移: {old_status} -> {new_status}")
        return True

    def add_listener(
        self, listener: Callable[[str, ThreadStatus, ThreadStatus], None]
    ) -> None:
        """添加状态变化监听器"""
        self.event_listeners.append(listener)

    def _notify_listeners(
        self, thread_id: str, old_status: ThreadStatus, new_status: ThreadStatus
    ) -> None:
        """通知所有监听器状态变化"""
        for listener in self.event_listeners:
            try:
                listener(thread_id, old_status, new_status)
            except Exception as e:
                logging.error(f"状态变化监听器执行失败: {e}")


# ============================================================================
# 第二部分：线程存储抽象层与多后端实现
# ============================================================================


class ThreadStorage(ABC):
    """
    线程存储抽象层 - 教学注释:

    这是ThreadDataMiddleware最重要的设计之一：存储抽象层。
    通过抽象层设计，我们可以支持多种存储后端（内存、Redis、数据库等），
    而不需要修改上层业务逻辑。

    设计原则:
    1. 接口隔离: 抽象层定义清晰的接口，隐藏具体实现细节
    2. 依赖倒置: 高层模块依赖抽象，不依赖具体实现
    3. 开放封闭: 支持添加新的存储后端，而不修改现有代码

    实际应用价值:
    - 开发环境可以使用内存存储，快速测试
    - 测试环境可以使用Redis存储，模拟生产环境
    - 生产环境可以使用分布式数据库，保证高可用性
    - 可以根据业务需求灵活切换存储后端
    """

    @abstractmethod
    async def save(self, thread_id: str, state: ThreadState) -> bool:
        """保存线程状态"""
        pass

    @abstractmethod
    async def load(self, thread_id: str) -> Optional[ThreadState]:
        """加载线程状态"""
        pass

    @abstractmethod
    async def delete(self, thread_id: str) -> bool:
        """删除线程状态"""
        pass

    @abstractmethod
    async def exists(self, thread_id: str) -> bool:
        """检查线程状态是否存在"""
        pass

    @abstractmethod
    async def list_threads(self, limit: int = 100, offset: int = 0) -> List[str]:
        """列出所有线程ID"""
        pass


class MemoryThreadStorage(ThreadStorage):
    """
    内存线程存储后端 - 教学注释:

    最简单的存储后端实现，将线程状态存储在内存中。
    适用于开发、测试环境，或不需要持久化的场景。

    优缺点分析:
    优点:
    - 实现简单，无需外部依赖
    - 性能极佳，直接内存访问
    - 适合快速原型开发和单元测试

    缺点:
    - 数据不持久，进程重启后数据丢失
    - 内存有限，不适合存储大量状态
    - 不支持多进程/多节点共享

    教学重点:
    通过这个简单实现，学生可以理解存储抽象层的基本接口和实现模式，
    然后扩展到更复杂的Redis存储后端。
    """

    def __init__(self):
        self.storage: Dict[str, ThreadState] = {}
        self.ttl_seconds: Optional[int] = None  # 生存时间（秒），None表示永不过期
        self.cleanup_interval: int = 60  # 清理过期状态的间隔（秒）

    async def save(self, thread_id: str, state: ThreadState) -> bool:
        """保存线程状态到内存"""
        self.storage[thread_id] = state
        logging.debug(f"内存存储: 线程 {thread_id} 状态已保存")
        return True

    async def load(self, thread_id: str) -> Optional[ThreadState]:
        """从内存加载线程状态"""
        state = self.storage.get(thread_id)
        if state:
            logging.debug(f"内存存储: 线程 {thread_id} 状态已加载")
        else:
            logging.debug(f"内存存储: 线程 {thread_id} 状态不存在")
        return state

    async def delete(self, thread_id: str) -> bool:
        """从内存删除线程状态"""
        if thread_id in self.storage:
            del self.storage[thread_id]
            logging.debug(f"内存存储: 线程 {thread_id} 状态已删除")
            return True
        return False

    async def exists(self, thread_id: str) -> bool:
        """检查线程状态是否存在"""
        return thread_id in self.storage

    async def list_threads(self, limit: int = 100, offset: int = 0) -> List[str]:
        """列出所有线程ID"""
        threads = list(self.storage.keys())
        return threads[offset : offset + limit]


class RedisThreadStorage(ThreadStorage):
    """
    Redis线程存储后端 - 教学注释:

    生产级存储后端实现，将线程状态持久化到Redis。
    支持数据持久化、多进程共享、高可用性等生产需求。

    关键技术点:
    1. 连接池管理: 重用Redis连接，提高性能
    2. 序列化/反序列化: 线程状态到JSON的转换
    3. TTL支持: 自动清理过期状态，防止内存泄漏
    4. 错误处理: 处理Redis连接失败、超时等异常
    5. 性能监控: 监控存储操作的性能和成功率

    生产级考虑:
    - Redis集群支持: 支持分片和故障转移
    - 数据备份: 定期备份重要状态数据
    - 监控告警: 监控Redis性能和存储容量
    - 安全配置: 密码认证、网络隔离等安全措施
    """

    def __init__(
        self, redis_url: str = "redis://localhost:6379/0", ttl_seconds: int = 86400
    ):
        """
        初始化Redis存储后端

        Args:
            redis_url: Redis连接URL
            ttl_seconds: 状态生存时间（秒），默认24小时
        """
        try:
            import redis.asyncio as redis

            self.redis_client = redis.from_url(redis_url)
            self.ttl_seconds = ttl_seconds
            self.prefix = "thread_state:"  # Redis key前缀，用于命名空间隔离
            self._connection_test()
            logging.info(f"Redis存储后端初始化成功: {redis_url}")
        except ImportError:
            logging.error("Redis库未安装，请运行: pip install redis")
            raise
        except Exception as e:
            logging.error(f"Redis存储后端初始化失败: {e}")
            raise

    def _connection_test(self) -> None:
        """测试Redis连接"""
        try:
            # 异步连接测试需要在实际使用时进行
            pass
        except Exception as e:
            logging.error(f"Redis连接测试失败: {e}")
            raise

    def _make_key(self, thread_id: str) -> str:
        """生成Redis key"""
        return f"{self.prefix}{thread_id}"

    async def save(self, thread_id: str, state: ThreadState) -> bool:
        """保存线程状态到Redis"""
        try:
            key = self._make_key(thread_id)
            state_dict = state.to_dict()
            state_json = json.dumps(state_dict, ensure_ascii=False)

            # 使用pipeline提高性能
            async with self.redis_client.pipeline() as pipe:
                await pipe.set(key, state_json)
                if self.ttl_seconds:
                    await pipe.expire(key, self.ttl_seconds)
                await pipe.execute()

            logging.debug(
                f"Redis存储: 线程 {thread_id} 状态已保存，TTL: {self.ttl_seconds}秒"
            )
            return True
        except Exception as e:
            logging.error(f"Redis存储失败 - 线程 {thread_id}: {e}")
            return False

    async def load(self, thread_id: str) -> Optional[ThreadState]:
        """从Redis加载线程状态"""
        try:
            key = self._make_key(thread_id)
            state_json = await self.redis_client.get(key)

            if not state_json:
                logging.debug(f"Redis存储: 线程 {thread_id} 状态不存在")
                return None

            state_dict = json.loads(state_json)
            state = ThreadState.from_dict(state_dict)

            logging.debug(f"Redis存储: 线程 {thread_id} 状态已加载")
            return state
        except json.JSONDecodeError as e:
            logging.error(f"Redis状态反序列化失败 - 线程 {thread_id}: {e}")
            return None
        except Exception as e:
            logging.error(f"Redis加载失败 - 线程 {thread_id}: {e}")
            return None

    async def delete(self, thread_id: str) -> bool:
        """从Redis删除线程状态"""
        try:
            key = self._make_key(thread_id)
            result = await self.redis_client.delete(key)
            success = result > 0

            if success:
                logging.debug(f"Redis存储: 线程 {thread_id} 状态已删除")
            else:
                logging.debug(f"Redis存储: 线程 {thread_id} 状态不存在")

            return success
        except Exception as e:
            logging.error(f"Redis删除失败 - 线程 {thread_id}: {e}")
            return False

    async def exists(self, thread_id: str) -> bool:
        """检查线程状态是否存在于Redis"""
        try:
            key = self._make_key(thread_id)
            exists = await self.redis_client.exists(key) > 0
            return exists
        except Exception as e:
            logging.error(f"Redis存在性检查失败 - 线程 {thread_id}: {e}")
            return False

    async def list_threads(self, limit: int = 100, offset: int = 0) -> List[str]:
        """列出Redis中的所有线程ID"""
        try:
            pattern = f"{self.prefix}*"
            keys = await self.redis_client.keys(pattern)

            # 移除前缀，返回纯线程ID
            thread_ids = [key.decode().replace(self.prefix, "") for key in keys]
            return thread_ids[offset : offset + limit]
        except Exception as e:
            logging.error(f"Redis列表查询失败: {e}")
            return []


class ThreadStorageFactory:
    """
    线程存储工厂 - 教学注释:

    工厂模式在存储抽象层中的应用，负责创建和管理不同的存储后端实例。
    通过工厂模式，我们可以:
    1. 统一存储后端的创建逻辑
    2. 实现存储后端的懒加载和连接池管理
    3. 支持存储后端的动态切换和热更新
    4. 提供存储后端的状态监控和管理

    设计模式应用:
    - 工厂模式: 创建不同类型的存储后端
    - 单例模式: 确保存储后端实例的唯一性
    - 策略模式: 根据不同场景选择不同存储策略
    """

    @staticmethod
    def create_storage(storage_type: str, **kwargs) -> ThreadStorage:
        """
        创建存储后端实例

        Args:
            storage_type: 存储类型，支持 "memory", "redis"
            **kwargs: 存储后端的配置参数

        Returns:
            ThreadStorage实例

        Raises:
            ValueError: 不支持的存储类型
        """
        if storage_type == "memory":
            return MemoryThreadStorage()
        elif storage_type == "redis":
            redis_url = kwargs.get("redis_url", "redis://localhost:6379/0")
            ttl_seconds = kwargs.get("ttl_seconds", 86400)
            return RedisThreadStorage(redis_url=redis_url, ttl_seconds=ttl_seconds)
        else:
            raise ValueError(f"不支持的存储类型: {storage_type}")


# ============================================================================
# 第三部分：状态合并策略与并发处理
# ============================================================================


class StateMergeStrategy(Enum):
    """
    状态合并策略枚举 - 教学注释:

    当多个请求同时修改同一线程状态时，需要选择合适的合并策略。
    不同的业务场景需要不同的合并策略:

    1. LAST_WRITE_WINS: 最后写入获胜，简单但可能丢失数据
    2. MERGE_MESSAGES: 合并消息列表，保留所有消息
    3. MERGE_METADATA: 合并元数据，智能处理冲突
    4. CUSTOM_MERGE: 自定义合并策略，满足特定业务需求

    选择合并策略的考虑因素:
    - 数据重要性: 关键数据不能丢失
    - 业务场景: 不同场景对一致性的要求不同
    - 性能要求: 复杂合并策略可能影响性能
    - 实现复杂度: 策略越复杂，实现和维护成本越高
    """

    LAST_WRITE_WINS = auto()  # 最后写入获胜
    MERGE_MESSAGES = auto()  # 合并消息列表
    MERGE_METADATA = auto()  # 合并元数据
    CUSTOM_MERGE = auto()  # 自定义合并


class StateConflictResolver:
    """
    状态冲突解决器 - 教学注释:

    处理并发状态更新的核心组件。当多个请求同时修改同一线程状态时，
    冲突解决器负责协调这些更新，确保数据一致性。

    关键技术:
    1. 乐观锁: 通过版本号检测冲突
    2. 冲突检测: 比较状态版本，发现冲突
    3. 冲突解决: 根据策略解决冲突
    4. 重试机制: 冲突时自动重试

    生产级考虑:
    - 重试次数限制: 防止无限重试
    - 退避策略: 冲突时延迟重试，减少竞争
    - 监控告警: 监控冲突频率，发现系统问题
    - 人工干预: 支持人工解决无法自动处理的冲突
    """

    def __init__(
        self, merge_strategy: StateMergeStrategy = StateMergeStrategy.MERGE_MESSAGES
    ):
        self.merge_strategy = merge_strategy
        self.max_retries = 3
        self.retry_delay = 0.1  # 秒

    async def resolve_conflict(
        self,
        storage: ThreadStorage,
        thread_id: str,
        new_state: ThreadState,
        current_version: int,
    ) -> bool:
        """
        解决状态冲突

        Args:
            storage: 存储后端
            thread_id: 线程ID
            new_state: 新状态
            current_version: 当前版本号

        Returns:
            是否成功解决冲突

        算法流程:
        1. 加载当前状态
        2. 检查版本冲突
        3. 根据策略合并状态
        4. 尝试保存合并后的状态
        5. 冲突时重试
        """
        for attempt in range(self.max_retries):
            try:
                # 加载当前状态
                current_state = await storage.load(thread_id)
                if not current_state:
                    logging.error(f"冲突解决失败: 线程 {thread_id} 状态不存在")
                    return False

                # 检查版本冲突
                if current_state.version != current_version:
                    logging.info(
                        f"检测到版本冲突: 期望版本 {current_version}, 实际版本 {current_state.version}"
                    )

                    # 根据策略合并状态
                    merged_state = self._merge_states(current_state, new_state)

                    # 尝试保存合并后的状态
                    success = await storage.save(thread_id, merged_state)

                    if success:
                        logging.info(
                            f"冲突解决成功 (尝试 {attempt + 1}/{self.max_retries}): 线程 {thread_id}"
                        )
                        return True
                    else:
                        logging.warning(
                            f"冲突解决保存失败 (尝试 {attempt + 1}/{self.max_retries}): 线程 {thread_id}"
                        )
                else:
                    # 无冲突，直接保存
                    success = await storage.save(thread_id, new_state)
                    if success:
                        return True

                # 冲突或保存失败，等待后重试
                await asyncio.sleep(self.retry_delay * (attempt + 1))

            except Exception as e:
                logging.error(
                    f"冲突解决异常 (尝试 {attempt + 1}/{self.max_retries}): {e}"
                )
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        logging.error(f"冲突解决失败，达到最大重试次数: 线程 {thread_id}")
        return False

    def _merge_states(
        self, base_state: ThreadState, new_state: ThreadState
    ) -> ThreadState:
        """
        合并两个状态

        Args:
            base_state: 基础状态（当前存储的状态）
            new_state: 新状态（尝试保存的状态）

        Returns:
            合并后的状态
        """
        if self.merge_strategy == StateMergeStrategy.LAST_WRITE_WINS:
            # 最后写入获胜：直接使用新状态
            return new_state

        elif self.merge_strategy == StateMergeStrategy.MERGE_MESSAGES:
            # 合并消息列表：保留所有消息，按时间排序
            merged_state = ThreadState.from_dict(base_state.to_dict())

            # 合并消息，去重
            base_message_ids = {msg.id for msg in base_state.messages}
            for message in new_state.messages:
                if message.id not in base_message_ids:
                    merged_state.add_message(message)

            # 合并元数据（新状态优先级高）
            merged_state.metadata.update(new_state.metadata)

            # 使用最新的状态和更新时间
            merged_state.status = new_state.status
            merged_state.updated_at = max(base_state.updated_at, new_state.updated_at)
            merged_state.version = max(base_state.version, new_state.version) + 1

            return merged_state

        elif self.merge_strategy == StateMergeStrategy.MERGE_METADATA:
            # 合并元数据：智能合并元数据字段
            merged_state = ThreadState.from_dict(base_state.to_dict())

            # 保留所有消息
            merged_state.messages = base_state.messages + new_state.messages

            # 智能合并元数据
            for key, new_value in new_state.metadata.items():
                if key not in base_state.metadata:
                    # 新字段直接添加
                    merged_state.metadata[key] = new_value
                else:
                    # 冲突字段，根据类型选择合并策略
                    base_value = base_state.metadata[key]
                    merged_state.metadata[key] = self._merge_metadata_value(
                        key, base_value, new_value
                    )

            # 使用最新的状态和更新时间
            merged_state.status = new_state.status
            merged_state.updated_at = max(base_state.updated_at, new_state.updated_at)
            merged_state.version = max(base_state.version, new_state.version) + 1

            return merged_state

        else:
            # 默认使用最后写入获胜
            return new_state

    def _merge_metadata_value(self, key: str, base_value: Any, new_value: Any) -> Any:
        """
        智能合并元数据值

        Args:
            key: 元数据键
            base_value: 基础值
            new_value: 新值

        Returns:
            合并后的值
        """
        # 根据数据类型选择合并策略
        if isinstance(base_value, dict) and isinstance(new_value, dict):
            # 字典合并
            merged = base_value.copy()
            merged.update(new_value)
            return merged
        elif isinstance(base_value, list) and isinstance(new_value, list):
            # 列表合并（去重）
            merged = base_value + new_value
            # 简单去重（假设列表元素可哈希）
            try:
                return list(dict.fromkeys(merged))
            except:
                return merged
        elif isinstance(base_value, set) and isinstance(new_value, set):
            # 集合并集
            return base_value.union(new_value)
        else:
            # 其他类型，新值优先级高
            return new_value


class ConcurrentStateManager:
    """
    并发状态管理器 - 教学注释:

    管理并发状态更新的高层组件，协调存储后端、冲突解决器和状态验证。
    这是ThreadDataMiddleware的核心协调者。

    设计模式:
    - 门面模式: 提供简单的接口，隐藏复杂的并发处理细节
    - 代理模式: 代理存储操作，添加并发控制逻辑
    - 观察者模式: 监听状态变化，触发相关操作

    核心功能:
    1. 并发控制: 控制对同一状态的并发访问
    2. 状态验证: 验证状态变化的合法性
    3. 事件发布: 发布状态变化事件
    4. 性能监控: 监控状态操作的性能指标
    """

    def __init__(
        self,
        storage: ThreadStorage,
        conflict_resolver: Optional[StateConflictResolver] = None,
    ):
        self.storage = storage
        self.conflict_resolver = conflict_resolver or StateConflictResolver()
        self.lifecycle_manager = ThreadStateLifecycleManager()
        self.locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.metrics = {
            "save_success": 0,
            "save_conflict": 0,
            "save_error": 0,
            "load_success": 0,
            "load_error": 0,
            "delete_success": 0,
            "delete_error": 0,
        }

    async def save_state(self, thread_id: str, state: ThreadState) -> bool:
        """
        保存线程状态（带并发控制）

        Args:
            thread_id: 线程ID
            state: 线程状态

        Returns:
            是否成功保存
        """
        # 获取线程锁，防止并发修改
        lock = self.locks[thread_id]
        async with lock:
            try:
                # 加载当前状态，获取当前版本
                current_state = await self.storage.load(thread_id)
                current_version = current_state.version if current_state else 0

                # 设置新状态的版本
                state.version = current_version + 1

                # 尝试保存
                success = await self.storage.save(thread_id, state)

                if not success and current_state:
                    # 保存失败，可能由于并发冲突
                    logging.debug(f"保存失败，尝试冲突解决: 线程 {thread_id}")
                    success = await self.conflict_resolver.resolve_conflict(
                        self.storage, thread_id, state, current_version
                    )

                # 更新指标
                if success:
                    self.metrics["save_success"] += 1

                    # 发布状态保存事件
                    if current_state:
                        self.lifecycle_manager.transition(
                            thread_id, current_state, state.status
                        )
                else:
                    self.metrics["save_error"] += 1

                return success

            except Exception as e:
                logging.error(f"保存状态失败: 线程 {thread_id}, 错误: {e}")
                self.metrics["save_error"] += 1
                return False

    async def load_state(self, thread_id: str) -> Optional[ThreadState]:
        """加载线程状态"""
        try:
            state = await self.storage.load(thread_id)
            if state:
                self.metrics["load_success"] += 1
            return state
        except Exception as e:
            logging.error(f"加载状态失败: 线程 {thread_id}, 错误: {e}")
            self.metrics["load_error"] += 1
            return None

    async def delete_state(self, thread_id: str) -> bool:
        """删除线程状态"""
        lock = self.locks[thread_id]
        async with lock:
            try:
                success = await self.storage.delete(thread_id)
                if success:
                    self.metrics["delete_success"] += 1
                    # 清理锁
                    if thread_id in self.locks:
                        del self.locks[thread_id]
                else:
                    self.metrics["delete_error"] += 1
                return success
            except Exception as e:
                logging.error(f"删除状态失败: 线程 {thread_id}, 错误: {e}")
                self.metrics["delete_error"] += 1
                return False

    def get_metrics(self) -> Dict[str, int]:
        """获取性能指标"""
        return self.metrics.copy()


# ============================================================================
# 第四部分：ThreadDataMiddleware实现与工程化实践
# ============================================================================


class ThreadDataMiddleware:
    """
    ThreadDataMiddleware - 教学注释:

    DeerFlow AI Agent框架的核心中间件，负责线程状态的完整管理。
    这是本课程的重点，学生需要深入理解其设计和实现。

    架构地位:
    - 位于中间件链的关键位置，通常是早期中间件
    - 负责维护对话线程的完整状态
    - 提供状态持久化和恢复能力
    - 支持多存储后端和并发控制

    设计要点:
    1. 异步兼容: 支持异步中间件链
    2. 错误处理: 优雅处理存储失败等异常
    3. 配置灵活: 支持运行时配置存储后端和合并策略
    4. 监控集成: 集成监控和日志系统
    5. 测试友好: 易于单元测试和集成测试
    """

    def __init__(self, storage_type: str = "memory", **storage_kwargs):
        """
        初始化ThreadDataMiddleware

        Args:
            storage_type: 存储类型 ("memory", "redis")
            **storage_kwargs: 存储后端配置参数
        """
        self.name = "ThreadDataMiddleware"
        self.storage = ThreadStorageFactory.create_storage(
            storage_type, **storage_kwargs
        )
        self.conflict_resolver = StateConflictResolver()
        self.concurrent_manager = ConcurrentStateManager(
            self.storage, self.conflict_resolver
        )
        self.lifecycle_manager = ThreadStateLifecycleManager()

        # 配置日志
        self.logger = logging.getLogger(self.name)

        logging.info(f"ThreadDataMiddleware初始化完成，存储类型: {storage_type}")

    async def __call__(
        self, context: Dict[str, Any], next_middleware: Callable
    ) -> Dict[str, Any]:
        """
        中间件执行入口

        Args:
            context: 请求上下文，包含线程ID、请求数据等
            next_middleware: 下一个中间件的回调函数

        Returns:
            处理后的上下文

        执行流程:
        1. 从上下文中提取线程ID
        2. 加载线程状态（如存在）
        3. 将线程状态添加到上下文
        4. 执行后续中间件
        5. 保存更新后的线程状态
        6. 返回处理后的上下文
        """
        thread_id = self._extract_thread_id(context)

        # 步骤1: 加载线程状态
        thread_state = await self._load_or_create_state(thread_id, context)

        # 步骤2: 将状态添加到上下文
        context["thread_state"] = thread_state
        context["thread_id"] = thread_id

        # 步骤3: 执行后续中间件链
        try:
            response_context = await next_middleware(context)
        except Exception as e:
            # 中间件链执行失败，更新状态为失败
            thread_state.update_status(ThreadStatus.FAILED)
            self.logger.error(f"中间件链执行失败: 线程 {thread_id}, 错误: {e}")
            raise

        # 步骤4: 从响应上下文中获取更新后的状态
        updated_state = response_context.get("thread_state", thread_state)

        # 步骤5: 保存更新后的状态
        await self._save_state(thread_id, updated_state)

        # 步骤6: 返回响应上下文
        return response_context

    def _extract_thread_id(self, context: Dict[str, Any]) -> str:
        """从上下文中提取线程ID"""
        # 优先使用上下文中的线程ID
        thread_id = context.get("thread_id")

        if not thread_id:
            # 如果没有线程ID，从请求数据中提取或生成新的
            request = context.get("request", {})
            thread_id = request.get("thread_id") or str(uuid.uuid4())

        return thread_id

    async def _load_or_create_state(
        self, thread_id: str, context: Dict[str, Any]
    ) -> ThreadState:
        """加载或创建线程状态"""
        # 尝试加载现有状态
        state = await self.concurrent_manager.load_state(thread_id)

        if state:
            # 状态存在，更新为处理中状态
            if self.lifecycle_manager.can_transition(
                state.status, ThreadStatus.PROCESSING
            ):
                state.update_status(ThreadStatus.PROCESSING)
            return state
        else:
            # 状态不存在，创建新状态
            new_state = ThreadState(thread_id=thread_id)

            # 添加上下文中的初始消息（如果有）
            initial_message = context.get("request", {}).get("message")
            if initial_message:
                message = Message(
                    role="user",
                    content=initial_message,
                    metadata={"source": "initial_request"},
                )
                new_state.add_message(message)

            # 设置初始状态为处理中
            new_state.update_status(ThreadStatus.PROCESSING)

            self.logger.info(f"创建新线程状态: {thread_id}")
            return new_state

    async def _save_state(self, thread_id: str, state: ThreadState) -> bool:
        """保存线程状态"""
        success = await self.concurrent_manager.save_state(thread_id, state)

        if success:
            self.logger.debug(f"线程状态保存成功: {thread_id}")
        else:
            self.logger.error(f"线程状态保存失败: {thread_id}")

        return success

    async def get_state(self, thread_id: str) -> Optional[ThreadState]:
        """获取线程状态（外部API）"""
        return await self.concurrent_manager.load_state(thread_id)

    async def update_state(
        self, thread_id: str, updater: Callable[[ThreadState], ThreadState]
    ) -> bool:
        """更新线程状态（外部API）"""
        state = await self.get_state(thread_id)
        if not state:
            return False

        updated_state = updater(state)
        return await self.concurrent_manager.save_state(thread_id, updated_state)

    async def delete_state(self, thread_id: str) -> bool:
        """删除线程状态（外部API）"""
        return await self.concurrent_manager.delete_state(thread_id)

    def get_metrics(self) -> Dict[str, Any]:
        """获取中间件性能指标"""
        base_metrics = self.concurrent_manager.get_metrics()
        return {
            "middleware_name": self.name,
            "storage_type": self.storage.__class__.__name__,
            **base_metrics,
        }


class ThreadStateMonitor:
    """
    线程状态监控器 - 教学注释:

    生产级状态管理系统的必备组件，用于监控线程状态的生命周期、
    性能指标和异常情况。提供可视化监控和告警能力。

    监控维度:
    1. 状态生命周期: 状态创建、更新、删除的统计
    2. 性能指标: 存储操作的延迟、成功率
    3. 资源使用: 内存、Redis连接等资源使用情况
    4. 异常监控: 错误率、冲突频率、存储失败等

    集成方式:
    - 与Prometheus集成，提供监控指标
    - 与Grafana集成，提供可视化面板
    - 与告警系统集成，自动发送告警
    - 与日志系统集成，提供结构化日志
    """

    def __init__(self, middleware: ThreadDataMiddleware):
        self.middleware = middleware
        self.monitoring_data = {
            "state_count": 0,
            "state_by_status": defaultdict(int),
            "operation_latency": defaultdict(list),
            "error_count": 0,
            "conflict_count": 0,
        }

    async def record_operation(
        self, operation: str, latency: float, success: bool
    ) -> None:
        """记录操作指标"""
        self.monitoring_data["operation_latency"][operation].append(latency)

        if not success:
            self.monitoring_data["error_count"] += 1

        if operation == "save" and not success:
            # 保存失败可能由于冲突
            self.monitoring_data["conflict_count"] += 1

    async def update_state_stats(self, state: ThreadState) -> None:
        """更新状态统计"""
        self.monitoring_data["state_count"] += 1
        self.monitoring_data["state_by_status"][state.status.name] += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取监控统计"""
        stats = self.monitoring_data.copy()

        # 计算平均延迟
        for operation, latencies in stats["operation_latency"].items():
            if latencies:
                stats[f"{operation}_avg_latency"] = sum(latencies) / len(latencies)
                stats[f"{operation}_max_latency"] = max(latencies)
                stats[f"{operation}_min_latency"] = min(latencies)

        return stats

    def generate_report(self) -> str:
        """生成监控报告"""
        stats = self.get_stats()
        report_lines = [
            "=== ThreadDataMiddleware 监控报告 ===",
            f"状态总数: {stats['state_count']}",
            "按状态分布:",
        ]

        for status, count in stats["state_by_status"].items():
            percentage = (
                (count / stats["state_count"] * 100) if stats["state_count"] > 0 else 0
            )
            report_lines.append(f"  {status}: {count} ({percentage:.1f}%)")

        report_lines.append(f"错误总数: {stats['error_count']}")
        report_lines.append(f"冲突总数: {stats['conflict_count']}")

        # 延迟统计
        report_lines.append("操作延迟统计:")
        for operation in ["save", "load", "delete"]:
            avg_key = f"{operation}_avg_latency"
            if avg_key in stats:
                report_lines.append(f"  {operation}: {stats[avg_key]:.3f}s (平均)")

        return "\n".join(report_lines)


# ============================================================================
# 演示函数与使用示例
# ============================================================================


async def demonstrate_basic_usage():
    """演示ThreadDataMiddleware的基本使用"""
    print("=== ThreadDataMiddleware 基本使用演示 ===")

    # 1. 创建中间件实例（内存存储）
    middleware = ThreadDataMiddleware(storage_type="memory")
    print("1. 创建ThreadDataMiddleware实例（内存存储）")

    # 2. 创建模拟上下文
    context = {
        "request": {
            "message": "你好，我想了解AI Agent架构",
            "thread_id": "test_thread_001",
        }
    }

    # 3. 模拟中间件链执行
    async def mock_next_middleware(ctx):
        """模拟后续中间件"""
        # 后续中间件可以修改线程状态
        state = ctx["thread_state"]
        response_message = Message(
            role="assistant",
            content="AI Agent架构包括状态管理、中间件链、工具系统等核心组件。",
            metadata={"response_type": "explanation"},
        )
        state.add_message(response_message)
        state.update_status(ThreadStatus.COMPLETED)

        # 返回更新后的上下文
        ctx["response"] = "处理完成"
        return ctx

    # 4. 执行中间件
    print("2. 执行ThreadDataMiddleware处理请求...")
    result = await middleware(context, mock_next_middleware)

    # 5. 检查结果
    print(f"3. 处理完成，线程ID: {result['thread_id']}")
    print(f"   响应: {result['response']}")

    # 6. 验证状态保存
    saved_state = await middleware.get_state("test_thread_001")
    if saved_state:
        print(f"4. 状态保存成功，消息数量: {len(saved_state.messages)}")
        print(f"   最终状态: {saved_state.status.name}")
        print(f"   状态版本: {saved_state.version}")
    else:
        print("4. 状态保存失败")

    print()


async def demonstrate_concurrent_updates():
    """演示并发状态更新和冲突解决"""
    print("=== 并发状态更新演示 ===")

    # 使用Redis存储后端（如果可用）或内存存储
    try:
        middleware = ThreadDataMiddleware(
            storage_type="redis", redis_url="redis://localhost:6379/0"
        )
        print("使用Redis存储后端演示并发更新")
    except:
        middleware = ThreadDataMiddleware(storage_type="memory")
        print("使用内存存储后端演示并发更新")

    thread_id = "concurrent_test_thread"

    # 创建初始状态
    initial_state = ThreadState(thread_id=thread_id)
    initial_state.add_message(Message(role="user", content="初始消息"))
    await middleware.concurrent_manager.save_state(thread_id, initial_state)

    print(f"1. 创建初始状态，版本: {initial_state.version}")

    # 模拟并发更新
    async def concurrent_update(task_id: int):
        """并发更新任务"""
        await asyncio.sleep(0.01 * task_id)  # 稍微错开时间

        # 加载当前状态
        state = await middleware.get_state(thread_id)
        if not state:
            return False

        # 添加任务特定的消息
        state.add_message(
            Message(
                role="user",
                content=f"并发更新任务 {task_id}",
                metadata={"task_id": task_id},
            )
        )

        # 尝试保存
        success = await middleware.concurrent_manager.save_state(thread_id, state)

        if success:
            print(f"   任务 {task_id}: 更新成功，新版本: {state.version}")
        else:
            print(f"   任务 {task_id}: 更新失败（冲突）")

        return success

    # 启动多个并发更新任务
    print("2. 启动5个并发更新任务...")
    tasks = [concurrent_update(i) for i in range(1, 6)]
    results = await asyncio.gather(*tasks)

    # 检查最终状态
    final_state = await middleware.get_state(thread_id)
    if final_state:
        print(f"3. 最终状态版本: {final_state.version}")
        print(f"   消息总数: {len(final_state.messages)}")
        print(f"   成功更新数: {sum(1 for r in results if r)}/{len(results)}")

    # 清理测试数据
    await middleware.delete_state(thread_id)
    print()


async def demonstrate_storage_abstraction():
    """演示存储抽象层的价值"""
    print("=== 存储抽象层演示 ===")

    print("1. 创建内存存储后端...")
    memory_storage = MemoryThreadStorage()

    print("2. 创建Redis存储后端...")
    try:
        redis_storage = RedisThreadStorage(redis_url="redis://localhost:6379/0")
        print("   Redis存储后端创建成功")
    except Exception as e:
        print(f"   Redis存储后端创建失败: {e}")
        redis_storage = None

    # 演示相同的API，不同的实现
    test_state = ThreadState(thread_id="storage_demo")
    test_state.add_message(Message(role="user", content="测试存储抽象层"))

    print("3. 使用内存存储后端保存状态...")
    await memory_storage.save("storage_demo", test_state)

    loaded_state = await memory_storage.load("storage_demo")
    print(f"   从内存存储加载状态: {loaded_state is not None}")

    if redis_storage:
        print("4. 使用Redis存储后端保存状态...")
        await redis_storage.save("storage_demo", test_state)

        loaded_from_redis = await redis_storage.load("storage_demo")
        print(f"   从Redis存储加载状态: {loaded_from_redis is not None}")

    print("5. 存储抽象层价值总结:")
    print("   - 统一的API接口，简化业务逻辑")
    print("   - 灵活的存储后端切换，适应不同环境")
    print("   - 易于测试，可以使用内存存储进行单元测试")
    print("   - 支持生产级需求，可以使用Redis等持久化存储")
    print()


async def demonstrate_production_features():
    """演示生产级特性"""
    print("=== 生产级特性演示 ===")

    # 创建带监控的中间件
    middleware = ThreadDataMiddleware(storage_type="memory")
    monitor = ThreadStateMonitor(middleware)

    print("1. 监控集成演示")

    # 模拟一些操作
    thread_ids = [f"prod_thread_{i}" for i in range(1, 6)]

    for i, thread_id in enumerate(thread_ids):
        state = ThreadState(thread_id=thread_id)
        state.add_message(Message(role="user", content=f"生产测试消息 {i}"))

        start_time = time.time()
        success = await middleware.concurrent_manager.save_state(thread_id, state)
        latency = time.time() - start_time

        await monitor.record_operation("save", latency, success)
        await monitor.update_state_stats(state)

    print("2. 生成监控报告")
    report = monitor.generate_report()
    print(report)

    print("3. 获取中间件指标")
    metrics = middleware.get_metrics()
    print(f"   中间件名称: {metrics['middleware_name']}")
    print(f"   存储类型: {metrics['storage_type']}")
    print(f"   保存成功次数: {metrics['save_success']}")
    print(f"   加载成功次数: {metrics['load_success']}")

    # 清理测试数据
    for thread_id in thread_ids:
        await middleware.delete_state(thread_id)

    print()


async def main_demo():
    """主演示函数"""
    print("=" * 60)
    print("ThreadDataMiddleware深度分析 - 课堂演示")
    print("=" * 60)
    print()

    # 设置日志级别
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        # 演示1: 基本使用
        await demonstrate_basic_usage()

        # 演示2: 并发更新
        await demonstrate_concurrent_updates()

        # 演示3: 存储抽象层
        await demonstrate_storage_abstraction()

        # 演示4: 生产级特性
        await demonstrate_production_features()

        print("=" * 60)
        print("演示完成！")
        print("=" * 60)

    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # 运行主演示
    asyncio.run(main_demo())
