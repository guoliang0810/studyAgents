#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 4 Lesson 16: 实战：跟踪中间件执行 - 课堂演示代码

本文件提供完整的中间件执行追踪系统实现，用于课堂教学演示。
采用四部分结构设计，全面展示中间件执行追踪的各个方面：
1. 追踪系统核心架构与数据结构
2. 追踪包装器与无侵入式监控
3. 性能报告生成与瓶颈分析
4. 工程化集成与生产实践

教学目标：
1. 理解中间件执行跟踪的重要性及应用场景
2. 掌握中间件执行跟踪器的设计与实现原理
3. 学会使用追踪包装器监控中间件执行性能
4. 掌握性能报告生成与瓶颈定位分析方法

运行要求：
Python 3.12+, 安装依赖: asyncio, typing-extensions, dataclasses-json

作者: 张老师 (DeerFlow核心贡献者)
版本: v1.0
日期: 2024年3月29日
"""

import asyncio
import time
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from abc import ABC, abstractmethod
import sys

# ============================================================================
# 第一部分：追踪系统核心架构与数据结构
# ============================================================================


@dataclass
class MiddlewareExecution:
    """
    中间件执行记录数据结构 - 教学注释:

    这个数据类用于记录单个中间件执行的完整信息，包括：
    1. 中间件名称: 标识是哪个中间件
    2. 执行阶段: "before" 或 "after"，表示前置处理还是后置处理
    3. 开始时间: 高精度时间戳，用于计算执行时长
    4. 结束时间: 高精度时间戳
    5. 执行时长: 自动计算，单位为毫秒
    6. 成功状态: 执行是否成功
    7. 错误信息: 如果执行失败，记录错误信息

    设计思考:
    - 使用@dataclass简化代码，自动生成__init__等方法
    - 添加duration_ms属性，自动计算执行时长
    - 支持序列化和反序列化，便于存储和传输
    - 字段设计要覆盖中间件执行的所有关键信息
    """

    middleware_name: str  # 中间件名称
    phase: str  # "before" 或 "after"
    start_time: float  # 开始时间（秒）
    end_time: float  # 结束时间（秒）
    success: bool  # 是否成功
    error: str = ""  # 错误信息

    @property
    def duration_ms(self) -> float:
        """计算执行时长（毫秒）"""
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于序列化和分析"""
        return {
            "middleware_name": self.middleware_name,
            "phase": self.phase,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
        }


class MiddlewareTracer:
    """
    中间件执行追踪器 - 教学注释:

    追踪器是整个追踪系统的核心，负责：
    1. 记录完整的请求执行过程
    2. 管理所有中间件的执行记录
    3. 生成详细的性能报告
    4. 支持错误追踪和瓶颈定位

    设计要点:
    - 使用列表存储所有执行记录，支持按时间顺序查询
    - 提供start_request和end_request方法记录请求整体时间
    - record_execution方法记录单个中间件执行
    - generate_report方法生成格式化性能报告
    - 支持统计分析和瓶颈定位

    性能考虑:
    - 执行记录存储在内存中，适用于单次请求追踪
    - 生产环境中可能需要考虑持久化存储和采样策略
    """

    def __init__(self):
        self.executions: List[MiddlewareExecution] = []
        self.request_start: float = 0
        self.request_end: float = 0
        print(f"🔧 [{self.__class__.__name__}] 追踪器初始化完成")

    def start_request(self):
        """开始追踪整个请求"""
        self.request_start = time.time()
        self.executions.clear()
        print(f"⏱️  [{self.__class__.__name__}] 开始追踪请求")

    def end_request(self):
        """结束请求追踪"""
        self.request_end = time.time()
        total_duration = (self.request_end - self.request_start) * 1000
        print(f"⏱️  [{self.__class__.__name__}] 请求完成: {total_duration:.2f}ms")

    def record_execution(
        self,
        middleware_name: str,
        phase: str,
        start_time: float,
        end_time: float,
        success: bool = True,
        error: str = "",
    ):
        """记录单个中间件执行"""
        execution = MiddlewareExecution(
            middleware_name=middleware_name,
            phase=phase,
            start_time=start_time,
            end_time=end_time,
            success=success,
            error=error,
        )
        self.executions.append(execution)
        status = "✅" if success else "❌"
        print(f"  {status} {middleware_name}.{phase}: {execution.duration_ms:.2f}ms")
        if error:
            print(f"    ⚠️ 错误: {error}")

    def generate_report(self) -> str:
        """生成格式化的执行报告"""

        # 计算总体统计
        total_duration = (self.request_end - self.request_start) * 1000
        before_count = len([e for e in self.executions if e.phase == "before"])
        after_count = len([e for e in self.executions if e.phase == "after"])
        success_count = sum(1 for e in self.executions if e.success)
        error_count = len(self.executions) - success_count

        # 按中间件分组统计
        middleware_stats: Dict[str, Dict[str, Any]] = {}
        for execution in self.executions:
            name = execution.middleware_name
            if name not in middleware_stats:
                middleware_stats[name] = {
                    "before_durations": [],
                    "after_durations": [],
                    "errors": [],
                }

            if execution.phase == "before":
                middleware_stats[name]["before_durations"].append(execution.duration_ms)
            else:
                middleware_stats[name]["after_durations"].append(execution.duration_ms)

            if not execution.success:
                middleware_stats[name]["errors"].append(execution.error)

        # 找出最慢的中间件执行
        slowest = (
            max(self.executions, key=lambda e: e.duration_ms)
            if self.executions
            else None
        )

        # 生成格式化报告
        report_lines = []
        report_lines.append("═══════════════════════════════════════════")
        report_lines.append("        中间件执行追踪报告")
        report_lines.append("═══════════════════════════════════════════")
        report_lines.append("")
        report_lines.append("📊 总体统计:")
        report_lines.append(f"   • 总执行时间: {total_duration:.2f}ms")
        report_lines.append(f"   • 前置中间件数: {before_count}")
        report_lines.append(f"   • 后置中间件数: {after_count}")
        report_lines.append(f"   • 成功执行: {success_count}")
        report_lines.append(f"   • 失败执行: {error_count}")
        report_lines.append("")

        report_lines.append("⏱️  执行时间明细:")
        report_lines.append("   【前置处理】")
        for name, stats in middleware_stats.items():
            if stats["before_durations"]:
                avg_time = sum(stats["before_durations"]) / len(
                    stats["before_durations"]
                )
                report_lines.append(
                    f"   • {name}: {avg_time:.2f}ms (共{len(stats['before_durations'])}次)"
                )

        report_lines.append("")
        report_lines.append("   【后置处理】")
        for name, stats in middleware_stats.items():
            if stats["after_durations"]:
                avg_time = sum(stats["after_durations"]) / len(stats["after_durations"])
                report_lines.append(
                    f"   • {name}: {avg_time:.2f}ms (共{len(stats['after_durations'])}次)"
                )

        report_lines.append("")
        if slowest:
            report_lines.append("🐌 最慢中间件:")
            report_lines.append(
                f"   • {slowest.middleware_name} ({slowest.phase}): {slowest.duration_ms:.2f}ms"
            )
        else:
            report_lines.append("🐌 最慢中间件: 无执行记录")

        report_lines.append("")
        report_lines.append("⚠️  错误列表:")
        error_found = False
        for name, stats in middleware_stats.items():
            if stats["errors"]:
                error_found = True
                for i, error in enumerate(stats["errors"]):
                    report_lines.append(f"   • {name}: {error}")

        if not error_found:
            report_lines.append("   • 无错误")

        report_lines.append("═══════════════════════════════════════════")

        return "\n".join(report_lines)

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息，便于程序化分析"""
        if not self.executions:
            return {}

        total_duration = (self.request_end - self.request_start) * 1000
        before_count = len([e for e in self.executions if e.phase == "before"])
        after_count = len([e for e in self.executions if e.phase == "after"])
        success_count = sum(1 for e in self.executions if e.success)

        # 按中间件统计
        middleware_stats = {}
        for execution in self.executions:
            name = execution.middleware_name
            if name not in middleware_stats:
                middleware_stats[name] = {"before": [], "after": [], "errors": []}

            if execution.phase == "before":
                middleware_stats[name]["before"].append(execution.duration_ms)
            else:
                middleware_stats[name]["after"].append(execution.duration_ms)

            if not execution.success:
                middleware_stats[name]["errors"].append(execution.error)

        return {
            "total_duration_ms": total_duration,
            "before_count": before_count,
            "after_count": after_count,
            "success_count": success_count,
            "error_count": len(self.executions) - success_count,
            "middleware_stats": middleware_stats,
        }


# ============================================================================
# 第二部分：追踪包装器与无侵入式监控
# ============================================================================


class AgentRequest:
    """Agent请求数据结构"""

    def __init__(
        self, user_id: str, message: str, metadata: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.message = message
        self.metadata = metadata or {}


class AgentResponse:
    """Agent响应数据结构"""

    def __init__(self, content: str, success: bool = True):
        self.content = content
        self.success = success


class AgentMiddleware(ABC):
    """中间件基类 - 定义标准中间件接口"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def before_agent(self, request: AgentRequest):
        """在Agent执行前调用"""
        pass

    @abstractmethod
    async def after_agent(self, response: AgentResponse):
        """在Agent执行后调用"""
        pass


class TracedMiddleware:
    """
    带追踪功能的中间件包装器 - 教学注释:

    包装器设计模式应用：
    1. 不修改原有中间件代码，实现功能扩展
    2. 可以灵活添加/移除追踪功能
    3. 支持对任意中间件进行包装
    4. 保持原有中间件的接口和行为

    设计要点:
    - 包装器持有原中间件实例和追踪器实例
    - before_agent和after_agent方法中包装追踪逻辑
    - 使用try-except确保错误被正确记录和传播
    - 保持异步接口的一致性

    性能考虑:
    - 包装器本身会带来少量性能开销（时间测量、记录存储）
    - 生产环境中可能需要采样策略减少开销
    """

    def __init__(self, middleware: AgentMiddleware, tracer: MiddlewareTracer):
        self.middleware = middleware
        self.tracer = tracer

    async def before_agent(self, request: AgentRequest):
        """追踪前置执行"""
        start = time.time()
        try:
            result = await self.middleware.before_agent(request)
            self.tracer.record_execution(
                self.middleware.name, "before", start, time.time(), success=True
            )
            return result
        except Exception as e:
            self.tracer.record_execution(
                self.middleware.name,
                "before",
                start,
                time.time(),
                success=False,
                error=str(e),
            )
            raise

    async def after_agent(self, response: AgentResponse):
        """追踪后置执行"""
        start = time.time()
        try:
            result = await self.middleware.after_agent(response)
            self.tracer.record_execution(
                self.middleware.name, "after", start, time.time(), success=True
            )
            return result
        except Exception as e:
            self.tracer.record_execution(
                self.middleware.name,
                "after",
                start,
                time.time(),
                success=False,
                error=str(e),
            )
            raise


# ============================================================================
# 第三部分：示例中间件实现
# ============================================================================


class AuthenticationMiddleware(AgentMiddleware):
    """认证中间件 - 模拟用户认证"""

    def __init__(self):
        super().__init__("authentication_middleware")

    async def before_agent(self, request: AgentRequest):
        """检查用户认证令牌"""
        await asyncio.sleep(0.01)  # 模拟网络延迟
        token = request.metadata.get("auth_token")
        if not token:
            raise ValueError("未提供认证令牌")
        if token != "user_token_123":
            raise ValueError("认证令牌无效")

        print(f"   🔐 [{self.name}] 用户认证通过: {request.user_id}")
        return request

    async def after_agent(self, response: AgentResponse):
        """后置处理：记录认证日志"""
        await asyncio.sleep(0.002)  # 模拟快速处理
        print(f"   📝 [{self.name}] 认证日志记录完成")
        return response


class LoggingMiddleware(AgentMiddleware):
    """日志中间件 - 记录请求和响应"""

    def __init__(self):
        super().__init__("logging_middleware")

    async def before_agent(self, request: AgentRequest):
        """记录请求日志"""
        await asyncio.sleep(0.005)  # 模拟日志写入延迟
        print(
            f"   📋 [{self.name}] 记录请求: {request.user_id} - {request.message[:20]}..."
        )
        return request

    async def after_agent(self, response: AgentResponse):
        """记录响应日志"""
        await asyncio.sleep(0.003)  # 模拟日志写入延迟
        print(
            f"   📋 [{self.name}] 记录响应: {'成功' if response.success else '失败'} - {response.content[:20]}..."
        )
        return response


class RateLimitMiddleware(AgentMiddleware):
    """限流中间件 - 模拟请求频率限制"""

    def __init__(self, requests_per_minute: int = 100):
        super().__init__("rate_limit_middleware")
        self.requests_per_minute = requests_per_minute
        self.request_counts: Dict[str, List[float]] = {}

    async def before_agent(self, request: AgentRequest):
        """检查请求频率"""
        await asyncio.sleep(0.008)  # 模拟Redis查询延迟

        user_id = request.user_id
        now = time.time()

        # 清理一分钟前的记录
        if user_id in self.request_counts:
            self.request_counts[user_id] = [
                t for t in self.request_counts[user_id] if now - t < 60
            ]
        else:
            self.request_counts[user_id] = []

        # 检查是否超过限制
        if len(self.request_counts[user_id]) >= self.requests_per_minute:
            raise ValueError(f"请求频率超过限制: {self.requests_per_minute}次/分钟")

        # 记录本次请求
        self.request_counts[user_id].append(now)
        print(f"   🚦 [{self.name}] 请求频率检查通过: {user_id}")
        return request

    async def after_agent(self, response: AgentResponse):
        """后置处理：更新限流统计"""
        await asyncio.sleep(0.004)  # 模拟快速处理
        print(f"   📊 [{self.name}] 限流统计更新完成")
        return response


class SlowMiddleware(AgentMiddleware):
    """模拟慢中间件 - 用于演示性能瓶颈"""

    def __init__(self, delay: float = 0.1):
        super().__init__("slow_middleware")
        self.delay = delay

    async def before_agent(self, request: AgentRequest):
        """模拟慢前置处理"""
        await asyncio.sleep(self.delay)
        print(f"   🐌 [{self.name}] 慢前置处理完成: {self.delay * 1000:.0f}ms延迟")
        return request

    async def after_agent(self, response: AgentResponse):
        """模拟慢后置处理"""
        await asyncio.sleep(self.delay / 2)
        print(f"   🐌 [{self.name}] 慢后置处理完成: {self.delay * 50:.0f}ms延迟")
        return response


class ErrorMiddleware(AgentMiddleware):
    """错误中间件 - 用于演示错误追踪"""

    def __init__(self, fail_probability: float = 0.3):
        super().__init__("error_middleware")
        self.fail_probability = fail_probability

    async def before_agent(self, request: AgentRequest):
        """随机失败，用于演示错误追踪"""
        await asyncio.sleep(0.005)
        import random

        if random.random() < self.fail_probability:
            raise ValueError("模拟随机失败: 中间件处理异常")
        print(f"   🎲 [{self.name}] 随机检查通过")
        return request

    async def after_agent(self, response: AgentResponse):
        """后置处理"""
        await asyncio.sleep(0.003)
        return response


# ============================================================================
# 第四部分：中间件链与测试系统
# ============================================================================


class MiddlewareChain:
    """
    简化版中间件链 - 教学注释:

    为了演示追踪系统，这里实现一个简化的中间件链。
    实际DeerFlow系统中的MiddlewareChain更复杂，支持优先级、动态调度等。
    """

    def __init__(self, middlewares: List[AgentMiddleware]):
        self.middlewares = middlewares

    async def execute_before(self, request: AgentRequest):
        """执行前置链"""
        print("\n执行前置链:")
        current_request = request
        for middleware in self.middlewares:
            current_request = await middleware.before_agent(current_request)
        return current_request

    async def execute_after(self, response: AgentResponse):
        """执行后置链（逆序）"""
        print("\n执行后置链:")
        current_response = response
        for middleware in reversed(self.middlewares):
            current_response = await middleware.after_agent(current_response)
        return current_response


async def test_tracer():
    """
    完整测试函数 - 教学注释:

    这个函数演示了完整的追踪系统使用流程：
    1. 创建追踪器
    2. 创建中间件实例
    3. 包装为追踪中间件
    4. 创建中间件链
    5. 执行请求处理
    6. 生成性能报告

    通过这个演示，学生可以：
    1. 理解追踪系统的完整工作流程
    2. 看到实际执行结果和性能报告
    3. 学习如何集成追踪系统到现有代码
    """

    # 创建追踪器
    tracer = MiddlewareTracer()

    # 创建中间件实例
    auth = AuthenticationMiddleware()
    logger = LoggingMiddleware()
    rate = RateLimitMiddleware(requests_per_minute=100)
    slow = SlowMiddleware(delay=0.1)  # 100ms延迟

    # 包装为追踪中间件
    traced_middlewares = [
        TracedMiddleware(m, tracer) for m in [auth, logger, rate, slow]
    ]

    # 创建中间件链
    chain = MiddlewareChain(traced_middlewares)

    # 开始追踪
    tracer.start_request()

    # 创建测试请求
    request = AgentRequest(
        user_id="test_user",
        message="这是一个测试消息，用于演示中间件执行追踪系统",
        metadata={"auth_token": "user_token_123"},
    )

    # 执行前置链
    try:
        await chain.execute_before(request)
    except Exception as e:
        print(f"   ❌ 前置链执行失败: {e}")

    # 模拟Agent处理
    print("\n模拟Agent处理 (耗时50ms)...")
    await asyncio.sleep(0.05)

    # 执行后置链
    response = AgentResponse(content="测试响应内容，表示Agent处理成功", success=True)
    try:
        await chain.execute_after(response)
    except Exception as e:
        print(f"   ❌ 后置链执行失败: {e}")

    # 结束追踪
    tracer.end_request()

    # 生成并显示报告
    print("\n" + tracer.generate_report())

    # 返回统计信息
    return tracer.get_statistics()


async def test_error_scenario():
    """测试错误场景 - 演示错误追踪"""
    print("\n" + "=" * 60)
    print("测试错误场景")
    print("=" * 60)

    tracer = MiddlewareTracer()

    # 创建包含错误中间件的链
    auth = AuthenticationMiddleware()
    logger = LoggingMiddleware()
    error_middleware = ErrorMiddleware(fail_probability=0.5)  # 50%失败概率

    traced_middlewares = [
        TracedMiddleware(m, tracer) for m in [auth, logger, error_middleware]
    ]

    chain = MiddlewareChain(traced_middlewares)

    tracer.start_request()

    request = AgentRequest(
        user_id="error_test_user",
        message="测试错误场景",
        metadata={"auth_token": "user_token_123"},
    )

    try:
        await chain.execute_before(request)
    except Exception as e:
        print(f"   ❌ 请求处理失败（预期中）: {e}")

    # 即使前置链失败，也尝试执行后置链（实际系统中可能需要特殊处理）
    response = AgentResponse(content="错误场景响应", success=False)
    try:
        await chain.execute_after(response)
    except Exception as e:
        print(f"   ❌ 后置链执行失败: {e}")

    tracer.end_request()

    print("\n" + tracer.generate_report())


async def test_performance_comparison():
    """测试性能对比 - 有无追踪系统的性能差异"""
    print("\n" + "=" * 60)
    print("测试性能对比：有无追踪系统")
    print("=" * 60)

    # 测试无追踪系统
    print("\n1. 无追踪系统:")
    start = time.time()

    auth = AuthenticationMiddleware()
    logger = LoggingMiddleware()
    rate = RateLimitMiddleware()

    chain = MiddlewareChain([auth, logger, rate])
    request = AgentRequest(
        "perf_user", "性能测试消息", {"auth_token": "user_token_123"}
    )

    await chain.execute_before(request)
    await asyncio.sleep(0.05)
    response = AgentResponse("性能测试响应", True)
    await chain.execute_after(response)

    no_trace_time = (time.time() - start) * 1000
    print(f"   总执行时间: {no_trace_time:.2f}ms")

    # 测试有追踪系统
    print("\n2. 有追踪系统:")
    start = time.time()

    tracer = MiddlewareTracer()
    traced_auth = TracedMiddleware(auth, tracer)
    traced_logger = TracedMiddleware(logger, tracer)
    traced_rate = TracedMiddleware(rate, tracer)

    tracer.start_request()
    chain = MiddlewareChain([traced_auth, traced_logger, traced_rate])

    await chain.execute_before(request)
    await asyncio.sleep(0.05)
    response = AgentResponse("性能测试响应", True)
    await chain.execute_after(response)

    tracer.end_request()

    trace_time = (time.time() - start) * 1000
    print(f"   总执行时间: {trace_time:.2f}ms")

    # 计算开销
    overhead = trace_time - no_trace_time
    overhead_percentage = (overhead / no_trace_time) * 100

    print(f"\n📊 追踪系统开销分析:")
    print(f"   • 无追踪: {no_trace_time:.2f}ms")
    print(f"   • 有追踪: {trace_time:.2f}ms")
    print(f"   • 绝对开销: {overhead:.2f}ms")
    print(f"   • 相对开销: {overhead_percentage:.2f}%")

    if overhead_percentage < 5:
        print("   ✅ 追踪系统开销可接受 (<5%)")
    else:
        print("   ⚠️  追踪系统开销较高，建议优化")


# ============================================================================
# 第五部分：主函数与演示执行
# ============================================================================


async def main_demo():
    """主演示函数 - 运行所有测试场景"""
    print("=" * 60)
    print("Day 4 Lesson 16: 中间件执行追踪系统演示")
    print("=" * 60)

    # 场景1: 基本追踪演示
    print("\n场景1: 基本追踪演示")
    print("-" * 40)
    stats = await test_tracer()

    # 场景2: 错误追踪演示
    await test_error_scenario()

    # 场景3: 性能对比演示
    await test_performance_comparison()

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)

    return stats


if __name__ == "__main__":
    # 运行主演示
    try:
        stats = asyncio.run(main_demo())

        # 提供交互选项
        print("\n🎮 交互选项:")
        print("1. 查看统计信息 (JSON格式)")
        print("2. 重新运行基本演示")
        print("3. 退出")

        while True:
            choice = input("\n请选择 (1-3): ").strip()
            if choice == "1":
                print("\n📊 统计信息 (JSON格式):")
                print(json.dumps(stats, indent=2, ensure_ascii=False))
            elif choice == "2":
                print("\n重新运行基本演示...")
                asyncio.run(test_tracer())
            elif choice == "3":
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
