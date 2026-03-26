#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 5 Lesson 17: ToolErrorHandlingMiddleware - 课堂演示代码

本文件提供完整的工具错误处理中间件实现，用于课堂教学演示。
采用四部分结构设计，全面展示工具错误处理中间件的各个方面：
1. 错误分类体系与数据结构
2. 核心错误处理中间件实现
3. 工具包装器与测试系统
4. 高级功能与生产实践

教学目标：
1. 理解工具错误的分类体系及严重级别
2. 掌握错误处理策略的选择机制和决策逻辑
3. 熟悉ToolErrorHandlingMiddleware的设计与实现原理
4. 掌握异步环境中错误处理的正确方法

运行要求：
Python 3.12+, 安装依赖: asyncio, typing-extensions, dataclasses-json

作者: 张老师 (DeerFlow核心贡献者)
版本: v1.0
日期: 2024年3月30日
"""

import asyncio
import time
import json
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime

# ============================================================================
# 第一部分：错误分类体系与数据结构
# ============================================================================


class ErrorSeverity(Enum):
    """
    错误严重级别 - 教学注释:

    错误的严重级别决定了处理策略的紧急程度和最终决策。
    四个级别从低到高：

    1. LOW: 可忽略的错误，不影响主要功能执行
       示例：非关键日志写入失败、缓存未命中

    2. MEDIUM: 警告级别错误，需要记录但可以继续执行
       示例：性能指标收集失败、非必需功能异常

    3. HIGH: 错误级别，需要处理但可能不需要立即终止
       示例：参数验证失败、网络请求超时（可重试）

    4. CRITICAL: 严重错误，必须立即处理或终止执行
       示例：权限不足、资源耗尽、数据损坏

    设计思考：
    - 级别划分要清晰，便于策略选择
    - 与业务场景结合，不同系统可能有不同定义
    - 支持动态调整，根据运行情况调整级别
    """

    LOW = "low"  # 可忽略，不影响执行
    MEDIUM = "medium"  # 警告，继续执行
    HIGH = "high"  # 错误，需要处理
    CRITICAL = "critical"  # 严重错误，终止执行


class ErrorCategory(Enum):
    """
    错误类别 - 教学注释:

    基于错误来源和性质的分类，用于选择针对性的处理策略。
    四大类别：

    1. TIMEOUT: 执行超时错误
       特点：可能是临时性问题，适合重试

    2. PERMISSION: 权限错误
       特点：通常需要人工介入，无法自动修复

    3. PARAMETER: 参数错误
       特点：调用方问题，可能需要回退或通知

    4. NETWORK: 网络错误
       特点：临时性问题，适合重试或回退

    5. RESOURCE: 资源错误
       特点：系统资源问题，可能需要扩容或通知

    6. UNKNOWN: 未知错误
       特点：无法分类的错误，需要人工分析

    设计思考：
    - 类别要覆盖常见错误类型
    - 每个类别应有明确的处理策略倾向
    - 支持扩展，允许添加新的错误类别
    """

    TIMEOUT = "timeout"
    PERMISSION = "permission"
    PARAMETER = "parameter"
    NETWORK = "network"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


@dataclass
class ToolError:
    """
    工具错误数据结构 - 教学注释:

    统一的错误表示格式，包含错误的所有相关信息。
    关键字段：

    1. tool_name: 发生错误的工具名称，便于定位问题
    2. error_message: 原始错误消息，包含详细描述
    3. category: 错误类别，用于策略选择
    4. severity: 错误严重级别，决定处理紧急程度
    5. retry_count: 已重试次数，用于重试策略控制
    6. original_error: 原始异常对象，保留完整堆栈信息
    7. timestamp: 错误发生时间，用于时序分析和监控
    8. context: 错误发生时的上下文信息，便于问题复现

    设计思考：
    - 使用@dataclass简化代码，自动生成常用方法
    - 包含足够的信息支持错误分析和处理
    - 支持序列化，便于日志记录和传输
    - 扩展性强，可以添加新字段而不影响现有代码
    """

    tool_name: str
    error_message: str
    category: ErrorCategory
    severity: ErrorSeverity
    retry_count: int = 0
    original_error: Optional[Exception] = None
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于序列化"""
        return {
            "tool_name": self.tool_name,
            "error_message": self.error_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "retry_count": self.retry_count,
            "timestamp": self.timestamp,
            "context": self.context,
        }

    def __str__(self) -> str:
        """友好的字符串表示"""
        return (
            f"ToolError(tool={self.tool_name}, "
            f"category={self.category.value}, "
            f"severity={self.severity.value}, "
            f"message={self.error_message[:50]}...)"
        )

    def is_retryable(self) -> bool:
        """检查错误是否可重试"""
        # 严重错误、权限错误通常不可重试
        if self.severity == ErrorSeverity.CRITICAL:
            return False
        if self.category == ErrorCategory.PERMISSION:
            return False
        return True


class ErrorHandlingStrategy(Enum):
    """
    错误处理策略 - 教学注释:

    针对不同错误类型的处理方式，每个策略有明确的适用场景：

    1. RETRY: 重试策略
       适用：临时性错误（网络抖动、超时）
       实现：等待后重新执行，通常有次数限制

    2. FALLBACK: 回退策略
       适用：主方案失败，但有备用方案
       实现：切换到备用实现或简化版本

    3. SKIP: 跳过策略
       适用：非关键操作失败
       实现：跳过当前操作，继续执行后续流程

    4. ABORT: 终止策略
       适用：严重错误无法恢复
       实现：安全终止当前流程，返回错误

    5. NOTIFY: 通知策略
       适用：需要人工介入的错误
       实现：记录错误并通知相关人员

    设计思考：
    - 策略要覆盖常见处理方式
    - 策略之间可以组合使用（如重试失败后回退）
    - 策略选择要考虑业务影响和用户体验
    """

    RETRY = "retry"  # 重试
    FALLBACK = "fallback"  # 回退到备选方案
    SKIP = "skip"  # 跳过该操作
    ABORT = "abort"  # 终止执行
    NOTIFY = "notify"  # 通知用户


def determine_strategy(error: ToolError) -> ErrorHandlingStrategy:
    """
    根据错误确定处理策略 - 教学注释:

    策略选择决策逻辑，基于错误类别和严重级别。
    决策优先级：
    1. 严重级别为CRITICAL -> ABORT（安全第一）
    2. 根据错误类别选择默认策略
    3. 考虑重试次数（超过限制则切换策略）

    策略映射表：
    - TIMEOUT/NETWORK: RETRY（临时性问题）
    - PARAMETER: FALLBACK（调用方问题，尝试替代方案）
    - PERMISSION/RESOURCE: NOTIFY（需要人工处理）
    - UNKNOWN: NOTIFY（需要分析）

    设计思考：
    - 策略选择要保守，安全优先
    - 允许配置覆盖默认策略
    - 支持基于历史数据的智能选择
    """

    # 严重错误直接终止
    if error.severity == ErrorSeverity.CRITICAL:
        return ErrorHandlingStrategy.ABORT

    # 如果已超过重试次数且错误可重试，考虑回退
    if error.retry_count >= 3 and error.is_retryable():
        return ErrorHandlingStrategy.FALLBACK

    # 根据错误类别选择策略
    strategy_map = {
        ErrorCategory.TIMEOUT: ErrorHandlingStrategy.RETRY,
        ErrorCategory.NETWORK: ErrorHandlingStrategy.RETRY,
        ErrorCategory.RESOURCE: ErrorHandlingStrategy.NOTIFY,
        ErrorCategory.PERMISSION: ErrorHandlingStrategy.NOTIFY,
        ErrorCategory.PARAMETER: ErrorHandlingStrategy.FALLBACK,
        ErrorCategory.UNKNOWN: ErrorHandlingStrategy.NOTIFY,
    }

    return strategy_map.get(error.category, ErrorHandlingStrategy.NOTIFY)


# ============================================================================
# 第二部分：核心错误处理中间件实现
# ============================================================================


class ToolErrorHandlingMiddleware:
    """
    工具错误处理中间件 - 教学注释:

    核心错误处理组件，负责：
    1. 错误分类：识别错误类型和严重级别
    2. 策略选择：根据错误特征选择合适策略
    3. 错误处理：执行重试、回退等操作
    4. 日志记录：保存错误信息用于分析和监控

    设计要点：
    - 支持配置：最大重试次数、重试延迟、是否启用回退等
    - 状态管理：维护错误日志和统计信息
    - 可扩展性：允许自定义错误分类和处理逻辑
    - 异步支持：完全兼容async/await编程模型

    性能考虑：
    - 错误分类使用关键词匹配，简单高效
    - 错误日志使用列表存储，内存占用可控
    - 支持批量处理和异步写入，减少I/O阻塞
    """

    def __init__(
        self,
        name: str = "tool_error_handling",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        enable_fallback: bool = True,
        enable_notification: bool = True,
    ):
        self.name = name
        self.max_retries = max_retries
        self.retry_delay = retry_delay  # 基础重试延迟（秒）
        self.enable_fallback = enable_fallback
        self.enable_notification = enable_notification
        self.error_log: List[ToolError] = []
        self.handling_stats: Dict[str, int] = {
            "total_errors": 0,
            "retry_success": 0,
            "retry_failed": 0,
            "fallback_success": 0,
            "fallback_failed": 0,
            "skip_count": 0,
            "abort_count": 0,
            "notify_count": 0,
        }

    def classify_error(
        self,
        error: Exception,
        tool_name: str = "unknown",
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolError:
        """
        分类错误 - 教学注释:

        基于错误信息的启发式分类方法：
        1. 提取错误消息（转换为小写便于匹配）
        2. 检查关键词判断错误类别
        3. 根据类别推断严重级别
        4. 构建ToolError对象

        分类规则：
        - "timeout"/"timed out" -> TIMEOUT (MEDIUM)
        - "permission"/"denied"/"forbidden" -> PERMISSION (HIGH)
        - "parameter"/"argument"/"invalid" -> PARAMETER (MEDIUM)
        - "network"/"connection"/"socket" -> NETWORK (MEDIUM)
        - "memory"/"disk"/"space"/"resource" -> RESOURCE (HIGH)
        - 其他 -> UNKNOWN (MEDIUM)

        设计思考：
        - 关键词匹配简单但有效，覆盖80%常见错误
        - 允许自定义分类规则或使用机器学习改进
        - 保持分类逻辑可维护和可测试
        """

        error_msg = str(error).lower()

        # 根据错误信息关键词判断类别和严重级别
        if any(
            keyword in error_msg for keyword in ["timeout", "timed out", "time out"]
        ):
            category = ErrorCategory.TIMEOUT
            severity = ErrorSeverity.MEDIUM
        elif any(
            keyword in error_msg
            for keyword in ["permission", "denied", "forbidden", "unauthorized"]
        ):
            category = ErrorCategory.PERMISSION
            severity = ErrorSeverity.HIGH
        elif any(
            keyword in error_msg
            for keyword in ["parameter", "argument", "invalid", "validation"]
        ):
            category = ErrorCategory.PARAMETER
            severity = ErrorSeverity.MEDIUM
        elif any(
            keyword in error_msg
            for keyword in ["network", "connection", "socket", "http"]
        ):
            category = ErrorCategory.NETWORK
            severity = ErrorSeverity.MEDIUM
        elif any(
            keyword in error_msg
            for keyword in ["memory", "disk", "space", "resource", "out of"]
        ):
            category = ErrorCategory.RESOURCE
            severity = ErrorSeverity.HIGH
        else:
            category = ErrorCategory.UNKNOWN
            severity = ErrorSeverity.MEDIUM

        # 构建ToolError对象
        return ToolError(
            tool_name=tool_name,
            error_message=str(error),
            category=category,
            severity=severity,
            original_error=error,
            context=context or {},
        )

    async def handle_error(
        self, error: ToolError, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理错误 - 教学注释:

        完整的错误处理流程：
        1. 确定处理策略（基于错误特征）
        2. 执行策略（重试、回退、跳过等）
        3. 记录处理结果和统计信息
        4. 返回处理结果供调用方使用

        重试策略细节：
        - 指数退避：延迟时间随重试次数增加
        - 最大重试限制：防止无限重试
        - 重试失败后降级：重试失败后尝试回退

        回退策略细节：
        - 检查是否启用回退功能
        - 执行备用方案（如果有）
        - 回退失败则终止或通知

        设计思考：
        - 每个策略有明确的成功/失败处理
        - 支持异步操作，避免阻塞
        - 提供详细的处理日志，便于调试
        """

        self.error_log.append(error)
        self.handling_stats["total_errors"] += 1

        strategy = determine_strategy(error)
        context = context or {}

        print(
            f"🔧 [{self.name}] 处理错误: {error.tool_name} - "
            f"{error.category.value} ({error.severity.value}) -> {strategy.value}"
        )

        start_time = time.time()

        try:
            if strategy == ErrorHandlingStrategy.RETRY:
                result = await self._handle_retry(error, context)
                elapsed = (time.time() - start_time) * 1000
                print(f"   ⏱️  处理时间: {elapsed:.1f}ms")
                return result

            elif strategy == ErrorHandlingStrategy.FALLBACK:
                result = await self._handle_fallback(error, context)
                elapsed = (time.time() - start_time) * 1000
                print(f"   ⏱️  处理时间: {elapsed:.1f}ms")
                return result

            elif strategy == ErrorHandlingStrategy.SKIP:
                self.handling_stats["skip_count"] += 1
                elapsed = (time.time() - start_time) * 1000
                print(f"⏭️  [{self.name}] 跳过操作: {error.tool_name}")
                print(f"   ⏱️  处理时间: {elapsed:.1f}ms")
                return {"action": "skip", "error": error, "success": True}

            elif strategy == ErrorHandlingStrategy.ABORT:
                self.handling_stats["abort_count"] += 1
                elapsed = (time.time() - start_time) * 1000
                print(f"🛑 [{self.name}] 终止执行: {error.tool_name}")
                print(f"   ⏱️  处理时间: {elapsed:.1f}ms")
                return {"action": "abort", "error": error, "success": False}

            elif strategy == ErrorHandlingStrategy.NOTIFY:
                self.handling_stats["notify_count"] += 1
                result = await self._handle_notify(error, context)
                elapsed = (time.time() - start_time) * 1000
                print(f"   ⏱️  处理时间: {elapsed:.1f}ms")
                return result

            else:
                elapsed = (time.time() - start_time) * 1000
                print(f"❓ [{self.name}] 未知策略: {strategy}")
                print(f"   ⏱️  处理时间: {elapsed:.1f}ms")
                return {"action": "unknown", "error": error, "success": False}

        except Exception as e:
            # 错误处理过程中发生异常
            elapsed = (time.time() - start_time) * 1000
            print(f"💥 [{self.name}] 错误处理失败: {e}")
            print(f"   ⏱️  处理时间: {elapsed:.1f}ms")
            return {
                "action": "error",
                "error": error,
                "success": False,
                "processing_error": str(e),
            }

    async def _handle_retry(
        self, error: ToolError, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理重试策略"""
        if error.retry_count < self.max_retries and error.is_retryable():
            error.retry_count += 1
            # 指数退避：延迟时间随重试次数增加
            delay = self.retry_delay * (2 ** (error.retry_count - 1))
            print(
                f"🔄 [{self.name}] 重试 ({error.retry_count}/{self.max_retries}) "
                f"等待 {delay:.1f}s"
            )
            await asyncio.sleep(delay)
            return {"action": "retry", "error": error, "success": True}
        else:
            print(f"⚠️  [{self.name}] 重试次数耗尽或不可重试")
            # 重试失败后尝试回退
            if self.enable_fallback:
                return await self._handle_fallback(error, context)
            else:
                return {"action": "retry_failed", "error": error, "success": False}

    async def _handle_fallback(
        self, error: ToolError, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理回退策略"""
        if self.enable_fallback:
            print(f"🔀 [{self.name}] 切换到备用方案")
            # 这里可以执行具体的回退逻辑
            # 例如：调用备用API、使用本地计算、返回缓存数据等
            fallback_result = await self._execute_fallback_logic(error, context)
            if fallback_result["success"]:
                self.handling_stats["fallback_success"] += 1
                return {
                    "action": "fallback",
                    "error": error,
                    "success": True,
                    "result": fallback_result,
                }
            else:
                self.handling_stats["fallback_failed"] += 1
                return {"action": "fallback_failed", "error": error, "success": False}
        else:
            print(f"❌ [{self.name}] 回退功能未启用")
            return {"action": "fallback_disabled", "error": error, "success": False}

    async def _execute_fallback_logic(
        self, error: ToolError, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行具体的回退逻辑（示例实现）"""
        # 这里只是一个示例，实际项目中需要根据具体工具实现
        tool_name = error.tool_name

        if tool_name == "weather_api":
            # 天气API失败，返回默认天气
            return {
                "success": True,
                "data": {"temperature": 20, "condition": "sunny", "source": "fallback"},
            }
        elif tool_name == "calculator":
            # 计算器失败，使用简化计算
            return {"success": True, "result": 0, "message": "使用简化计算"}
        else:
            # 通用回退：返回错误但继续执行
            return {"success": True, "message": "使用通用回退策略"}

    async def _handle_notify(
        self, error: ToolError, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理通知策略"""
        if self.enable_notification:
            print(f"📢 [{self.name}] 通知相关人员")
            # 这里可以实现具体的通知逻辑
            # 例如：发送邮件、Slack消息、记录到监控系统等
            notification_sent = await self._send_notification(error, context)
            return {
                "action": "notify",
                "error": error,
                "success": True,
                "notification_sent": notification_sent,
            }
        else:
            print(f"🔇 [{self.name}] 通知功能未启用")
            return {"action": "notify_disabled", "error": error, "success": False}

    async def _send_notification(
        self, error: ToolError, context: Dict[str, Any]
    ) -> bool:
        """发送通知（示例实现）"""
        # 模拟发送通知
        await asyncio.sleep(0.1)
        print(
            f"   📧 通知内容: 工具 {error.tool_name} 发生 {error.category.value} 错误"
        )
        print(f"   📧 错误详情: {error.error_message[:100]}")
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """获取错误处理统计信息"""
        return {
            "total_errors": self.handling_stats["total_errors"],
            "by_category": self._count_errors_by_category(),
            "by_severity": self._count_errors_by_severity(),
            "handling_stats": self.handling_stats.copy(),
            "recent_errors": [e.to_dict() for e in self.error_log[-10:]]
            if self.error_log
            else [],
        }

    def _count_errors_by_category(self) -> Dict[str, int]:
        """按类别统计错误"""
        counts = {cat.value: 0 for cat in ErrorCategory}
        for error in self.error_log:
            counts[error.category.value] += 1
        return counts

    def _count_errors_by_severity(self) -> Dict[str, int]:
        """按严重级别统计错误"""
        counts = {sev.value: 0 for sev in ErrorSeverity}
        for error in self.error_log:
            counts[error.severity.value] += 1
        return counts

    def generate_report(self) -> str:
        """生成错误处理报告"""
        stats = self.get_statistics()

        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("工具错误处理报告")
        report_lines.append("=" * 60)

        report_lines.append("\n📊 总体统计:")
        report_lines.append(f"   总错误数: {stats['total_errors']}")
        report_lines.append(f"   处理成功率: {self._calculate_success_rate():.1%}")

        report_lines.append("\n🔍 按类别分布:")
        for category, count in stats["by_category"].items():
            if count > 0:
                percentage = (
                    (count / stats["total_errors"] * 100)
                    if stats["total_errors"] > 0
                    else 0
                )
                report_lines.append(f"   • {category}: {count} ({percentage:.1f}%)")

        report_lines.append("\n⚠️  按严重级别分布:")
        for severity, count in stats["by_severity"].items():
            if count > 0:
                percentage = (
                    (count / stats["total_errors"] * 100)
                    if stats["total_errors"] > 0
                    else 0
                )
                report_lines.append(f"   • {severity}: {count} ({percentage:.1f}%)")

        report_lines.append("\n🔄 处理策略统计:")
        handling = stats["handling_stats"]
        report_lines.append(f"   重试成功: {handling['retry_success']}")
        report_lines.append(f"   重试失败: {handling['retry_failed']}")
        report_lines.append(f"   回退成功: {handling['fallback_success']}")
        report_lines.append(f"   回退失败: {handling['fallback_failed']}")
        report_lines.append(f"   跳过操作: {handling['skip_count']}")
        report_lines.append(f"   终止执行: {handling['abort_count']}")
        report_lines.append(f"   通知用户: {handling['notify_count']}")

        report_lines.append("\n" + "=" * 60)
        return "\n".join(report_lines)

    def _calculate_success_rate(self) -> float:
        """计算处理成功率"""
        total = self.handling_stats["total_errors"]
        if total == 0:
            return 1.0

        successes = (
            self.handling_stats["retry_success"]
            + self.handling_stats["fallback_success"]
            + self.handling_stats["skip_count"]
        )
        return successes / total


# ============================================================================
# 第三部分：工具包装器与测试系统
# ============================================================================


def wrap_tool_call(
    tool_name: str,
    tool_func: Callable,
    middleware: ToolErrorHandlingMiddleware,
    fallback_func: Optional[Callable] = None,
) -> Callable:
    """
    包装工具调用 - 教学注释:

    工具调用包装器，自动处理错误：
    1. 执行原始工具函数
    2. 捕获异常并分类错误
    3. 调用错误处理中间件
    4. 根据处理结果决定下一步操作

    支持的功能：
    - 自动重试：失败后自动重试（根据策略）
    - 优雅降级：主方案失败后尝试备用方案
    - 透明处理：对调用方隐藏错误处理细节
    - 上下文传递：保留调用上下文便于问题排查

    设计思考：
    - 包装器模式实现，不修改原工具代码
    - 支持同步和异步工具函数
    - 提供灵活的配置选项
    - 保持调用接口一致
    """

    async def async_wrapper(*args, **kwargs):
        """异步工具包装器"""
        context = {
            "tool_name": tool_name,
            "args": args,
            "kwargs": kwargs,
            "timestamp": time.time(),
        }

        max_attempts = middleware.max_retries + 1  # 初始尝试 + 重试次数
        attempt = 0

        while attempt < max_attempts:
            attempt += 1
            try:
                # 执行工具函数
                if asyncio.iscoroutinefunction(tool_func):
                    result = await tool_func(*args, **kwargs)
                else:
                    result = tool_func(*args, **kwargs)

                print(f"✅ [{tool_name}] 执行成功 (尝试 {attempt})")
                return {"success": True, "result": result, "attempts": attempt}

            except Exception as e:
                print(f"❌ [{tool_name}] 执行失败 (尝试 {attempt}): {e}")

                # 分类错误
                error = middleware.classify_error(e, tool_name, context)
                error.retry_count = attempt - 1  # 当前尝试计数

                # 处理错误
                handling_result = await middleware.handle_error(error, context)

                # 根据处理结果决定下一步
                if handling_result["action"] == "retry" and attempt < max_attempts:
                    # 继续重试循环
                    continue
                elif handling_result["action"] == "fallback" and fallback_func:
                    # 尝试回退方案
                    try:
                        if asyncio.iscoroutinefunction(fallback_func):
                            fallback_result = await fallback_func(*args, **kwargs)
                        else:
                            fallback_result = fallback_func(*args, **kwargs)
                        print(f"🔀 [{tool_name}] 回退方案成功")
                        return {
                            "success": True,
                            "result": fallback_result,
                            "attempts": attempt,
                            "fallback": True,
                        }
                    except Exception as fallback_error:
                        print(f"💥 [{tool_name}] 回退方案也失败: {fallback_error}")
                        # 回退失败，继续处理
                        pass
                elif handling_result["action"] == "skip":
                    # 跳过操作，返回默认值
                    print(f"⏭️  [{tool_name}] 跳过操作")
                    return {"success": True, "skipped": True, "attempts": attempt}
                elif handling_result["action"] == "abort":
                    # 终止执行
                    print(f"🛑 [{tool_name}] 终止执行")
                    return {
                        "success": False,
                        "error": error,
                        "attempts": attempt,
                        "aborted": True,
                    }
                elif handling_result["action"] == "notify":
                    # 通知后继续（如果可能）
                    print(f"📢 [{tool_name}] 已通知，继续执行（如果可能）")
                    # 这里可以根据业务决定是否继续
                    # 示例中我们返回错误但标记为已通知
                    return {
                        "success": False,
                        "error": error,
                        "attempts": attempt,
                        "notified": True,
                    }
                else:
                    # 其他情况，返回错误
                    return {"success": False, "error": error, "attempts": attempt}

        # 所有尝试都失败
        print(f"💀 [{tool_name}] 所有尝试都失败")
        return {"success": False, "error": "所有尝试都失败", "attempts": attempt}

    return async_wrapper


class ParameterValidator:
    """
    参数验证器 - 教学注释:

    工具参数验证组件，确保输入参数符合要求：
    1. 必填参数检查：确保必需参数存在
    2. 类型验证：检查参数类型是否符合预期
    3. 范围验证：检查数值参数是否在有效范围内
    4. 格式验证：检查字符串参数格式（如邮箱、URL等）

    验证模式：
    - 严格模式：任何验证失败立即抛出异常
    - 宽松模式：收集所有错误后统一返回

    设计思考：
    - 支持灵活的验证规则定义
    - 提供清晰的错误消息
    - 支持嵌套参数验证
    - 可扩展的验证规则系统
    """

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.errors: List[Exception] = []

    def validate(
        self, params: Dict[str, Any], schema: Dict[str, Dict[str, Any]]
    ) -> Tuple[bool, List[Exception]]:
        """验证参数"""
        self.errors = []

        for param_name, rules in schema.items():
            value = params.get(param_name)

            # 检查必填参数
            if rules.get("required", False) and value is None:
                error = ValueError(f"参数 '{param_name}' 是必需的")
                self._handle_error(error)
                if self.strict_mode:
                    return False, self.errors

            if value is None:
                continue  # 可选参数为空，跳过进一步验证

            # 检查类型
            expected_type = rules.get("type")
            if expected_type and not isinstance(value, expected_type):
                error = TypeError(
                    f"参数 '{param_name}' 类型错误: "
                    f"期望 {expected_type.__name__}, 实际 {type(value).__name__}"
                )
                self._handle_error(error)
                if self.strict_mode:
                    return False, self.errors

            # 检查范围（数值类型）
            if isinstance(value, (int, float)):
                min_val = rules.get("min")
                max_val = rules.get("max")

                if min_val is not None and value < min_val:
                    error = ValueError(f"参数 '{param_name}' 值太小: 最小为 {min_val}")
                    self._handle_error(error)
                    if self.strict_mode:
                        return False, self.errors

                if max_val is not None and value > max_val:
                    error = ValueError(f"参数 '{param_name}' 值太大: 最大为 {max_val}")
                    self._handle_error(error)
                    if self.strict_mode:
                        return False, self.errors

            # 检查长度（字符串、列表等）
            if hasattr(value, "__len__"):
                min_len = rules.get("min_length")
                max_len = rules.get("max_length")
                actual_len = len(value)

                if min_len is not None and actual_len < min_len:
                    error = ValueError(
                        f"参数 '{param_name}' 长度不足: "
                        f"最小长度 {min_len}, 实际长度 {actual_len}"
                    )
                    self._handle_error(error)
                    if self.strict_mode:
                        return False, self.errors

                if max_len is not None and actual_len > max_len:
                    error = ValueError(
                        f"参数 '{param_name}' 长度超出: "
                        f"最大长度 {max_len}, 实际长度 {actual_len}"
                    )
                    self._handle_error(error)
                    if self.strict_mode:
                        return False, self.errors

            # 检查格式（字符串）
            if isinstance(value, str):
                pattern = rules.get("pattern")
                if pattern and not re.match(pattern, value):
                    error = ValueError(f"参数 '{param_name}' 格式错误")
                    self._handle_error(error)
                    if self.strict_mode:
                        return False, self.errors

        return len(self.errors) == 0, self.errors

    def _handle_error(self, error: Exception):
        """处理验证错误"""
        self.errors.append(error)
        if self.strict_mode:
            raise error


# ============================================================================
# 第四部分：示例工具与测试演示
# ============================================================================


# 示例工具函数
async def unreliable_calculator(x: int, y: int, fail_probability: float = 0.3) -> int:
    """不稳定的计算器工具（用于演示）"""
    await asyncio.sleep(0.1)  # 模拟处理时间

    # 随机失败
    if random.random() < fail_probability:
        error_type = random.choice(
            [
                TimeoutError("计算超时"),
                ValueError("无效参数"),
                ConnectionError("网络连接失败"),
                MemoryError("内存不足"),
            ]
        )
        raise error_type

    return x + y


async def reliable_calculator(x: int, y: int) -> int:
    """可靠的计算器（备用方案）"""
    await asyncio.sleep(0.05)
    return x + y  # 简单实现，总是成功


async def weather_api(city: str, fail_probability: float = 0.2) -> Dict[str, Any]:
    """模拟天气API（可能失败）"""
    await asyncio.sleep(0.2)

    if random.random() < fail_probability:
        raise ConnectionError(f"无法连接到天气API: {city}")

    return {
        "city": city,
        "temperature": random.randint(15, 30),
        "condition": random.choice(["sunny", "cloudy", "rainy"]),
        "humidity": random.randint(40, 80),
    }


async def file_processor(filename: str, operation: str = "read") -> str:
    """模拟文件处理器（可能权限错误）"""
    await asyncio.sleep(0.15)

    if operation == "write" and "secret" in filename:
        raise PermissionError(f"没有权限写入文件: {filename}")

    if "corrupted" in filename:
        raise IOError(f"文件损坏: {filename}")

    return f"{operation} {filename} 成功"


async def main_demo():
    """主演示函数"""
    print("=" * 60)
    print("Day 5 Lesson 17: 工具错误处理中间件演示")
    print("=" * 60)

    # 创建错误处理中间件
    middleware = ToolErrorHandlingMiddleware(
        name="demo_error_handler",
        max_retries=2,
        retry_delay=0.5,
        enable_fallback=True,
        enable_notification=True,
    )

    # 演示1: 不稳定的计算器
    print("\n演示1: 不稳定的计算器")
    print("-" * 40)

    wrapped_calc = wrap_tool_call(
        "unreliable_calculator",
        unreliable_calculator,
        middleware,
        fallback_func=reliable_calculator,
    )

    # 测试多次调用
    test_cases = [(3, 5), (10, 20), (100, 200)]
    for x, y in test_cases:
        print(f"\n计算 {x} + {y}:")
        result = await wrapped_calc(x, y)
        if result["success"]:
            print(
                f"   ✅ 结果: {result.get('result', 'N/A')} "
                f"(尝试 {result.get('attempts', 1)} 次)"
            )
            if result.get("fallback"):
                print("   🔀 使用了回退方案")
        else:
            print(f"   ❌ 失败: {result.get('error', '未知错误')}")

    # 演示2: 天气API
    print("\n\n演示2: 天气API调用")
    print("-" * 40)

    wrapped_weather = wrap_tool_call("weather_api", weather_api, middleware)

    cities = ["Beijing", "Shanghai", "Guangzhou", "Shenzhen"]
    for city in cities:
        print(f"\n获取 {city} 天气:")
        result = await wrapped_weather(city)
        if result["success"]:
            weather_data = result.get("result", {})
            print(f"   ✅ 温度: {weather_data.get('temperature', 'N/A')}°C")
            print(f"     天气: {weather_data.get('condition', 'N/A')}")
        else:
            print(f"   ❌ 失败: {result.get('error', '未知错误')}")

    # 演示3: 文件处理器（权限错误）
    print("\n\n演示3: 文件处理器（权限错误）")
    print("-" * 40)

    wrapped_file = wrap_tool_call("file_processor", file_processor, middleware)

    files = ["document.txt", "secret_file.txt", "corrupted_data.txt"]
    for filename in files:
        print(f"\n处理文件 {filename}:")
        result = await wrapped_file(filename, "write")
        if result["success"]:
            print(f"   ✅ {result.get('result', '成功')}")
        else:
            print(f"   ❌ 失败: {result.get('error', '未知错误')}")
            if result.get("notified"):
                print("   📢 已通知相关人员")

    # 显示错误处理统计
    print("\n" + "=" * 60)
    print("错误处理统计报告")
    print("=" * 60)
    print(middleware.generate_report())

    # 显示详细错误日志（如果存在）
    stats = middleware.get_statistics()
    if stats["recent_errors"]:
        print("\n📋 最近错误记录:")
        for i, error in enumerate(stats["recent_errors"], 1):
            print(
                f"  {i}. {error['tool_name']}: {error['category']} - {error['error_message'][:50]}..."
            )

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)

    return middleware.get_statistics()


async def interactive_demo():
    """交互式演示（可选）"""
    print("\n🎮 交互式演示模式")
    print("=" * 40)

    middleware = ToolErrorHandlingMiddleware()

    while True:
        print("\n请选择测试场景:")
        print("1. 测试超时错误 (自动重试)")
        print("2. 测试权限错误 (通知用户)")
        print("3. 测试参数错误 (回退方案)")
        print("4. 测试资源错误 (需要人工介入)")
        print("5. 查看当前统计")
        print("6. 退出")

        choice = input("\n请输入选项 (1-6): ").strip()

        if choice == "1":
            print("\n测试超时错误...")

            # 模拟超时错误
            async def timeout_tool():
                await asyncio.sleep(0.3)
                raise TimeoutError("工具执行超时")

            wrapped = wrap_tool_call("timeout_tool", timeout_tool, middleware)
            result = await wrapped()
            print(f"结果: {result}")

        elif choice == "2":
            print("\n测试权限错误...")

            # 模拟权限错误
            async def permission_tool():
                raise PermissionError("没有访问权限")

            wrapped = wrap_tool_call("permission_tool", permission_tool, middleware)
            result = await wrapped()
            print(f"结果: {result}")

        elif choice == "3":
            print("\n测试参数错误...")

            # 模拟参数错误
            async def parameter_tool(x: int):
                if x < 0:
                    raise ValueError("参数不能为负数")
                return x * 2

            wrapped = wrap_tool_call("parameter_tool", parameter_tool, middleware)
            result = await wrapped(-5)
            print(f"结果: {result}")

        elif choice == "4":
            print("\n测试资源错误...")

            # 模拟资源错误
            async def resource_tool():
                raise MemoryError("内存不足")

            wrapped = wrap_tool_call("resource_tool", resource_tool, middleware)
            result = await wrapped()
            print(f"结果: {result}")

        elif choice == "5":
            print("\n当前统计信息:")
            print(middleware.generate_report())

        elif choice == "6":
            print("退出交互演示")
            break

        else:
            print("无效选项，请重新输入")


if __name__ == "__main__":
    import re  # 用于参数验证的正则匹配

    # 运行主演示
    try:
        stats = asyncio.run(main_demo())

        # 提供交互选项
        print("\n🎮 演示选项:")
        print("1. 查看详细统计信息 (JSON格式)")
        print("2. 运行交互式演示")
        print("3. 重新运行主演示")
        print("4. 退出")

        while True:
            choice = input("\n请选择 (1-4): ").strip()
            if choice == "1":
                print("\n📊 详细统计信息 (JSON格式):")
                print(json.dumps(stats, indent=2, ensure_ascii=False))
            elif choice == "2":
                print("\n启动交互式演示...")
                asyncio.run(interactive_demo())
            elif choice == "3":
                print("\n重新运行主演示...")
                stats = asyncio.run(main_demo())
            elif choice == "4":
                print("退出演示程序")
                break
            else:
                print("无效选择，请重新输入")

    except KeyboardInterrupt:
        print("\n\n演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示运行出错: {e}")
        import traceback

        traceback.print_exc()
