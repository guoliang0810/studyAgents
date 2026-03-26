#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 5 Lesson 20: 实战：错误处理和澄清机制 - 课堂演示代码

本文件提供完整的错误处理和澄清机制集成系统实现，用于课堂教学演示。
采用四部分结构设计，全面展示三个中间件协同工作的各个方面：
1. 错误处理与澄清机制集成基础
2. 统一错误响应格式化系统
3. 集成中间件链实现
4. 完整测试系统与端到端演示

教学目标：
1. 理解错误处理、澄清机制、标题生成三个系统的协同工作原理
2. 掌握系统集成的方法和最佳实践
3. 熟悉完整错误处理系统的架构设计
4. 能够设计并实现用户友好的错误响应格式
5. 能够测试和验证集成系统的健壮性

运行要求：
Python 3.12+, 安装依赖: asyncio, typing-extensions, dataclasses-json
前置课程: 已完成ToolErrorHandlingMiddleware、ClarificationMiddleware、TitleMiddleware学习

作者: 张老师 (DeerFlow核心贡献者)
版本: v1.0
日期: 2024年4月1日
"""

import asyncio
import re
import time
import json
import random
from typing import List, Dict, Optional, Tuple, Any, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter, defaultdict
import heapq

# ============================================================================
# 第一部分：错误处理与澄清机制集成基础
# ============================================================================


class ErrorSeverity(Enum):
    """错误严重程度枚举"""

    INFO = "info"  # 信息性错误，不影响继续执行
    WARNING = "warning"  # 警告，可能影响结果但可继续执行
    ERROR = "error"  # 错误，当前操作失败但系统可恢复
    CRITICAL = "critical"  # 严重错误，系统需要重启或人工干预


@dataclass
class UnifiedError:
    """统一错误表示"""

    error_code: str  # 错误代码，如"TOOL_NOT_FOUND"
    error_message: str  # 用户友好的错误消息
    severity: ErrorSeverity  # 错误严重程度
    source: str  # 错误来源，如"ToolErrorHandlingMiddleware"
    details: Dict[str, Any] = field(default_factory=dict)  # 详细错误信息
    suggested_actions: List[str] = field(default_factory=list)  # 建议操作
    requires_clarification: bool = False  # 是否需要澄清
    clarification_prompt: Optional[str] = None  # 澄清提示

    def to_response_format(self) -> Dict[str, Any]:
        """转换为响应格式"""
        return {
            "error": {
                "code": self.error_code,
                "message": self.error_message,
                "severity": self.severity.value,
                "source": self.source,
            },
            "details": self.details,
            "suggestions": self.suggested_actions,
            "requires_clarification": self.requires_clarification,
            "clarification_prompt": self.clarification_prompt,
        }


@dataclass
class ClarificationContext:
    """澄清上下文"""

    conversation_id: str
    clarification_type: str  # "missing_parameter", "ambiguous_intent", "conflict"
    missing_parameters: List[str] = field(default_factory=list)
    ambiguous_options: List[str] = field(default_factory=list)
    conflict_details: Dict[str, Any] = field(default_factory=dict)
    clarification_history: List[Dict[str, Any]] = field(default_factory=list)
    max_attempts: int = 3
    current_attempt: int = 1

    def should_retry(self) -> bool:
        """是否应该重试澄清"""
        return self.current_attempt < self.max_attempts

    def record_attempt(self, user_response: str, success: bool):
        """记录澄清尝试"""
        self.clarification_history.append(
            {
                "attempt": self.current_attempt,
                "user_response": user_response,
                "success": success,
                "timestamp": time.time(),
            }
        )
        if success:
            self.current_attempt = self.max_attempts  # 标记完成
        else:
            self.current_attempt += 1


@dataclass
class IntegratedState:
    """集成系统状态"""

    conversation_id: str
    current_title: Optional[str] = None
    error_history: List[UnifiedError] = field(default_factory=list)
    clarification_context: Optional[ClarificationContext] = None
    is_in_clarification: bool = False
    is_in_error_recovery: bool = False
    recovery_strategy: Optional[str] = None

    def add_error(self, error: UnifiedError):
        """添加错误到历史"""
        self.error_history.append(error)
        # 限制历史大小
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]

    def get_recent_errors(self, count: int = 5) -> List[UnifiedError]:
        """获取最近的错误"""
        return self.error_history[-count:] if self.error_history else []

    def enter_clarification(self, context: ClarificationContext):
        """进入澄清状态"""
        self.clarification_context = context
        self.is_in_clarification = True
        self.is_in_error_recovery = False

    def exit_clarification(self):
        """退出澄清状态"""
        self.clarification_context = None
        self.is_in_clarification = False

    def enter_error_recovery(self, strategy: str):
        """进入错误恢复状态"""
        self.is_in_error_recovery = True
        self.recovery_strategy = strategy
        self.is_in_clarification = False

    def exit_error_recovery(self):
        """退出错误恢复状态"""
        self.is_in_error_recovery = False
        self.recovery_strategy = None


# ============================================================================
# 第二部分：统一错误响应格式化系统
# ============================================================================


class UnifiedErrorFormatter:
    """统一错误格式化器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "include_suggestions": True,
            "include_details": False,  # 生产环境建议关闭
            "user_friendly": True,
            "localization": "zh_CN",
        }
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Dict[str, str]]:
        """加载错误模板"""
        return {
            "TOOL_NOT_FOUND": {
                "zh_CN": "抱歉，找不到您请求的工具 '{tool_name}'。",
                "en_US": "Sorry, the tool '{tool_name}' you requested was not found.",
            },
            "MISSING_PARAMETER": {
                "zh_CN": "请提供'{parameter_name}'参数的值。",
                "en_US": "Please provide a value for the '{parameter_name}' parameter.",
            },
            "AMBIGUOUS_INTENT": {
                "zh_CN": "您的请求不够明确，请问您是想要：{options}？",
                "en_US": "Your request is ambiguous. Did you mean: {options}?",
            },
            "PERMISSION_DENIED": {
                "zh_CN": "您没有执行此操作的权限。",
                "en_US": "You don't have permission to perform this operation.",
            },
            "NETWORK_ERROR": {
                "zh_CN": "网络连接出现问题，请稍后重试。",
                "en_US": "Network connection issue, please try again later.",
            },
            "TIMEOUT": {
                "zh_CN": "操作超时，请稍后重试或简化您的请求。",
                "en_US": "Operation timed out, please try again later or simplify your request.",
            },
        }

    def format_error(
        self, error: UnifiedError, user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """格式化错误"""
        user_context = user_context or {}

        # 获取模板消息
        template = self.templates.get(error.error_code, {}).get(
            self.config["localization"], error.error_message
        )

        # 格式化消息
        formatted_message = template.format(**error.details)

        # 构建响应
        response = {
            "type": "error_response",
            "error": {
                "code": error.error_code,
                "message": formatted_message,
                "severity": error.severity.value,
            },
        }

        # 添加建议（如果启用）
        if self.config["include_suggestions"] and error.suggested_actions:
            response["suggestions"] = error.suggested_actions

        # 添加详细信息（如果启用）
        if self.config["include_details"]:
            response["technical_details"] = {
                "source": error.source,
                "timestamp": time.time(),
                "details": error.details,
            }

        # 添加澄清信息（如果需要）
        if error.requires_clarification and error.clarification_prompt:
            response["clarification_required"] = True
            response["clarification_prompt"] = error.clarification_prompt
            response["next_step"] = "awaiting_clarification"
        else:
            response["clarification_required"] = False
            response["next_step"] = self._determine_next_step(error)

        return response

    def _determine_next_step(self, error: UnifiedError) -> str:
        """确定下一步"""
        if error.severity == ErrorSeverity.CRITICAL:
            return "system_recovery_needed"
        elif error.severity == ErrorSeverity.ERROR:
            return "retry_or_alternative"
        elif error.severity == ErrorSeverity.WARNING:
            return "continue_with_warning"
        else:
            return "continue_normal"


class ClarificationResponseBuilder:
    """澄清响应构建器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "max_options": 3,
            "include_examples": True,
            "progressive_clarification": True,
        }

    def build_clarification_prompt(
        self, context: ClarificationContext, user_message: str
    ) -> Dict[str, Any]:
        """构建澄清提示"""

        if context.clarification_type == "missing_parameter":
            return self._build_missing_parameter_prompt(context, user_message)
        elif context.clarification_type == "ambiguous_intent":
            return self._build_ambiguous_intent_prompt(context, user_message)
        elif context.clarification_type == "conflict":
            return self._build_conflict_prompt(context, user_message)
        else:
            return self._build_generic_prompt(context, user_message)

    def _build_missing_parameter_prompt(
        self, context: ClarificationContext, user_message: str
    ) -> Dict[str, Any]:
        """构建缺失参数提示"""
        missing_params = context.missing_parameters

        if len(missing_params) == 1:
            prompt = f"请提供'{missing_params[0]}'的值："
        else:
            param_list = "、".join(missing_params)
            prompt = (
                f"请提供以下参数的值：{param_list}。您可以一次提供多个值，用逗号分隔。"
            )

        # 添加示例（如果启用）
        if self.config["include_examples"] and len(missing_params) == 1:
            example = self._get_parameter_example(missing_params[0])
            if example:
                prompt += f"\n例如：{example}"

        return {
            "type": "clarification_request",
            "clarification_type": "missing_parameter",
            "prompt": prompt,
            "missing_parameters": missing_params,
            "attempt": context.current_attempt,
            "max_attempts": context.max_attempts,
        }

    def _build_ambiguous_intent_prompt(
        self, context: ClarificationContext, user_message: str
    ) -> Dict[str, Any]:
        """构建模糊意图提示"""
        options = context.ambiguous_options[: self.config["max_options"]]
        options_text = "、".join([f"'{opt}'" for opt in options])

        prompt = f"您的请求不够明确，请问您是想要：{options_text}？"

        # 渐进式澄清：如果是第二次尝试，提供更具体的选项
        if self.config["progressive_clarification"] and context.current_attempt > 1:
            prompt += "\n或者请更详细地描述您的需求。"

        return {
            "type": "clarification_request",
            "clarification_type": "ambiguous_intent",
            "prompt": prompt,
            "options": options,
            "attempt": context.current_attempt,
            "max_attempts": context.max_attempts,
        }

    def _build_conflict_prompt(
        self, context: ClarificationContext, user_message: str
    ) -> Dict[str, Any]:
        """构建冲突提示"""
        conflict = context.conflict_details

        prompt = f"检测到冲突：{conflict.get('description', '参数或条件冲突')}。"

        if "resolution_options" in conflict:
            options = conflict["resolution_options"][: self.config["max_options"]]
            options_text = "、".join([f"'{opt}'" for opt in options])
            prompt += f"\n请选择解决方案：{options_text}"

        return {
            "type": "clarification_request",
            "clarification_type": "conflict",
            "prompt": prompt,
            "conflict_details": conflict,
            "attempt": context.current_attempt,
            "max_attempts": context.max_attempts,
        }

    def _build_generic_prompt(
        self, context: ClarificationContext, user_message: str
    ) -> Dict[str, Any]:
        """构建通用提示"""
        prompt = "请澄清您的请求："

        if context.current_attempt > 1:
            prompt += (
                f"\n（第{context.current_attempt}次尝试，共{context.max_attempts}次）"
            )

        return {
            "type": "clarification_request",
            "clarification_type": "generic",
            "prompt": prompt,
            "attempt": context.current_attempt,
            "max_attempts": context.max_attempts,
        }

    def _get_parameter_example(self, parameter_name: str) -> Optional[str]:
        """获取参数示例"""
        examples = {
            "date": "2024-04-01",
            "time": "14:30",
            "location": "北京",
            "budget": "5000元",
            "category": "科技、娱乐、体育",
        }
        return examples.get(parameter_name)


# ============================================================================
# 第三部分：集成中间件链实现
# ============================================================================


class IntegratedErrorHandlingMiddleware:
    """集成错误处理中间件"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "enable_error_detection": True,
            "enable_clarification": True,
            "max_clarification_attempts": 3,
            "error_recovery_strategies": ["retry", "alternative", "fallback"],
        }
        self.error_formatter = UnifiedErrorFormatter()
        self.clarification_builder = ClarificationResponseBuilder()
        self.state_manager = IntegratedStateManager()

    async def process(
        self, request: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理请求"""

        # 1. 获取或创建状态
        conversation_id = request.get("conversation_id", "default")
        state = self.state_manager.get_or_create_state(conversation_id)

        # 2. 检查是否在澄清状态中
        if state.is_in_clarification and state.clarification_context:
            return await self._handle_clarification_response(request, state, context)

        # 3. 检查是否在错误恢复中
        if state.is_in_error_recovery:
            return await self._handle_error_recovery(request, state, context)

        # 4. 正常处理流程
        try:
            # 模拟处理（实际中会调用真正的处理器）
            result = await self._process_request(request, context)

            # 检查结果中是否包含错误
            if self._contains_error(result):
                return await self._handle_detected_error(
                    result, request, state, context
                )

            # 成功处理，更新标题（如果适用）
            if "title" in result and result["title"]:
                state.current_title = result["title"]

            return result

        except Exception as e:
            # 捕获未处理的异常
            error = self._create_error_from_exception(e, request)
            state.add_error(error)

            # 根据错误严重程度决定下一步
            if error.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
                state.enter_error_recovery("exception_recovery")

            return self.error_formatter.format_error(error, context)

    async def _process_request(
        self, request: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """模拟处理请求"""
        # 模拟处理延迟
        await asyncio.sleep(0.01)

        # 检查常见错误模式
        error = self._detect_common_errors(request)
        if error:
            return {"error": error.to_response_format()}

        # 模拟成功响应
        return {
            "success": True,
            "result": "请求处理成功",
            "title": self._generate_title(request),
        }

    def _detect_common_errors(self, request: Dict[str, Any]) -> Optional[UnifiedError]:
        """检测常见错误"""
        # 检查工具是否存在
        if "tool" in request and request["tool"] == "unknown_tool":
            return UnifiedError(
                error_code="TOOL_NOT_FOUND",
                error_message=f"找不到工具 '{request['tool']}'",
                severity=ErrorSeverity.ERROR,
                source="IntegratedErrorHandlingMiddleware",
                details={"tool_name": request["tool"]},
                suggested_actions=[
                    "检查工具名称拼写",
                    "查看可用工具列表",
                    "使用类似功能的替代工具",
                ],
            )

        # 检查缺失参数
        if "parameters" in request:
            required_params = ["action", "target"]
            missing = [p for p in required_params if p not in request["parameters"]]
            if missing:
                return UnifiedError(
                    error_code="MISSING_PARAMETER",
                    error_message=f"缺少必要参数",
                    severity=ErrorSeverity.WARNING,
                    source="IntegratedErrorHandlingMiddleware",
                    details={"missing_parameters": missing},
                    suggested_actions=[f"提供参数'{p}'的值" for p in missing],
                    requires_clarification=True,
                    clarification_prompt=f"请提供参数'{missing[0]}'的值",
                )

        return None

    def _contains_error(self, result: Dict[str, Any]) -> bool:
        """检查结果是否包含错误"""
        return "error" in result or ("success" in result and not result["success"])

    async def _handle_detected_error(
        self,
        result: Dict[str, Any],
        request: Dict[str, Any],
        state: IntegratedState,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理检测到的错误"""
        # 从结果中提取错误信息
        if "error" in result:
            error_data = result["error"]
            error = UnifiedError(
                error_code=error_data.get("code", "UNKNOWN_ERROR"),
                error_message=error_data.get("message", "未知错误"),
                severity=ErrorSeverity(error_data.get("severity", "error")),
                source=error_data.get("source", "unknown"),
                details=error_data.get("details", {}),
                suggested_actions=error_data.get("suggestions", []),
            )
        else:
            error = UnifiedError(
                error_code="PROCESSING_ERROR",
                error_message="请求处理失败",
                severity=ErrorSeverity.ERROR,
                source="IntegratedErrorHandlingMiddleware",
                details={"result": result},
            )

        state.add_error(error)

        # 判断是否需要澄清
        if error.requires_clarification and self.config["enable_clarification"]:
            clarification_context = ClarificationContext(
                conversation_id=state.conversation_id,
                clarification_type="missing_parameter",
                missing_parameters=error.details.get("missing_parameters", []),
                max_attempts=self.config["max_clarification_attempts"],
            )
            state.enter_clarification(clarification_context)

            clarification_prompt = (
                self.clarification_builder.build_clarification_prompt(
                    clarification_context, request.get("message", "")
                )
            )
            return clarification_prompt

        # 不需要澄清，直接返回错误响应
        return self.error_formatter.format_error(error, context)

    async def _handle_clarification_response(
        self, request: Dict[str, Any], state: IntegratedState, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理澄清响应"""
        if not state.clarification_context:
            # 状态不一致，回到正常流程
            state.exit_clarification()
            return await self.process(request, context)

        clarification_context = state.clarification_context

        # 记录用户响应
        user_response = request.get("message", "")
        clarification_context.record_attempt(
            user_response, success=True
        )  # 简化：假设成功

        # 检查是否达到最大尝试次数
        if not clarification_context.should_retry():
            state.exit_clarification()
            # 使用用户响应重新处理请求
            updated_request = {**request, "clarification_response": user_response}
            return await self.process(updated_request, context)

        # 还需要更多澄清
        clarification_prompt = self.clarification_builder.build_clarification_prompt(
            clarification_context, user_response
        )
        return clarification_prompt

    async def _handle_error_recovery(
        self, request: Dict[str, Any], state: IntegratedState, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理错误恢复"""
        # 简化的恢复策略
        if state.recovery_strategy == "retry":
            # 重试原始请求
            state.exit_error_recovery()
            return await self.process(request, context)
        elif state.recovery_strategy == "alternative":
            # 尝试替代方案
            state.exit_error_recovery()
            alternative_request = self._create_alternative_request(request)
            return await self.process(alternative_request, context)
        else:
            # 回退策略
            state.exit_error_recovery()
            return {
                "success": False,
                "error": "无法从错误中恢复，请尝试其他操作",
                "recovery_attempted": True,
            }

    def _create_error_from_exception(
        self, exception: Exception, request: Dict[str, Any]
    ) -> UnifiedError:
        """从异常创建错误"""
        error_code = exception.__class__.__name__.upper()

        return UnifiedError(
            error_code=error_code,
            error_message=str(exception),
            severity=ErrorSeverity.ERROR,
            source="IntegratedErrorHandlingMiddleware",
            details={
                "exception_type": exception.__class__.__name__,
                "request": request,
            },
            suggested_actions=["检查请求格式", "验证参数有效性", "稍后重试"],
        )

    def _generate_title(self, request: Dict[str, Any]) -> str:
        """生成标题（简化版）"""
        message = request.get("message", "")
        if len(message) > 20:
            return message[:20] + "..."
        return message or "未知请求"

    def _create_alternative_request(
        self, original_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建替代请求"""
        # 简化的替代方案：移除可能有问题参数
        alternative = original_request.copy()
        if "parameters" in alternative:
            # 移除复杂的参数
            alternative["parameters"] = {
                k: v
                for k, v in alternative["parameters"].items()
                if not isinstance(v, (dict, list))
            }
        return alternative


class IntegratedStateManager:
    """集成状态管理器"""

    def __init__(self):
        self.states: Dict[str, IntegratedState] = {}

    def get_or_create_state(self, conversation_id: str) -> IntegratedState:
        """获取或创建状态"""
        if conversation_id not in self.states:
            self.states[conversation_id] = IntegratedState(
                conversation_id=conversation_id
            )
        return self.states[conversation_id]

    def clear_state(self, conversation_id: str):
        """清除状态"""
        if conversation_id in self.states:
            del self.states[conversation_id]

    def get_all_states(self) -> Dict[str, IntegratedState]:
        """获取所有状态"""
        return self.states.copy()


# ============================================================================
# 第四部分：完整测试系统与端到端演示
# ============================================================================


class IntegratedSystemTestSuite:
    """集成系统测试套件"""

    def __init__(self):
        self.middleware = IntegratedErrorHandlingMiddleware()

    async def run_all_tests(self):
        """运行所有测试"""
        print("🎓 Day 5 Lesson 20: 集成错误处理与澄清系统 - 测试套件")
        print("=" * 80)

        await self.test_normal_flow()
        await self.test_error_detection()
        await self.test_clarification_flow()
        await self.test_error_recovery()
        await self.test_integration_scenarios()

        print("\n✅ 所有测试完成！")

    async def test_normal_flow(self):
        """测试正常流程"""
        print("\n🧪 测试1: 正常请求流程")
        print("-" * 40)

        request = {
            "conversation_id": "test_normal",
            "message": "帮我搜索Python教程",
            "tool": "search_tool",
            "parameters": {"query": "Python教程", "max_results": 5},
        }

        response = await self.middleware.process(request, {})
        print(f"请求: {request['message']}")
        print(f"响应: {response}")

        if response.get("success"):
            print("✅ 正常流程测试通过")
        else:
            print("❌ 正常流程测试失败")

    async def test_error_detection(self):
        """测试错误检测"""
        print("\n🧪 测试2: 错误检测")
        print("-" * 40)

        # 测试未知工具
        request = {
            "conversation_id": "test_error",
            "message": "使用未知工具",
            "tool": "unknown_tool",
        }

        response = await self.middleware.process(request, {})
        print(f"请求: {request['message']} (使用未知工具)")
        print(f"响应类型: {response.get('type')}")
        print(f"错误代码: {response.get('error', {}).get('code')}")

        if response.get("type") == "error_response":
            print("✅ 错误检测测试通过")
        else:
            print("❌ 错误检测测试失败")

    async def test_clarification_flow(self):
        """测试澄清流程"""
        print("\n🧪 测试3: 澄清流程")
        print("-" * 40)

        # 第一轮：缺失参数触发澄清
        request1 = {
            "conversation_id": "test_clarification",
            "message": "搜索资料",
            "tool": "search_tool",
            "parameters": {},  # 缺失必要参数
        }

        response1 = await self.middleware.process(request1, {})
        print(f"第一轮请求: {request1['message']}")
        print(f"第一轮响应: {response1.get('prompt', '无提示')}")

        # 第二轮：提供澄清响应
        if response1.get("type") == "clarification_request":
            request2 = {
                "conversation_id": "test_clarification",
                "message": "Python教程",  # 提供缺失参数
            }

            response2 = await self.middleware.process(request2, {})
            print(f"第二轮请求: {request2['message']}")
            print(f"第二轮响应: {response2}")

            if response2.get("success"):
                print("✅ 澄清流程测试通过")
            else:
                print("❌ 澄清流程测试失败")
        else:
            print("❌ 未触发澄清流程")

    async def test_error_recovery(self):
        """测试错误恢复"""
        print("\n🧪 测试4: 错误恢复")
        print("-" * 40)

        # 模拟一个会引发异常的处理
        # 这里简化处理，实际测试中会模拟更复杂的场景
        print("测试场景: 异常捕获与恢复")

        # 创建一个会触发错误恢复的请求
        request = {"conversation_id": "test_recovery", "message": "复杂请求"}

        # 这里实际测试需要更复杂的设置
        print("✅ 错误恢复测试框架就绪")

    async def test_integration_scenarios(self):
        """测试集成场景"""
        print("\n🧪 测试5: 集成场景")
        print("-" * 40)

        scenarios = [
            {
                "name": "复杂对话流",
                "requests": [
                    {"message": "搜索资料", "parameters": {}},
                    {"message": "Python教程"},
                    {"message": "再搜索一下Java"},
                ],
            },
            {
                "name": "错误链处理",
                "requests": [
                    {"message": "使用未知工具", "tool": "unknown_tool"},
                    {"message": "那用搜索工具", "tool": "search_tool"},
                ],
            },
        ]

        for scenario in scenarios:
            print(f"\n场景: {scenario['name']}")
            for i, req in enumerate(scenario["requests"]):
                full_request = {
                    "conversation_id": f"test_scenario_{scenario['name']}",
                    **req,
                }
                response = await self.middleware.process(full_request, {})
                print(f"  步骤{i + 1}: {req.get('message')}")
                print(f"    响应: {response.get('type', 'unknown')}")

        print("\n✅ 集成场景测试完成")


async def main_demo():
    """主演示函数"""
    test_suite = IntegratedSystemTestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main_demo())
