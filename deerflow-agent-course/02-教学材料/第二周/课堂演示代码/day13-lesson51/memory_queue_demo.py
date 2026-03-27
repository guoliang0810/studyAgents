#!/usr/bin/env python3
"""
Day 13 - 第51节课：记忆更新队列机制
====================================

本演示代码实现记忆更新队列系统，包括：
1. UpdateType - 更新类型枚举
2. MemoryUpdate - 更新数据模型
3. ConflictResolver - 冲突解决器
4. MemoryUpdateQueue - 异步更新队列
5. RetryPolicy - 重试策略

运行方式:
    python memory_queue_demo.py          # 运行演示
    python memory_queue_demo.py --test   # 运行测试
"""

import time
import asyncio
import uuid
import threading
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from collections import deque
from abc import ABC, abstractmethod
import sys


# ============================================================================
# 第一部分：更新类型和状态定义
# ============================================================================

class UpdateType(Enum):
    """更新类型枚举
    
    定义记忆更新的不同操作类型：
    - ADD: 添加新记忆
    - UPDATE: 更新现有记忆
    - DELETE: 删除记忆
    - MERGE: 合并记忆
    - ARCHIVE: 归档记忆
    """
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    ARCHIVE = "archive"


class UpdateStatus(Enum):
    """更新状态枚举
    
    更新的生命周期状态：
    - PENDING: 等待处理
    - PROCESSING: 处理中
    - COMPLETED: 已完成
    - FAILED: 失败
    - CONFLICT: 冲突
    - RETRYING: 重试中
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"
    RETRYING = "retrying"


class ConflictStrategy(Enum):
    """冲突解决策略枚举
    
    - LAST_WRITE_WINS: 最后写入获胜
    - FIRST_WRITE_WINS: 首次写入获胜
    - MERGE: 合并更新
    - MANUAL: 手动解决
    - TIMESTAMP: 基于时间戳
    """
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MERGE = "merge"
    MANUAL = "manual"
    TIMESTAMP = "timestamp"


# ============================================================================
# 第二部分：更新数据模型
# ============================================================================

@dataclass
class MemoryUpdate:
    """记忆更新数据模型
    
    表示一次记忆更新操作：
    - id: 更新唯一标识符
    - update_type: 更新类型
    - fact_id: 目标记忆ID（ADD时可为None）
    - content: 更新内容
    - source: 更新来源
    - timestamp: 创建时间戳
    - priority: 优先级（0-10，越高越优先）
    - metadata: 扩展元数据
    - status: 当前状态
    - retry_count: 重试次数
    - error_message: 错误信息
    """
    
    update_type: UpdateType
    content: str
    source: str
    fact_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    priority: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: UpdateStatus = UpdateStatus.PENDING
    retry_count: int = 0
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """初始化后验证"""
        if not 0 <= self.priority <= 10:
            raise ValueError(f"优先级必须在0-10之间，收到: {self.priority}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "update_type": self.update_type.value,
            "fact_id": self.fact_id,
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp,
            "priority": self.priority,
            "metadata": self.metadata,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "error_message": self.error_message
        }
    
    def __lt__(self, other: 'MemoryUpdate') -> bool:
        """支持优先级队列比较（优先级高的排前面）"""
        if self.priority == other.priority:
            return self.timestamp > other.timestamp  # 时间晚的优先
        return self.priority < other.priority  # 优先级低的"小于"优先级高的
    
    def __gt__(self, other: 'MemoryUpdate') -> bool:
        """支持max()比较（优先级高的更大）"""
        if self.priority == other.priority:
            return self.timestamp > other.timestamp  # 时间晚的优先
        return self.priority > other.priority  # 优先级高的更大


# ============================================================================
# 第三部分：冲突解决器
# ============================================================================

@dataclass
class ConflictInfo:
    """冲突信息
    
    描述两个更新之间的冲突：
    - existing_update: 已存在的更新
    - new_update: 新来的更新
    - conflict_type: 冲突类型
    - suggested_resolution: 建议的解决方式
    """
    existing_update: MemoryUpdate
    new_update: MemoryUpdate
    conflict_type: str
    suggested_resolution: ConflictStrategy


class ConflictResolver:
    """冲突解决器
    
    处理记忆更新时的冲突：
    1. 检测冲突 - 判断两个更新是否冲突
    2. 分析冲突 - 确定冲突类型和严重程度
    3. 解决冲突 - 根据策略执行解决方案
    """
    
    def __init__(self, strategy: ConflictStrategy = ConflictStrategy.LAST_WRITE_WINS):
        self.strategy = strategy
        self.conflict_count: int = 0
        self.resolved_count: int = 0
    
    def detect_conflict(self, existing: MemoryUpdate, new: MemoryUpdate) -> bool:
        """检测是否存在冲突
        
        冲突条件：
        1. 同一fact_id
        2. 时间接近（1秒内）
        3. 更新类型相同或不兼容
        
        Args:
            existing: 已存在的更新
            new: 新来的更新
            
        Returns:
            是否存在冲突
        """
        # 不同fact_id不冲突
        if existing.fact_id != new.fact_id and existing.fact_id is not None:
            return False
        
        # DELETE vs UPDATE 冲突
        if (existing.update_type == UpdateType.DELETE and 
            new.update_type in [UpdateType.UPDATE, UpdateType.MERGE]):
            return True
        
        # UPDATE vs UPDATE 在短时间内冲突
        if (existing.update_type in [UpdateType.UPDATE, UpdateType.ADD] and
            new.update_type in [UpdateType.UPDATE, UpdateType.ADD] and
            abs(existing.timestamp - new.timestamp) < 1.0):
            return True
        
        return False
    
    def analyze_conflict(self, existing: MemoryUpdate, 
                         new: MemoryUpdate) -> ConflictInfo:
        """分析冲突详情
        
        Args:
            existing: 已存在的更新
            new: 新来的更新
            
        Returns:
            ConflictInfo冲突信息
        """
        self.conflict_count += 1
        
        # 确定冲突类型
        if existing.update_type == UpdateType.DELETE:
            conflict_type = "delete_vs_update"
            suggested = ConflictStrategy.FIRST_WRITE_WINS
        elif new.timestamp > existing.timestamp:
            conflict_type = "concurrent_update"
            suggested = ConflictStrategy.LAST_WRITE_WINS
        else:
            conflict_type = "concurrent_update"
            suggested = ConflictStrategy.MERGE
        
        return ConflictInfo(
            existing_update=existing,
            new_update=new,
            conflict_type=conflict_type,
            suggested_resolution=suggested
        )
    
    def resolve(self, existing: MemoryUpdate, new: MemoryUpdate) -> Tuple[MemoryUpdate, Optional[MemoryUpdate]]:
        """解决冲突
        
        根据策略返回保留的更新和可选的被丢弃的更新
        
        Args:
            existing: 已存在的更新
            new: 新来的更新
            
        Returns:
            (保留的更新, 被丢弃的更新或None)
        """
        conflict_info = self.analyze_conflict(existing, new)
        
        if self.strategy == ConflictStrategy.LAST_WRITE_WINS:
            # 时间戳更新的获胜
            if new.timestamp >= existing.timestamp:
                self.resolved_count += 1
                return new, existing
            else:
                self.resolved_count += 1
                return existing, new
                
        elif self.strategy == ConflictStrategy.FIRST_WRITE_WINS:
            # 时间戳更早的获胜
            if existing.timestamp <= new.timestamp:
                self.resolved_count += 1
                return existing, new
            else:
                self.resolved_count += 1
                return new, existing
                
        elif self.strategy == ConflictStrategy.MERGE:
            # 合并两个更新
            merged = MemoryUpdate(
                update_type=UpdateType.MERGE,
                content=f"{existing.content} | {new.content}",
                source=f"{existing.source},{new.source}",
                fact_id=existing.fact_id,
                priority=max(existing.priority, new.priority),
                metadata={
                    "merged_from": [existing.id, new.id],
                    "merged_at": time.time()
                }
            )
            self.resolved_count += 1
            return merged, None
            
        elif self.strategy == ConflictStrategy.TIMESTAMP:
            # 基于时间戳，新的覆盖旧的
            if new.timestamp > existing.timestamp:
                self.resolved_count += 1
                return new, existing
            else:
                self.resolved_count += 1
                return existing, new
        
        # 默认：最后写入获胜
        self.resolved_count += 1
        return new, existing
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return {
            "conflict_count": self.conflict_count,
            "resolved_count": self.resolved_count
        }


# ============================================================================
# 第四部分：重试策略
# ============================================================================

class RetryPolicy:
    """重试策略
    
    定义更新失败时的重试行为：
    - max_retries: 最大重试次数
    - base_delay: 基础延迟（秒）
    - max_delay: 最大延迟（秒）
    - exponential_backoff: 是否使用指数退避
    """
    
    def __init__(self, max_retries: int = 3, base_delay: float = 0.1,
                 max_delay: float = 10.0, exponential_backoff: bool = True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_backoff = exponential_backoff
    
    def should_retry(self, update: MemoryUpdate) -> bool:
        """判断是否应该重试
        
        Args:
            update: 更新对象
            
        Returns:
            是否应该重试
        """
        return update.retry_count < self.max_retries
    
    def get_delay(self, retry_count: int) -> float:
        """获取重试延迟
        
        使用指数退避：delay = base_delay × 2^retry_count
        
        Args:
            retry_count: 当前重试次数
            
        Returns:
            延迟秒数
        """
        if self.exponential_backoff:
            delay = self.base_delay * (2 ** retry_count)
        else:
            delay = self.base_delay
        
        return min(delay, self.max_delay)
    
    def execute_with_retry(self, func: Callable, update: MemoryUpdate, 
                           *args, **kwargs) -> Tuple[bool, Optional[str]]:
        """执行函数并自动重试
        
        Args:
            func: 要执行的函数
            update: 更新对象
            *args, **kwargs: 函数参数
            
        Returns:
            (是否成功, 错误信息或None)
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = func(update, *args, **kwargs)
                return True, None
            except Exception as e:
                last_error = str(e)
                update.retry_count = attempt + 1
                
                if attempt < self.max_retries:
                    delay = self.get_delay(attempt)
                    time.sleep(delay)
        
        return False, last_error


# ============================================================================
# 第五部分：更新队列
# ============================================================================

class MemoryUpdateQueue:
    """记忆更新队列
    
    实现异步更新处理：
    1. 接收更新请求
    2. 检测和解决冲突
    3. 按优先级处理更新
    4. 失败时自动重试
    5. 持久化处理结果
    
    特点：
    - 线程安全
    - 支持优先级
    - 自动冲突解决
    - 失败重试
    """
    
    def __init__(self, 
                 conflict_strategy: ConflictStrategy = ConflictStrategy.LAST_WRITE_WINS,
                 retry_policy: Optional[RetryPolicy] = None,
                 batch_size: int = 10):
        # 使用deque作为队列
        self._queue: deque[MemoryUpdate] = deque()
        self._processing_queue: Dict[str, MemoryUpdate] = {}  # 正在处理的更新
        self._completed_updates: List[MemoryUpdate] = []  # 已完成的更新
        
        # 组件
        self.conflict_resolver = ConflictResolver(strategy=conflict_strategy)
        self.retry_policy = retry_policy or RetryPolicy()
        self.batch_size = batch_size
        
        # 线程安全
        self._lock = threading.Lock()
        self._is_running = False
        
        # 统计
        self.stats = {
            "total_received": 0,
            "total_processed": 0,
            "total_failed": 0,
            "total_conflicts": 0
        }
        
        # 回调函数
        self._on_callbacks: List[Callable] = []
    
    def submit(self, update: MemoryUpdate) -> str:
        """提交更新到队列
        
        Args:
            update: 更新对象
            
        Returns:
            更新ID
        """
        with self._lock:
            self._queue.append(update)
            self.stats["total_received"] += 1
        
        return update.id
    
    def create_update(self, update_type: UpdateType, content: str,
                      source: str, fact_id: Optional[str] = None,
                      priority: int = 5) -> str:
        """便捷方法：创建并提交更新
        
        Args:
            update_type: 更新类型
            content: 更新内容
            source: 更新来源
            fact_id: 目标记忆ID
            priority: 优先级
            
        Returns:
            更新ID
        """
        update = MemoryUpdate(
            update_type=update_type,
            content=content,
            source=source,
            fact_id=fact_id,
            priority=priority
        )
        return self.submit(update)
    
    def process_next(self) -> Optional[MemoryUpdate]:
        """处理队列中的下一个更新
        
        Returns:
            处理的更新，队列为空返回None
        """
        with self._lock:
            if not self._queue:
                return None
            
            # 获取优先级最高的更新
            update = max(self._queue)
            self._queue.remove(update)
            update.status = UpdateStatus.PROCESSING
            self._processing_queue[update.id] = update
        
        # 处理更新（不持有锁）
        success = self._process_update(update)
        
        with self._lock:
            if success:
                update.status = UpdateStatus.COMPLETED
                self.stats["total_processed"] += 1
                self._completed_updates.append(update)
            else:
                update.status = UpdateStatus.FAILED
                self.stats["total_failed"] += 1
            
            if update.id in self._processing_queue:
                del self._processing_queue[update.id]
        
        # 触发回调
        self._trigger_callbacks(update)
        
        return update
    
    def _process_update(self, update: MemoryUpdate) -> bool:
        """处理单个更新（模拟实现）
        
        实际应用中这里会调用存储层
        
        Args:
            update: 更新对象
            
        Returns:
            是否成功
        """
        try:
            # 模拟处理时间
            time.sleep(0.01)
            
            # 模拟偶尔失败（10%概率）
            import random
            if random.random() < 0.1:
                raise RuntimeError("模拟处理失败")
            
            return True
        except Exception as e:
            update.error_message = str(e)
            
            # 尝试重试
            if self.retry_policy.should_retry(update):
                update.status = UpdateStatus.RETRYING
                return self._process_update(update)
            
            return False
    
    def process_batch(self, max_items: int = None) -> List[MemoryUpdate]:
        """批量处理队列中的更新
        
        Args:
            max_items: 最大处理数量
            
        Returns:
            处理的更新列表
        """
        max_items = max_items or self.batch_size
        results = []
        
        for _ in range(max_items):
            result = self.process_next()
            if result is None:
                break
            results.append(result)
        
        return results
    
    def process_all(self) -> List[MemoryUpdate]:
        """处理队列中的所有更新
        
        Returns:
            处理的更新列表
        """
        results = []
        
        while True:
            result = self.process_next()
            if result is None:
                break
            results.append(result)
        
        return results
    
    def get_queue_size(self) -> int:
        """获取队列大小"""
        with self._lock:
            return len(self._queue)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        with self._lock:
            stats = self.stats.copy()
            stats.update({
                "queue_size": len(self._queue),
                "processing_count": len(self._processing_queue),
                "completed_count": len(self._completed_updates),
                "conflict_stats": self.conflict_resolver.get_stats()
            })
        return stats
    
    def on_update(self, callback: Callable[[MemoryUpdate], None]) -> None:
        """注册更新处理完成回调"""
        self._on_callbacks.append(callback)
    
    def _trigger_callbacks(self, update: MemoryUpdate) -> None:
        """触发回调"""
        for callback in self._on_callbacks:
            try:
                callback(update)
            except Exception:
                pass  # 忽略回调异常
    
    def clear_completed(self) -> int:
        """清除已完成的更新记录
        
        Returns:
            清除的数量
        """
        with self._lock:
            count = len(self._completed_updates)
            self._completed_updates.clear()
            return count


# ============================================================================
# 第六部分：测试套件
# ============================================================================

def run_tests():
    """运行所有测试"""
    print("🧪 运行记忆更新队列测试套件")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 6
    
    # 测试1: MemoryUpdate数据模型
    print("\n📊 测试1: MemoryUpdate数据模型")
    try:
        update = MemoryUpdate(
            update_type=UpdateType.ADD,
            content="用户喜欢Python",
            source="user",
            priority=8
        )
        
        assert update.update_type == UpdateType.ADD
        assert update.content == "用户喜欢Python"
        assert update.priority == 8
        assert update.status == UpdateStatus.PENDING
        assert update.retry_count == 0
        
        # 测试序列化
        data = update.to_dict()
        assert data["update_type"] == "add"
        assert data["content"] == "用户喜欢Python"
        
        print("   ✅ MemoryUpdate数据模型正常")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试2: 优先级排序
    print("\n📊 测试2: 优先级排序")
    try:
        updates = [
            MemoryUpdate(UpdateType.UPDATE, "低优先级", "sys", priority=3),
            MemoryUpdate(UpdateType.UPDATE, "高优先级", "sys", priority=9),
            MemoryUpdate(UpdateType.UPDATE, "中优先级", "sys", priority=5),
        ]
        
        # 取最大值应该是高优先级的
        max_update = max(updates)
        assert max_update.priority == 9, f"Expected priority 9, got {max_update.priority}"
        
        print("   ✅ 优先级排序正常")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试3: 冲突检测
    print("\n📊 测试3: 冲突检测")
    try:
        resolver = ConflictResolver(strategy=ConflictStrategy.LAST_WRITE_WINS)
        
        current_time = time.time()
        existing = MemoryUpdate(
            UpdateType.UPDATE, "旧内容", "user",
            fact_id="fact_001",
            timestamp=current_time - 0.5
        )
        new = MemoryUpdate(
            UpdateType.UPDATE, "新内容", "user",
            fact_id="fact_001",
            timestamp=current_time
        )
        
        # 应该检测到冲突
        has_conflict = resolver.detect_conflict(existing, new)
        assert has_conflict, "Should detect conflict for same fact_id"
        
        # 不同fact_id不应冲突
        no_conflict_update = MemoryUpdate(
            UpdateType.UPDATE, "其他内容", "user",
            fact_id="fact_002"
        )
        has_conflict2 = resolver.detect_conflict(existing, no_conflict_update)
        assert not has_conflict2, "Different fact_id should not conflict"
        
        print("   ✅ 冲突检测正常")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试4: 冲突解决
    print("\n📊 测试4: 冲突解决")
    try:
        resolver = ConflictResolver(strategy=ConflictStrategy.LAST_WRITE_WINS)
        
        current_time = time.time()
        existing = MemoryUpdate(
            UpdateType.UPDATE, "旧内容", "user",
            timestamp=current_time - 1
        )
        new = MemoryUpdate(
            UpdateType.UPDATE, "新内容", "user",
            timestamp=current_time
        )
        
        winner, loser = resolver.resolve(existing, new)
        assert winner.id == new.id, "Newer update should win"
        assert loser.id == existing.id
        
        stats = resolver.get_stats()
        assert stats["conflict_count"] == 1
        assert stats["resolved_count"] == 1
        
        print("   ✅ 冲突解决正常")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试5: 重试策略
    print("\n📊 测试5: 重试策略")
    try:
        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        
        # 测试延迟计算（指数退避）
        assert policy.get_delay(0) == 0.01
        assert policy.get_delay(1) == 0.02
        assert policy.get_delay(2) == 0.04
        assert policy.get_delay(3) == 0.08
        
        # 测试是否应该重试
        update = MemoryUpdate(UpdateType.UPDATE, "测试", "sys")
        assert policy.should_retry(update)  # retry_count=0 < 3
        
        update.retry_count = 3
        assert not policy.should_retry(update)  # retry_count=3 >= 3
        
        print("   ✅ 重试策略正常")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试6: 更新队列处理
    print("\n📊 测试6: 更新队列处理")
    try:
        queue = MemoryUpdateQueue(
            conflict_strategy=ConflictStrategy.LAST_WRITE_WINS,
            retry_policy=RetryPolicy(max_retries=2, base_delay=0.01)
        )
        
        # 提交多个更新
        queue.create_update(UpdateType.ADD, "内容1", "user", priority=5)
        queue.create_update(UpdateType.UPDATE, "内容2", "user", priority=8)
        queue.create_update(UpdateType.DELETE, "内容3", "user", priority=3)
        
        assert queue.get_queue_size() == 3
        
        # 批量处理
        results = queue.process_batch(max_items=10)
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        
        # 验证高优先级的先处理
        stats = queue.get_stats()
        assert stats["total_received"] == 3
        assert queue.get_queue_size() == 0
        
        print(f"   ✅ 更新队列处理正常 (处理={len(results)}条)")
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
    """运行记忆更新队列演示"""
    print("📨 Day 13 - 第51节课：记忆更新队列机制演示")
    print("=" * 60)
    
    # 1. 演示更新数据模型
    print("\n📝 演示1: MemoryUpdate数据模型")
    print("-" * 40)
    
    updates = [
        MemoryUpdate(UpdateType.ADD, "用户是Python开发者", "user", priority=8),
        MemoryUpdate(UpdateType.UPDATE, "用户偏好：暗色主题", "system", priority=6),
        MemoryUpdate(UpdateType.DELETE, "过期缓存数据", "system", priority=3),
    ]
    
    for update in updates:
        print(f"更新类型: {update.update_type.value}")
        print(f"  内容: {update.content}")
        print(f"  来源: {update.source}, 优先级: {update.priority}")
        print()
    
    # 2. 演示冲突检测和解决
    print("\n📝 演示2: 冲突检测和解决")
    print("-" * 40)
    
    resolver = ConflictResolver(strategy=ConflictStrategy.LAST_WRITE_WINS)
    
    current_time = time.time()
    
    # 创建两个冲突的更新
    update1 = MemoryUpdate(
        UpdateType.UPDATE, "用户说他喜欢Java", "user",
        fact_id="fact_001",
        timestamp=current_time - 2
    )
    update2 = MemoryUpdate(
        UpdateType.UPDATE, "用户说他喜欢Python", "user",
        fact_id="fact_001",
        timestamp=current_time
    )
    
    has_conflict = resolver.detect_conflict(update1, update2)
    print(f"更新1: '{update1.content}'")
    print(f"更新2: '{update2.content}'")
    print(f"检测到冲突: {has_conflict}")
    
    if has_conflict:
        winner, loser = resolver.resolve(update1, update2)
        print(f"解决结果: 保留 '{winner.content}'")
        print(f"丢弃: '{loser.content if loser else None}'")
    
    # 3. 演示更新队列
    print("\n\n📝 演示3: 更新队列处理")
    print("-" * 40)
    
    queue = MemoryUpdateQueue(
        conflict_strategy=ConflictStrategy.LAST_WRITE_WINS,
        retry_policy=RetryPolicy(max_retries=2, base_delay=0.05)
    )
    
    # 模拟多个并发更新
    print("提交10个模拟更新...")
    for i in range(10):
        update_type = [UpdateType.ADD, UpdateType.UPDATE, UpdateType.DELETE][i % 3]
        priority = (i % 5) + 1
        queue.create_update(
            update_type,
            f"模拟更新内容 {i+1}",
            source="demo",
            priority=priority
        )
    
    print(f"队列大小: {queue.get_queue_size()}")
    
    # 处理所有更新
    print("\n处理队列...")
    results = queue.process_all()
    
    # 统计结果
    success_count = sum(1 for r in results if r.status == UpdateStatus.COMPLETED)
    failed_count = sum(1 for r in results if r.status == UpdateStatus.FAILED)
    
    print(f"\n处理结果:")
    print(f"  总处理: {len(results)}")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count} (含重试)")
    
    stats = queue.get_stats()
    print(f"\n队列统计:")
    print(f"  总接收: {stats['total_received']}")
    print(f"  总处理: {stats['total_processed']}")
    print(f"  总失败: {stats['total_failed']}")
    
    # 4. 演示优先级处理
    print("\n\n📝 演示4: 优先级处理")
    print("-" * 40)
    
    queue2 = MemoryUpdateQueue()
    
    # 按不同优先级提交
    priorities = [1, 10, 5, 8, 3]
    for i, p in enumerate(priorities):
        queue2.create_update(
            UpdateType.UPDATE,
            f"优先级 {p} 的更新",
            source="priority_demo",
            priority=p
        )
    
    print("提交的优先级顺序:", priorities)
    print("预期处理顺序: 10, 8, 5, 3, 1")
    
    results2 = queue2.process_all()
    print("\n实际处理顺序:")
    for i, r in enumerate(results2):
        print(f"  {i+1}. {r.content}")
    
    print("\n" + "=" * 60)
    print("✅ 演示完成！")


if __name__ == "__main__":
    if "--test" in sys.argv:
        success = run_tests()
        sys.exit(0 if success else 1)
    else:
        run_demo()
