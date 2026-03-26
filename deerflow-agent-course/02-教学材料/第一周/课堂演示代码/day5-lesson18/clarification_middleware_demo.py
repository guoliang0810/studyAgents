#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 5 Lesson 18: ClarificationMiddleware - 课堂演示代码

本文件提供完整的澄清中间件实现，用于课堂教学演示。
采用四部分结构设计，全面展示澄清机制的各个方面：
1. 澄清机制基础与数据结构
2. ClarificationMiddleware核心实现
3. 智能澄清生成器
4. 完整测试系统与高级功能

教学目标：
1. 理解澄清机制的概念及其在AI交互中的重要性
2. 掌握澄清触发条件的分类与检测方法
3. 熟悉ClarificationMiddleware的设计与实现原理
4. 掌握智能澄清生成和状态管理技术

运行要求：
Python 3.12+, 安装依赖: asyncio, typing-extensions, dataclasses-json

作者: 张老师 (DeerFlow核心贡献者)
版本: v1.0
日期: 2024年3月31日
"""

import asyncio
import time
import re
import json
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime

# ============================================================================
# 第一部分：澄清机制基础与数据结构
# ============================================================================


class ClarificationTrigger(Enum):
    """
    澄清触发条件 - 教学注释:

    澄清机制需要明确的触发条件，避免过度询问或遗漏重要澄清。
    五大触发条件：

    1. AMBIGUITY: 模糊性 - 用户请求含义不明确，有多种解释可能
       示例："帮我弄一下"（弄什么？怎么弄？）

    2. MISSING_REQUIRED: 缺失必需信息 - 缺少执行任务的关键信息
       示例："帮我搜索"（搜索什么？）

    3. CONFLICT: 冲突需求 - 用户请求中存在矛盾或冲突的要求
       示例："我想要A但是也想要B"（A和B互斥）

    4. TOO_BROAD: 过于宽泛 - 请求范围太大，无法有效执行
       示例："随便吧"（缺乏具体目标）

    5. UNKNOWN_ENTITY: 未知实体 - 请求中包含系统无法识别的实体
       示例："处理张三的数据"（张三是谁？）

    设计思考：
    - 每个触发条件应有明确的检测逻辑
    - 条件之间可能有重叠，需要优先级排序
    - 支持扩展，允许添加新的触发条件
    """

    AMBIGUITY = "ambiguity"  # 模糊性
    MISSING_REQUIRED = "missing_required"  # 缺失必需信息
    CONFLICT = "conflict"  # 冲突需求
    TOO_BROAD = "too_broad"  # 过于宽泛
    UNKNOWN_ENTITY = "unknown_entity"  # 未知实体


@dataclass
class Clarification:
    """
    澄清数据结构 - 教学注释:

    统一的澄清数据表示，包含所有必要信息用于生成澄清问题和处理用户回应。
    关键字段：

    1. trigger: 触发条件 - 为什么需要澄清
    2. question: 澄清问题 - 向用户提出的具体问题
    3. context: 原始上下文 - 触发澄清的原始请求和上下文
    4. suggestions: 建议选项 - 给用户的提示或选项（可选）
    5. required: 是否必需 - 用户必须回应才能继续
    6. response: 用户回应 - 用户提供的澄清信息（处理后填充）

    设计思考：
    - 数据结构要足够灵活，支持多种澄清场景
    - 序列化友好，便于存储和传输
    - 包含足够上下文，便于后续处理
    """

    trigger: ClarificationTrigger
    question: str
    context: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    required: bool = True
    response: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)
    clarification_id: str = field(
        default_factory=lambda: f"clar_{int(time.time() * 1000)}"
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "clarification_id": self.clarification_id,
            "trigger": self.trigger.value,
            "question": self.question,
            "context": self.context,
            "suggestions": self.suggestions,
            "required": self.required,
            "response": self.response,
            "timestamp": self.timestamp,
        }

    def __str__(self) -> str:
        """友好的字符串表示"""
        return (
            f"Clarification({self.trigger.value}): {self.question}\n"
            f"  建议: {', '.join(self.suggestions) if self.suggestions else '无'}\n"
            f"  必需: {'是' if self.required else '否'}"
        )


@dataclass
class AgentRequest:
    """
    简化的Agent请求类 - 教学注释:

    为了演示目的简化的请求类，实际DeerFlow中会更复杂。
    包含用户请求的基本信息和元数据。

    关键字段：
    1. user_id: 用户标识
    2. message: 用户消息文本
    3. metadata: 请求元数据，用于存储中间件处理结果

    设计思考：
    - 保持简单，专注于澄清机制演示
    - 与真实DeerFlow API兼容
    - 支持扩展，可以添加更多字段
    """

    user_id: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    request_id: str = field(default_factory=lambda: f"req_{int(time.time() * 1000)}")


@dataclass
class ClarificationState:
    """
    澄清状态管理 - 教学注释:

    跟踪澄清对话的状态，支持多轮澄清和状态恢复。
    关键功能：

    1. 状态跟踪：当前处于什么澄清阶段
    2. 历史记录：所有澄清请求和回应的历史
    3. 超时管理：澄清等待超时处理
    4. 恢复机制：澄清后恢复原始任务

    设计思考：
    - 状态管理是澄清机制的核心挑战
    - 需要支持并发和异步操作
    - 状态需要持久化，支持会话恢复
    """

    user_id: str
    current_clarification: Optional[Clarification] = None
    clarification_history: List[Clarification] = field(default_factory=list)
    original_request: Optional[AgentRequest] = None
    state: str = "idle"  # idle, waiting_for_clarification, processing, completed
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    timeout: float = 300.0  # 5分钟超时

    def add_clarification(self, clarification: Clarification):
        """添加澄清到历史"""
        self.clarification_history.append(clarification)
        self.current_clarification = clarification
        self.state = "waiting_for_clarification"
        self.last_updated = time.time()

    def add_response(self, response: Dict[str, Any]) -> bool:
        """添加用户回应"""
        if self.current_clarification:
            self.current_clarification.response = response
            self.state = "processing"
            self.last_updated = time.time()
            return True
        return False

    def is_expired(self) -> bool:
        """检查是否超时"""
        return time.time() - self.last_updated > self.timeout

    def can_continue(self) -> bool:
        """检查是否可以继续执行"""
        if self.state == "completed":
            return True
        if self.state == "waiting_for_clarification":
            return False
        if self.current_clarification and self.current_clarification.required:
            return self.current_clarification.response is not None
        return True


# ============================================================================
# 第二部分：ClarificationMiddleware核心实现
# ============================================================================


class ClarificationMiddleware:
    """
    澄清中间件 - 教学注释:

    核心澄清检测和处理中间件，集成到Agent处理流程中。
    主要功能：

    1. 模糊性检测：分析用户请求的清晰度
    2. 澄清生成：创建合适的澄清问题
    3. 状态管理：跟踪澄清对话状态
    4. 前置处理：在Agent执行前进行澄清检查

    设计思考：
    - 中间件模式允许无缝集成到现有系统
    - 检测逻辑要平衡准确性和性能
    - 支持配置，适应不同应用场景
    """

    def __init__(
        self,
        enable_ambiguity_detection: bool = True,
        enable_missing_detection: bool = True,
        enable_conflict_detection: bool = True,
        enable_broad_detection: bool = True,
        min_message_length: int = 10,
        max_clarifications: int = 3,
    ):
        self.name = "clarification"
        self.enable_ambiguity_detection = enable_ambiguity_detection
        self.enable_missing_detection = enable_missing_detection
        self.enable_conflict_detection = enable_conflict_detection
        self.enable_broad_detection = enable_broad_detection
        self.min_message_length = min_message_length
        self.max_clarifications = max_clarifications

        self.clarifications_made = 0
        self.clarification_states: Dict[str, ClarificationState] = {}
        self.detection_patterns = self._init_detection_patterns()

        print(f"🔧 [{self.name}] 中间件初始化完成")
        print(
            f"   配置: 模糊检测={enable_ambiguity_detection}, "
            f"缺失检测={enable_missing_detection}, "
            f"冲突检测={enable_conflict_detection}, "
            f"宽泛检测={enable_broad_detection}"
        )

    def _init_detection_patterns(self) -> Dict[str, Any]:
        """初始化检测模式"""
        return {
            "ambiguous_phrases": [
                "弄一下",
                "处理一下",
                "搞一下",
                "弄弄",
                "处理处理",
                "帮忙",
                "帮帮我",
                "帮个忙",
                "帮忙一下",
            ],
            "conflict_indicators": [
                "但是",
                "可是",
                "然而",
                "不过",
                "却",
                "又",
                "既要",
                "又要",
                "既要...又要",
                "既想...又想",
            ],
            "vague_responses": [
                "随便",
                "都可以",
                "无所谓",
                "你定",
                "你看着办",
                "差不多就行",
                "随便吧",
                "都可以的",
            ],
            "required_info_keywords": {
                "search": ["搜索", "查找", "找", "查", "search", "find"],
                "create": ["创建", "新建", "生成", "建立", "create", "make"],
                "delete": ["删除", "移除", "删掉", "delete", "remove"],
                "update": ["更新", "修改", "编辑", "update", "edit"],
                "analyze": ["分析", "统计", "研究", "analyze", "statistics"],
            },
        }

    def detect_ambiguity(
        self, message: str, context: Dict[str, Any]
    ) -> Optional[Clarification]:
        """
        检测请求中的模糊性

        教学注释:
        模糊性检测是澄清机制的基础，通过多种策略识别不明确的请求：
        1. 关键词匹配：检测模糊表达（"弄一下"）
        2. 长度检查：过短的请求可能信息不足
        3. 意图分析：识别请求类型和必需信息
        4. 冲突检测：发现矛盾的需求

        检测策略优先级：
        1. 冲突检测（最高优先级）
        2. 模糊表达检测
        3. 长度检查（过于宽泛）
        4. 必需信息检查
        """

        message_lower = message.lower()

        # 1. 检测冲突需求
        if self.enable_conflict_detection:
            for indicator in self.detection_patterns["conflict_indicators"]:
                if indicator in message_lower:
                    return Clarification(
                        trigger=ClarificationTrigger.CONFLICT,
                        question="我注意到你的请求中有冲突的需求：",
                        context={"message": message, "conflict_indicator": indicator},
                        suggestions=[
                            "请确认你最终想要什么",
                            "两个需求都要还是只选择一个",
                            "提供更明确的优先级",
                        ],
                        required=True,
                    )

        # 2. 检测模糊表达
        if self.enable_ambiguity_detection:
            for phrase in self.detection_patterns["ambiguous_phrases"]:
                if phrase in message_lower:
                    return Clarification(
                        trigger=ClarificationTrigger.AMBIGUITY,
                        question="你的请求比较模糊，能具体说明吗？",
                        context={"message": message, "ambiguous_phrase": phrase},
                        suggestions=[
                            "具体描述你想要的操作",
                            "说明期望的结果",
                            "提供更多的上下文信息",
                        ],
                        required=True,
                    )

        # 3. 检测过于宽泛
        if self.enable_broad_detection:
            # 检查消息长度
            if len(message.strip()) < self.min_message_length:
                # 检查是否是模糊回应
                is_vague_response = any(
                    vague in message_lower
                    for vague in self.detection_patterns["vague_responses"]
                )

                if is_vague_response:
                    return Clarification(
                        trigger=ClarificationTrigger.TOO_BROAD,
                        question="你的回应比较模糊，我需要更具体的指示：",
                        context={"message": message, "is_vague_response": True},
                        suggestions=[
                            "请提供具体的选择或偏好",
                            "说明你的考虑因素",
                            "给出明确的方向或要求",
                        ],
                        required=True,
                    )
                else:
                    # 普通短消息
                    return Clarification(
                        trigger=ClarificationTrigger.TOO_BROAD,
                        question="你的请求比较简短，能提供更多细节吗？",
                        context={"message": message, "length": len(message.strip())},
                        suggestions=[
                            "具体描述你想要什么",
                            "说明背景和约束条件",
                            "提供具体的参数或要求",
                        ],
                        required=True,
                    )

        # 4. 检测缺失的必需信息
        if self.enable_missing_detection:
            missing_info = self._detect_missing_required_info(message_lower)
            if missing_info:
                return Clarification(
                    trigger=ClarificationTrigger.MISSING_REQUIRED,
                    question=f"你的请求中缺少一些关键信息：{missing_info}",
                    context={"message": message, "missing_info": missing_info},
                    suggestions=[
                        "请提供缺失的信息",
                        "具体说明相关细节",
                        "补充必要的参数或条件",
                    ],
                    required=True,
                )

        # 不需要澄清
        return None

    def _detect_missing_required_info(self, message_lower: str) -> Optional[str]:
        """检测缺失的必需信息"""
        detected_intent = None
        missing_info = []

        # 检测意图类型
        for intent, keywords in self.detection_patterns[
            "required_info_keywords"
        ].items():
            if any(keyword in message_lower for keyword in keywords):
                detected_intent = intent
                break

        if not detected_intent:
            return None

        # 根据意图检查必需信息
        if detected_intent == "search":
            # 搜索需要搜索内容
            if not any(
                word in message_lower for word in ["内容", "什么", "关键词", "query"]
            ):
                missing_info.append("搜索内容")
            # 搜索可能需要范围
            if not any(
                word in message_lower for word in ["范围", "哪里", "在哪", "where"]
            ):
                missing_info.append("搜索范围")

        elif detected_intent == "create":
            # 创建需要类型和名称
            if not any(
                word in message_lower for word in ["类型", "什么", "kind", "type"]
            ):
                missing_info.append("创建类型")
            if not any(
                word in message_lower for word in ["名字", "名称", "name", "title"]
            ):
                missing_info.append("名称")

        elif detected_intent == "delete":
            # 删除需要对象
            if not any(
                word in message_lower for word in ["什么", "哪个", "对象", "what"]
            ):
                missing_info.append("删除对象")

        elif detected_intent == "update":
            # 更新需要对象和内容
            if not any(
                word in message_lower for word in ["什么", "哪个", "对象", "what"]
            ):
                missing_info.append("更新对象")
            if not any(
                word in message_lower for word in ["内容", "改成", "修改为", "to"]
            ):
                missing_info.append("更新内容")

        elif detected_intent == "analyze":
            # 分析需要对象和维度
            if not any(
                word in message_lower for word in ["什么", "数据", "分析什么", "data"]
            ):
                missing_info.append("分析对象")
            if not any(
                word in message_lower for word in ["维度", "角度", "方面", "dimension"]
            ):
                missing_info.append("分析维度")

        return "、".join(missing_info) if missing_info else None

    async def before_agent(
        self, request: AgentRequest, config: Optional[Dict[str, Any]] = None
    ) -> AgentRequest:
        """
        Agent执行前的澄清检查

        教学注释:
        这是中间件的核心方法，在Agent处理用户请求之前执行。
        流程：
        1. 检查是否超过最大澄清次数
        2. 检测请求中的模糊性和问题
        3. 如果需要澄清，更新请求元数据
        4. 跟踪澄清状态

        设计要点：
        - 异步设计支持IO操作
        - 幂等性：多次调用结果一致
        - 上下文保持：保留原始请求信息
        """

        config = config or {}
        user_id = request.user_id

        # 检查澄清次数限制
        if self.clarifications_made >= self.max_clarifications:
            print(f"⚠️ [{self.name}] 已达到最大澄清次数限制 ({self.max_clarifications})")
            return request

        # 获取或创建用户澄清状态
        if user_id not in self.clarification_states:
            self.clarification_states[user_id] = ClarificationState(user_id=user_id)

        state = self.clarification_states[user_id]

        # 检查超时
        if state.is_expired():
            print(f"🕒 [{self.name}] 用户 {user_id} 的澄清状态已超时，重置")
            self.clarification_states[user_id] = ClarificationState(user_id=user_id)
            state = self.clarification_states[user_id]

        # 如果正在等待澄清回应，检查是否已收到
        if state.state == "waiting_for_clarification":
            print(f"⏳ [{self.name}] 用户 {user_id} 正在等待澄清回应")
            request.metadata["awaiting_clarification"] = True
            request.metadata["clarification_state"] = state
            return request

        # 检测是否需要澄清
        clarification = self.detect_ambiguity(request.message, {})

        if clarification:
            self.clarifications_made += 1

            # 记录澄清
            state.add_clarification(clarification)
            state.original_request = request

            print(
                f"💬 [{self.name}] 需要澄清 ({self.clarifications_made}/{self.max_clarifications})"
            )
            print(f"   用户: {user_id}")
            print(f"   触发条件: {clarification.trigger.value}")
            print(f"   问题: {clarification.question}")
            if clarification.suggestions:
                print(f"   建议: {', '.join(clarification.suggestions)}")

            # 在请求元数据中添加澄清信息
            request.metadata["needs_clarification"] = True
            request.metadata["clarification"] = clarification
            request.metadata["clarification_state"] = state

        else:
            print(f"✅ [{self.name}] 不需要澄清，请求清晰")
            request.metadata["needs_clarification"] = False

        return request

    async def handle_clarification_response(
        self, user_id: str, response: Dict[str, Any]
    ) -> Optional[AgentRequest]:
        """
        处理用户澄清回应

        教学注释:
        当用户回应澄清问题时调用此方法。
        流程：
        1. 验证用户状态
        2. 记录用户回应
        3. 更新澄清状态
        4. 返回更新后的原始请求（如果需要继续）

        设计要点：
        - 支持多种回应格式（文本、选择、确认等）
        - 验证回应有效性
        - 状态转换管理
        """

        if user_id not in self.clarification_states:
            print(f"❌ [{self.name}] 用户 {user_id} 没有等待中的澄清")
            return None

        state = self.clarification_states[user_id]

        if state.state != "waiting_for_clarification":
            print(f"❌ [{self.name}] 用户 {user_id} 不处于等待澄清状态")
            return None

        if not state.current_clarification:
            print(f"❌ [{self.name}] 用户 {user_id} 没有当前澄清")
            return None

        # 记录用户回应
        success = state.add_response(response)

        if not success:
            print(f"❌ [{self.name}] 记录用户回应失败")
            return None

        print(f"✅ [{self.name}] 用户 {user_id} 澄清回应已记录")
        print(f"   回应: {json.dumps(response, ensure_ascii=False, indent=2)}")

        # 检查是否可以继续
        if state.can_continue():
            state.state = "completed"
            print(f"🚀 [{self.name}] 用户 {user_id} 澄清完成，可以继续执行")

            # 返回更新后的原始请求
            if state.original_request:
                updated_request = state.original_request
                # 将澄清信息合并到请求中
                if "clarification_responses" not in updated_request.metadata:
                    updated_request.metadata["clarification_responses"] = []

                for clar in state.clarification_history:
                    if clar.response:
                        updated_request.metadata["clarification_responses"].append(
                            {
                                "clarification_id": clar.clarification_id,
                                "question": clar.question,
                                "response": clar.response,
                            }
                        )

                # 更新请求消息（可选：将澄清信息整合到消息中）
                if response.get("text"):
                    updated_request.message = (
                        f"{updated_request.message} ({response['text']})"
                    )

                return updated_request

        return None

    def get_user_state(self, user_id: str) -> Optional[ClarificationState]:
        """获取用户澄清状态"""
        return self.clarification_states.get(user_id)

    def reset_user_state(self, user_id: str):
        """重置用户澄清状态"""
        if user_id in self.clarification_states:
            del self.clarification_states[user_id]
            print(f"🔄 [{self.name}] 用户 {user_id} 澄清状态已重置")


# ============================================================================
# 第三部分：智能澄清生成器
# ============================================================================


class SmartClarificationGenerator:
    """
    智能澄清生成器 - 教学注释:

    基于意图识别的智能澄清生成，比简单规则更准确和自然。
    主要功能：

    1. 意图识别：判断用户请求的类型和目的
    2. 信息缺口分析：检测缺失的关键信息
    3. 自然语言生成：创建符合人类交流习惯的问题
    4. 个性化建议：提供具体、可操作的选项

    设计思考：
    - 使用模式匹配进行意图识别（可扩展为ML模型）
    - 问题模板确保自然性和一致性
    - 支持上下文感知，基于对话历史生成问题
    """

    def __init__(self):
        self.intent_patterns = {
            "search": {
                "keywords": ["搜索", "查找", "找", "查", "search", "find", "look for"],
                "required_info": ["搜索内容", "搜索范围", "搜索条件"],
                "question_templates": {
                    "搜索内容": "你要搜索什么内容？",
                    "搜索范围": "在什么范围内搜索？",
                    "搜索条件": "有什么特定的搜索条件吗？",
                },
                "suggestion_templates": {
                    "搜索内容": "提供具体的搜索关键词",
                    "搜索范围": "比如'在当前文件'、'在整个项目'、'在互联网上'",
                    "搜索条件": "比如'最近一周'、'包含图片'、'中文内容'",
                },
            },
            "create": {
                "keywords": ["创建", "新建", "生成", "建立", "create", "make", "build"],
                "required_info": ["创建类型", "名称", "位置", "内容"],
                "question_templates": {
                    "创建类型": "要创建什么类型的内容？",
                    "名称": "叫什么名字？",
                    "位置": "创建在哪里？",
                    "内容": "内容是什么？",
                },
                "suggestion_templates": {
                    "创建类型": "比如'文件'、'文件夹'、'记录'、'项目'",
                    "名称": "提供具体的名称",
                    "位置": "比如'在桌面'、'在当前目录'、'在指定路径'",
                    "内容": "提供具体的内容或模板",
                },
            },
            "delete": {
                "keywords": ["删除", "移除", "删掉", "delete", "remove"],
                "required_info": ["删除对象", "确认", "备份"],
                "question_templates": {
                    "删除对象": "要删除什么？",
                    "确认": "确认要删除吗？",
                    "备份": "需要先备份吗？",
                },
                "suggestion_templates": {
                    "删除对象": "请提供具体的对象名称或路径",
                    "确认": "请输入'确认删除'或提供更多信息",
                    "备份": "选择'需要备份'或'直接删除'",
                },
            },
            "update": {
                "keywords": ["更新", "修改", "编辑", "update", "edit", "modify"],
                "required_info": ["更新对象", "更新内容", "更新方式"],
                "question_templates": {
                    "更新对象": "要更新什么？",
                    "更新内容": "更新成什么样子？",
                    "更新方式": "如何更新？",
                },
                "suggestion_templates": {
                    "更新对象": "提供具体的对象名称或标识",
                    "更新内容": "描述具体的变化",
                    "更新方式": "比如'完全替换'、'部分修改'、'增量更新'",
                },
            },
            "analyze": {
                "keywords": [
                    "分析",
                    "统计",
                    "研究",
                    "analyze",
                    "statistics",
                    "research",
                ],
                "required_info": ["分析对象", "分析维度", "分析目的"],
                "question_templates": {
                    "分析对象": "要分析什么数据？",
                    "分析维度": "从什么角度分析？",
                    "分析目的": "分析的目的是什么？",
                },
                "suggestion_templates": {
                    "分析对象": "比如'销售数据'、'用户日志'、'系统指标'",
                    "分析维度": "比如'按时间'、'按地区'、'按产品'",
                    "分析目的": "比如'发现问题'、'优化性能'、'预测趋势'",
                },
            },
        }

        self.context_awareness = True
        self.history_awareness = True
        self.conversation_history: Dict[str, List[Dict[str, Any]]] = {}

    def detect_intent(self, message: str) -> Tuple[Optional[str], List[str]]:
        """
        检测用户意图和缺失信息

        教学注释:
        意图识别是智能澄清的基础，通过以下步骤：
        1. 关键词匹配：识别请求类型
        2. 信息提取：从请求中提取已有信息
        3. 缺口分析：对比必需信息，找出缺失项
        4. 置信度评估：评估识别结果的可靠性

        返回：意图类型，缺失信息列表
        """
        message_lower = message.lower()
        detected_intent = None
        confidence = 0.0

        # 检测意图
        for intent, pattern in self.intent_patterns.items():
            for keyword in pattern["keywords"]:
                if keyword in message_lower:
                    detected_intent = intent
                    confidence += 0.3  # 每个匹配关键词增加置信度
                    break

        if not detected_intent:
            return None, []

        # 检查缺失信息
        missing_info = []
        required_info = self.intent_patterns[detected_intent]["required_info"]

        for info in required_info:
            # 简单检查：根据信息类型检查是否存在相关词汇
            if not self._check_info_present(message_lower, detected_intent, info):
                missing_info.append(info)

        return detected_intent, missing_info

    def _check_info_present(self, message: str, intent: str, info_type: str) -> bool:
        """检查特定类型的信息是否存在于消息中"""
        # 根据意图和信息类型定义检查规则
        check_rules = {
            "search": {
                "搜索内容": lambda m: any(
                    word in m for word in ["内容", "什么", "关键词", "query", "搜索"]
                ),
                "搜索范围": lambda m: any(
                    word in m for word in ["范围", "哪里", "在哪", "where", "范围"]
                ),
                "搜索条件": lambda m: any(
                    word in m for word in ["条件", "要求", "filter", "条件"]
                ),
            },
            "create": {
                "创建类型": lambda m: any(
                    word in m for word in ["类型", "什么", "kind", "type", "类型"]
                ),
                "名称": lambda m: any(
                    word in m for word in ["名字", "名称", "name", "title", "叫"]
                ),
                "位置": lambda m: any(
                    word in m for word in ["位置", "在哪", "where", "位置", "地方"]
                ),
                "内容": lambda m: any(
                    word in m for word in ["内容", "什么", "content", "包含", "有"]
                ),
            },
            "delete": {
                "删除对象": lambda m: any(
                    word in m for word in ["什么", "哪个", "对象", "what", "删除"]
                ),
                "确认": lambda m: any(
                    word in m for word in ["确认", "确定", "confirm", "是否", "真的"]
                ),
                "备份": lambda m: any(
                    word in m for word in ["备份", "backup", "保留", "存档"]
                ),
            },
            "update": {
                "更新对象": lambda m: any(
                    word in m for word in ["什么", "哪个", "对象", "what", "更新"]
                ),
                "更新内容": lambda m: any(
                    word in m for word in ["内容", "改成", "修改为", "to", "变成"]
                ),
                "更新方式": lambda m: any(
                    word in m for word in ["方式", "怎么", "如何", "how", "方法"]
                ),
            },
            "analyze": {
                "分析对象": lambda m: any(
                    word in m for word in ["什么", "数据", "分析什么", "data", "对象"]
                ),
                "分析维度": lambda m: any(
                    word in m for word in ["维度", "角度", "方面", "dimension", "按"]
                ),
                "分析目的": lambda m: any(
                    word in m for word in ["目的", "为什么", "目标", "purpose", "为了"]
                ),
            },
        }

        if intent in check_rules and info_type in check_rules[intent]:
            return check_rules[intent][info_type](message)

        return False

    def generate_clarification(
        self, message: str, context: Dict[str, Any], user_id: Optional[str] = None
    ) -> Optional[Clarification]:
        """
        生成智能澄清问题

        教学注释:
        基于意图识别结果生成自然、有针对性的澄清问题。
        流程：
        1. 意图识别和缺口分析
        2. 问题生成（使用模板）
        3. 建议生成（提供具体选项）
        4. 上下文整合（基于对话历史）

        设计要点：
        - 问题要自然，符合人类交流习惯
        - 建议要具体、可操作
        - 支持多轮澄清对话
        """

        # 检测意图和缺失信息
        intent, missing_info = self.detect_intent(message)

        if not intent or not missing_info:
            return None

        # 生成问题和建议
        questions = []
        suggestions = []

        for info in missing_info:
            if info in self.intent_patterns[intent]["question_templates"]:
                questions.append(
                    self.intent_patterns[intent]["question_templates"][info]
                )

            if info in self.intent_patterns[intent]["suggestion_templates"]:
                suggestions.append(
                    self.intent_patterns[intent]["suggestion_templates"][info]
                )

        if not questions:
            return None

        # 构建澄清上下文
        clarification_context = {
            "message": message,
            "detected_intent": intent,
            "missing_info": missing_info,
            "timestamp": time.time(),
        }

        # 添加上下文信息
        if user_id and self.history_awareness:
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []

            # 添加当前消息到历史
            self.conversation_history[user_id].append(
                {
                    "role": "user",
                    "message": message,
                    "timestamp": time.time(),
                    "intent": intent,
                }
            )

            clarification_context["conversation_history"] = self.conversation_history[
                user_id
            ][-3:]  # 最近3条

        # 创建澄清对象
        return Clarification(
            trigger=ClarificationTrigger.MISSING_REQUIRED,
            question="\n".join(questions),
            context=clarification_context,
            suggestions=suggestions,
            required=True,
        )

    def add_conversation_turn(
        self,
        user_id: str,
        role: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """添加对话轮次到历史"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []

        turn = {"role": role, "message": message, "timestamp": time.time()}

        if metadata:
            turn.update(metadata)

        self.conversation_history[user_id].append(turn)

        # 限制历史长度
        if len(self.conversation_history[user_id]) > 10:
            self.conversation_history[user_id] = self.conversation_history[user_id][-5:]

    def get_conversation_history(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户对话历史"""
        return self.conversation_history.get(user_id, []).copy()


# ============================================================================
# 第四部分：完整测试系统与高级功能
# ============================================================================


async def basic_demo():
    """基础演示：ClarificationMiddleware基本功能"""
    print("=" * 70)
    print("🧪 基础演示：ClarificationMiddleware基本功能")
    print("=" * 70)

    # 创建中间件
    middleware = ClarificationMiddleware(
        enable_ambiguity_detection=True,
        enable_missing_detection=True,
        enable_conflict_detection=True,
        enable_broad_detection=True,
        min_message_length=10,
        max_clarifications=3,
    )

    # 测试消息
    test_messages = [
        "帮我弄一下",  # 模糊性
        "帮我搜索",  # 缺失必需信息
        "我想要A但是也想要B",  # 冲突需求
        "随便吧",  # 过于宽泛
        "分析数据",  # 缺失分析维度
        "请创建一个新项目，命名为我的项目，内容是关于AI的研究",  # 清晰请求
    ]

    for msg in test_messages:
        print(f"\n📝 测试消息: '{msg}'")
        print("-" * 50)

        # 创建请求
        request = AgentRequest(user_id="test_user", message=msg)

        # 执行中间件
        result = await middleware.before_agent(request)

        # 分析结果
        if result.metadata.get("needs_clarification", False):
            clarification = result.metadata["clarification"]
            print(f"   ⚠️ 需要澄清")
            print(f"   触发条件: {clarification.trigger.value}")
            print(f"   问题: {clarification.question}")
            if clarification.suggestions:
                print(f"   建议: {', '.join(clarification.suggestions)}")
        else:
            print(f"   ✅ 不需要澄清，请求清晰")
            print(f"   可以直接执行")


async def smart_generator_demo():
    """智能生成器演示"""
    print("\n" + "=" * 70)
    print("🧠 智能生成器演示：意图识别和澄清生成")
    print("=" * 70)

    # 创建智能生成器
    generator = SmartClarificationGenerator()

    # 测试消息
    test_messages = [
        "帮我搜索相关信息",
        "创建一个新文件",
        "删除一些旧数据",
        "更新用户配置",
        "分析销售数据",
    ]

    for msg in test_messages:
        print(f"\n📝 测试消息: '{msg}'")
        print("-" * 50)

        # 生成澄清
        clarification = generator.generate_clarification(msg, {}, "test_user")

        if clarification:
            intent = clarification.context.get("detected_intent", "unknown")
            missing_info = clarification.context.get("missing_info", [])

            print(f"   🔍 检测到意图: {intent}")
            print(f"   ❌ 缺失信息: {', '.join(missing_info)}")
            print(f"   ❓ 澄清问题: {clarification.question}")
            print(f"   💡 建议: {', '.join(clarification.suggestions)}")
        else:
            print(f"   ✅ 请求完整，不需要澄清")


async def full_integration_demo():
    """完整集成演示"""
    print("\n" + "=" * 70)
    print("🔗 完整集成演示：中间件 + 智能生成器")
    print("=" * 70)

    # 创建组件
    middleware = ClarificationMiddleware()
    generator = SmartClarificationGenerator()

    # 模拟对话流程
    print("\n💬 模拟对话流程:")
    print("-" * 50)

    # 第一轮：用户模糊请求
    user_message_1 = "帮我弄一下数据"
    print(f"👤 用户: {user_message_1}")

    request_1 = AgentRequest(user_id="user_123", message=user_message_1)
    result_1 = await middleware.before_agent(request_1)

    if result_1.metadata.get("needs_clarification", False):
        clarification_1 = result_1.metadata["clarification"]
        print(f"🤖 AI: {clarification_1.question}")
        if clarification_1.suggestions:
            print(f"     建议: {clarification_1.suggestions[0]}")

        # 模拟用户回应
        user_response_1 = {"text": "我想分析上个月的销售数据"}
        print(f"👤 用户: {user_response_1['text']}")

        # 处理用户回应
        updated_request = await middleware.handle_clarification_response(
            "user_123", user_response_1
        )

        if updated_request:
            # 使用智能生成器进一步澄清
            clarification_2 = generator.generate_clarification(
                updated_request.message, {}, "user_123"
            )

            if clarification_2:
                print(f"🤖 AI: {clarification_2.question}")
                if clarification_2.suggestions:
                    print(f"     建议: {clarification_2.suggestions[0]}")

                # 模拟最终回应
                user_response_2 = {"text": "从产品类别和地区两个维度分析"}
                print(f"👤 用户: {user_response_2['text']}")

                # 最终处理
                await middleware.handle_clarification_response(
                    "user_123", user_response_2
                )

                print(f"\n✅ 对话完成，可以执行任务:")
                print(f"   任务: 分析上个月的销售数据")
                print(f"   维度: 产品类别和地区")
            else:
                print(f"\n✅ 信息完整，可以执行任务")
        else:
            print(f"\n❌ 处理用户回应失败")
    else:
        print(f"\n✅ 请求清晰，直接执行")


async def performance_test():
    """性能测试"""
    print("\n" + "=" * 70)
    print("⚡ 性能测试：处理速度和准确性")
    print("=" * 70)

    import time
    import statistics

    middleware = ClarificationMiddleware()

    # 测试数据集
    test_cases = [
        ("清晰请求", "请帮我搜索关于Python异步编程的教程", False),
        ("模糊请求", "弄一下", True),
        ("缺失信息", "创建文件", True),
        ("冲突需求", "既要快又要好", True),
        ("宽泛请求", "随便", True),
    ]

    results = []

    for case_name, message, expected_needs_clarification in test_cases:
        start_time = time.perf_counter()

        request = AgentRequest(user_id="perf_test", message=message)
        result = await middleware.before_agent(request)

        elapsed = time.perf_counter() - start_time

        actual_needs_clarification = result.metadata.get("needs_clarification", False)
        correct = actual_needs_clarification == expected_needs_clarification

        results.append(
            {
                "case": case_name,
                "message": message,
                "time_ms": elapsed * 1000,
                "correct": correct,
                "needs_clarification": actual_needs_clarification,
            }
        )

        print(
            f"   {case_name}: {elapsed * 1000:.2f} ms, {'正确' if correct else '错误'}"
        )

    # 统计
    avg_time = statistics.mean(r["time_ms"] for r in results)
    accuracy = sum(1 for r in results if r["correct"]) / len(results) * 100

    print(f"\n📊 性能统计:")
    print(f"   平均处理时间: {avg_time:.2f} ms")
    print(f"   准确率: {accuracy:.1f}%")
    print(f"   总测试数: {len(results)}")


async def advanced_features_demo():
    """高级功能演示"""
    print("\n" + "=" * 70)
    print("🚀 高级功能演示：状态管理和多轮对话")
    print("=" * 70)

    middleware = ClarificationMiddleware()

    # 模拟多用户场景
    users = ["user_a", "user_b", "user_c"]

    for user_id in users:
        print(f"\n👤 用户: {user_id}")

        # 用户A：简单澄清
        if user_id == "user_a":
            request = AgentRequest(user_id=user_id, message="帮我搜索")
            result = await middleware.before_agent(request)

            if result.metadata.get("needs_clarification", False):
                state = middleware.get_user_state(user_id)
                print(f"   状态: {state.state}")
                print(
                    f"   当前澄清: {state.current_clarification.question if state.current_clarification else '无'}"
                )

        # 用户B：多轮澄清
        elif user_id == "user_b":
            # 第一轮
            request1 = AgentRequest(user_id=user_id, message="创建")
            result1 = await middleware.before_agent(request1)

            if result1.metadata.get("needs_clarification", False):
                # 模拟用户回应
                await middleware.handle_clarification_response(
                    user_id, {"text": "创建一个Python脚本文件"}
                )

                # 第二轮（基于回应继续）
                state = middleware.get_user_state(user_id)
                if state and state.original_request:
                    # 更新请求并重新检查
                    updated_request = AgentRequest(
                        user_id=user_id,
                        message=f"{state.original_request.message} (创建一个Python脚本文件)",
                    )
                    result2 = await middleware.before_agent(updated_request)

                    if result2.metadata.get("needs_clarification", False):
                        print(f"   需要第二轮澄清")
                    else:
                        print(f"   澄清完成，可以执行")

        # 用户C：超时测试
        elif user_id == "user_c":
            request = AgentRequest(user_id=user_id, message="随便弄一下")
            result = await middleware.before_agent(request)

            if result.metadata.get("needs_clarification", False):
                state = middleware.get_user_state(user_id)
                print(f"   初始状态: {state.state}")

                # 模拟超时（修改时间戳）
                import time

                state.last_updated = time.time() - 400  # 设置6分钟前

                print(f"   超时检查: {'已超时' if state.is_expired() else '未超时'}")

                # 重置状态
                middleware.reset_user_state(user_id)
                print(f"   状态重置: {middleware.get_user_state(user_id) is None}")


async def main_demo():
    """主演示函数"""
    print("🎓 Day 5 Lesson 18: ClarificationMiddleware - 完整演示")
    print("=" * 70)

    try:
        # 运行所有演示
        await basic_demo()
        await smart_generator_demo()
        await full_integration_demo()
        await performance_test()
        await advanced_features_demo()

        print("\n" + "=" * 70)
        print("✅ 所有演示完成！")
        print("=" * 70)

        # 总结
        print("\n📚 本课重点总结:")
        print("   1. 澄清机制的五种触发条件")
        print("   2. ClarificationMiddleware的设计与实现")
        print("   3. 智能澄清生成器的意图识别")
        print("   4. 澄清状态管理和多轮对话")
        print("   5. 性能考虑和最佳实践")

    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # 运行主演示
    asyncio.run(main_demo())
