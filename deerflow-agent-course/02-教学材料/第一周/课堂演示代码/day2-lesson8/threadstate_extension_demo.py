#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 2 Lesson 8: 实战扩展ThreadState (Practical: Extending ThreadState)
课堂演示代码 - ThreadState扩展与学习助手Agent实现

本文件展示了完整的ThreadState扩展方案，包含四个部分：
1. 业务需求分析与状态字段识别 - 从学习助手业务推导状态字段
2. Reducer函数设计与实现 - 实现状态合并逻辑、边界处理、数据验证
3. ThreadState扩展与兼容性设计 - 展示继承ThreadState、添加Annotated字段、兼容性处理
4. 完整Agent实现与工程化分析 - 构建学习助手Agent，展示状态更新、业务逻辑分离、工程化最佳实践

教学目标：
- 掌握基于实际业务需求扩展ThreadState的完整流程和方法论
- 理解状态扩展设计中的关注点分离和领域建模原则
- 了解扩展状态与原有状态的兼容性考虑和最佳实践

作者：张老师（10年AI系统架构经验，DeerFlow核心贡献者）
版本：v1.0
创建日期：2024年3月27日
"""

import asyncio
import time
import json
import logging
import random
from abc import ABC, abstractmethod
from typing import (
    Dict,
    List,
    Optional,
    Any,
    Type,
    Union,
    Set,
    Tuple,
    Annotated,
    NotRequired,
)
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from datetime import datetime, timedelta
from collections import OrderedDict, defaultdict
from functools import wraps
import inspect

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("threadstate_extension.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 第一部分：业务需求分析与状态字段识别
# ============================================================================
print("=" * 60)
print("第一部分：业务需求分析与状态字段识别")
print("=" * 60)


class BusinessRequirementAnalyzer:
    """
    业务需求分析器 - 演示如何从业务需求推导状态字段

    学习助手业务需求分析：
    1. 跟踪学习进度：学习主题、学习时长、掌握程度
    2. 个性化教学：根据掌握程度调整教学内容和难度
    3. 复习管理：安排复习计划，避免遗忘曲线
    """

    def __init__(self):
        self.requirements = []
        self.state_fields = []

    def analyze_learning_assistant(self) -> Dict[str, Any]:
        """分析学习助手业务需求，推导状态字段"""
        print("\n1.1 业务需求分析过程：")
        print("  学习助手核心业务场景：")
        print("  - 用户学习Python基础，需要跟踪学习进度")
        print("  - 根据掌握程度调整教学难度和内容")
        print("  - 安排定期复习，巩固学习效果")

        # 核心需求推导
        requirements = [
            {
                "id": "REQ-001",
                "description": "跟踪学习主题",
                "rationale": "了解用户正在学习的内容，提供针对性教学",
                "state_implication": "需要存储当前学习主题",
            },
            {
                "id": "REQ-002",
                "description": "累计学习时长",
                "rationale": "评估学习投入程度，调整学习计划",
                "state_implication": "需要累加学习时间",
            },
            {
                "id": "REQ-003",
                "description": "评估掌握程度",
                "rationale": "了解学习效果，调整教学策略",
                "state_implication": "需要记录掌握程度分数",
            },
            {
                "id": "REQ-004",
                "description": "管理复习计划",
                "rationale": "安排定期复习，避免遗忘",
                "state_implication": "需要存储复习计划列表",
            },
        ]

        self.requirements = requirements

        print("\n  推导出的业务需求：")
        for req in requirements:
            print(f"  {req['id']}: {req['description']}")
            print(f"     理由: {req['rationale']}")
            print(f"     状态含义: {req['state_implication']}")

        return requirements

    def derive_state_fields(
        self, requirements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """从业务需求推导状态字段定义"""
        print("\n1.2 状态字段推导：")

        # 字段推导映射
        field_mapping = {
            "REQ-001": {
                "field_name": "learning_topic",
                "type": "str",
                "default_value": "",
                "update_strategy": "latest",
                "description": "当前学习主题",
            },
            "REQ-002": {
                "field_name": "study_duration",
                "type": "int",
                "default_value": 0,
                "update_strategy": "accumulate",
                "description": "累计学习时长（分钟）",
            },
            "REQ-003": {
                "field_name": "mastery_level",
                "type": "int",
                "default_value": 0,
                "update_strategy": "latest_with_range",
                "range": "0-100",
                "description": "掌握程度（0-100）",
            },
            "REQ-004": {
                "field_name": "review_schedule",
                "type": "List[StudyRecord]",
                "default_value": [],
                "update_strategy": "list_merge",
                "description": "复习计划列表",
            },
        }

        state_fields = []
        for req in requirements:
            if req["id"] in field_mapping:
                field_def = field_mapping[req["id"]]
                field_def["source_requirement"] = req["description"]
                state_fields.append(field_def)

                print(f"  {req['id']} → {field_def['field_name']}:")
                print(f"     类型: {field_def['type']}")
                print(f"     默认值: {field_def['default_value']}")
                print(f"     更新策略: {field_def['update_strategy']}")
                print(f"     描述: {field_def['description']}")

        self.state_fields = state_fields

        # 显示领域建模结果
        print("\n1.3 领域建模结果：")
        print("  学习助手核心领域模型：")
        print("  - LearningSession: 学习会话，包含主题、时长、时间")
        print("  - MasteryAssessment: 掌握程度评估，包含分数、评估时间")
        print("  - ReviewPlan: 复习计划，包含复习时间、主题、状态")
        print("  - LearningProgress: 学习进度聚合，包含所有状态字段")

        return state_fields

    def generate_design_document(self) -> str:
        """生成设计文档"""
        doc = "# 学习助手ThreadState扩展设计文档\n\n"

        doc += "## 1. 业务需求分析\n"
        for req in self.requirements:
            doc += f"- **{req['id']}**: {req['description']}\n"
            doc += f"  - 理由: {req['rationale']}\n"
            doc += f"  - 状态含义: {req['state_implication']}\n"

        doc += "\n## 2. 状态字段设计\n"
        for field_def in self.state_fields:
            doc += f"- **{field_def['field_name']}** ({field_def['type']})\n"
            doc += f"  - 来源需求: {field_def['source_requirement']}\n"
            doc += f"  - 默认值: {field_def['default_value']}\n"
            doc += f"  - 更新策略: {field_def['update_strategy']}\n"
            doc += f"  - 描述: {field_def['description']}\n"

        return doc


# ============================================================================
# 第二部分：Reducer函数设计与实现
# ============================================================================
print("\n" + "=" * 60)
print("第二部分：Reducer函数设计与实现")
print("=" * 60)


@dataclass
class StudyRecord:
    """学习记录数据类"""

    topic: str
    duration_minutes: int
    timestamp: datetime
    mastery_score: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "topic": self.topic,
            "duration_minutes": self.duration_minutes,
            "timestamp": self.timestamp.isoformat(),
            "mastery_score": self.mastery_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StudyRecord":
        """从字典创建"""
        return cls(
            topic=data["topic"],
            duration_minutes=data["duration_minutes"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            mastery_score=data.get("mastery_score"),
        )


def merge_duration(current: int, update: int) -> int:
    """
    学习时长合并函数 - 累加策略

    参数:
        current: 当前状态中的时长
        update: 更新中的时长

    返回:
        合并后的时长

    设计考虑:
        1. 时长应该累加，反映总学习时间
        2. 需要处理负值等异常情况
        3. 考虑整数溢出问题（Python自动处理大整数）
    """
    print(f"  合并学习时长: {current} + {update} = {current + update}")

    # 输入验证
    if not isinstance(update, int):
        raise TypeError(f"学习时长必须是整数，收到: {type(update)}")

    if update < 0:
        # 可以记录警告，但允许负值（可能表示修正）
        logger.warning(f"学习时长为负值: {update}")

    # 累加合并
    return current + update


def merge_mastery(current: int, update: int) -> int:
    """
    掌握程度合并函数 - 取最新值，限制范围

    参数:
        current: 当前状态中的掌握程度
        update: 更新中的掌握程度

    返回:
        合并后的掌握程度

    设计考虑:
        1. 掌握程度应该取最新值，反映最新评估
        2. 需要限制在0-100范围内
        3. 考虑异常值处理
    """
    print(f"  合并掌握程度: 当前={current}, 更新={update}")

    # 输入验证
    if not isinstance(update, int):
        raise TypeError(f"掌握程度必须是整数，收到: {type(update)}")

    # 范围限制
    if update < 0:
        logger.warning(f"掌握程度低于最小值，调整为0: {update}")
        update = 0
    elif update > 100:
        logger.warning(f"掌握程度超过最大值，调整为100: {update}")
        update = 100

    # 取最新值
    return update


def merge_review_schedule(
    current: List[StudyRecord], update: List[StudyRecord]
) -> List[StudyRecord]:
    """
    复习计划合并函数 - 列表合并，去重排序

    参数:
        current: 当前状态中的复习计划列表
        update: 更新中的复习计划列表

    返回:
        合并后的复习计划列表

    设计考虑:
        1. 列表合并，保留所有唯一记录
        2. 按时间排序，确保复习顺序合理
        3. 去重策略：相同主题和时间的记录视为重复
    """
    print(f"  合并复习计划: 当前{len(current)}条, 更新{len(update)}条")

    # 输入验证
    if not isinstance(update, list):
        raise TypeError(f"复习计划必须是列表，收到: {type(update)}")

    # 创建合并列表
    merged = current.copy()

    # 添加更新记录，去重
    for record in update:
        # 检查是否已存在相同记录
        duplicate = False
        for existing in merged:
            if (
                existing.topic == record.topic
                and existing.timestamp == record.timestamp
            ):
                duplicate = True
                break

        if not duplicate:
            merged.append(record)

    # 按时间排序
    merged.sort(key=lambda x: x.timestamp)

    print(f"  合并后: {len(merged)}条记录")
    return merged


class ReducerTestSuite:
    """Reducer函数测试套件"""

    @staticmethod
    def test_merge_duration():
        """测试学习时长合并"""
        print("\n2.1 学习时长合并测试:")

        # 正常累加
        result = merge_duration(60, 90)
        assert result == 150, f"预期150，实际{result}"
        print("  ✓ 正常累加: 60 + 90 = 150")

        # 负值处理
        result = merge_duration(100, -20)
        assert result == 80, f"预期80，实际{result}"
        print("  ✓ 负值累加: 100 + (-20) = 80")

        # 零值
        result = merge_duration(50, 0)
        assert result == 50, f"预期50，实际{result}"
        print("  ✓ 零值累加: 50 + 0 = 50")

        print("  所有学习时长合并测试通过!")

    @staticmethod
    def test_merge_mastery():
        """测试掌握程度合并"""
        print("\n2.2 掌握程度合并测试:")

        # 正常最新值
        result = merge_mastery(70, 85)
        assert result == 85, f"预期85，实际{result}"
        print("  ✓ 正常最新值: 70 → 85")

        # 范围限制 - 过低
        result = merge_mastery(80, -10)
        assert result == 0, f"预期0，实际{result}"
        print("  ✓ 过低值限制: -10 → 0")

        # 范围限制 - 过高
        result = merge_mastery(60, 150)
        assert result == 100, f"预期100，实际{result}"
        print("  ✓ 过高值限制: 150 → 100")

        # 相同值
        result = merge_mastery(75, 75)
        assert result == 75, f"预期75，实际{result}"
        print("  ✓ 相同值: 75 → 75")

        print("  所有掌握程度合并测试通过!")

    @staticmethod
    def test_merge_review_schedule():
        """测试复习计划合并"""
        print("\n2.3 复习计划合并测试:")

        # 创建测试记录
        record1 = StudyRecord(
            topic="Python基础",
            duration_minutes=60,
            timestamp=datetime(2024, 3, 26, 10, 0),
            mastery_score=70,
        )

        record2 = StudyRecord(
            topic="Python函数",
            duration_minutes=90,
            timestamp=datetime(2024, 3, 27, 14, 0),
            mastery_score=85,
        )

        record3 = StudyRecord(
            topic="Python基础",  # 重复主题，不同时间
            duration_minutes=45,
            timestamp=datetime(2024, 3, 28, 9, 0),
            mastery_score=80,
        )

        # 空列表合并
        result = merge_review_schedule([], [record1, record2])
        assert len(result) == 2, f"预期2条，实际{len(result)}"
        print("  ✓ 空列表合并: 0 + 2 = 2")

        # 列表去重合并
        current = [record1]
        update = [record1, record2, record3]  # record1重复
        result = merge_review_schedule(current, update)
        assert len(result) == 3, f"预期3条，实际{len(result)}"
        print("  ✓ 列表去重合并: 1 + 3(去重1) = 3")

        # 排序测试
        assert result[0].topic == "Python基础", "第一条应为Python基础"
        assert result[0].timestamp == datetime(2024, 3, 26, 10, 0), "时间排序错误"
        print("  ✓ 时间排序: 按时间顺序排列")

        print("  所有复习计划合并测试通过!")

    @staticmethod
    def run_all_tests():
        """运行所有测试"""
        print("\n运行Reducer函数测试套件...")
        ReducerTestSuite.test_merge_duration()
        ReducerTestSuite.test_merge_mastery()
        ReducerTestSuite.test_merge_review_schedule()
        print("\n所有Reducer函数测试通过!")


# ============================================================================
# 第三部分：ThreadState扩展与兼容性设计
# ============================================================================
print("\n" + "=" * 60)
print("第三部分：ThreadState扩展与兼容性设计")
print("=" * 60)


class BaseThreadState:
    """
    基础ThreadState类（模拟DeerFlow的ThreadState）

    在实际DeerFlow中，ThreadState是LangGraph的状态基类
    这里我们模拟其核心功能，展示扩展模式
    """

    def __init__(self, values: Optional[Dict[str, Any]] = None):
        self._values = values or {}

    def get(self, key: str, default: Any = None) -> Any:
        """获取状态值"""
        return self._values.get(key, default)

    def set(self, key: str, value: Any):
        """设置状态值"""
        self._values[key] = value

    def update(self, updates: Dict[str, Any]):
        """批量更新状态值"""
        self._values.update(updates)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self._values.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseThreadState":
        """从字典创建"""
        return cls(data.copy())


class LearningThreadState(BaseThreadState):
    """
    学习助手扩展的ThreadState

    扩展字段说明:
    1. learning_topic: 当前学习主题 (str)
    2. study_duration: 累计学习时长 (int, 分钟)
    3. mastery_level: 掌握程度 (int, 0-100)
    4. review_schedule: 复习计划列表 (List[StudyRecord])

    兼容性设计:
    1. 新字段使用NotRequired或提供默认值
    2. 支持与基础ThreadState的相互转换
    3. 提供字段验证和类型转换
    """

    # 扩展字段定义（模拟Annotated字段）
    EXTENDED_FIELDS = {
        "learning_topic": {
            "type": str,
            "default": "",
            "description": "当前学习主题",
            "required": False,
        },
        "study_duration": {
            "type": int,
            "default": 0,
            "description": "累计学习时长（分钟）",
            "required": False,
        },
        "mastery_level": {
            "type": int,
            "default": 0,
            "description": "掌握程度（0-100）",
            "required": False,
        },
        "review_schedule": {
            "type": list,
            "default": [],
            "description": "复习计划列表",
            "required": False,
        },
    }

    def __init__(self, values: Optional[Dict[str, Any]] = None):
        super().__init__(values)
        self._ensure_extended_fields()

    def _ensure_extended_fields(self):
        """确保扩展字段存在（兼容性处理）"""
        for field_name, field_def in self.EXTENDED_FIELDS.items():
            if field_name not in self._values:
                self._values[field_name] = field_def["default"]

    def get_learning_topic(self) -> str:
        """获取学习主题"""
        return self.get("learning_topic", "")

    def set_learning_topic(self, topic: str):
        """设置学习主题"""
        if not isinstance(topic, str):
            raise TypeError(f"学习主题必须是字符串，收到: {type(topic)}")
        self.set("learning_topic", topic)

    def get_study_duration(self) -> int:
        """获取学习时长"""
        return self.get("study_duration", 0)

    def add_study_duration(self, duration: int):
        """增加学习时长"""
        current = self.get_study_duration()
        merged = merge_duration(current, duration)
        self.set("study_duration", merged)

    def get_mastery_level(self) -> int:
        """获取掌握程度"""
        return self.get("mastery_level", 0)

    def set_mastery_level(self, level: int):
        """设置掌握程度"""
        current = self.get_mastery_level()
        merged = merge_mastery(current, level)
        self.set("mastery_level", merged)

    def get_review_schedule(self) -> List[StudyRecord]:
        """获取复习计划"""
        raw = self.get("review_schedule", [])
        # 转换回StudyRecord对象
        if raw and isinstance(raw[0], dict):
            return [StudyRecord.from_dict(r) for r in raw]
        return raw

    def add_review_record(self, record: StudyRecord):
        """添加复习记录"""
        current = self.get_review_schedule()
        merged = merge_review_schedule(current, [record])
        # 存储为字典格式
        self.set("review_schedule", [r.to_dict() for r in merged])

    def to_extended_dict(self) -> Dict[str, Any]:
        """转换为扩展字典（包含所有字段）"""
        result = self.to_dict()

        # 确保扩展字段存在
        for field_name, field_def in self.EXTENDED_FIELDS.items():
            if field_name not in result:
                result[field_name] = field_def["default"]

        # 处理复习计划序列化
        if "review_schedule" in result and result["review_schedule"]:
            if isinstance(result["review_schedule"][0], StudyRecord):
                result["review_schedule"] = [
                    r.to_dict() for r in result["review_schedule"]
                ]

        return result

    @classmethod
    def from_base_state(cls, base_state: BaseThreadState) -> "LearningThreadState":
        """从基础状态创建扩展状态（兼容性转换）"""
        return cls(base_state.to_dict())

    def to_base_state(self) -> BaseThreadState:
        """转换为基础状态（丢弃扩展字段或保留为普通字段）"""
        return BaseThreadState(self.to_dict())


class StateCompatibilityChecker:
    """状态兼容性检查器"""

    @staticmethod
    def check_backward_compatibility(extended_state: LearningThreadState) -> bool:
        """检查向后兼容性（新状态能否转换为旧状态）"""
        print("\n3.1 向后兼容性检查:")

        # 转换为基础状态
        base_state = extended_state.to_base_state()

        # 检查基础字段是否可访问
        base_fields = base_state.to_dict()

        # 扩展字段在基础状态中作为普通字段存在
        for field_name in LearningThreadState.EXTENDED_FIELDS:
            if field_name in base_fields:
                print(f"  ✓ 扩展字段'{field_name}'在基础状态中可访问")
            else:
                print(f"  ✗ 扩展字段'{field_name}'在基础状态中丢失")
                return False

        print("  向后兼容性检查通过!")
        return True

    @staticmethod
    def check_forward_compatibility(base_state: BaseThreadState) -> bool:
        """检查向前兼容性（旧状态能否升级为新状态）"""
        print("\n3.2 向前兼容性检查:")

        # 转换为扩展状态
        try:
            extended_state = LearningThreadState.from_base_state(base_state)

            # 检查扩展字段是否有默认值
            for field_name, field_def in LearningThreadState.EXTENDED_FIELDS.items():
                value = extended_state.get(field_name)
                if value is not None:
                    print(f"  ✓ 扩展字段'{field_name}'已正确初始化: {value}")
                else:
                    print(f"  ✗ 扩展字段'{field_name}'初始化失败")
                    return False

            print("  向前兼容性检查通过!")
            return True

        except Exception as e:
            print(f"  ✗ 向前兼容性检查失败: {e}")
            return False

    @staticmethod
    def run_compatibility_tests():
        """运行兼容性测试"""
        print("\n运行状态兼容性测试...")

        # 创建扩展状态
        extended_state = LearningThreadState(
            {
                "learning_topic": "Python基础",
                "study_duration": 120,
                "mastery_level": 75,
                "review_schedule": [],
            }
        )

        # 向后兼容性测试
        backward_ok = StateCompatibilityChecker.check_backward_compatibility(
            extended_state
        )

        # 向前兼容性测试
        base_state = BaseThreadState(
            {"some_old_field": "旧字段值", "another_old_field": 42}
        )
        forward_ok = StateCompatibilityChecker.check_forward_compatibility(base_state)

        if backward_ok and forward_ok:
            print("\n所有兼容性测试通过!")
            return True
        else:
            print("\n兼容性测试失败!")
            return False


# ============================================================================
# 第四部分：完整Agent实现与工程化分析
# ============================================================================
print("\n" + "=" * 60)
print("第四部分：完整Agent实现与工程化分析")
print("=" * 60)


class LearningAssistant:
    """
    学习助手Agent

    使用扩展的LearningThreadState实现完整的学习助手功能
    演示业务逻辑与状态管理的分离
    """

    def __init__(self, initial_state: Optional[LearningThreadState] = None):
        self.state = initial_state or LearningThreadState()
        self.study_sessions = []

    async def study(self, topic: str, duration_minutes: int) -> Dict[str, Any]:
        """
        学习一个主题

        参数:
            topic: 学习主题
            duration_minutes: 学习时长（分钟）

        返回:
            学习结果
        """
        print(f"\n4.1 学习 '{topic}' ({duration_minutes}分钟):")

        # 更新学习主题
        self.state.set_learning_topic(topic)

        # 增加学习时长
        self.state.add_study_duration(duration_minutes)

        # 创建学习记录
        session = StudyRecord(
            topic=topic, duration_minutes=duration_minutes, timestamp=datetime.now()
        )
        self.study_sessions.append(session)

        # 模拟掌握程度评估（实际中可能基于测验或模型评估）
        mastery_increase = min(duration_minutes // 10, 20)  # 每10分钟增加1%，最多20%
        new_mastery = min(self.state.get_mastery_level() + mastery_increase, 100)
        self.state.set_mastery_level(new_mastery)

        # 安排复习（基于艾宾浩斯遗忘曲线）
        self._schedule_review(topic)

        result = {
            "topic": topic,
            "duration": duration_minutes,
            "total_duration": self.state.get_study_duration(),
            "mastery_level": self.state.get_mastery_level(),
            "session_count": len(self.study_sessions),
        }

        print(f"  学习完成!")
        print(f"  累计时长: {result['total_duration']}分钟")
        print(f"  掌握程度: {result['mastery_level']}/100")

        return result

    def _schedule_review(self, topic: str):
        """安排复习计划"""
        # 艾宾浩斯遗忘曲线：1天后、7天后、30天后
        review_times = [
            datetime.now() + timedelta(days=1),
            datetime.now() + timedelta(days=7),
            datetime.now() + timedelta(days=30),
        ]

        for review_time in review_times:
            record = StudyRecord(
                topic=topic,
                duration_minutes=30,  # 复习时长
                timestamp=review_time,
            )
            self.state.add_review_record(record)

        print(f"  已安排3次复习计划")

    async def assess_progress(self) -> Dict[str, Any]:
        """评估学习进度"""
        print("\n4.2 学习进度评估:")

        total_duration = self.state.get_study_duration()
        mastery = self.state.get_mastery_level()
        review_count = len(self.state.get_review_schedule())

        # 进度评估逻辑
        if total_duration == 0:
            progress_level = "未开始"
        elif total_duration < 180:  # 3小时
            progress_level = "入门"
        elif total_duration < 600:  # 10小时
            progress_level = "进阶"
        else:
            progress_level = "精通"

        # 掌握程度评估
        if mastery < 30:
            mastery_level = "基础"
        elif mastery < 70:
            mastery_level = "中等"
        else:
            mastery_level = "高级"

        assessment = {
            "total_study_hours": total_duration / 60,
            "mastery_score": mastery,
            "mastery_level": mastery_level,
            "progress_level": progress_level,
            "review_scheduled": review_count,
            "current_topic": self.state.get_learning_topic(),
        }

        print(f"  总学习时长: {assessment['total_study_hours']:.1f}小时")
        print(
            f"  掌握程度: {assessment['mastery_score']}/100 ({assessment['mastery_level']})"
        )
        print(f"  进度等级: {assessment['progress_level']}")
        print(f"  复习计划: {assessment['review_scheduled']}个")

        return assessment

    async def get_recommendations(self) -> List[str]:
        """获取学习建议"""
        print("\n4.3 学习建议生成:")

        recommendations = []
        state_dict = self.state.to_extended_dict()

        # 基于状态的个性化建议
        if state_dict["study_duration"] < 60:  # 少于1小时
            recommendations.append("建议每天学习至少30分钟，建立学习习惯")

        if state_dict["mastery_level"] < 50:
            recommendations.append("当前掌握程度较低，建议复习已学内容并完成练习")

        if len(state_dict["review_schedule"]) > 5:
            recommendations.append("复习计划较多，建议优先安排近期复习")

        # 主题建议
        current_topic = state_dict["learning_topic"]
        if current_topic:
            if "基础" in current_topic:
                recommendations.append(f"掌握{current_topic}后，建议学习'Python函数'")
            elif "函数" in current_topic:
                recommendations.append(f"掌握{current_topic}后，建议学习'面向对象编程'")

        # 如果没有特定建议，提供通用建议
        if not recommendations:
            recommendations.append("保持每天学习，定期复习，完成练习")

        print(f"  生成{len(recommendations)}条建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")

        return recommendations

    def get_state_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        return {
            "learning_topic": self.state.get_learning_topic(),
            "study_duration": self.state.get_study_duration(),
            "mastery_level": self.state.get_mastery_level(),
            "review_count": len(self.state.get_review_schedule()),
            "session_count": len(self.study_sessions),
        }


class EngineeringAnalysis:
    """工程化分析"""

    @staticmethod
    def analyze_design_patterns():
        """分析设计模式应用"""
        print("\n4.4 设计模式分析:")

        patterns = [
            {
                "pattern": "状态模式 (State Pattern)",
                "application": "ThreadState管理学习状态",
                "benefit": "封装状态变化逻辑，支持扩展",
            },
            {
                "pattern": "策略模式 (Strategy Pattern)",
                "application": "不同的Reducer函数实现不同合并策略",
                "benefit": "灵活支持多种合并逻辑，易于扩展",
            },
            {
                "pattern": "组合模式 (Composite Pattern)",
                "application": "StudyRecord组合成review_schedule列表",
                "benefit": "统一处理单个对象和对象集合",
            },
            {
                "pattern": "领域驱动设计 (DDD)",
                "application": "LearningThreadState作为领域模型",
                "benefit": "业务逻辑与状态管理分离，代码可维护",
            },
        ]

        for p in patterns:
            print(f"  {p['pattern']}:")
            print(f"    应用: {p['application']}")
            print(f"    优势: {p['benefit']}")

    @staticmethod
    def analyze_performance_considerations():
        """分析性能考虑"""
        print("\n4.5 性能考虑分析:")

        considerations = [
            "状态字段数量: 控制在合理范围，避免状态对象过大",
            "Reducer复杂度: 保持O(1)或O(n)复杂度，避免复杂算法",
            "序列化开销: 状态需要频繁序列化/反序列化，优化数据结构",
            "内存使用: 大列表字段（如review_schedule）考虑分页或懒加载",
            "并发安全: 状态更新需要考虑并发访问，使用适当锁或原子操作",
        ]

        for i, consideration in enumerate(considerations, 1):
            print(f"  {i}. {consideration}")

    @staticmethod
    def generate_best_practices():
        """生成最佳实践"""
        print("\n4.6 ThreadState扩展最佳实践:")

        practices = [
            "1. 需求驱动设计: 从业务需求推导状态字段，避免过度设计",
            "2. 关注点分离: 状态管理与业务逻辑分离，Reducer只负责合并逻辑",
            "3. 兼容性优先: 新字段使用NotRequired或默认值，确保向前向后兼容",
            "4. 测试全覆盖: 为每个Reducer函数编写完整测试，覆盖边界情况",
            "5. 性能监控: 监控状态大小和Reducer执行时间，及时发现性能问题",
            "6. 文档完善: 为扩展字段提供完整文档，包括类型、默认值、更新策略",
            "7. 版本管理: 状态结构变化时考虑版本迁移方案",
        ]

        for practice in practices:
            print(f"  {practice}")


async def main_demo():
    """主演示函数"""
    print("\n" + "=" * 60)
    print("ThreadState扩展完整演示")
    print("=" * 60)

    # 第一部分：需求分析
    print("\n[第一部分] 业务需求分析与状态字段识别")
    analyzer = BusinessRequirementAnalyzer()
    requirements = analyzer.analyze_learning_assistant()
    state_fields = analyzer.derive_state_fields(requirements)

    design_doc = analyzer.generate_design_document()
    with open("threadstate_design.md", "w", encoding="utf-8") as f:
        f.write(design_doc)
    print("  设计文档已保存到: threadstate_design.md")

    # 第二部分：Reducer测试
    print("\n[第二部分] Reducer函数测试")
    ReducerTestSuite.run_all_tests()

    # 第三部分：兼容性测试
    print("\n[第三部分] 兼容性测试")
    StateCompatibilityChecker.run_compatibility_tests()

    # 第四部分：完整Agent演示
    print("\n[第四部分] 完整Agent演示")

    # 创建学习助手
    assistant = LearningAssistant()

    # 模拟多天学习
    print("\n模拟学习过程:")

    # 第一天：学习Python基础
    print("\n--- 第一天 ---")
    await assistant.study("Python基础", 60)

    # 第二天：继续学习Python基础
    print("\n--- 第二天 ---")
    await assistant.study("Python基础", 90)

    # 第三天：学习Python函数
    print("\n--- 第三天 ---")
    await assistant.study("Python函数", 120)

    # 评估进度
    assessment = await assistant.assess_progress()

    # 获取建议
    recommendations = await assistant.get_recommendations()

    # 显示状态摘要
    print("\n4.7 最终状态摘要:")
    summary = assistant.get_state_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")

    # 工程化分析
    EngineeringAnalysis.analyze_design_patterns()
    EngineeringAnalysis.analyze_performance_considerations()
    EngineeringAnalysis.generate_best_practices()

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    print("开始运行ThreadState扩展演示...")
    try:
        asyncio.run(main_demo())
    except Exception as e:
        print(f"演示运行失败: {str(e)}")
        import traceback

        traceback.print_exc()
