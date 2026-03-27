#!/usr/bin/env python3
"""
Day 13 - 第49节课：记忆系统架构设计
====================================

本演示代码实现Agent记忆系统的三层架构，包括：
1. Fact - 事实数据模型，存储单条记忆
2. MemoryStore - 存储抽象接口，定义标准操作
3. ShortTermMemory - 短期记忆，基于会话的临时存储
4. LongTermMemory - 长期记忆，持久化的知识存储
5. WorkingMemory - 工作记忆，当前任务上下文
6. MemorySystem - 完整的记忆系统，整合三层记忆

运行方式:
    python memory_architecture_demo.py          # 运行演示
    python memory_architecture_demo.py --test   # 运行测试
"""

import time
import uuid
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import sys
import json


# ============================================================================
# 第一部分：记忆类型和状态定义
# ============================================================================

class MemoryType(Enum):
    """记忆类型枚举
    
    定义三种不同类型的记忆：
    - SHORT_TERM: 短期记忆，基于会话，会话结束后可清理
    - LONG_TERM: 长期记忆，持久化存储，跨会话保留
    - WORKING: 工作记忆，当前任务上下文，任务结束后可清理
    """
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    WORKING = "working"


class MemoryStatus(Enum):
    """记忆状态枚举
    
    记忆的生命周期状态：
    - ACTIVE: 活跃状态，正在使用
    - ARCHIVED: 已归档，不再主动使用但保留
    - EXPIRED: 已过期，等待清理
    - DELETED: 已删除，标记为删除
    """
    ACTIVE = "active"
    ARCHIVED = "archived"
    EXPIRED = "expired"
    DELETED = "deleted"


# ============================================================================
# 第二部分：Fact数据模型
# ============================================================================

@dataclass
class Fact:
    """事实（Fact）数据模型
    
    表示Agent记忆系统中的一条事实知识，核心字段：
    - id: 唯一标识符
    - content: 事实内容
    - source: 来源（user/system/tool）
    - confidence: 置信度（0.0-1.0）
    - memory_type: 记忆类型
    - created_at: 创建时间戳
    - updated_at: 最后更新时间戳
    - metadata: 扩展元数据
    
    设计考虑：
    - 置信度用于区分用户明确说的（高）vs 系统推断的（低）
    - 时间戳用于记忆生命周期管理
    - 元数据支持扩展，不修改核心结构
    """
    
    content: str
    source: str  # "user", "system", "tool"
    confidence: float = 1.0  # 0.0 - 1.0
    memory_type: MemoryType = MemoryType.SHORT_TERM
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    access_count: int = 0
    status: MemoryStatus = MemoryStatus.ACTIVE
    
    def __post_init__(self):
        """初始化后验证"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"置信度必须在0.0-1.0之间，收到: {self.confidence}")
        if not isinstance(self.tags, set):
            self.tags = set(self.tags)
    
    def update(self, content: Optional[str] = None, 
               confidence: Optional[float] = None) -> None:
        """更新事实内容
        
        Args:
            content: 新内容（可选）
            confidence: 新置信度（可选）
        """
        if content is not None:
            self.content = content
        if confidence is not None:
            if not 0.0 <= confidence <= 1.0:
                raise ValueError(f"置信度必须在0.0-1.0之间")
            self.confidence = confidence
        self.updated_at = time.time()
    
    def access(self) -> None:
        """记录访问，更新访问计数"""
        self.access_count += 1
    
    def archive(self) -> None:
        """归档事实"""
        self.status = MemoryStatus.ARCHIVED
        self.updated_at = time.time()
    
    def delete(self) -> None:
        """标记删除"""
        self.status = MemoryStatus.DELETED
        self.updated_at = time.time()
    
    def add_tag(self, tag: str) -> None:
        """添加标签"""
        self.tags.add(tag)
        self.updated_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（便于序列化）"""
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
            "memory_type": self.memory_type.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "tags": list(self.tags),
            "access_count": self.access_count,
            "status": self.status.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Fact':
        """从字典创建Fact"""
        return cls(
            id=data["id"],
            content=data["content"],
            source=data["source"],
            confidence=data["confidence"],
            memory_type=MemoryType(data["memory_type"]),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            metadata=data.get("metadata", {}),
            tags=set(data.get("tags", [])),
            access_count=data.get("access_count", 0),
            status=MemoryStatus(data.get("status", "active"))
        )


# ============================================================================
# 第三部分：MemoryStore抽象接口
# ============================================================================

class MemoryStore(ABC):
    """记忆存储抽象接口
    
    定义记忆存储的标准操作，所有具体存储实现必须继承此接口：
    - add: 添加新记忆
    - search: 搜索记忆
    - get: 获取单条记忆
    - update: 更新记忆
    - delete: 删除记忆
    
    设计原则：
    - 接口稳定，实现可变
    - 支持多种后端（内存、数据库、向量存储）
    - 线程安全
    """
    
    @abstractmethod
    def add(self, fact: Fact) -> str:
        """添加新记忆
        
        Args:
            fact: 要添加的事实
            
        Returns:
            记忆的ID
        """
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 10, 
               min_confidence: float = 0.0) -> List[Fact]:
        """搜索记忆
        
        Args:
            query: 搜索关键词
            limit: 返回结果数量限制
            min_confidence: 最小置信度过滤
            
        Returns:
            匹配的记忆列表
        """
        pass
    
    @abstractmethod
    def get(self, fact_id: str) -> Optional[Fact]:
        """获取单条记忆
        
        Args:
            fact_id: 记忆ID
            
        Returns:
            记忆对象，不存在返回None
        """
        pass
    
    @abstractmethod
    def update(self, fact_id: str, **kwargs) -> bool:
        """更新记忆
        
        Args:
            fact_id: 记忆ID
            **kwargs: 要更新的字段
            
        Returns:
            是否更新成功
        """
        pass
    
    @abstractmethod
    def delete(self, fact_id: str) -> bool:
        """删除记忆
        
        Args:
            fact_id: 记忆ID
            
        Returns:
            是否删除成功
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """获取记忆数量
        
        Returns:
            记忆总数
        """
        pass
    
    @abstractmethod
    def clear(self) -> int:
        """清空所有记忆
        
        Returns:
            清除的记忆数量
        """
        pass


# ============================================================================
# 第四部分：内存存储实现
# ============================================================================

class InMemoryStore(MemoryStore):
    """基于内存的记忆存储实现
    
    使用字典存储，适合开发测试和小规模场景：
    - 快速读写
    - 不持久化
    - 线程安全
    """
    
    def __init__(self):
        self._storage: Dict[str, Fact] = {}
        self._lock = threading.Lock()
    
    def add(self, fact: Fact) -> str:
        """添加记忆"""
        with self._lock:
            self._storage[fact.id] = fact
            return fact.id
    
    def search(self, query: str, limit: int = 10,
               min_confidence: float = 0.0) -> List[Fact]:
        """搜索记忆（子串匹配，支持中文）"""
        with self._lock:
            query_lower = query.lower()
            results: List[Fact] = []

            for fact in self._storage.values():
                if (fact.status == MemoryStatus.ACTIVE and
                    fact.confidence >= min_confidence and
                    query_lower in fact.content.lower()):
                    fact.access()
                    results.append(fact)

            # 按置信度排序
            results.sort(key=lambda f: f.confidence, reverse=True)
            return results[:limit]
    
    def get(self, fact_id: str) -> Optional[Fact]:
        """获取单条记忆"""
        with self._lock:
            fact = self._storage.get(fact_id)
            if fact and fact.status == MemoryStatus.ACTIVE:
                fact.access()
                return fact
            return None
    
    def update(self, fact_id: str, **kwargs) -> bool:
        """更新记忆"""
        with self._lock:
            fact = self._storage.get(fact_id)
            if not fact or fact.status != MemoryStatus.ACTIVE:
                return False
            
            if "content" in kwargs:
                fact.update(content=kwargs["content"])
            if "confidence" in kwargs:
                fact.update(confidence=kwargs["confidence"])
            if "metadata" in kwargs:
                fact.metadata.update(kwargs["metadata"])
                fact.updated_at = time.time()
            
            return True
    
    def delete(self, fact_id: str) -> bool:
        """删除记忆"""
        with self._lock:
            fact = self._storage.get(fact_id)
            if fact:
                fact.delete()
                return True
            return False
    
    def count(self) -> int:
        """获取活跃记忆数量"""
        with self._lock:
            return sum(1 for f in self._storage.values() 
                      if f.status == MemoryStatus.ACTIVE)
    
    def clear(self) -> int:
        """清空所有记忆"""
        with self._lock:
            count = len(self._storage)
            self._storage.clear()
            return count
    
    def get_all(self) -> List[Fact]:
        """获取所有活跃记忆（调试用）"""
        with self._lock:
            return [f for f in self._storage.values() 
                   if f.status == MemoryStatus.ACTIVE]


# ============================================================================
# 第五部分：三层记忆实现
# ============================================================================

class ShortTermMemory:
    """短期记忆
    
    基于会话的临时存储特点：
    - 存储当前会话的对话历史
    - 有容量限制，超出时清理最旧的
    - 会话结束时可选择性持久化到长期记忆
    
    适用场景：
    - 对话历史记录
    - 临时用户输入缓存
    - 会话状态跟踪
    """
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.store = InMemoryStore()
        self._creation_time = time.time()
    
    def add_fact(self, content: str, source: str = "user", 
                 confidence: float = 1.0) -> str:
        """添加事实到短期记忆"""
        fact = Fact(
            content=content,
            source=source,
            confidence=confidence,
            memory_type=MemoryType.SHORT_TERM
        )
        
        # 检查容量，超出则清理最旧的
        if self.store.count() >= self.max_size:
            self._evict_oldest()
        
        return self.store.add(fact)
    
    def _evict_oldest(self) -> None:
        """清理最旧的记忆"""
        facts = self.store.get_all()
        if facts:
            oldest = min(facts, key=lambda f: f.created_at)
            self.store.delete(oldest.id)
    
    def search(self, query: str, limit: int = 5) -> List[Fact]:
        """搜索短期记忆"""
        return self.store.search(query, limit=limit)
    
    def get_recent(self, count: int = 10) -> List[Fact]:
        """获取最近的记忆"""
        facts = self.store.get_all()
        facts.sort(key=lambda f: f.created_at, reverse=True)
        return facts[:count]
    
    def clear(self) -> int:
        """清空短期记忆"""
        return self.store.clear()
    
    def promote_to_long_term(self, fact_id: str, 
                             long_term: 'LongTermMemory') -> bool:
        """将记忆提升到长期记忆"""
        fact = self.store.get(fact_id)
        if fact:
            # 创建长期记忆副本
            long_fact = Fact(
                content=fact.content,
                source=fact.source,
                confidence=fact.confidence,
                memory_type=MemoryType.LONG_TERM,
                metadata=fact.metadata.copy(),
                tags=fact.tags.copy()
            )
            long_term.store.add(long_fact)
            return True
        return False


class LongTermMemory:
    """长期记忆
    
    持久化的知识存储特点：
    - 存储重要且持久的知识
    - 支持置信度加权搜索
    - 不自动清理，需要手动归档
    
    适用场景：
    - 用户画像和偏好
    - 重要事实和知识
    - 历史对话精华
    """
    
    def __init__(self):
        self.store = InMemoryStore()
        self._stats = {
            "total_added": 0,
            "total_promoted": 0
        }
    
    def add_fact(self, content: str, source: str = "system",
                 confidence: float = 1.0, tags: Optional[Set[str]] = None) -> str:
        """添加事实到长期记忆"""
        fact = Fact(
            content=content,
            source=source,
            confidence=confidence,
            memory_type=MemoryType.LONG_TERM,
            tags=tags or set()
        )
        self._stats["total_added"] += 1
        return self.store.add(fact)
    
    def search(self, query: str, limit: int = 10, 
               min_confidence: float = 0.5) -> List[Fact]:
        """搜索长期记忆（带置信度过滤）"""
        return self.store.search(query, limit=limit, 
                                min_confidence=min_confidence)
    
    def get_by_tag(self, tag: str) -> List[Fact]:
        """按标签获取记忆"""
        results = []
        for fact in self.store.get_all():
            if tag in fact.tags:
                results.append(fact)
        return results
    
    def archive_old(self, older_than_days: int = 30) -> int:
        """归档旧记忆"""
        cutoff_time = time.time() - (older_than_days * 86400)
        archived = 0
        
        for fact in self.store.get_all():
            if fact.created_at < cutoff_time:
                fact.archive()
                archived += 1
        
        return archived
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        all_facts = self.store.get_all()
        return {
            "total_active": len(all_facts),
            "total_added": self._stats["total_added"],
            "avg_confidence": sum(f.confidence for f in all_facts) / max(1, len(all_facts)),
            "by_source": self._count_by_source(all_facts)
        }
    
    def _count_by_source(self, facts: List[Fact]) -> Dict[str, int]:
        """按来源统计"""
        counts: Dict[str, int] = defaultdict(int)
        for fact in facts:
            counts[fact.source] += 1
        return dict(counts)


class WorkingMemory:
    """工作记忆
    
    当前任务上下文特点：
    - 存储当前任务相关信息
    - 任务相关性评分
    - 任务结束后可清理
    
    适用场景：
    - 当前任务上下文
    - 步骤执行状态
    - 中间计算结果
    """
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.store = InMemoryStore()
        self._task_start_time = time.time()
    
    def add_context(self, content: str, relevance: float = 1.0,
                    metadata: Optional[Dict] = None) -> str:
        """添加上下文信息"""
        fact = Fact(
            content=content,
            source="system",
            confidence=relevance,
            memory_type=MemoryType.WORKING,
            metadata={"task_id": self.task_id, **(metadata or {})}
        )
        return self.store.add(fact)
    
    def get_context(self, query: str = "", limit: int = 10) -> List[Fact]:
        """获取相关上下文"""
        if query:
            return self.store.search(query, limit=limit)
        return self.store.get_all()[:limit]
    
    def clear(self) -> int:
        """清空工作记忆（任务完成时调用）"""
        return self.store.clear()
    
    def get_task_duration(self) -> float:
        """获取任务持续时间（秒）"""
        return time.time() - self._task_start_time


# ============================================================================
# 第六部分：完整记忆系统
# ============================================================================

class MemorySystem:
    """完整记忆系统
    
    整合三层记忆，提供统一接口：
    - short_term: 短期记忆
    - long_term: 长期记忆
    - working: 工作记忆（按任务创建）
    
    功能：
    - 统一的记忆管理
    - 记忆类型转换
    - 跨层搜索
    """
    
    def __init__(self, short_term_size: int = 100):
        self.short_term = ShortTermMemory(max_size=short_term_size)
        self.long_term = LongTermMemory()
        self._working_memories: Dict[str, WorkingMemory] = {}
    
    def create_working_memory(self, task_id: str) -> WorkingMemory:
        """为任务创建工作记忆"""
        working = WorkingMemory(task_id)
        self._working_memories[task_id] = working
        return working
    
    def add_to_short_term(self, content: str, source: str = "user") -> str:
        """添加到短期记忆"""
        return self.short_term.add_fact(content, source)
    
    def add_to_long_term(self, content: str, source: str = "system",
                         confidence: float = 1.0, 
                         tags: Optional[Set[str]] = None) -> str:
        """添加到长期记忆"""
        return self.long_term.add_fact(content, source, confidence, tags)
    
    def search_all(self, query: str, limit: int = 10) -> Dict[str, List[Fact]]:
        """跨层搜索"""
        return {
            "short_term": self.short_term.search(query, limit=limit),
            "long_term": self.long_term.search(query, limit=limit)
        }
    
    def promote_to_long_term(self, fact_id: str) -> bool:
        """从短期提升到长期"""
        return self.short_term.promote_to_long_term(fact_id, self.long_term)
    
    def get_working_memory(self, task_id: str) -> Optional[WorkingMemory]:
        """获取任务的工作记忆"""
        return self._working_memories.get(task_id)
    
    def cleanup_working_memory(self, task_id: str) -> int:
        """清理完成任务的工作记忆"""
        working = self._working_memories.get(task_id)
        if working:
            count = working.clear()
            del self._working_memories[task_id]
            return count
        return 0
    
    def get_summary(self) -> Dict[str, Any]:
        """获取记忆系统摘要"""
        return {
            "short_term_count": self.short_term.store.count(),
            "long_term_stats": self.long_term.get_stats(),
            "active_working_tasks": len(self._working_memories),
            "working_task_ids": list(self._working_memories.keys())
        }


# ============================================================================
# 第七部分：测试套件
# ============================================================================

def run_tests():
    """运行所有测试"""
    print("🧪 运行记忆系统架构测试套件")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 7
    
    # 测试1: Fact数据模型基本功能
    print("\n📊 测试1: Fact数据模型基本功能")
    try:
        fact = Fact(
            content="用户喜欢Python编程",
            source="user",
            confidence=0.95,
            memory_type=MemoryType.SHORT_TERM
        )
        
        # 验证字段
        assert fact.content == "用户喜欢Python编程"
        assert fact.source == "user"
        assert fact.confidence == 0.95
        assert fact.status == MemoryStatus.ACTIVE
        
        # 测试更新
        fact.update(confidence=1.0)
        assert fact.confidence == 1.0
        
        # 测试访问计数
        fact.access()
        assert fact.access_count == 1
        
        print("   ✅ Fact数据模型功能正常")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试2: Fact序列化和反序列化
    print("\n📊 测试2: Fact序列化和反序列化")
    try:
        fact = Fact(
            content="测试内容",
            source="system",
            confidence=0.8,
            tags={"python", "ai"}
        )
        
        # 序列化
        data = fact.to_dict()
        assert data["content"] == "测试内容"
        assert set(data["tags"]) == {"python", "ai"}
        
        # 反序列化
        fact2 = Fact.from_dict(data)
        assert fact2.content == fact.content
        assert fact2.confidence == fact.confidence
        assert fact2.tags == fact.tags
        
        print("   ✅ 序列化/反序列化功能正常")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试3: InMemoryStore基本操作
    print("\n📊 测试3: InMemoryStore基本操作")
    try:
        store = InMemoryStore()
        
        # 添加
        fact = Fact(content="测试事实", source="system")
        fact_id = store.add(fact)
        assert fact_id == fact.id
        
        # 获取
        retrieved = store.get(fact_id)
        assert retrieved is not None
        assert retrieved.content == "测试事实"
        
        # 搜索
        results = store.search("测试")
        assert len(results) >= 1
        
        # 更新
        success = store.update(fact_id, confidence=0.5)
        assert success
        
        # 删除
        success = store.delete(fact_id)
        assert success
        
        print("   ✅ InMemoryStore基本操作正常")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试4: ShortTermMemory容量限制
    print("\n📊 测试4: ShortTermMemory容量限制")
    try:
        memory = ShortTermMemory(max_size=5)
        
        # 添加超过容量的记忆
        for i in range(8):
            memory.add_fact(f"记忆内容 {i}", source="user")
        
        # 应该只保留最近的5条
        count = memory.store.count()
        assert count == 5, f"Expected 5, got {count}"
        
        # 检查最旧的已被清理
        recent = memory.get_recent(count=5)
        contents = [f.content for f in recent]
        assert "记忆内容 0" not in contents  # 最旧的应该被清理
        assert "记忆内容 7" in contents  # 最新的应该保留
        
        print("   ✅ ShortTermMemory容量限制正常")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试5: LongTermMemory置信度过滤
    print("\n📊 测试5: LongTermMemory置信度过滤")
    try:
        memory = LongTermMemory()
        
        # 添加不同置信度的记忆
        memory.add_fact("高置信度事实", confidence=0.95)
        memory.add_fact("中置信度事实", confidence=0.7)
        memory.add_fact("低置信度事实", confidence=0.3)
        
        # 搜索时过滤低置信度
        results = memory.search("事实", min_confidence=0.5)
        assert len(results) == 2  # 只有高和中置信度
        
        for fact in results:
            assert fact.confidence >= 0.5
        
        print("   ✅ LongTermMemory置信度过滤正常")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试6: WorkingMemory上下文管理
    print("\n📊 测试6: WorkingMemory上下文管理")
    try:
        working = WorkingMemory(task_id="task_001")
        
        # 添加上下文
        ctx_id = working.add_context("当前任务步骤1", relevance=1.0)
        working.add_context("临时计算结果", relevance=0.5)
        
        # 获取上下文
        context = working.get_context()
        assert len(context) == 2
        
        # 清理
        cleared = working.clear()
        assert cleared == 2
        assert working.store.count() == 0
        
        print("   ✅ WorkingMemory上下文管理正常")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
    
    # 测试7: MemorySystem完整流程
    print("\n📊 测试7: MemorySystem完整流程")
    try:
        system = MemorySystem()
        
        # 1. 添加到短期记忆
        short_id = system.add_to_short_term("用户说了你好", source="user")
        
        # 2. 提升到长期记忆
        success = system.promote_to_long_term(short_id)
        assert success
        
        # 3. 添加到长期记忆
        system.add_to_long_term("用户是Python开发者", 
                                source="system", 
                                tags={"user_profile"})
        
        # 4. 创建工作记忆
        working = system.create_working_memory("task_001")
        working.add_context("正在处理用户请求")
        
        # 5. 跨层搜索
        results = system.search_all("用户")
        assert len(results["short_term"]) >= 1 or len(results["long_term"]) >= 1
        
        # 6. 获取摘要
        summary = system.get_summary()
        assert summary["active_working_tasks"] == 1
        
        print("   ✅ MemorySystem完整流程正常")
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
# 第八部分：演示主程序
# ============================================================================

def run_demo():
    """运行记忆系统演示"""
    print("🧠 Day 13 - 第49节课：记忆系统架构设计演示")
    print("=" * 60)
    
    # 1. 演示Fact数据模型
    print("\n📝 演示1: Fact数据模型")
    print("-" * 40)
    
    # 创建不同来源的Fact
    user_fact = Fact(
        content="我是一名Python后端开发工程师",
        source="user",
        confidence=1.0,
        memory_type=MemoryType.LONG_TERM
    )
    user_fact.add_tag("user_profile")
    user_fact.add_tag("skills")
    
    system_fact = Fact(
        content="用户可能对AI Agent开发感兴趣",
        source="system",
        confidence=0.7,
        memory_type=MemoryType.LONG_TERM
    )
    
    print(f"用户事实: {user_fact.content}")
    print(f"  置信度: {user_fact.confidence}, 标签: {user_fact.tags}")
    print(f"系统推断: {system_fact.content}")
    print(f"  置信度: {system_fact.confidence}")
    
    # 2. 演示短期记忆
    print("\n\n📝 演示2: 短期记忆（对话历史）")
    print("-" * 40)
    
    short_memory = ShortTermMemory(max_size=10)
    
    # 模拟对话
    dialogues = [
        ("你好，我想学习Python", "user"),
        ("好的，我可以帮你学习Python", "system"),
        ("我想学怎么写爬虫", "user"),
        ("爬虫是一个很好的学习项目，可以从requests库开始", "system"),
        ("requests库怎么用？", "user"),
    ]
    
    for content, source in dialogues:
        fact_id = short_memory.add_fact(content, source=source)
        print(f"  [{source}] {content}")
    
    print(f"\n短期记忆中存储了 {short_memory.store.count()} 条记录")
    
    # 搜索相关记忆
    search_results = short_memory.search("爬虫")
    print(f"搜索'爬虫'找到 {len(search_results)} 条结果")
    
    # 3. 演示长期记忆
    print("\n\n📝 演示3: 长期记忆（用户画像）")
    print("-" * 40)
    
    long_memory = LongTermMemory()
    
    # 添加用户画像信息
    profile_facts = [
        ("用户是Python开发者，有5年经验", "user", 1.0, {"profile", "experience"}),
        ("用户对AI Agent技术感兴趣", "system", 0.8, {"profile", "interest"}),
        ("用户偏好使用VS Code编辑器", "tool", 0.9, {"profile", "preference"}),
        ("用户之前问过关于FastAPI的问题", "system", 0.85, {"history", "tech"}),
    ]
    
    for content, source, confidence, tags in profile_facts:
        long_memory.add_fact(content, source=source, 
                            confidence=confidence, tags=tags)
    
    # 显示统计
    stats = long_memory.get_stats()
    print(f"长期记忆统计:")
    print(f"  活跃记忆数: {stats['total_active']}")
    print(f"  平均置信度: {stats['avg_confidence']:.2f}")
    print(f"  按来源: {stats['by_source']}")
    
    # 按标签搜索
    profile_facts = long_memory.get_by_tag("profile")
    print(f"\n用户画像相关记忆 ({len(profile_facts)} 条):")
    for fact in profile_facts:
        print(f"  - {fact.content} (置信度: {fact.confidence})")
    
    # 4. 演示工作记忆
    print("\n\n📝 演示4: 工作记忆（任务上下文）")
    print("-" * 40)
    
    task_id = "task_codegen_001"
    working = WorkingMemory(task_id=task_id)
    
    # 模拟任务执行过程
    working.add_context("任务: 生成Python API代码", relevance=1.0)
    working.add_context("用户需求: FastAPI + SQLAlchemy", relevance=0.95)
    working.add_context("生成进度: 模型定义完成", relevance=0.8)
    working.add_context("临时结果: User模型类已创建", relevance=0.7)
    
    print(f"任务ID: {task_id}")
    print(f"任务持续时间: {working.get_task_duration():.2f}秒")
    print(f"工作记忆上下文 ({working.store.count()} 条):")
    
    context = working.get_context()
    for fact in context:
        print(f"  - {fact.content} (相关度: {fact.confidence})")
    
    # 5. 演示完整记忆系统
    print("\n\n📝 演示5: 完整记忆系统")
    print("-" * 40)
    
    memory_system = MemorySystem(short_term_size=50)
    
    # 使用记忆系统
    memory_system.add_to_short_term("开始新会话", source="system")
    memory_system.add_to_long_term(
        "用户是DeerFlow课程学员", 
        source="system",
        confidence=1.0,
        tags={"student", "course"}
    )
    
    # 创建并使用工作记忆
    task_working = memory_system.create_working_memory("lesson_49")
    task_working.add_context("正在学习记忆系统架构")
    
    # 跨层搜索
    print("跨层搜索'用户':")
    search_results = memory_system.search_all("用户")
    for layer, facts in search_results.items():
        if facts:
            print(f"  {layer}: {len(facts)} 条结果")
    
    # 获取系统摘要
    summary = memory_system.get_summary()
    print(f"\n记忆系统摘要:")
    print(f"  短期记忆数量: {summary['short_term_count']}")
    print(f"  长期记忆总数: {summary['long_term_stats']['total_active']}")
    print(f"  活跃任务数: {summary['active_working_tasks']}")
    
    print("\n" + "=" * 60)
    print("✅ 演示完成！")


if __name__ == "__main__":
    if "--test" in sys.argv:
        success = run_tests()
        sys.exit(0 if success else 1)
    else:
        run_demo()
