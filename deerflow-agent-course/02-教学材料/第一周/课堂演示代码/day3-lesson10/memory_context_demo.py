#!/usr/bin/env python3
# 教育代码说明：本文件为AI Agent架构师训练营课堂演示代码，包含详细注释用于教学目的
# Educational code note: This file contains detailed comments for teaching purposes in AI Agent Architect Training Camp
"""
Day 3 Lesson 10: 内存上下文注入机制 - 课堂演示代码

本文件演示内存上下文注入机制的完整设计与实现，包含四个部分：
1. 内存系统架构模拟 - 三层内存架构模拟和生命周期管理
2. 上下文注入状态机实现 - 对话历史格式化、过滤和注入流程
3. 记忆检索系统设计 - 多策略记忆检索和相关性评分
4. 内存系统架构分析 - 设计模式、性能优化、最佳实践分析

学习目标：
- 掌握内存系统三层架构（短期、长期、工作记忆）的设计原理
- 理解上下文注入的完整流程和token管理
- 实现多种记忆检索策略（关键词、时间、相关性）
- 设计适应token限制的动态上下文窗口

版本: 1.0
作者: DeerFlow架构师训练营
日期: 2024年3月27日
"""

import json
import time
import re
from typing import TypedDict, Optional, List, Dict, Any, Union, Callable
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from collections import deque, defaultdict
import argparse
from datetime import datetime, timedelta

# 模拟tiktoken的token计算（简化版）
try:
    import tiktoken

    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False
    print("⚠️  tiktoken未安装，使用简化token计算")

# ============================================================================
# 第一部分：内存系统架构模拟
# ============================================================================

print("=" * 60)
print("第一部分：内存系统架构模拟")
print("=" * 60)
print()

# ============================================================================
# 1.1 三层内存架构定义
# ============================================================================

print("🏗️ 1.1 三层内存架构定义")
print()


class MemoryType(Enum):
    """内存类型枚举"""

    SHORT_TERM = "short_term"  # 短期记忆：当前会话的对话历史
    LONG_TERM = "long_term"  # 长期记忆：跨会话的重要信息
    WORKING = "working"  # 工作记忆：当前推理的临时信息


class MemoryItem:
    """内存项"""

    def __init__(
        self,
        content: str,
        memory_type: MemoryType,
        timestamp: float = None,
        metadata: Dict[str, Any] = None,
    ):
        self.content = content
        self.memory_type = memory_type
        self.timestamp = timestamp or time.time()
        self.metadata = metadata or {}

        # 计算token数（简化）
        self.token_count = self._estimate_tokens(content)

        # 重要性评分（0.0-1.0）
        self.importance = metadata.get("importance", 0.5) if metadata else 0.5

        # 相关标签
        self.tags = metadata.get("tags", []) if metadata else []

    def _estimate_tokens(self, text: str) -> int:
        """估算token数（简化实现）"""
        # 在实际系统中使用tiktoken
        if HAS_TIKTOKEN:
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
            except:
                pass

        # 简化估算：英文约4字符1个token，中文约2字符1个token
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        other_chars = len(text) - chinese_chars
        return (chinese_chars // 2) + (other_chars // 4)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "token_count": self.token_count,
            "importance": self.importance,
            "tags": self.tags,
        }

    def __repr__(self):
        return f"MemoryItem(content={self.content[:50]}..., type={self.memory_type.value}, tokens={self.token_count})"


class ShortTermMemory:
    """短期记忆（对话历史）"""

    def __init__(self, max_items: int = 20, max_tokens: int = 4000):
        self.max_items = max_items
        self.max_tokens = max_tokens
        self.items = deque(maxlen=max_items)
        self.current_tokens = 0

    def add(self, item: MemoryItem):
        """添加记忆项"""
        # 检查token限制
        if self.current_tokens + item.token_count > self.max_tokens:
            self._evict_oldest()

        self.items.append(item)
        self.current_tokens += item.token_count

    def _evict_oldest(self):
        """淘汰最旧的记忆项"""
        if self.items:
            removed = self.items.popleft()
            self.current_tokens -= removed.token_count

    def get_recent(self, count: int = 10) -> List[MemoryItem]:
        """获取最近的记忆项"""
        return list(self.items)[-count:]

    def get_all(self) -> List[MemoryItem]:
        """获取所有记忆项"""
        return list(self.items)

    def clear(self):
        """清空短期记忆"""
        self.items.clear()
        self.current_tokens = 0

    def stats(self) -> Dict[str, Any]:
        """统计信息"""
        return {
            "item_count": len(self.items),
            "token_count": self.current_tokens,
            "max_items": self.max_items,
            "max_tokens": self.max_tokens,
        }


class LongTermMemory:
    """长期记忆（重要信息存储）"""

    def __init__(self):
        self.items = []  # 在实际系统中会使用数据库

    def add(self, item: MemoryItem):
        """添加长期记忆项"""
        # 长期记忆只存储重要性高的项目
        if item.importance >= 0.7:
            self.items.append(item)
            print(
                f"💾 长期记忆添加: {item.content[:50]}... (重要性: {item.importance})"
            )

    def search_by_tags(self, tags: List[str]) -> List[MemoryItem]:
        """按标签搜索"""
        results = []
        for item in self.items:
            if any(tag in item.tags for tag in tags):
                results.append(item)
        return results

    def search_by_keywords(self, keywords: List[str]) -> List[MemoryItem]:
        """按关键词搜索"""
        results = []
        for item in self.items:
            content_lower = item.content.lower()
            if any(keyword.lower() in content_lower for keyword in keywords):
                results.append(item)
        return results

    def get_important(self, min_importance: float = 0.8) -> List[MemoryItem]:
        """获取重要性高的记忆项"""
        return [item for item in self.items if item.importance >= min_importance]


class WorkingMemory:
    """工作记忆（当前推理的临时信息）"""

    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens
        self.items = []
        self.current_tokens = 0

    def add(self, item: MemoryItem):
        """添加工作记忆项"""
        if self.current_tokens + item.token_count <= self.max_tokens:
            self.items.append(item)
            self.current_tokens += item.token_count
        else:
            print(f"⚠️  工作记忆已满，无法添加: {item.content[:50]}...")

    def clear(self):
        """清空工作记忆"""
        self.items.clear()
        self.current_tokens = 0

    def get_context(self) -> str:
        """获取上下文（所有工作记忆内容）"""
        return "\n".join([item.content for item in self.items])


# ============================================================================
# 1.2 内存系统整合
# ============================================================================

print("🔗 1.2 内存系统整合")
print()


class MemorySystem:
    """三层内存系统"""

    def __init__(self):
        self.short_term = ShortTermMemory(max_items=20, max_tokens=4000)
        self.long_term = LongTermMemory()
        self.working = WorkingMemory(max_tokens=2000)

        # 内存操作统计
        self.stats = {
            "short_term_adds": 0,
            "long_term_adds": 0,
            "working_adds": 0,
            "searches": 0,
        }

    def add_memory(
        self, content: str, memory_type: MemoryType, metadata: Dict[str, Any] = None
    ) -> MemoryItem:
        """添加记忆"""
        item = MemoryItem(content, memory_type, metadata=metadata)

        # 根据类型添加到相应内存
        if memory_type == MemoryType.SHORT_TERM:
            self.short_term.add(item)
            self.stats["short_term_adds"] += 1
        elif memory_type == MemoryType.LONG_TERM:
            self.long_term.add(item)
            self.stats["long_term_adds"] += 1
        elif memory_type == MemoryType.WORKING:
            self.working.add(item)
            self.stats["working_adds"] += 1

        return item

    def search_memories(
        self, query: str, memory_types: List[MemoryType] = None
    ) -> List[MemoryItem]:
        """搜索记忆"""
        self.stats["searches"] += 1

        if memory_types is None:
            memory_types = [MemoryType.SHORT_TERM, MemoryType.LONG_TERM]

        results = []

        # 从长期记忆搜索
        if MemoryType.LONG_TERM in memory_types:
            keywords = query.split()
            long_term_results = self.long_term.search_by_keywords(keywords)
            results.extend(long_term_results)

        # 从短期记忆搜索（最近的相关对话）
        if MemoryType.SHORT_TERM in memory_types:
            short_term_items = self.short_term.get_all()
            # 简单关键词匹配
            for item in short_term_items[-10:]:  # 最近10条
                if any(
                    keyword in item.content.lower() for keyword in query.lower().split()
                ):
                    results.append(item)

        # 按相关性排序（简化：按时间倒序）
        results.sort(key=lambda x: x.timestamp, reverse=True)

        return results

    def get_context_for_injection(self, max_tokens: int = 3000) -> str:
        """获取用于注入的上下文"""
        # 1. 获取工作记忆上下文
        working_context = self.working.get_context()

        # 2. 从短期记忆获取最近对话
        short_term_items = self.short_term.get_recent(10)
        short_term_context = "\n".join([item.content for item in short_term_items])

        # 3. 从长期记忆获取相关记忆
        # 使用工作记忆内容作为查询
        if working_context:
            long_term_items = self.long_term.search_by_keywords(
                working_context.split()[:5]
            )
            long_term_context = "\n".join(
                [item.content for item in long_term_items[:3]]
            )
        else:
            long_term_context = ""

        # 组合上下文
        full_context = f"""工作记忆：
{working_context}

近期对话：
{short_term_context}

相关记忆：
{long_term_context}"""

        # 估算token数并修剪
        estimated_tokens = self._estimate_tokens(full_context)
        if estimated_tokens > max_tokens:
            print(
                f"⚠️  上下文超过token限制 ({estimated_tokens} > {max_tokens})，进行修剪"
            )
            full_context = self._trim_context(full_context, max_tokens)

        return full_context

    def _estimate_tokens(self, text: str) -> int:
        """估算token数"""
        # 简化实现
        return len(text) // 4

    def _trim_context(self, context: str, max_tokens: int) -> str:
        """修剪上下文以适应token限制"""
        # 简单实现：按段落修剪
        paragraphs = context.split("\n\n")
        trimmed = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = len(para) // 4
            if current_tokens + para_tokens <= max_tokens:
                trimmed.append(para)
                current_tokens += para_tokens
            else:
                # 尝试修剪段落内部
                words = para.split()
                trimmed_words = []
                for word in words:
                    word_tokens = len(word) // 4 + 1
                    if current_tokens + word_tokens <= max_tokens:
                        trimmed_words.append(word)
                        current_tokens += word_tokens
                    else:
                        break
                if trimmed_words:
                    trimmed.append(" ".join(trimmed_words))
                break

        return "\n\n".join(trimmed)

    def print_stats(self):
        """打印统计信息"""
        print("📊 内存系统统计:")
        print(f"  短期记忆: {self.short_term.stats()}")
        print(f"  长期记忆项数: {len(self.long_term.items)}")
        print(f"  工作记忆项数: {len(self.working.items)}")
        print(f"  操作统计: {self.stats}")


# 演示内存系统
print("🎬 演示三层内存系统:")
print()

memory_system = MemorySystem()

# 添加一些记忆
print("📝 添加记忆项:")
memories = [
    (
        "用户: 你好，我想学习Python编程",
        MemoryType.SHORT_TERM,
        {"importance": 0.3, "tags": ["greeting", "python"]},
    ),
    (
        "助手: 你好！我很乐意帮助你学习Python。",
        MemoryType.SHORT_TERM,
        {"importance": 0.3},
    ),
    (
        "用户: Python有什么优势？",
        MemoryType.SHORT_TERM,
        {"importance": 0.4, "tags": ["python", "advantages"]},
    ),
    (
        "助手: Python语法简洁，有丰富的库，适合初学者。",
        MemoryType.SHORT_TERM,
        {"importance": 0.4},
    ),
    (
        "Python是一种高级编程语言，广泛用于数据科学和AI。",
        MemoryType.LONG_TERM,
        {"importance": 0.8, "tags": ["python", "definition"]},
    ),
    (
        "列表推导式是Python的优雅特性：[x*2 for x in range(10)]",
        MemoryType.LONG_TERM,
        {"importance": 0.9, "tags": ["python", "feature"]},
    ),
    ("当前任务: 解释Python列表推导式", MemoryType.WORKING, {"importance": 0.5}),
]

for content, mem_type, metadata in memories:
    item = memory_system.add_memory(content, mem_type, metadata)
    print(f"  {mem_type.value}: {content[:50]}...")

print()

# 搜索记忆
print("🔍 搜索记忆 (关键词: 'Python'):")
search_results = memory_system.search_memories("Python")
for i, item in enumerate(search_results[:3], 1):
    print(
        f"  {i}. {item.content[:60]}... (类型: {item.memory_type.value}, 重要性: {item.importance})"
    )

print()

# 获取注入上下文
print("🔄 获取注入上下文:")
context = memory_system.get_context_for_injection(max_tokens=500)
print(f"上下文长度: {len(context)} 字符")
print(f"上下文预览: {context[:200]}...")
print()

memory_system.print_stats()
print()

print(
    "🎯 第一部分总结: 通过三层内存架构模拟，学员已掌握短期、长期、工作记忆的设计原理和基本操作。"
)
print()

# ============================================================================
# 第二部分：上下文注入状态机实现
# ============================================================================

print("=" * 60)
print("第二部分：上下文注入状态机实现")
print("=" * 60)
print()

# ============================================================================
# 2.1 上下文注入状态定义
# ============================================================================

print("🔄 2.1 上下文注入状态定义")
print()


class InjectionState(Enum):
    """上下文注入状态枚举"""

    INITIAL = "initial"  # 初始状态
    FORMATTING = "formatting"  # 格式化对话历史
    FILTERING = "filtering"  # 过滤不相关内容
    PRIORITIZING = "prioritizing"  # 优先级排序
    TOKEN_COUNTING = "token_counting"  # token计数
    TRIMMING = "trimming"  # 修剪超限内容
    INJECTING = "injecting"  # 注入到提示
    COMPLETE = "complete"  # 完成
    ERROR = "error"  # 错误


class ContextItem:
    """上下文项（用于注入）"""

    def __init__(self, content: str, source: str, priority: float = 0.5):
        self.content = content
        self.source = source  # 来源：short_term, long_term, working
        self.priority = priority  # 优先级 0.0-1.0
        self.token_count = 0
        self.timestamp = time.time()
        self.metadata = {}

    def calculate_tokens(self):
        """计算token数"""
        self.token_count = len(self.content) // 4  # 简化计算
        return self.token_count

    def __repr__(self):
        return f"ContextItem(content={self.content[:30]}..., source={self.source}, tokens={self.token_count}, priority={self.priority})"


class ContextInjectionStateMachine:
    """上下文注入状态机"""

    def __init__(self, memory_system: MemorySystem):
        self.memory_system = memory_system
        self.current_state = InjectionState.INITIAL
        self.context_items = []  # 待注入的上下文项
        self.injected_items = []  # 已注入的上下文项
        self.current_tokens = 0
        self.max_tokens = 3000  # 默认token限制

        # 状态转换表
        self.transitions = {
            InjectionState.INITIAL: InjectionState.FORMATTING,
            InjectionState.FORMATTING: InjectionState.FILTERING,
            InjectionState.FILTERING: InjectionState.PRIORITIZING,
            InjectionState.PRIORITIZING: InjectionState.TOKEN_COUNTING,
            InjectionState.TOKEN_COUNTING: InjectionState.TRIMMING,
            InjectionState.TRIMMING: InjectionState.INJECTING,
            InjectionState.INJECTING: InjectionState.COMPLETE,
        }

        # 错误处理
        self.errors = []

    def run(self, max_tokens: int = 3000) -> str:
        """运行状态机，返回注入后的提示"""
        print(f"🚀 启动上下文注入状态机 (max_tokens={max_tokens})")
        self.max_tokens = max_tokens
        self.current_state = InjectionState.INITIAL

        try:
            while self.current_state != InjectionState.COMPLETE:
                self._process_current_state()

                # 状态转换
                if self.current_state in self.transitions:
                    next_state = self.transitions[self.current_state]
                    print(
                        f"  ↪️  状态转换: {self.current_state.value} → {next_state.value}"
                    )
                    self.current_state = next_state
                else:
                    break
        except Exception as e:
            self.current_state = InjectionState.ERROR
            self.errors.append(str(e))
            print(f"❌ 状态机错误: {e}")

        # 生成最终提示
        return self._generate_final_prompt()

    def _process_current_state(self):
        """处理当前状态"""
        state_handlers = {
            InjectionState.INITIAL: self._handle_initial,
            InjectionState.FORMATTING: self._handle_formatting,
            InjectionState.FILTERING: self._handle_filtering,
            InjectionState.PRIORITIZING: self._handle_prioritizing,
            InjectionState.TOKEN_COUNTING: self._handle_token_counting,
            InjectionState.TRIMMING: self._handle_trimming,
            InjectionState.INJECTING: self._handle_injecting,
        }

        handler = state_handlers.get(self.current_state)
        if handler:
            print(f"  📍 处理状态: {self.current_state.value}")
            handler()

    def _handle_initial(self):
        """初始状态处理"""
        print("  📋 收集内存系统统计...")
        self.memory_system.print_stats()

    def _handle_formatting(self):
        """格式化对话历史"""
        print("  📝 格式化对话历史...")

        # 1. 获取工作记忆
        working_context = self.memory_system.working.get_context()
        if working_context:
            self.context_items.append(
                ContextItem(working_context, "working", priority=0.9)
            )

        # 2. 获取短期记忆（最近对话）
        short_term_items = self.memory_system.short_term.get_recent(10)
        for i, item in enumerate(short_term_items):
            formatted = f"[对话{i + 1}] {item.content}"
            self.context_items.append(
                ContextItem(formatted, "short_term", priority=0.7)
            )

        # 3. 获取长期记忆（相关记忆）
        # 使用工作记忆内容作为查询
        if working_context:
            keywords = working_context.split()[:5]
            long_term_items = self.memory_system.long_term.search_by_keywords(keywords)
            for i, item in enumerate(long_term_items[:3]):
                formatted = f"[记忆{i + 1}] {item.content}"
                self.context_items.append(
                    ContextItem(formatted, "long_term", priority=0.8)
                )

        print(f"  ✅ 格式化完成: {len(self.context_items)} 个上下文项")

    def _handle_filtering(self):
        """过滤不相关内容"""
        print(f"  🧹 过滤前: {len(self.context_items)} 个上下文项")

        # 简单的过滤规则
        filtered_items = []
        for item in self.context_items:
            # 过滤空内容
            if not item.content or item.content.strip() == "":
                continue

            # 过滤过短的上下文（可能不完整）
            if len(item.content) < 10:
                continue

            filtered_items.append(item)

        self.context_items = filtered_items
        print(f"  ✅ 过滤后: {len(self.context_items)} 个上下文项")

    def _handle_prioritizing(self):
        """优先级排序"""
        print(f"  📊 对 {len(self.context_items)} 个上下文项进行优先级排序...")

        # 根据来源和内容计算优先级
        for item in self.context_items:
            # 基础优先级
            base_priority = item.priority

            # 根据来源调整
            if item.source == "working":
                item.priority = base_priority * 1.2  # 工作记忆优先级最高
            elif item.source == "long_term":
                item.priority = base_priority * 1.1  # 长期记忆次之
            elif item.source == "short_term":
                item.priority = base_priority * 1.0  # 短期记忆保持原优先级

            # 根据长度调整（适中长度最好）
            content_len = len(item.content)
            if 100 < content_len < 500:
                item.priority *= 1.05  # 适中长度有优势
            elif content_len > 1000:
                item.priority *= 0.9  # 过长内容降低优先级

        # 按优先级排序（降序）
        self.context_items.sort(key=lambda x: x.priority, reverse=True)

        # 显示前5项
        print("  📈 优先级最高的5个上下文项:")
        for i, item in enumerate(self.context_items[:5], 1):
            print(f"    {i}. {item.content[:50]}... (优先级: {item.priority:.2f})")

    def _handle_token_counting(self):
        """token计数"""
        print("  🧮 计算token数...")

        self.current_tokens = 0
        for item in self.context_items:
            item.calculate_tokens()
            self.current_tokens += item.token_count

        print(f"  📊 总token数: {self.current_tokens} (限制: {self.max_tokens})")

        # 检查是否超限
        if self.current_tokens > self.max_tokens:
            print(f"  ⚠️  token超限: {self.current_tokens} > {self.max_tokens}")
        else:
            print(f"  ✅ token在限制内")

    def _handle_trimming(self):
        """修剪超限内容"""
        if self.current_tokens <= self.max_tokens:
            print("  ✅ token未超限，无需修剪")
            return

        print(f"  ✂️  开始修剪 (当前: {self.current_tokens}, 限制: {self.max_tokens})")

        # 优先保留高优先级的上下文项
        self.context_items.sort(key=lambda x: x.priority, reverse=True)

        # 计算需要修剪的token数
        excess_tokens = self.current_tokens - self.max_tokens
        print(f"  🔢 需要修剪 {excess_tokens} 个token")

        # 修剪策略：从低优先级开始修剪
        trimmed_items = []
        remaining_tokens = 0

        for item in self.context_items:
            if remaining_tokens + item.token_count <= self.max_tokens:
                trimmed_items.append(item)
                remaining_tokens += item.token_count
            else:
                # 尝试部分修剪该项
                if item.token_count > 100:  # 只修剪较长的项
                    trimmed_content = self._trim_content(item.content, excess_tokens)
                    if trimmed_content:
                        trimmed_item = ContextItem(
                            trimmed_content, item.source, item.priority
                        )
                        trimmed_item.token_count = trimmed_item.calculate_tokens()
                        trimmed_items.append(trimmed_item)
                        remaining_tokens += trimmed_item.token_count
                        excess_tokens -= item.token_count - trimmed_item.token_count
                # 否则完全丢弃该项

        self.context_items = trimmed_items
        self.current_tokens = remaining_tokens

        print(
            f"  ✅ 修剪完成: 保留 {len(self.context_items)} 项, {self.current_tokens} 个token"
        )

    def _trim_content(self, content: str, target_tokens_reduction: int) -> str:
        """修剪内容以减少token数"""
        # 简化实现：按段落修剪
        paragraphs = content.split("\n\n")
        trimmed_paragraphs = []
        current_tokens = 0
        target_tokens = len(content) // 4 - target_tokens_reduction

        for para in paragraphs:
            para_tokens = len(para) // 4
            if current_tokens + para_tokens <= target_tokens:
                trimmed_paragraphs.append(para)
                current_tokens += para_tokens
            else:
                break

        return "\n\n".join(trimmed_paragraphs)

    def _handle_injecting(self):
        """注入到提示"""
        print("  💉 将上下文注入到提示...")

        # 标记为已注入
        self.injected_items = self.context_items.copy()

        print(f"  ✅ 注入完成: {len(self.injected_items)} 个上下文项已注入")

    def _generate_final_prompt(self) -> str:
        """生成最终提示"""
        if self.current_state == InjectionState.ERROR:
            return f"上下文注入失败: {', '.join(self.errors)}"

        print("  📄 生成最终提示...")

        # 组装提示
        prompt_parts = []

        # 1. 系统提示
        system_prompt = """你是一个专业的AI助手，拥有以下上下文信息："""
        prompt_parts.append(system_prompt)

        # 2. 上下文部分
        for i, item in enumerate(self.injected_items, 1):
            source_label = {
                "working": "工作记忆",
                "short_term": "近期对话",
                "long_term": "相关知识",
            }.get(item.source, item.source)

            prompt_parts.append(f"\n[{source_label} {i}]")
            prompt_parts.append(item.content)

        # 3. 用户指令部分
        prompt_parts.append("\n\n基于以上上下文，请回答用户的问题。")

        final_prompt = "\n".join(prompt_parts)

        # 统计信息
        stats = {
            "上下文项数": len(self.injected_items),
            "总token数": self.current_tokens,
            "最终字符数": len(final_prompt),
            "状态": self.current_state.value,
        }

        print("  📊 最终提示统计:")
        for key, value in stats.items():
            print(f"    {key}: {value}")

        return final_prompt


# ============================================================================
# 2.2 上下文注入演示
# ============================================================================

print("🎬 2.2 上下文注入演示")
print()

# 创建状态机实例
print("1. 创建上下文注入状态机")
state_machine = ContextInjectionStateMachine(memory_system)
print(f"   初始状态: {state_machine.current_state.value}")
print()

# 运行状态机
print("2. 运行状态机 (max_tokens=500)")
print("-" * 40)
final_prompt = state_machine.run(max_tokens=500)
print("-" * 40)
print()

# 显示最终提示
print("3. 生成的最终提示:")
print("-" * 60)
print(final_prompt[:300] + "..." if len(final_prompt) > 300 else final_prompt)
print("-" * 60)
print()

print("🔧 演示扩展: 不同token限制下的注入效果")
print()

# 演示不同token限制
token_limits = [200, 500, 1000, 2000]
for limit in token_limits:
    print(f"运行状态机 (max_tokens={limit})")
    test_sm = ContextInjectionStateMachine(memory_system)
    test_prompt = test_sm.run(max_tokens=limit)
    print(f"  结果: {len(test_sm.injected_items)} 项, {test_sm.current_tokens} tokens")
    print()

print(
    "🎯 第二部分总结: 通过状态机实现上下文注入流程，学员已掌握格式化、过滤、排序、修剪等关键步骤的设计原理。"
)
print()

# ============================================================================
# 第三部分：记忆检索系统设计
# ============================================================================

print("=" * 60)
print("第三部分：记忆检索系统设计")
print("=" * 60)
print()

# ============================================================================
# 3.1 记忆检索策略定义
# ============================================================================

print("🔍 3.1 记忆检索策略定义")
print()


class RetrievalStrategy(ABC):
    """记忆检索策略基类"""

    @abstractmethod
    def retrieve(self, query: str, memories: List[MemoryItem]) -> List[MemoryItem]:
        """检索记忆"""
        pass

    def score_memory(self, query: str, memory: MemoryItem) -> float:
        """评分记忆（0.0-1.0）"""
        pass


class KeywordRetrieval(RetrievalStrategy):
    """关键词检索策略"""

    def retrieve(self, query: str, memories: List[MemoryItem]) -> List[MemoryItem]:
        """基于关键词的检索"""
        keywords = self._extract_keywords(query)

        scored_memories = []
        for memory in memories:
            score = self.score_memory(query, memory)
            if score > 0.1:  # 最低阈值
                scored_memories.append((memory, score))

        # 按分数排序
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        return [memory for memory, score in scored_memories]

    def score_memory(self, query: str, memory: MemoryItem) -> float:
        """基于关键词匹配的评分"""
        keywords = self._extract_keywords(query)

        if not keywords:
            return 0.0

        # 计算匹配的关键词数量
        content_lower = memory.content.lower()
        matched_keywords = 0

        for keyword in keywords:
            if keyword.lower() in content_lower:
                matched_keywords += 1

        # 基础分数：匹配关键词比例
        base_score = matched_keywords / len(keywords)

        # 根据记忆重要性调整
        adjusted_score = base_score * (0.5 + memory.importance * 0.5)

        return min(adjusted_score, 1.0)

    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词（简化实现）"""
        # 移除停用词和标点
        stop_words = {
            "的",
            "了",
            "在",
            "是",
            "我",
            "有",
            "和",
            "就",
            "不",
            "人",
            "都",
            "一",
            "一个",
            "上",
            "也",
            "很",
            "到",
            "说",
            "要",
            "去",
            "你",
            "会",
            "着",
            "没有",
            "看",
            "好",
            "自己",
            "这",
        }

        words = query.split()
        keywords = []

        for word in words:
            # 移除标点
            clean_word = re.sub(r"[^\w\u4e00-\u9fff]", "", word)
            if clean_word and clean_word not in stop_words and len(clean_word) > 1:
                keywords.append(clean_word)

        return keywords[:10]  # 最多10个关键词


class TemporalRetrieval(RetrievalStrategy):
    """时间检索策略（优先返回最近的记忆）"""

    def retrieve(self, query: str, memories: List[MemoryItem]) -> List[MemoryItem]:
        """基于时间的检索"""
        # 按时间排序（最近的在前）
        sorted_memories = sorted(memories, key=lambda x: x.timestamp, reverse=True)

        # 计算时间分数
        scored_memories = []
        max_time = max([m.timestamp for m in memories]) if memories else time.time()
        min_time = min([m.timestamp for m in memories]) if memories else time.time()

        for memory in sorted_memories:
            score = self.score_memory(query, memory)

            # 时间衰减因子
            time_range = max_time - min_time if max_time > min_time else 1
            time_factor = 1.0 - ((max_time - memory.timestamp) / time_range) * 0.5

            final_score = score * time_factor
            if final_score > 0.05:  # 很低阈值，主要依赖时间排序
                scored_memories.append((memory, final_score))

        # 按最终分数排序
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        return [memory for memory, score in scored_memories[:20]]  # 最多20条

    def score_memory(self, query: str, memory: MemoryItem) -> float:
        """时间策略的评分（主要基于时间）"""
        # 时间策略也考虑基本的相关性
        keywords = query.split()
        content_lower = memory.content.lower()

        # 简单关键词匹配
        matches = 0
        for keyword in keywords[:5]:  # 只检查前5个词
            if keyword.lower() in content_lower:
                matches += 1

        # 基础相关性分数
        base_score = matches / min(len(keywords), 5) if keywords else 0.0

        # 结合记忆重要性
        return base_score * (0.3 + memory.importance * 0.7)


class RelevanceRetrieval(RetrievalStrategy):
    """相关性检索策略（基于语义相似度）"""

    def __init__(self):
        # 简化的相似度计算（实际中会使用嵌入模型）
        self.similarity_cache = {}

    def retrieve(self, query: str, memories: List[MemoryItem]) -> List[MemoryItem]:
        """基于相关性的检索"""
        scored_memories = []

        for memory in memories:
            score = self.score_memory(query, memory)
            if score > 0.2:  # 相关性阈值较高
                scored_memories.append((memory, score))

        # 按相关性分数排序
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        return [memory for memory, score in scored_memories]

    def score_memory(self, query: str, memory: MemoryItem) -> float:
        """基于语义相似度的评分"""
        # 简化实现：使用TF-IDF风格的相似度计算
        query_words = set(self._tokenize(query))
        memory_words = set(self._tokenize(memory.content))

        if not query_words or not memory_words:
            return 0.0

        # Jaccard相似度
        intersection = query_words.intersection(memory_words)
        union = query_words.union(memory_words)

        similarity = len(intersection) / len(union) if union else 0.0

        # 根据记忆类型和重要性调整
        type_factor = 1.0
        if memory.memory_type == MemoryType.LONG_TERM:
            type_factor = 1.2  # 长期记忆更相关
        elif memory.memory_type == MemoryType.WORKING:
            type_factor = 1.1  # 工作记忆次之

        adjusted_similarity = similarity * type_factor * (0.5 + memory.importance * 0.5)

        return min(adjusted_similarity, 1.0)

    def _tokenize(self, text: str) -> List[str]:
        """分词（简化实现）"""
        # 移除标点，分割单词
        clean_text = re.sub(r"[^\w\u4e00-\u9fff\s]", " ", text)
        tokens = clean_text.lower().split()

        # 过滤停用词
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "的",
            "了",
            "在",
            "是",
            "我",
            "有",
            "和",
        }
        return [token for token in tokens if token not in stop_words and len(token) > 1]


class HybridRetrieval(RetrievalStrategy):
    """混合检索策略（组合多种策略）"""

    def __init__(self, strategies: List[RetrievalStrategy] = None):
        if strategies is None:
            self.strategies = [
                KeywordRetrieval(),
                TemporalRetrieval(),
                RelevanceRetrieval(),
            ]
        else:
            self.strategies = strategies

        # 权重配置
        self.weights = {
            "KeywordRetrieval": 0.4,
            "TemporalRetrieval": 0.3,
            "RelevanceRetrieval": 0.3,
        }

    def retrieve(self, query: str, memories: List[MemoryItem]) -> List[MemoryItem]:
        """混合检索"""
        if not memories:
            return []

        # 收集所有策略的结果
        all_results = {}

        for strategy in self.strategies:
            strategy_name = strategy.__class__.__name__
            weight = self.weights.get(strategy_name, 0.2)

            strategy_results = strategy.retrieve(query, memories)

            # 为每个结果分配分数
            for i, memory in enumerate(strategy_results):
                # 排名分数（越靠前分数越高）
                rank_score = (
                    1.0 - (i / len(strategy_results)) if strategy_results else 0.0
                )

                # 策略特定分数
                strategy_score = strategy.score_memory(query, memory)

                # 综合分数
                combined_score = (rank_score * 0.3 + strategy_score * 0.7) * weight

                if memory not in all_results:
                    all_results[memory] = 0.0

                all_results[memory] += combined_score

        # 转换为列表并排序
        scored_memories = [(memory, score) for memory, score in all_results.items()]
        scored_memories.sort(key=lambda x: x[1], reverse=True)

        return [memory for memory, score in scored_memories]

    def score_memory(self, query: str, memory: MemoryItem) -> float:
        """混合评分（所有策略的平均分）"""
        scores = []
        for strategy in self.strategies:
            score = strategy.score_memory(query, memory)
            scores.append(score)

        return sum(scores) / len(scores) if scores else 0.0


# ============================================================================
# 3.2 记忆检索系统
# ============================================================================

print("🏗️ 3.2 记忆检索系统")
print()


class MemoryRetrievalSystem:
    """记忆检索系统"""

    def __init__(self, memory_system: MemorySystem):
        self.memory_system = memory_system

        # 可用策略
        self.strategies = {
            "keyword": KeywordRetrieval(),
            "temporal": TemporalRetrieval(),
            "relevance": RelevanceRetrieval(),
            "hybrid": HybridRetrieval(),
        }

        # 默认策略
        self.default_strategy = "hybrid"

        # 缓存系统（简化）
        self.cache = {}

    def retrieve_memories(
        self,
        query: str,
        strategy: str = None,
        limit: int = 10,
        memory_types: List[MemoryType] = None,
    ) -> List[MemoryItem]:
        """检索记忆"""
        if strategy is None:
            strategy = self.default_strategy

        # 检查缓存
        cache_key = f"{query}_{strategy}_{limit}"
        if cache_key in self.cache:
            print(f"  🔄 使用缓存结果 (查询: '{query[:30]}...')")
            return self.cache[cache_key][:limit]

        # 收集指定类型的记忆
        all_memories = []

        if memory_types is None:
            memory_types = [
                MemoryType.SHORT_TERM,
                MemoryType.LONG_TERM,
                MemoryType.WORKING,
            ]

        for mem_type in memory_types:
            if mem_type == MemoryType.SHORT_TERM:
                all_memories.extend(self.memory_system.short_term.get_all())
            elif mem_type == MemoryType.LONG_TERM:
                all_memories.extend(self.memory_system.long_term.items)
            elif mem_type == MemoryType.WORKING:
                all_memories.extend(self.memory_system.working.items)

        if not all_memories:
            return []

        # 使用指定策略检索
        retrieval_strategy = self.strategies.get(strategy)
        if not retrieval_strategy:
            print(f"  ⚠️  策略 '{strategy}' 不存在，使用默认策略")
            retrieval_strategy = self.strategies[self.default_strategy]

        # 执行检索
        print(f"  🔍 使用策略 '{strategy}' 检索记忆 (查询: '{query[:30]}...')")
        results = retrieval_strategy.retrieve(query, all_memories)

        # 缓存结果
        self.cache[cache_key] = results

        return results[:limit]

    def compare_strategies(
        self, query: str, limit: int = 5
    ) -> Dict[str, List[MemoryItem]]:
        """比较不同策略的结果"""
        print(f"  📊 比较检索策略 (查询: '{query[:30]}...')")

        results = {}

        for strategy_name, strategy in self.strategies.items():
            print(f"    ▶️  执行策略: {strategy_name}")
            strategy_results = strategy.retrieve(query, self._get_all_memories())

            # 计算平均分数
            if strategy_results:
                scores = [
                    strategy.score_memory(query, mem) for mem in strategy_results[:5]
                ]
                avg_score = sum(scores) / len(scores)
                print(f"      平均相关性: {avg_score:.3f}")

            results[strategy_name] = strategy_results[:limit]

        return results

    def _get_all_memories(self) -> List[MemoryItem]:
        """获取所有记忆"""
        all_memories = []
        all_memories.extend(self.memory_system.short_term.get_all())
        all_memories.extend(self.memory_system.long_term.items)
        all_memories.extend(self.memory_system.working.items)
        return all_memories

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """分析查询"""
        print(f"  🧪 分析查询: '{query}'")

        analysis = {
            "query_length": len(query),
            "word_count": len(query.split()),
            "estimated_tokens": len(query) // 4,
            "suggested_strategies": [],
        }

        # 根据查询特征建议策略
        words = query.split()
        if len(words) <= 3:
            analysis["suggested_strategies"].append("temporal")
            analysis["suggested_strategies"].append("keyword")
        elif len(words) >= 10:
            analysis["suggested_strategies"].append("relevance")
            analysis["suggested_strategies"].append("hybrid")
        else:
            analysis["suggested_strategies"].extend(["hybrid", "keyword", "relevance"])

        # 检查是否包含时间相关词汇
        time_keywords = [
            "昨天",
            "今天",
            "刚刚",
            "最近",
            "以前",
            "之前",
            "之后",
            "上周",
            "上月",
            "去年",
        ]
        if any(keyword in query for keyword in time_keywords):
            analysis["suggested_strategies"].insert(0, "temporal")

        print(f"    分析结果: {analysis}")
        return analysis


# ============================================================================
# 3.3 记忆检索演示
# ============================================================================

print("🎬 3.3 记忆检索演示")
print()

# 创建检索系统
print("1. 创建记忆检索系统")
retrieval_system = MemoryRetrievalSystem(memory_system)
print(f"   可用策略: {list(retrieval_system.strategies.keys())}")
print(f"   默认策略: {retrieval_system.default_strategy}")
print()

# 添加更多记忆用于演示
print("2. 添加更多记忆用于检索演示")
additional_memories = [
    (
        "Python的列表推导式非常高效，可以替代for循环",
        MemoryType.LONG_TERM,
        {"importance": 0.85, "tags": ["python", "performance", "list_comprehension"]},
    ),
    (
        "昨天我们讨论了AI Agent的架构设计",
        MemoryType.SHORT_TERM,
        {"importance": 0.6, "tags": ["ai", "architecture", "discussion"]},
    ),
    (
        "用户问过关于机器学习算法的问题",
        MemoryType.LONG_TERM,
        {"importance": 0.75, "tags": ["ml", "algorithm", "question"]},
    ),
    (
        "当前正在实现记忆检索系统",
        MemoryType.WORKING,
        {"importance": 0.9, "tags": ["implementation", "retrieval", "current"]},
    ),
    (
        "DeerFlow使用LangGraph进行状态管理",
        MemoryType.LONG_TERM,
        {"importance": 0.95, "tags": ["deerflow", "langgraph", "state_management"]},
    ),
    (
        "内存系统有三层：短期、长期、工作记忆",
        MemoryType.SHORT_TERM,
        {"importance": 0.7, "tags": ["memory", "architecture", "three_layer"]},
    ),
]

for content, mem_type, metadata in additional_memories:
    item = memory_system.add_memory(content, mem_type, metadata)
    print(f"   {mem_type.value}: {content[:50]}...")
print()

# 测试不同检索策略
print("3. 测试不同检索策略")
print("-" * 40)

test_queries = [
    "Python列表推导式",
    "内存系统设计",
    "昨天讨论的内容",
    "AI Agent架构",
]

for query in test_queries:
    print(f"查询: '{query}'")

    # 分析查询
    analysis = retrieval_system.analyze_query(query)

    # 使用混合策略检索
    results = retrieval_system.retrieve_memories(query, strategy="hybrid", limit=3)

    print(f"  混合策略结果:")
    for i, item in enumerate(results, 1):
        print(
            f"    {i}. {item.content[:60]}... (类型: {item.memory_type.value}, 重要性: {item.importance:.2f})"
        )

    print()
print("-" * 40)
print()

# 比较策略
print("4. 比较不同检索策略")
print("-" * 40)

comparison_query = "Python内存系统"
print(f"比较查询: '{comparison_query}'")
print()

strategy_results = retrieval_system.compare_strategies(comparison_query, limit=3)

for strategy_name, results in strategy_results.items():
    print(f"策略: {strategy_name}")
    if results:
        for i, item in enumerate(results, 1):
            print(f"  {i}. {item.content[:50]}...")
    else:
        print("  无结果")
    print()
print("-" * 40)
print()

# 演示缓存效果
print("5. 演示缓存效果")
print("-" * 40)

cache_query = "Python列表"
print(f"第一次查询: '{cache_query}'")
results1 = retrieval_system.retrieve_memories(cache_query, strategy="hybrid", limit=3)
print(f"  结果数: {len(results1)}")

print(f"第二次查询（相同）: '{cache_query}'")
results2 = retrieval_system.retrieve_memories(cache_query, strategy="hybrid", limit=3)
print(f"  结果数: {len(results2)}")

if results1 == results2:
    print("  ✅ 缓存命中，结果相同")
else:
    print("  ⚠️  缓存未命中或结果不同")
print("-" * 40)
print()

print(
    "🎯 第三部分总结: 通过多种检索策略的实现和比较，学员已掌握关键词、时间、相关性检索的设计原理和混合策略的集成方法。"
)
print()

# ============================================================================
# 第四部分：内存系统架构分析
# ============================================================================

print("=" * 60)
print("第四部分：内存系统架构分析")
print("=" * 60)
print()

# ============================================================================
# 4.1 设计模式分析
# ============================================================================

print("🏛️ 4.1 设计模式分析")
print()

print("📚 本内存系统使用的设计模式:")
print()

design_patterns = [
    {
        "name": "策略模式 (Strategy Pattern)",
        "description": "记忆检索系统使用策略模式实现多种检索算法",
        "implementation": "RetrievalStrategy 抽象基类，KeywordRetrieval、TemporalRetrieval、RelevanceRetrieval 具体策略",
        "benefits": "易于扩展新策略，策略之间可互换，符合开闭原则",
    },
    {
        "name": "状态模式 (State Pattern)",
        "description": "上下文注入使用状态模式管理注入流程",
        "implementation": "ContextInjectionStateMachine 中的状态枚举和状态处理器",
        "benefits": "简化复杂的状态转换逻辑，每个状态的处理逻辑独立",
    },
    {
        "name": "观察者模式 (Observer Pattern)",
        "description": "内存系统统计使用观察者模式跟踪操作",
        "implementation": "MemorySystem 中的 stats 字典跟踪各种操作计数",
        "benefits": "松耦合的统计跟踪，便于添加新的统计维度",
    },
    {
        "name": "工厂方法模式 (Factory Method)",
        "description": "检索策略的创建使用工厂方法",
        "implementation": "MemoryRetrievalSystem 中的 strategies 字典管理策略实例",
        "benefits": "集中管理策略创建，支持动态策略切换",
    },
    {
        "name": "组合模式 (Composite Pattern)",
        "description": "混合检索策略使用组合模式",
        "implementation": "HybridRetrieval 组合多个基础检索策略",
        "benefits": "可以创建复杂的检索策略而不修改现有代码",
    },
]

for i, pattern in enumerate(design_patterns, 1):
    print(f"{i}. {pattern['name']}")
    print(f"   描述: {pattern['description']}")
    print(f"   实现: {pattern['implementation']}")
    print(f"   优势: {pattern['benefits']}")
    print()

# ============================================================================
# 4.2 性能优化分析
# ============================================================================

print("⚡ 4.2 性能优化分析")
print()

performance_analysis = """
内存系统的性能关键指标和优化策略：

1. 🕒 响应时间优化
   • 检索缓存: MemoryRetrievalSystem 中的 cache 减少重复计算
   • 懒加载: 只在需要时计算token数
   • 分页查询: 限制检索结果数量 (limit 参数)

2. 💾 内存使用优化
   • 内存限制: 每层内存都有最大token/item限制
   • 淘汰策略: ShortTermMemory 使用 LRU-like 淘汰
   • 重要性过滤: LongTermMemory 只存储重要性高的项目

3. 🔍 检索效率优化
   • 多策略并行: HybridRetrieval 可并行执行多个策略
   • 结果缓存: 相同查询直接返回缓存结果
   • 预计算: 记忆添加时计算token数和重要性

4. 📈 可扩展性设计
   • 插件化策略: 易于添加新的检索策略
   • 配置化参数: 可通过配置调整各层内存限制
   • 水平扩展: 可支持分布式内存存储
"""

print(performance_analysis)
print()

# ============================================================================
# 4.3 架构决策权衡
# ============================================================================

print("⚖️ 4.3 架构决策权衡")
print()

tradeoff_analysis = """
在内存系统设计中面临的架构决策权衡：

1. 准确性 vs 响应时间
   • 高准确性: 使用复杂的相关性算法，但响应慢
   • 快速响应: 使用简单关键词匹配，但准确性低
   • 权衡方案: HybridRetrieval 平衡两者，根据查询复杂度选择策略

2. 内存占用 vs 信息保留
   • 保留更多信息: 需要更多内存，可能影响性能
   • 限制内存: 可能丢失重要历史信息
   • 权衡方案: 三层架构 + 重要性评分，优先保留重要信息

3. 实时性 vs 一致性
   • 强一致性: 所有操作同步更新，影响实时性
   • 最终一致性: 允许延迟更新，提高实时性
   • 权衡方案: 短期记忆强一致，长期记忆最终一致

4. 复杂度 vs 可维护性
   • 高度优化: 性能更好，但代码复杂难维护
   • 简单设计: 易于维护，但可能性能不足
   • 权衡方案: 核心算法优化，外围代码保持简洁
"""

print(tradeoff_analysis)
print()

# ============================================================================
# 4.4 反模式识别
# ============================================================================

print("🚫 4.4 反模式识别")
print()

anti_patterns = [
    {
        "name": "上帝对象 (God Object)",
        "description": "单个类承担过多职责",
        "example": "将所有内存操作放在一个类中",
        "solution": "拆分为 MemorySystem、RetrievalSystem、InjectionStateMachine 等",
        "status": "已避免",
    },
    {
        "name": "霰弹式修改 (Shotgun Surgery)",
        "description": "一个变更需要修改多个类",
        "example": "添加新记忆类型需要修改多个检索策略",
        "solution": "使用策略模式和抽象接口",
        "status": "已避免",
    },
    {
        "name": "过度工程 (Over-Engineering)",
        "description": "为不存在的需求设计复杂方案",
        "example": "实现过于复杂的检索算法",
        "solution": "根据实际需求选择合适复杂度",
        "status": "需警惕",
    },
    {
        "name": "硬编码配置 (Hard-Coded Configuration)",
        "description": "将配置值硬编码在代码中",
        "example": "内存限制、token限制硬编码",
        "solution": "使用配置文件和参数化设计",
        "status": "部分存在，需改进",
    },
]

print("内存系统中识别和避免的反模式:")
print()
for i, pattern in enumerate(anti_patterns, 1):
    print(f"{i}. {pattern['name']}")
    print(f"   描述: {pattern['description']}")
    print(f"   示例: {pattern['example']}")
    print(f"   解决方案: {pattern['solution']}")
    print(f"   状态: {pattern['status']}")
    print()

# ============================================================================
# 4.5 最佳实践建议
# ============================================================================

print("✅ 4.5 最佳实践建议")
print()

best_practices = """
内存上下文注入系统的最佳实践：

1. 🎯 设计原则
   • 单一职责: 每个类/函数只做一件事
   • 开闭原则: 对扩展开放，对修改关闭
   • 依赖倒置: 依赖抽象，而非具体实现

2. 🔧 实现指导
   • 参数化设计: 所有限制都应作为参数可配置
   • 渐进增强: 从简单实现开始，逐步添加优化
   • 测试驱动: 为每个检索策略编写单元测试

3. 📊 监控与调优
   • 性能指标: 跟踪响应时间、命中率、内存使用
   • A/B测试: 对比不同策略的实际效果
   • 用户反馈: 根据用户满意度调整算法权重

4. 🚀 生产就绪建议
   • 错误处理: 添加全面的异常处理和重试机制
   • 日志记录: 详细记录检索和注入过程
   • 熔断降级: 在系统压力大时自动降级功能
"""

print(best_practices)
print()

# ============================================================================
# 4.6 扩展与演进
# ============================================================================

print("🔮 4.6 扩展与演进")
print()

extension_ideas = """
内存系统的未来扩展方向：

1. 🧠 智能记忆管理
   • 自动摘要: 对长内容生成摘要，减少token占用
   • 重要性学习: 根据使用频率自动调整重要性评分
   • 情感分析: 识别记忆的情感倾向，优先保留积极记忆

2. 🌐 分布式内存
   • 分片存储: 将记忆分布到多个节点
   • 一致性协议: 实现跨节点的记忆同步
   • 故障转移: 自动切换故障节点

3. 🔗 外部系统集成
   • 向量数据库: 集成向量检索提高相关性
   • 知识图谱: 建立记忆之间的关联关系
   • 外部API: 连接外部知识源丰富记忆内容

4. 🛡️ 安全与隐私
   • 加密存储: 敏感记忆内容加密存储
   • 访问控制: 基于角色的记忆访问权限
   • 数据脱敏: 自动识别和脱敏敏感信息
"""

print(extension_ideas)
print()

# ============================================================================
# 4.7 完整系统演示
# ============================================================================

print("🚀 4.7 完整系统演示")
print()

print("现在演示完整的端到端内存上下文注入流程:")
print("-" * 60)

# 创建完整流程演示
print("1. 初始化内存系统")
demo_memory_system = MemorySystem()

print("2. 添加示例记忆")
demo_memories = [
    (
        "用户: 我想学习Python Agent开发",
        MemoryType.SHORT_TERM,
        {"tags": ["python", "agent"]},
    ),
    (
        "助手: Python Agent需要使用LangGraph框架",
        MemoryType.SHORT_TERM,
        {"tags": ["langgraph"]},
    ),
    (
        "LangGraph是构建状态机的强大框架",
        MemoryType.LONG_TERM,
        {"importance": 0.9, "tags": ["langgraph", "state machine"]},
    ),
    ("当前任务: 设计内存上下文注入系统", MemoryType.WORKING, {"importance": 0.8}),
]

for content, mem_type, metadata in demo_memories:
    demo_memory_system.add_memory(content, mem_type, metadata)
    print(f"   添加: {content[:50]}...")

print()

print("3. 创建检索系统")
demo_retrieval = MemoryRetrievalSystem(demo_memory_system)

print("4. 执行记忆检索")
query = "Python Agent开发需要什么？"
results = demo_retrieval.retrieve_memories(query, strategy="hybrid", limit=3)
print(f"   查询: '{query}'")
print(f"   检索结果:")
for i, item in enumerate(results, 1):
    print(f"     {i}. {item.content[:60]}...")

print()

print("5. 执行上下文注入")
demo_state_machine = ContextInjectionStateMachine(demo_memory_system)
final_prompt = demo_state_machine.run(max_tokens=400)
print(f"   生成提示长度: {len(final_prompt)} 字符")
print(f"   使用token数: {demo_state_machine.current_tokens}")

print()

print("6. 最终系统统计")
demo_memory_system.print_stats()

print("-" * 60)
print()

# ============================================================================
# 总结与作业
# ============================================================================

print("🎓 课程总结")
print()

summary = """
本课程深入讲解了内存上下文注入机制的完整设计与实现：

🔑 核心知识点:
1. 三层内存架构: 短期、长期、工作记忆的设计原理
2. 上下文注入流程: 格式化→过滤→排序→修剪→注入的状态机
3. 记忆检索策略: 关键词、时间、相关性及混合检索算法
4. 系统架构分析: 设计模式、性能优化、最佳实践

💡 关键技能:
• 能够设计合理的内存系统架构
• 能够实现上下文注入的完整流程
• 能够选择合适的记忆检索策略
• 能够进行系统性能分析和优化

🚀 下一步:
1. 完成课后练习，巩固所学知识
2. 尝试扩展功能，实现智能记忆管理
3. 在实际项目中应用内存上下文注入
"""

print(summary)
print()

print("=" * 60)
print("🎉 Day 3 Lesson 10: 内存上下文注入机制 - 课堂演示完成!")
print("=" * 60)

# 主程序入口
if __name__ == "__main__":
    print()
    print("🏁 运行完整演示 (使用命令行参数控制)")
    print()

    import sys

    # 简单的命令行参数解析
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("用法: python memory_context_demo.py [选项]")
            print("选项:")
            print("  --part N       运行特定部分 (1-4)")
            print("  --tokens N     设置token限制 (默认: 500)")
            print("  --query TEXT   设置测试查询")
            print("  --help         显示此帮助")
        elif sys.argv[1] == "--part":
            part = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            print(f"运行第 {part} 部分")
            # 这里可以添加按部分运行的逻辑
        else:
            print(f"未知参数: {sys.argv[1]}")
    else:
        print("✅ 演示代码运行完成!")
        print(f"总代码行数: {sum(1 for line in open(__file__) if line.strip())}")
        print("👨‍🏫 教师提示: 建议逐部分讲解，重点讲解设计决策和权衡")
        print("👨‍🎓 学生提示: 运行代码，观察输出，修改参数实验不同效果")
