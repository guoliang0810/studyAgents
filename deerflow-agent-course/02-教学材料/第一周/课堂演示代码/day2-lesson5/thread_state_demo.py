#!/usr/bin/env python3
"""
ThreadState状态机设计演示代码
Day 2 第5节课：课堂演示代码

本代码演示DeerFlow ThreadState状态机的设计原理和实现，包括：
1. ThreadState结构定义与类型注解
2. Reducer函数设计与合并逻辑
3. 状态机工作流程与状态流转
4. 状态设计模式分析与应用

通过模拟实现，深入理解状态机在AI Agent中的作用和价值。
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, TypedDict, Annotated, NotRequired
from dataclasses import dataclass, field
from enum import Enum
import time
from datetime import datetime
from copy import deepcopy
import random

# ============================================================================
# 第一部分：ThreadState结构模拟
# ============================================================================


class MessageRole(str, Enum):
    """消息角色枚举"""

    HUMAN = "human"
    AI = "ai"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class Message:
    """消息类（简化版）"""

    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建"""
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class Artifact:
    """生成文件类"""

    id: str
    type: str  # "code", "text", "image", "data"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"Artifact(id={self.id}, type={self.type}, size={len(self.content)})"


@dataclass
class TodoItem:
    """待办事项类"""

    id: str
    description: str
    status: str  # "pending", "in_progress", "completed", "failed"
    priority: int = 1  # 1-5，1最高
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def mark_completed(self):
        """标记为完成"""
        self.status = "completed"
        self.updated_at = datetime.now()

    def mark_in_progress(self):
        """标记为进行中"""
        self.status = "in_progress"
        self.updated_at = datetime.now()


# ============================================================================
# Reducer函数定义（状态合并逻辑）
# ============================================================================


def merge_messages(existing: List[Message], new: List[Message]) -> List[Message]:
    """合并消息列表"""
    # 消息合并逻辑：简单追加，实际中可能需要去重或特殊处理
    result = existing.copy()
    result.extend(new)

    # 保持时间顺序（假设消息按时间顺序到达）
    result.sort(key=lambda msg: msg.timestamp)

    # 限制最大消息数（防止内存爆炸）
    max_messages = 100
    if len(result) > max_messages:
        # 保留最新的max_messages条消息
        result = result[-max_messages:]

    return result


def merge_artifacts(existing: List[Artifact], new: List[Artifact]) -> List[Artifact]:
    """合并生成文件列表"""
    result = existing.copy()

    for artifact in new:
        # 检查是否已存在相同ID的artifact
        existing_ids = {a.id for a in result}
        if artifact.id not in existing_ids:
            result.append(artifact)
        else:
            # 已存在，更新内容（假设新版本覆盖旧版本）
            for i, existing_artifact in enumerate(result):
                if existing_artifact.id == artifact.id:
                    result[i] = artifact
                    break

    # 按创建时间排序
    result.sort(key=lambda a: a.created_at)
    return result


def merge_todos(existing: List[TodoItem], new: List[TodoItem]) -> List[TodoItem]:
    """合并待办事项列表"""
    result = existing.copy()

    for todo in new:
        # 检查是否已存在相同ID的todo
        existing_ids = {t.id for t in result}
        if todo.id not in existing_ids:
            result.append(todo)
        else:
            # 已存在，更新状态（保留最新状态）
            for i, existing_todo in enumerate(result):
                if existing_todo.id == todo.id:
                    # 特殊逻辑：已完成的不再更新为pending
                    if (
                        existing_todo.status == "completed"
                        and todo.status != "completed"
                    ):
                        # 保持完成状态
                        pass
                    else:
                        # 更新为新的状态
                        result[i] = todo
                    break

    # 按优先级和状态排序
    result.sort(
        key=lambda t: (
            t.priority,
            0 if t.status == "pending" else 1 if t.status == "in_progress" else 2,
        )
    )
    return result


def merge_strings(existing: str, new: str) -> str:
    """合并字符串（用于简单字段）"""
    # 如果新值为空，保持原值
    if not new:
        return existing

    # 如果原值为空，使用新值
    if not existing:
        return new

    # 否则，使用新值（覆盖）
    return new


def merge_dicts(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """合并字典（深度合并）"""
    result = existing.copy()

    for key, value in new.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # 递归合并字典
            result[key] = merge_dicts(result[key], value)
        else:
            # 覆盖或添加新值
            result[key] = value

    return result


# ============================================================================
# ThreadState定义（模拟DeerFlow ThreadState）
# ============================================================================


class ThreadState(TypedDict, total=False):
    """
    ThreadState状态定义
    模拟DeerFlow ThreadState结构，展示类型注解和Reducer绑定
    """

    # 必需字段（没有NotRequired注解）
    messages: Annotated[List[Message], "对话历史", merge_messages]

    # 可选字段（使用NotRequired）
    artifacts: NotRequired[Annotated[List[Artifact], "生成文件", merge_artifacts]]
    todos: NotRequired[Annotated[List[TodoItem], "待办事项", merge_todos]]
    viewed_images: NotRequired[Annotated[List[str], "已查看图片", merge_messages]]

    # 简单字段
    current_step: NotRequired[Annotated[str, "当前步骤", merge_strings]]
    reasoning: NotRequired[Annotated[str, "推理过程", merge_strings]]

    # 元数据字段
    metadata: NotRequired[Annotated[Dict[str, Any], "元数据", merge_dicts]]
    created_at: NotRequired[Annotated[datetime, "创建时间", merge_strings]]
    updated_at: NotRequired[Annotated[datetime, "更新时间", merge_strings]]

    # 自定义扩展字段（演示如何扩展）
    # user_preferences: NotRequired[Annotated[Dict[str, Any], "用户偏好", merge_dicts]]
    # conversation_summary: NotRequired[Annotated[str, "对话摘要", merge_strings]]


class ThreadStateManager:
    """ThreadState管理器"""

    # Reducer函数映射
    REDUCERS = {
        "messages": merge_messages,
        "artifacts": merge_artifacts,
        "todos": merge_todos,
        "viewed_images": merge_messages,  # 复用相同的合并逻辑
        "current_step": merge_strings,
        "reasoning": merge_strings,
        "metadata": merge_dicts,
        "created_at": merge_strings,
        "updated_at": merge_strings,
    }

    @staticmethod
    def create_initial_state() -> ThreadState:
        """创建初始状态"""
        return {
            "messages": [],
            "artifacts": [],
            "todos": [],
            "viewed_images": [],
            "current_step": "init",
            "reasoning": "",
            "metadata": {
                "version": "1.0",
                "created_by": "ThreadStateDemo",
                "environment": "development",
            },
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

    @staticmethod
    def merge_states(
        existing_state: ThreadState, new_state: ThreadState
    ) -> ThreadState:
        """合并两个状态"""
        result = existing_state.copy()

        for key, new_value in new_state.items():
            if key in result:
                # 获取对应的Reducer函数
                reducer = ThreadStateManager.REDUCERS.get(key)
                if reducer:
                    # 应用Reducer合并逻辑
                    result[key] = reducer(result[key], new_value)
                else:
                    # 没有Reducer，直接覆盖
                    result[key] = new_value
            else:
                # 新字段，直接添加
                result[key] = new_value

        # 更新更新时间
        result["updated_at"] = datetime.now()

        return result

    @staticmethod
    def apply_operation(
        state: ThreadState, operation_type: str, operation_data: Dict[str, Any]
    ) -> ThreadState:
        """应用操作到状态"""
        new_state_part = {}

        if operation_type == "add_message":
            new_state_part["messages"] = [
                Message(
                    role=MessageRole(operation_data.get("role", "human")),
                    content=operation_data["content"],
                )
            ]

        elif operation_type == "add_artifact":
            new_state_part["artifacts"] = [
                Artifact(
                    id=operation_data.get("id", f"artifact_{int(time.time())}"),
                    type=operation_data.get("type", "text"),
                    content=operation_data["content"],
                    metadata=operation_data.get("metadata", {}),
                )
            ]

        elif operation_type == "add_todo":
            new_state_part["todos"] = [
                TodoItem(
                    id=operation_data.get("id", f"todo_{int(time.time())}"),
                    description=operation_data["description"],
                    status=operation_data.get("status", "pending"),
                    priority=operation_data.get("priority", 1),
                )
            ]

        elif operation_type == "update_step":
            new_state_part["current_step"] = operation_data["step"]
            new_state_part["reasoning"] = operation_data.get("reasoning", "")

        elif operation_type == "mark_todo_completed":
            # 特殊操作：更新现有todo
            todo_id = operation_data["todo_id"]
            updated_todos = []

            for todo in state.get("todos", []):
                if todo.id == todo_id:
                    todo_copy = deepcopy(todo)
                    todo_copy.mark_completed()
                    updated_todos.append(todo_copy)
                else:
                    updated_todos.append(todo)

            new_state_part["todos"] = updated_todos

        else:
            raise ValueError(f"未知操作类型: {operation_type}")

        # 合并到现有状态
        return ThreadStateManager.merge_states(state, new_state_part)

    @staticmethod
    def print_state_summary(state: ThreadState, title: str = "状态摘要"):
        """打印状态摘要"""
        print(f"\n{'=' * 60}")
        print(f"📊 {title}")
        print(f"{'=' * 60}")

        print(f"📝 消息数量: {len(state.get('messages', []))}")
        print(f"📁 生成文件: {len(state.get('artifacts', []))}")
        print(f"✅ 待办事项: {len(state.get('todos', []))}")
        print(f"🖼️  查看图片: {len(state.get('viewed_images', []))}")
        print(f"📍 当前步骤: {state.get('current_step', 'N/A')}")
        print(f"🧠 推理长度: {len(state.get('reasoning', ''))} 字符")
        print(f"📅 创建时间: {state.get('created_at', 'N/A')}")
        print(f"🔄 更新时间: {state.get('updated_at', 'N/A')}")

        # 待办事项状态统计
        todos = state.get("todos", [])
        if todos:
            status_counts = {}
            for todo in todos:
                status_counts[todo.status] = status_counts.get(todo.status, 0) + 1

            print(
                f"📋 待办状态: {', '.join([f'{status}:{count}' for status, count in status_counts.items()])}"
            )

        print(f"{'=' * 60}")

    @staticmethod
    def visualize_state_flow(states: List[ThreadState]):
        """可视化状态流转"""
        print(f"\n{'=' * 70}")
        print("🔄 状态流转可视化")
        print(f"{'=' * 70}")

        for i, state in enumerate(states):
            step = state.get("current_step", f"step_{i}")
            msg_count = len(state.get("messages", []))
            todo_count = len(state.get("todos", []))
            artifact_count = len(state.get("artifacts", []))

            print(f"┌─ 状态 {i + 1}: {step}")
            print(
                f"│   消息: {msg_count}条 | 待办: {todo_count}个 | 文件: {artifact_count}个"
            )

            # 显示最后一条消息（如果有）
            messages = state.get("messages", [])
            if messages:
                last_msg = messages[-1]
                print(
                    f"│   最后消息: [{last_msg.role.value}] {last_msg.content[:50]}..."
                )

            # 显示进行中的待办（如果有）
            todos = state.get("todos", [])
            in_progress = [t for t in todos if t.status == "in_progress"]
            if in_progress:
                print(f"│   进行中: {in_progress[0].description[:40]}...")

            if i < len(states) - 1:
                print(f"│   ↓")

        print(f"└─ 最终状态")
        print(f"{'=' * 70}")


# ============================================================================
# 第二部分：状态机工作流程演示
# ============================================================================


class AgentStateMachine:
    """Agent状态机"""

    def __init__(self, initial_state: Optional[ThreadState] = None):
        self.state_history: List[ThreadState] = []
        self.current_state = initial_state or ThreadStateManager.create_initial_state()
        self.state_history.append(deepcopy(self.current_state))

    def apply_operation(
        self, operation_type: str, operation_data: Dict[str, Any]
    ) -> ThreadState:
        """应用操作并记录历史"""
        self.current_state = ThreadStateManager.apply_operation(
            self.current_state, operation_type, operation_data
        )
        self.state_history.append(deepcopy(self.current_state))
        return self.current_state

    def run_planning_phase(self) -> None:
        """运行规划阶段"""
        print("\n🔍 阶段1: 任务规划")
        print("-" * 40)

        # 添加系统消息
        self.apply_operation(
            "add_message",
            {
                "role": "system",
                "content": "你是一个旅行规划助手，请帮助用户规划一次北京三日游。",
            },
        )

        # 添加用户消息
        self.apply_operation(
            "add_message",
            {
                "role": "human",
                "content": "我想规划一次北京三日游，请帮我制定详细的行程安排。",
            },
        )

        # 添加待办事项
        self.apply_operation(
            "add_todo",
            {
                "id": "todo_1",
                "description": "分析用户需求，确定旅行主题和预算范围",
                "status": "pending",
                "priority": 1,
            },
        )

        self.apply_operation(
            "add_todo",
            {
                "id": "todo_2",
                "description": "设计三日游行程大纲，包括主要景点和活动",
                "status": "pending",
                "priority": 2,
            },
        )

        self.apply_operation(
            "add_todo",
            {
                "id": "todo_3",
                "description": "提供交通、住宿、餐饮建议",
                "status": "pending",
                "priority": 3,
            },
        )

        self.apply_operation(
            "add_todo",
            {
                "id": "todo_4",
                "description": "生成最终行程文档",
                "status": "pending",
                "priority": 4,
            },
        )

        # 更新当前步骤
        self.apply_operation(
            "update_step",
            {
                "step": "planning",
                "reasoning": "用户请求北京三日游规划，需要分析需求、设计行程、提供建议、生成文档。",
            },
        )

        ThreadStateManager.print_state_summary(self.current_state, "规划阶段完成")

    def run_execution_phase(self) -> None:
        """运行执行阶段"""
        print("\n🔧 阶段2: 任务执行")
        print("-" * 40)

        # 标记第一个待办为进行中
        self.apply_operation("mark_todo_completed", {"todo_id": "todo_1"})

        # 添加AI回复
        self.apply_operation(
            "add_message",
            {
                "role": "ai",
                "content": "好的，我将为您规划一次精彩的北京三日游。首先分析您的需求：您可能对历史文化、美食体验、现代都市都有兴趣。预算范围中等，希望体验地道北京生活。",
            },
        )

        # 添加生成文件（行程大纲）
        self.apply_operation(
            "add_artifact",
            {
                "id": "artifact_1",
                "type": "text",
                "content": "# 北京三日游行程大纲\n\n## 第一天：历史文化之旅\n- 上午：天安门广场、故宫博物院\n- 下午：景山公园、南锣鼓巷\n- 晚上：王府井小吃街\n\n## 第二天：皇家园林与现代都市\n- 上午：颐和园\n- 下午：鸟巢、水立方\n- 晚上：三里屯太古里\n\n## 第三天：长城与老北京\n- 全天：八达岭长城\n- 晚上：老舍茶馆、烤鸭晚餐",
                "metadata": {"format": "markdown", "version": "1.0"},
            },
        )

        # 标记第二个待办为进行中
        self.apply_operation("mark_todo_completed", {"todo_id": "todo_2"})

        # 更新当前步骤
        self.apply_operation(
            "update_step",
            {
                "step": "execution",
                "reasoning": "已完成需求分析和行程大纲设计，正在提供详细建议。",
            },
        )

        ThreadStateManager.print_state_summary(self.current_state, "执行阶段完成")

    def run_review_phase(self) -> None:
        """运行审查阶段"""
        print("\n📋 阶段3: 结果审查")
        print("-" * 40)

        # 添加用户反馈
        self.apply_operation(
            "add_message",
            {
                "role": "human",
                "content": "行程大纲很好，但我想增加一些美食体验，比如北京烤鸭和豆汁儿。",
            },
        )

        # 添加AI回复
        self.apply_operation(
            "add_message",
            {
                "role": "ai",
                "content": "好的，我会在行程中增加美食体验。第二天午餐安排全聚德烤鸭，第三天早餐尝试豆汁儿和焦圈。另外，我还会为您推荐几家地道的北京小吃店。",
            },
        )

        # 更新生成文件
        self.apply_operation(
            "add_artifact",
            {
                "id": "artifact_2",
                "type": "text",
                "content": "# 北京美食推荐\n\n## 必吃美食\n1. 北京烤鸭：全聚德、便宜坊\n2. 豆汁儿+焦圈：老磁器口豆汁店\n3. 炸酱面：海碗居\n4. 涮羊肉：东来顺\n5. 驴打滚、艾窝窝：护国寺小吃\n\n## 行程调整\n- 第二天午餐：全聚德烤鸭（王府井店）\n- 第三天早餐：老磁器口豆汁店\n- 增加：牛街清真小吃体验",
                "metadata": {"format": "markdown", "version": "1.1"},
            },
        )

        # 标记第三个待办为进行中
        self.apply_operation("mark_todo_completed", {"todo_id": "todo_3"})

        # 更新当前步骤
        self.apply_operation(
            "update_step",
            {
                "step": "review",
                "reasoning": "根据用户反馈增加了美食体验，正在完善最终文档。",
            },
        )

        ThreadStateManager.print_state_summary(self.current_state, "审查阶段完成")

    def run_completion_phase(self) -> None:
        """运行完成阶段"""
        print("\n🎉 阶段4: 任务完成")
        print("-" * 40)

        # 添加最终AI回复
        self.apply_operation(
            "add_message",
            {
                "role": "ai",
                "content": "北京三日游行程规划已完成！我已为您准备了详细的行程安排、美食推荐、交通和住宿建议。您可以查看生成的文档，如有需要可以进一步调整。",
            },
        )

        # 添加最终文档
        self.apply_operation(
            "add_artifact",
            {
                "id": "artifact_3",
                "type": "text",
                "content": "# 北京三日游完整行程规划\n\n## 行程概览\n- 预算：中等（约3000-5000元）\n- 主题：历史文化+美食体验+现代都市\n- 适合：首次来北京的游客\n\n## 详细安排（见之前文档）\n## 美食推荐（见美食文档）\n## 交通建议：地铁为主，搭配出租车\n## 住宿推荐：王府井或前门附近酒店\n## 注意事项：提前预约故宫门票，避开周一闭馆",
                "metadata": {"format": "markdown", "version": "1.2"},
            },
        )

        # 标记所有待办为完成
        self.apply_operation("mark_todo_completed", {"todo_id": "todo_4"})

        # 添加已查看图片（模拟）
        self.apply_operation(
            "add_message",
            {
                "role": "tool",
                "content": "已查看北京地图、景点图片、美食图片等10张相关图片",
            },
        )

        # 更新当前步骤
        self.apply_operation(
            "update_step",
            {
                "step": "completed",
                "reasoning": "所有任务已完成，用户满意，生成最终文档。",
            },
        )

        ThreadStateManager.print_state_summary(self.current_state, "完成阶段完成")

    def run_full_workflow(self) -> None:
        """运行完整工作流程"""
        print("\n" + "=" * 70)
        print("🚀 开始Agent状态机完整工作流程演示")
        print("=" * 70)

        self.run_planning_phase()
        self.run_execution_phase()
        self.run_review_phase()
        self.run_completion_phase()

        # 可视化状态流转
        ThreadStateManager.visualize_state_flow(self.state_history)

        print("\n🎉 Agent状态机演示完成！")


# ============================================================================
# 第三部分：状态设计模式分析
# ============================================================================


class StateDesignAnalyzer:
    """状态设计分析器"""

    @staticmethod
    def analyze_threadstate_design() -> None:
        """分析ThreadState设计模式"""
        print("\n" + "=" * 70)
        print("🏗️  ThreadState设计模式分析")
        print("=" * 70)

        design_principles = [
            {
                "name": "类型安全",
                "description": "使用TypedDict和类型注解确保状态结构类型安全",
                "benefits": ["编译时检查", "IDE自动补全", "文档化"],
                "implementation": "Python 3.8+ TypedDict, mypy类型检查",
            },
            {
                "name": "可扩展性",
                "description": "通过NotRequired注解支持可选字段，便于扩展",
                "benefits": ["向后兼容", "渐进增强", "场景适配"],
                "implementation": "NotRequired[Annotated[...]] 语法",
            },
            {
                "name": "可合并性",
                "benefits": ["状态更新幂等", "并行操作安全", "历史状态重建"],
                "implementation": "Reducer函数 + Annotated元数据绑定",
            },
            {
                "name": "自描述性",
                "description": "状态字段包含类型、描述、合并逻辑信息",
                "benefits": ["代码即文档", "降低理解成本", "便于维护"],
                "implementation": "Annotated[类型, 描述, Reducer]",
            },
        ]

        print("\n📚 核心设计原则:")
        for principle in design_principles:
            print(f"\n🔹 {principle['name']}:")
            print(f"   {principle['description']}")
            print(f"   优点: {', '.join(principle['benefits'])}")
            print(f"   实现: {principle['implementation']}")

        # 设计对比
        print("\n🔍 设计对比分析:")
        alternatives = [
            ("全局变量", "简单但难以管理，缺乏结构，容易出错"),
            ("数据库", "持久化好但延迟高，不适合实时状态管理"),
            ("事件总线", "解耦好但状态分散，调试困难"),
            ("ThreadState", "类型安全、可合并、自描述，适合Agent状态管理"),
        ]

        for name, desc in alternatives:
            print(f"   • {name}: {desc}")

        # 适用场景
        print("\n🎯 适用场景:")
        scenarios = [
            "多步骤Agent任务（规划→执行→审查→完成）",
            "需要状态持久化和恢复的长时间对话",
            "并行操作需要状态合并的场景",
            "需要强类型检查和自动验证的项目",
        ]

        for i, scenario in enumerate(scenarios, 1):
            print(f"   {i}. {scenario}")

        print("\n" + "=" * 70)

    @staticmethod
    def demonstrate_custom_state_extension() -> None:
        """演示自定义状态扩展"""
        print("\n" + "=" * 70)
        print("🔧 自定义状态字段扩展演示")
        print("=" * 70)

        # 定义自定义Reducer
        def merge_sentiment_scores(
            existing: Dict[str, float], new: Dict[str, float]
        ) -> Dict[str, float]:
            """合并情感分数（取平均值）"""
            result = existing.copy()
            for key, value in new.items():
                if key in result:
                    # 计算平均值
                    result[key] = (result[key] + value) / 2
                else:
                    result[key] = value
            return result

        # 扩展ThreadState
        ExtendedState = TypedDict(
            "ExtendedState",
            {
                "messages": Annotated[List[Message], "对话历史", merge_messages],
                "sentiment_scores": Annotated[
                    Dict[str, float], "情感分数", merge_sentiment_scores
                ],
                "user_feedback": NotRequired[
                    Annotated[List[str], "用户反馈", merge_messages]
                ],
            },
            total=False,
        )

        # 演示使用
        print("\n🎭 扩展状态示例:")
        print("   新增字段: sentiment_scores (情感分数)")
        print("   新增字段: user_feedback (用户反馈)")
        print("   自定义Reducer: merge_sentiment_scores (计算平均值)")

        # 创建扩展状态
        extended_state: ExtendedState = {
            "messages": [Message(role=MessageRole.HUMAN, content="这个产品很好用！")],
            "sentiment_scores": {"product": 0.8, "service": 0.6},
            "user_feedback": ["界面友好", "功能强大"],
        }

        print(f"\n📊 扩展状态内容:")
        print(f"   消息: {len(extended_state['messages'])}条")
        print(f"   情感分数: {extended_state['sentiment_scores']}")
        print(f"   用户反馈: {extended_state['user_feedback']}")

        print("\n💡 扩展指南:")
        print("   1. 定义新的Reducer函数（如果需要特殊合并逻辑）")
        print("   2. 使用TypedDict定义扩展状态类型")
        print("   3. 使用Annotated绑定类型、描述和Reducer")
        print("   4. 使用NotRequired标记可选字段")
        print("   5. 更新状态管理器支持新字段")

        print("\n" + "=" * 70)


# ============================================================================
# 第四部分：最佳实践与常见错误
# ============================================================================


class StateManagementBestPractices:
    """状态管理最佳实践"""

    @staticmethod
    def demonstrate_best_practices() -> None:
        """演示最佳实践"""
        print("\n" + "=" * 70)
        print("📚 状态管理最佳实践")
        print("=" * 70)

        practices = [
            (
                "1. 保持Reducer幂等性",
                "同一操作多次应用结果相同",
                "def merge_messages(existing, new):\n    # 去重逻辑确保幂等\n    return list(dict.fromkeys(existing + new))",
            ),
            (
                "2. 设计可序列化状态",
                "状态应能JSON序列化，便于持久化和传输",
                "class Message:\n    def to_dict(self):\n        return {\n            'role': self.role.value,\n            'content': self.content\n        }",
            ),
            (
                "3. 限制状态大小",
                "防止状态无限增长导致内存问题",
                "def merge_messages(existing, new):\n    # 保留最近100条消息\n    combined = existing + new\n    return combined[-100:] if len(combined) > 100 else combined",
            ),
            (
                "4. 提供状态验证",
                "确保状态符合业务规则",
                "def validate_state(state):\n    if 'messages' not in state:\n        raise ValueError('状态必须包含messages字段')",
            ),
            (
                "5. 实现状态版本迁移",
                "支持状态结构升级",
                "def migrate_state_v1_to_v2(state_v1):\n    state_v2 = state_v1.copy()\n    state_v2['metadata'] = state_v1.get('metadata', {})\n    state_v2['metadata']['version'] = '2.0'\n    return state_v2",
            ),
            (
                "6. 记录状态变更历史",
                "便于调试和审计",
                "class StateMachine:\n    def __init__(self):\n        self.state_history = []\n        \n    def apply_operation(self, op):\n        new_state = merge_states(self.state, op)\n        self.state_history.append({\n            'timestamp': datetime.now(),\n            'operation': op,\n            'new_state': new_state\n        })",
            ),
        ]

        for title, description, example in practices:
            print(f"\n{title}:")
            print(f"   {description}")
            print(f"   示例:\n   {example}")

        print("\n⚠️ 常见错误与避免方法:")
        errors = [
            ("状态字段过多", "导致状态臃肿，难以维护", "按领域分组，使用嵌套结构"),
            ("Reducer过于复杂", "难以测试和调试", "保持Reducer简单，单一职责"),
            ("缺乏类型检查", "运行时错误难以排查", "使用mypy进行类型检查"),
            ("状态并发修改", "导致数据竞争和不一致", "使用锁或不可变数据结构"),
            ("忽略状态序列化", "持久化和传输困难", "设计时考虑序列化需求"),
        ]

        for error, cause, solution in errors:
            print(f"   • {error}: {cause} → 解决方案: {solution}")

        print("\n" + "=" * 70)


# ============================================================================
# 主程序
# ============================================================================


def main():
    """主函数：运行完整的ThreadState演示"""
    print("=" * 80)
    print("🎓 Day 2 第5节课：ThreadState状态机设计演示")
    print("=" * 80)

    try:
        # 第一部分：基础结构演示
        print("\n📦 第一部分：ThreadState基础结构")
        print("-" * 60)

        # 创建初始状态
        initial_state = ThreadStateManager.create_initial_state()
        ThreadStateManager.print_state_summary(initial_state, "初始状态")

        # 演示状态合并
        print("\n🔄 演示状态合并:")
        state1 = ThreadStateManager.create_initial_state()
        state2 = ThreadStateManager.apply_operation(
            state1, "add_message", {"role": "human", "content": "你好，世界！"}
        )
        ThreadStateManager.print_state_summary(state2, "添加消息后的状态")

        # 第二部分：状态机工作流程
        print("\n\n🤖 第二部分：Agent状态机工作流程")
        print("-" * 60)

        state_machine = AgentStateMachine()
        state_machine.run_full_workflow()

        # 第三部分：设计模式分析
        print("\n\n🏗️ 第三部分：状态设计模式分析")
        print("-" * 60)

        StateDesignAnalyzer.analyze_threadstate_design()
        StateDesignAnalyzer.demonstrate_custom_state_extension()

        # 第四部分：最佳实践
        print("\n\n📚 第四部分：状态管理最佳实践")
        print("-" * 60)

        StateManagementBestPractices.demonstrate_best_practices()

        print("\n" + "=" * 80)
        print("🎉 ThreadState状态机设计演示完成！")
        print("💡 关键收获:")
        print("   1. ThreadState提供类型安全的状态管理")
        print("   2. Reducer函数确保状态合并的幂等性和一致性")
        print("   3. 状态机模式使Agent工作流程清晰可控")
        print("   4. 良好的状态设计是AI Agent架构的基石")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
