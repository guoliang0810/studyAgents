#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 4 Lesson 14: 中间件链编排与执行流程 - 课堂演示代码

本文件提供完整的中间件链编排与执行流程实现，用于课堂教学演示。
采用四部分结构设计，全面展示中间件链编排的各个方面：
1. 中间件链架构与编排引擎
2. 高级中间件实现与限流机制
3. 动态调度与智能编排系统
4. 中间件编排工程化分析与最佳实践

教学目标：
1. 理解中间件执行顺序对系统行为的影响
2. 掌握MiddlewareChain类的设计和实现原理
3. 了解限流中间件的实现机制和应用场景
4. 理解动态中间件调度器的设计思路

运行要求：
Python 3.12+, 安装依赖: asyncio, typing-extensions, dataclasses-json

作者: 张老师 (DeerFlow核心贡献者)
版本: v1.0
日期: 2024年3月28日
"""

import asyncio
import time
import random
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import hashlib
import json
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# 第一部分：中间件链架构与编排引擎
# ============================================================================


class MiddlewareExecutionOrder(Enum):
    """中间件执行顺序配置枚举"""

    FIXED_ORDER = "fixed_order"  # 固定顺序
    DYNAMIC_ORDER = "dynamic_order"  # 动态顺序
    PRIORITY_BASED = "priority_based"  # 基于优先级


@dataclass
class AgentRequest:
    """Agent请求数据结构"""

    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "message": self.message,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class AgentResponse:
    """Agent响应数据结构"""

    result: str
    status_code: int = 200
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "result": self.result,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class AgentMiddleware:
    """中间件基类 - 定义标准中间件接口"""

    def __init__(self, name: str, priority: int = 10):
        self.name = name
        self.priority = priority  # 优先级，数值越小优先级越高
        self.enabled = True

    async def before_agent(self, request: AgentRequest) -> Optional[AgentRequest]:
        """
        在Agent执行前调用的方法
        可以修改请求、验证请求、记录日志等
        返回修改后的请求或None（表示终止执行）
        """
        raise NotImplementedError("子类必须实现before_agent方法")

    async def after_agent(
        self, request: AgentRequest, response: AgentResponse
    ) -> Optional[AgentResponse]:
        """
        在Agent执行后调用的方法
        可以修改响应、记录日志、处理错误等
        返回修改后的响应或None（表示使用原响应）
        """
        raise NotImplementedError("子类必须实现after_agent方法")

    async def on_error(
        self, request: AgentRequest, error: Exception
    ) -> Optional[AgentResponse]:
        """
        错误处理方法
        当中间件链执行过程中发生错误时调用
        可以处理错误并返回响应，或重新抛出异常
        """
        logger.error(f"中间件 {self.name} 处理请求时发生错误: {error}")
        return None


class MiddlewareChain:
    """
    中间件链编排引擎 - 核心编排组件

    功能特性：
    1. 支持中间件链的构建和管理
    2. 支持前置顺序执行和后置逆序执行
    3. 支持中间件优先级配置
    4. 支持错误处理和恢复机制
    5. 支持中间件链的动态调整
    """

    def __init__(
        self,
        name: str,
        execution_order: MiddlewareExecutionOrder = MiddlewareExecutionOrder.FIXED_ORDER,
    ):
        self.name = name
        self.execution_order = execution_order
        self.middlewares: List[AgentMiddleware] = []
        self._sorted_middlewares: List[AgentMiddleware] = []
        self._needs_sorting = True

    def add_middleware(
        self, middleware: AgentMiddleware, position: Optional[int] = None
    ) -> None:
        """
        添加中间件到链中

        Args:
            middleware: 要添加的中间件
            position: 插入位置，None表示追加到末尾
        """
        if position is None:
            self.middlewares.append(middleware)
        else:
            self.middlewares.insert(position, middleware)

        self._needs_sorting = True

    def remove_middleware(self, middleware_name: str) -> bool:
        """
        从链中移除中间件

        Args:
            middleware_name: 要移除的中间件名称

        Returns:
            是否成功移除
        """
        for i, mw in enumerate(self.middlewares):
            if mw.name == middleware_name:
                self.middlewares.pop(i)
                self._needs_sorting = True
                return True
        return False

    def _sort_middlewares(self) -> None:
        """根据执行顺序策略对中间件进行排序"""
        if self.execution_order == MiddlewareExecutionOrder.FIXED_ORDER:
            # 固定顺序 - 按照添加顺序
            self._sorted_middlewares = self.middlewares.copy()
        elif self.execution_order == MiddlewareExecutionOrder.PRIORITY_BASED:
            # 基于优先级 - 优先级数值越小越先执行
            self._sorted_middlewares = sorted(
                self.middlewares, key=lambda m: m.priority
            )
        else:
            # 动态顺序 - 保持原始顺序，动态调度器会调整
            self._sorted_middlewares = self.middlewares.copy()

        self._needs_sorting = False

    def get_sorted_middlewares(self) -> List[AgentMiddleware]:
        """获取排序后的中间件列表"""
        if self._needs_sorting:
            self._sort_middlewares()
        return self._sorted_middlewares

    async def execute_before_chain(
        self, request: AgentRequest
    ) -> Optional[AgentRequest]:
        """
        执行前置中间件链（顺序执行）

        Args:
            request: 原始请求

        Returns:
            处理后的请求或None（表示终止执行）
        """
        # 获取排序后的中间件列表
        middlewares = self.get_sorted_middlewares()

        current_request = request

        # 顺序执行前置处理
        for middleware in middlewares:
            if not middleware.enabled:
                logger.debug(f"跳过禁用的中间件: {middleware.name}")
                continue

            try:
                logger.debug(f"执行前置中间件: {middleware.name}")
                result = await middleware.before_agent(current_request)

                if result is None:
                    # 中间件返回None表示终止执行
                    logger.info(f"中间件 {middleware.name} 终止了请求执行")
                    return None

                current_request = result

            except Exception as e:
                logger.error(f"中间件 {middleware.name} 前置处理失败: {e}")
                # 调用中间件的错误处理方法
                error_response = await middleware.on_error(current_request, e)
                if error_response is not None:
                    # 中间件处理了错误，返回响应
                    return error_response
                else:
                    # 中间件未处理错误，继续传播
                    raise

        return current_request

    async def execute_after_chain(
        self, request: AgentRequest, response: AgentResponse
    ) -> AgentResponse:
        """
        执行后置中间件链（逆序执行）

        Args:
            request: 原始请求
            response: Agent生成的响应

        Returns:
            处理后的响应
        """
        # 获取排序后的中间件列表（逆序）
        middlewares = list(reversed(self.get_sorted_middlewares()))

        current_response = response

        # 逆序执行后置处理
        for middleware in middlewares:
            if not middleware.enabled:
                logger.debug(f"跳过禁用的中间件: {middleware.name}")
                continue

            try:
                logger.debug(f"执行后置中间件: {middleware.name}")
                result = await middleware.after_agent(request, current_response)

                if result is not None:
                    current_response = result

            except Exception as e:
                logger.error(f"中间件 {middleware.name} 后置处理失败: {e}")
                # 调用中间件的错误处理方法
                error_response = await middleware.on_error(request, e)
                if error_response is not None:
                    # 中间件处理了错误，更新响应
                    current_response = error_response

        return current_response

    async def execute_full_chain(
        self, request: AgentRequest, agent_func: Callable[[AgentRequest], AgentResponse]
    ) -> AgentResponse:
        """
        执行完整的中间件链（前置 + Agent + 后置）

        Args:
            request: 原始请求
            agent_func: Agent执行函数

        Returns:
            最终响应
        """
        logger.info(f"开始执行中间件链: {self.name}")

        # 1. 执行前置中间件链
        processed_request = await self.execute_before_chain(request)

        if processed_request is None:
            # 前置中间件链终止了执行
            return AgentResponse(
                result="请求被中间件终止",
                status_code=403,
                error_message="请求被中间件终止执行",
            )

        # 2. 执行Agent
        try:
            agent_response = await agent_func(processed_request)
        except Exception as e:
            logger.error(f"Agent执行失败: {e}")
            agent_response = AgentResponse(
                result="Agent执行失败", status_code=500, error_message=str(e)
            )

        # 3. 执行后置中间件链
        final_response = await self.execute_after_chain(
            processed_request, agent_response
        )

        logger.info(f"中间件链执行完成: {self.name}")
        return final_response


class SimpleAgent:
    """简单的Agent实现，用于演示"""

    def __init__(self, name: str):
        self.name = name

    async def process(self, request: AgentRequest) -> AgentResponse:
        """处理请求"""
        logger.info(f"Agent {self.name} 处理请求: {request.message}")

        # 模拟处理逻辑
        await asyncio.sleep(0.1)  # 模拟处理耗时

        result = f"Agent {self.name} 处理结果: {request.message.upper()}"

        return AgentResponse(
            result=result,
            status_code=200,
            metadata={"agent_name": self.name, "processed_at": time.time()},
        )


# ============================================================================
# 第二部分：高级中间件实现与限流机制
# ============================================================================


class LoggingMiddleware(AgentMiddleware):
    """日志中间件 - 记录请求和响应日志"""

    def __init__(self):
        super().__init__(
            "logging_middleware", priority=100
        )  # 优先级低，最后执行前置，最先执行后置

    async def before_agent(self, request: AgentRequest) -> Optional[AgentRequest]:
        """记录请求日志"""
        logger.info(
            f"[请求日志] 用户: {request.user_id}, 消息: {request.message}, 时间: {datetime.fromtimestamp(request.timestamp)}"
        )

        # 添加日志标记到请求元数据
        if "log_entries" not in request.metadata:
            request.metadata["log_entries"] = []

        request.metadata["log_entries"].append(
            {
                "type": "request",
                "middleware": self.name,
                "timestamp": time.time(),
                "user_id": request.user_id,
                "message": request.message,
            }
        )

        return request

    async def after_agent(
        self, request: AgentRequest, response: AgentResponse
    ) -> Optional[AgentResponse]:
        """记录响应日志"""
        logger.info(
            f"[响应日志] 状态码: {response.status_code}, 结果: {response.result[:50]}, 错误: {response.error_message}"
        )

        # 添加日志标记到响应元数据
        if "log_entries" not in response.metadata:
            response.metadata["log_entries"] = []

        response.metadata["log_entries"].append(
            {
                "type": "response",
                "middleware": self.name,
                "timestamp": time.time(),
                "status_code": response.status_code,
                "has_error": response.error_message is not None,
            }
        )

        return response


class AuthenticationMiddleware(AgentMiddleware):
    """认证中间件 - 验证用户身份"""

    def __init__(self, valid_tokens: Set[str]):
        super().__init__("authentication_middleware", priority=1)  # 高优先级，最先执行
        self.valid_tokens = valid_tokens

    async def before_agent(self, request: AgentRequest) -> Optional[AgentRequest]:
        """验证用户身份"""
        token = request.metadata.get("auth_token")

        if not token:
            logger.warning(f"认证失败: 请求缺少认证令牌")
            return None  # 终止执行

        if token not in self.valid_tokens:
            logger.warning(f"认证失败: 无效的认证令牌")
            return None  # 终止执行

        logger.info(f"认证成功: 用户 {request.user_id}")

        # 添加认证信息到请求元数据
        request.metadata["authenticated"] = True
        request.metadata["auth_time"] = time.time()

        return request


class RateLimitMiddleware(AgentMiddleware):
    """
    限流中间件 - 基于时间窗口的请求限流

    实现算法: 滑动时间窗口算法
    每个用户在每个时间窗口内只能发送指定数量的请求
    """

    def __init__(
        self, window_size_seconds: int = 60, max_requests_per_window: int = 10
    ):
        super().__init__("rate_limit_middleware", priority=2)
        self.window_size_seconds = window_size_seconds
        self.max_requests_per_window = max_requests_per_window

        # 存储每个用户的请求时间戳
        self.user_requests: Dict[str, deque] = defaultdict(deque)

    def _clean_old_requests(self, user_id: str, current_time: float) -> None:
        """清理过期的请求记录"""
        if user_id not in self.user_requests:
            return

        window_start = current_time - self.window_size_seconds

        # 移除时间窗口之外的请求时间戳
        while (
            self.user_requests[user_id]
            and self.user_requests[user_id][0] < window_start
        ):
            self.user_requests[user_id].popleft()

    async def before_agent(self, request: AgentRequest) -> Optional[AgentRequest]:
        """检查请求频率"""
        if not request.user_id:
            # 没有用户ID，跳过限流检查
            return request

        current_time = time.time()

        # 清理过期的请求记录
        self._clean_old_requests(request.user_id, current_time)

        # 检查当前时间窗口内的请求数量
        request_count = len(self.user_requests[request.user_id])

        if request_count >= self.max_requests_per_window:
            logger.warning(
                f"限流触发: 用户 {request.user_id} 在 {self.window_size_seconds}秒内已发送{request_count}个请求"
            )

            # 计算需要等待的时间
            oldest_request_time = self.user_requests[request.user_id][0]
            window_end = oldest_request_time + self.window_size_seconds
            wait_time = max(0, window_end - current_time)

            # 返回限流响应
            request.metadata["rate_limited"] = True
            request.metadata["wait_time_seconds"] = wait_time
            request.metadata["retry_after"] = window_end

            return None  # 终止执行

        # 记录当前请求时间
        self.user_requests[request.user_id].append(current_time)

        # 添加限流信息到请求元数据
        request.metadata["rate_limit_info"] = {
            "window_size_seconds": self.window_size_seconds,
            "max_requests": self.max_requests_per_window,
            "current_request_count": request_count + 1,
            "window_start": current_time - self.window_size_seconds,
            "window_end": current_time,
        }

        return request


class ValidationMiddleware(AgentMiddleware):
    """验证中间件 - 验证请求数据的完整性和格式"""

    def __init__(self, max_message_length: int = 1000):
        super().__init__("validation_middleware", priority=3)
        self.max_message_length = max_message_length

    async def before_agent(self, request: AgentRequest) -> Optional[AgentRequest]:
        """验证请求数据"""
        # 检查消息是否为空
        if not request.message or not request.message.strip():
            logger.warning("验证失败: 消息内容为空")
            return None

        # 检查消息长度
        if len(request.message) > self.max_message_length:
            logger.warning(
                f"验证失败: 消息长度超过限制 ({len(request.message)} > {self.max_message_length})"
            )

            # 添加验证失败信息到请求元数据
            request.metadata["validation_failed"] = True
            request.metadata["validation_error"] = (
                f"消息长度超过{self.max_message_length}字符限制"
            )

            return None

        # 检查敏感词（简单示例）
        sensitive_words = ["密码", "密钥", "token", "secret"]
        for word in sensitive_words:
            if word in request.message.lower():
                logger.warning(f"验证失败: 消息包含敏感词 '{word}'")
                request.metadata["sensitive_word_detected"] = word
                # 这里可以选择继续执行，但记录警告

        # 添加验证信息到请求元数据
        request.metadata["validated"] = True
        request.metadata["validation_timestamp"] = time.time()

        return request


class CacheMiddleware(AgentMiddleware):
    """缓存中间件 - 缓存请求结果，减少重复计算"""

    def __init__(self, cache_ttl_seconds: int = 300):
        super().__init__("cache_middleware", priority=5)
        self.cache_ttl_seconds = cache_ttl_seconds

        # 简单的内存缓存
        self.cache: Dict[str, Tuple[AgentResponse, float]] = {}

    def _get_cache_key(self, request: AgentRequest) -> str:
        """生成缓存键"""
        # 基于请求内容和用户ID生成缓存键
        key_data = f"{request.user_id}:{request.message}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def before_agent(self, request: AgentRequest) -> Optional[AgentRequest]:
        """检查缓存"""
        cache_key = self._get_cache_key(request)

        if cache_key in self.cache:
            cached_response, cached_time = self.cache[cache_key]

            # 检查缓存是否过期
            if time.time() - cached_time < self.cache_ttl_seconds:
                logger.info(f"缓存命中: 使用缓存的响应")

                # 添加缓存信息到响应
                cached_response.metadata["cached"] = True
                cached_response.metadata["cache_key"] = cache_key
                cached_response.metadata["cache_age_seconds"] = (
                    time.time() - cached_time
                )

                # 这里无法直接返回响应，需要在after_agent中处理
                # 我们将在请求元数据中标记缓存命中
                request.metadata["cache_hit"] = True
                request.metadata["cache_key"] = cache_key
                request.metadata["cached_response"] = cached_response
            else:
                # 缓存过期，删除
                del self.cache[cache_key]

        return request

    async def after_agent(
        self, request: AgentRequest, response: AgentResponse
    ) -> Optional[AgentResponse]:
        """缓存响应结果"""
        # 如果请求被缓存命中，直接返回缓存的响应
        if request.metadata.get("cache_hit"):
            cached_response = request.metadata.get("cached_response")
            if cached_response:
                logger.info(f"返回缓存响应")
                return cached_response

        # 只缓存成功的响应
        if response.status_code == 200:
            cache_key = self._get_cache_key(request)
            self.cache[cache_key] = (response, time.time())

            # 添加缓存信息到响应元数据
            response.metadata["cached"] = True
            response.metadata["cache_key"] = cache_key
            response.metadata["cache_ttl_seconds"] = self.cache_ttl_seconds

        return response


# ============================================================================
# 第三部分：动态调度与智能编排系统
# ============================================================================


class RequestFeatureAnalyzer:
    """请求特征分析器 - 分析请求特征，为动态调度提供依据"""

    def __init__(self):
        self.feature_weights = {
            "message_length": 0.2,
            "has_user_id": 0.3,
            "has_session_id": 0.2,
            "request_time": 0.1,
            "metadata_complexity": 0.2,
        }

    def analyze(self, request: AgentRequest) -> Dict[str, Any]:
        """分析请求特征"""
        features = {}

        # 消息长度特征
        features["message_length"] = len(request.message)

        # 用户ID特征
        features["has_user_id"] = 1.0 if request.user_id else 0.0

        # 会话ID特征
        features["has_session_id"] = 1.0 if request.session_id else 0.0

        # 请求时间特征（转换为一天中的小时）
        request_time = datetime.fromtimestamp(request.timestamp)
        features["request_time"] = request_time.hour / 24.0

        # 元数据复杂度特征
        features["metadata_complexity"] = len(json.dumps(request.metadata)) / 1000.0

        # 计算总体复杂度分数
        complexity_score = 0.0
        for feature_name, weight in self.feature_weights.items():
            if feature_name in features:
                complexity_score += features[feature_name] * weight

        features["complexity_score"] = complexity_score

        # 请求类型分类
        if features["complexity_score"] > 0.7:
            features["request_type"] = "complex"
        elif features["complexity_score"] > 0.4:
            features["request_type"] = "medium"
        else:
            features["request_type"] = "simple"

        return features


class DynamicMiddlewareScheduler:
    """
    动态中间件调度器 - 根据请求特征动态调整中间件执行顺序和启用状态

    调度策略：
    1. 简单请求：跳过部分验证和缓存中间件
    2. 复杂请求：启用所有中间件，调整执行顺序
    3. 高峰期：启用限流中间件，调整优先级
    4. 低峰期：禁用限流中间件，提高响应速度
    """

    def __init__(self, feature_analyzer: RequestFeatureAnalyzer):
        self.feature_analyzer = feature_analyzer
        self.scheduling_strategies = {
            "simple": self._simple_request_strategy,
            "medium": self._medium_request_strategy,
            "complex": self._complex_request_strategy,
            "peak_hours": self._peak_hours_strategy,
            "off_peak": self._off_peak_strategy,
        }

    def _simple_request_strategy(
        self, middlewares: List[AgentMiddleware]
    ) -> List[AgentMiddleware]:
        """简单请求调度策略"""
        # 对于简单请求，禁用部分中间件以提高性能
        scheduled = []
        for mw in middlewares:
            if mw.name in ["cache_middleware", "rate_limit_middleware"]:
                # 禁用缓存和限流中间件
                mw_copy = type(mw).__new__(type(mw))
                mw_copy.__dict__ = mw.__dict__.copy()
                mw_copy.enabled = False
                scheduled.append(mw_copy)
            else:
                scheduled.append(mw)

        # 调整优先级：验证中间件优先级降低
        for mw in scheduled:
            if mw.name == "validation_middleware":
                mw.priority = 10  # 降低优先级

        return scheduled

    def _medium_request_strategy(
        self, middlewares: List[AgentMiddleware]
    ) -> List[AgentMiddleware]:
        """中等复杂度请求调度策略"""
        # 启用所有中间件，保持默认优先级
        return middlewares.copy()

    def _complex_request_strategy(
        self, middlewares: List[AgentMiddleware]
    ) -> List[AgentMiddleware]:
        """复杂请求调度策略"""
        # 启用所有中间件，调整优先级确保安全性和验证
        scheduled = middlewares.copy()

        # 提高认证和验证中间件的优先级
        for mw in scheduled:
            if mw.name == "authentication_middleware":
                mw.priority = 0  # 最高优先级
            elif mw.name == "validation_middleware":
                mw.priority = 1  # 次高优先级
            elif mw.name == "rate_limit_middleware":
                mw.priority = 2  # 提高限流优先级

        return scheduled

    def _peak_hours_strategy(
        self, middlewares: List[AgentMiddleware]
    ) -> List[AgentMiddleware]:
        """高峰期调度策略"""
        # 高峰期启用限流，提高限流阈值
        scheduled = []
        for mw in middlewares:
            if mw.name == "rate_limit_middleware":
                # 创建限流中间件副本，调整阈值
                mw_copy = type(mw).__new__(type(mw))
                mw_copy.__dict__ = mw.__dict__.copy()
                mw_copy.max_requests_per_window = 5  # 降低阈值
                mw_copy.enabled = True
                mw_copy.priority = 1  # 提高优先级
                scheduled.append(mw_copy)
            else:
                scheduled.append(mw)

        return scheduled

    def _off_peak_strategy(
        self, middlewares: List[AgentMiddleware]
    ) -> List[AgentMiddleware]:
        """低峰期调度策略"""
        # 低峰期禁用限流，提高响应速度
        scheduled = []
        for mw in middlewares:
            if mw.name == "rate_limit_middleware":
                mw_copy = type(mw).__new__(type(mw))
                mw_copy.__dict__ = mw.__dict__.copy()
                mw_copy.enabled = False
                scheduled.append(mw_copy)
            else:
                scheduled.append(mw)

        return scheduled

    def schedule_middlewares(
        self, request: AgentRequest, middlewares: List[AgentMiddleware]
    ) -> List[AgentMiddleware]:
        """根据请求特征调度中间件"""
        # 分析请求特征
        features = self.feature_analyzer.analyze(request)
        request_type = features.get("request_type", "medium")

        # 确定当前时间段
        current_hour = datetime.fromtimestamp(request.timestamp).hour
        time_strategy = "peak_hours" if 9 <= current_hour <= 17 else "off_peak"

        # 应用调度策略
        scheduled = middlewares.copy()

        # 首先应用时间策略
        scheduled = self.scheduling_strategies[time_strategy](scheduled)

        # 然后应用请求类型策略
        scheduled = self.scheduling_strategies[request_type](scheduled)

        return scheduled


class SmartMiddlewareChain(MiddlewareChain):
    """智能中间件链 - 集成动态调度器的增强中间件链"""

    def __init__(self, name: str):
        super().__init__(name, execution_order=MiddlewareExecutionOrder.DYNAMIC_ORDER)
        self.feature_analyzer = RequestFeatureAnalyzer()
        self.dynamic_scheduler = DynamicMiddlewareScheduler(self.feature_analyzer)

    def get_sorted_middlewares(self) -> List[AgentMiddleware]:
        """获取动态调度后的中间件列表"""
        # 首先获取基本排序
        middlewares = super().get_sorted_middlewares()

        # 动态调度需要请求上下文，这里返回原始列表
        # 实际调度将在execute_before_chain中进行
        return middlewares

    async def execute_before_chain(
        self, request: AgentRequest
    ) -> Optional[AgentRequest]:
        """执行动态调度后的前置中间件链"""
        # 动态调度中间件
        scheduled_middlewares = self.dynamic_scheduler.schedule_middlewares(
            request, self.middlewares
        )

        current_request = request

        # 顺序执行前置处理
        for middleware in scheduled_middlewares:
            if not middleware.enabled:
                logger.debug(f"跳过禁用的中间件: {middleware.name}")
                continue

            try:
                logger.debug(f"执行前置中间件: {middleware.name}")
                result = await middleware.before_agent(current_request)

                if result is None:
                    # 中间件返回None表示终止执行
                    logger.info(f"中间件 {middleware.name} 终止了请求执行")
                    return None

                current_request = result

            except Exception as e:
                logger.error(f"中间件 {middleware.name} 前置处理失败: {e}")
                error_response = await middleware.on_error(current_request, e)
                if error_response is not None:
                    return error_response
                else:
                    raise

        return current_request


# ============================================================================
# 第四部分：中间件编排工程化分析与最佳实践
# ============================================================================


class MiddlewareChainAnalyzer:
    """中间件链分析器 - 分析编排性能、调试中间件链"""

    def __init__(self, middleware_chain: MiddlewareChain):
        self.middleware_chain = middleware_chain
        self.performance_stats = defaultdict(list)
        self.error_stats = defaultdict(int)

    async def analyze_execution(
        self, request: AgentRequest, agent_func: Callable
    ) -> Dict[str, Any]:
        """分析中间件链执行性能"""
        execution_data = {
            "request_id": hashlib.md5(str(request.to_dict()).encode()).hexdigest(),
            "timestamp": time.time(),
            "middleware_execution_times": {},
            "enabled_middlewares": [],
            "disabled_middlewares": [],
            "errors": [],
        }

        # 记录启用的中间件
        for mw in self.middleware_chain.middlewares:
            if mw.enabled:
                execution_data["enabled_middlewares"].append(
                    {"name": mw.name, "priority": mw.priority}
                )
            else:
                execution_data["disabled_middlewares"].append(mw.name)

        # 监控中间件执行时间
        original_before_agent = {}
        original_after_agent = {}

        # 包装中间件方法以监控执行时间
        for mw in self.middleware_chain.middlewares:
            if mw.enabled:
                # 包装before_agent方法
                original_before_agent[mw.name] = mw.before_agent

                async def wrapped_before(
                    mw=mw, req=request, original=original_before_agent[mw.name]
                ):
                    start_time = time.time()
                    try:
                        result = await original(req)
                        execution_time = time.time() - start_time
                        execution_data["middleware_execution_times"][
                            f"{mw.name}_before"
                        ] = execution_time
                        return result
                    except Exception as e:
                        execution_data["errors"].append(
                            {"middleware": mw.name, "phase": "before", "error": str(e)}
                        )
                        raise

                mw.before_agent = wrapped_before.__get__(mw, type(mw))

                # 包装after_agent方法（类似处理，略）

        # 执行中间件链
        try:
            response = await self.middleware_chain.execute_full_chain(
                request, agent_func
            )
            execution_data["success"] = True
            execution_data["response_status"] = response.status_code
        except Exception as e:
            execution_data["success"] = False
            execution_data["error"] = str(e)

        # 恢复原始方法
        for mw in self.middleware_chain.middlewares:
            if mw.name in original_before_agent:
                mw.before_agent = original_before_agent[mw.name]

        # 记录统计数据
        self.performance_stats[execution_data["request_id"]] = execution_data

        return execution_data

    def generate_performance_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        if not self.performance_stats:
            return {"message": "没有执行数据"}

        total_executions = len(self.performance_stats)
        successful_executions = sum(
            1 for data in self.performance_stats.values() if data.get("success", False)
        )
        error_count = sum(
            len(data.get("errors", [])) for data in self.performance_stats.values()
        )

        # 计算平均执行时间
        execution_times = []
        for data in self.performance_stats.values():
            for time_key, exec_time in data.get(
                "middleware_execution_times", {}
            ).items():
                execution_times.append((time_key, exec_time))

        avg_times = {}
        if execution_times:
            time_by_middleware = defaultdict(list)
            for time_key, exec_time in execution_times:
                time_by_middleware[time_key].append(exec_time)

            for mw_key, times in time_by_middleware.items():
                avg_times[mw_key] = sum(times) / len(times)

        return {
            "total_executions": total_executions,
            "success_rate": successful_executions / total_executions
            if total_executions > 0
            else 0,
            "error_count": error_count,
            "average_execution_times": avg_times,
            "most_frequent_errors": self._get_most_frequent_errors(),
        }

    def _get_most_frequent_errors(self) -> List[Dict[str, Any]]:
        """获取最频繁的错误"""
        error_counts = defaultdict(int)
        for data in self.performance_stats.values():
            for error in data.get("errors", []):
                error_key = (
                    f"{error['middleware']}:{error['phase']}:{error['error'][:50]}"
                )
                error_counts[error_key] += 1

        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        return [
            {"error": error_key, "count": count} for error_key, count in sorted_errors
        ]


class MiddlewareChainVisualizer:
    """中间件链可视化器 - 生成中间件链结构图"""

    @staticmethod
    def generate_ascii_chain(middleware_chain: MiddlewareChain) -> str:
        """生成ASCII格式的中间件链图"""
        lines = []
        lines.append(f"中间件链: {middleware_chain.name}")
        lines.append("=" * 50)

        middlewares = middleware_chain.get_sorted_middlewares()

        # 前置处理链
        lines.append("前置处理链 (顺序执行):")
        lines.append("┌─────────────────────────────────────┐")

        for i, mw in enumerate(middlewares):
            status = "✓" if mw.enabled else "✗"
            lines.append(
                f"│ {i + 1:2d}. [{status}] {mw.name:<30} (优先级: {mw.priority:2d}) │"
            )

        lines.append("└─────────────────────────────────────┘")

        # Agent执行
        lines.append("")
        lines.append("     ↓")
        lines.append("   [Agent]")
        lines.append("     ↓")
        lines.append("")

        # 后置处理链
        lines.append("后置处理链 (逆序执行):")
        lines.append("┌─────────────────────────────────────┐")

        for i, mw in enumerate(reversed(middlewares)):
            status = "✓" if mw.enabled else "✗"
            lines.append(
                f"│ {i + 1:2d}. [{status}] {mw.name:<30} (优先级: {mw.priority:2d}) │"
            )

        lines.append("└─────────────────────────────────────┘")

        return "\n".join(lines)

    @staticmethod
    def generate_execution_flow(
        middleware_chain: MiddlewareChain, request: AgentRequest
    ) -> str:
        """生成执行流程图"""
        lines = []
        lines.append(f"执行流程图 - 请求: {request.message[:30]}...")
        lines.append("=" * 60)

        # 请求信息
        lines.append(f"用户: {request.user_id or '匿名'}")
        lines.append(f"时间: {datetime.fromtimestamp(request.timestamp)}")
        lines.append(f"消息长度: {len(request.message)} 字符")
        lines.append("")

        # 中间件链状态
        middlewares = middleware_chain.get_sorted_middlewares()
        enabled_count = sum(1 for mw in middlewares if mw.enabled)
        disabled_count = len(middlewares) - enabled_count

        lines.append(f"中间件链状态: {enabled_count}个启用, {disabled_count}个禁用")
        lines.append("")

        # 执行顺序
        lines.append("执行顺序:")
        for i, mw in enumerate(middlewares):
            arrow = "→" if i < len(middlewares) - 1 else "→ [Agent]"
            status = "✓" if mw.enabled else "✗"
            lines.append(f"  {i + 1:2d}. {status} {mw.name:<25} {arrow}")

        return "\n".join(lines)


# ============================================================================
# 演示函数和主程序
# ============================================================================


async def demonstrate_middleware_chain() -> None:
    """演示中间件链编排与执行流程"""
    print("=" * 80)
    print("Day 4 Lesson 14: 中间件链编排与执行流程 - 演示")
    print("=" * 80)

    # 创建Agent
    agent = SimpleAgent("demo_agent")

    # ========================================================================
    # 演示1: 基本中间件链执行
    # ========================================================================
    print("\n1. 基本中间件链执行演示")
    print("-" * 40)

    # 创建中间件链
    chain = MiddlewareChain("basic_chain")

    # 添加中间件
    chain.add_middleware(LoggingMiddleware())
    chain.add_middleware(
        AuthenticationMiddleware(valid_tokens={"token123", "token456"})
    )
    chain.add_middleware(
        RateLimitMiddleware(window_size_seconds=30, max_requests_per_window=3)
    )
    chain.add_middleware(ValidationMiddleware(max_message_length=500))
    chain.add_middleware(CacheMiddleware(cache_ttl_seconds=60))

    # 创建请求
    request = AgentRequest(
        message="Hello, this is a test message for middleware chain demonstration.",
        user_id="user123",
        metadata={"auth_token": "token123"},
    )

    # 可视化中间件链
    visualizer = MiddlewareChainVisualizer()
    print(visualizer.generate_ascii_chain(chain))
    print()
    print(visualizer.generate_execution_flow(chain, request))

    # 执行中间件链
    print("\n执行中间件链...")
    response = await chain.execute_full_chain(request, agent.process)

    print(f"\n响应结果:")
    print(f"  状态码: {response.status_code}")
    print(f"  结果: {response.result[:80]}...")
    print(f"  错误: {response.error_message}")
    print(f"  元数据: {json.dumps(response.metadata, indent=2, default=str)}")

    # ========================================================================
    # 演示2: 中间件执行顺序影响
    # ========================================================================
    print("\n\n2. 中间件执行顺序影响演示")
    print("-" * 40)

    print("演示不同中间件执行顺序对系统行为的影响:")

    # 场景1: 认证 -> 限流 -> 验证
    chain1 = MiddlewareChain("order_scenario_1")
    chain1.add_middleware(AuthenticationMiddleware(valid_tokens={"token123"}))
    chain1.add_middleware(
        RateLimitMiddleware(window_size_seconds=30, max_requests_per_window=5)
    )
    chain1.add_middleware(ValidationMiddleware(max_message_length=500))
    chain1.add_middleware(LoggingMiddleware())

    # 场景2: 限流 -> 认证 -> 验证 (可能浪费资源)
    chain2 = MiddlewareChain("order_scenario_2")
    chain2.add_middleware(
        RateLimitMiddleware(window_size_seconds=30, max_requests_per_window=5)
    )
    chain2.add_middleware(AuthenticationMiddleware(valid_tokens={"token123"}))
    chain2.add_middleware(ValidationMiddleware(max_message_length=500))
    chain2.add_middleware(LoggingMiddleware())

    # 场景3: 验证 -> 认证 -> 限流 (可能暴露系统信息)
    chain3 = MiddlewareChain("order_scenario_3")
    chain3.add_middleware(ValidationMiddleware(max_message_length=500))
    chain3.add_middleware(AuthenticationMiddleware(valid_tokens={"token123"}))
    chain3.add_middleware(
        RateLimitMiddleware(window_size_seconds=30, max_requests_per_window=5)
    )
    chain3.add_middleware(LoggingMiddleware())

    print("\n场景1 (推荐顺序): 认证 -> 限流 -> 验证")
    print("  优点: 1. 先认证，避免无效请求占用资源")
    print("        2. 认证后限流，更准确")
    print("        3. 最后验证，避免重复验证")

    print("\n场景2 (次优顺序): 限流 -> 认证 -> 验证")
    print("  缺点: 1. 未认证请求也占用了限流配额")
    print("        2. 可能被恶意用户利用")

    print("\n场景3 (不推荐顺序): 验证 -> 认证 -> 限流")
    print("  缺点: 1. 验证可能暴露系统验证规则")
    print("        2. 认证前验证可能浪费资源")

    # ========================================================================
    # 演示3: 动态调度中间件链
    # ========================================================================
    print("\n\n3. 动态调度中间件链演示")
    print("-" * 40)

    # 创建智能中间件链
    smart_chain = SmartMiddlewareChain("smart_chain")
    smart_chain.add_middleware(LoggingMiddleware())
    smart_chain.add_middleware(
        AuthenticationMiddleware(valid_tokens={"token123", "token456"})
    )
    smart_chain.add_middleware(
        RateLimitMiddleware(window_size_seconds=30, max_requests_per_window=5)
    )
    smart_chain.add_middleware(ValidationMiddleware(max_message_length=500))
    smart_chain.add_middleware(CacheMiddleware(cache_ttl_seconds=60))

    # 创建不同复杂度的请求
    simple_request = AgentRequest(
        message="Hi",  # 简单消息
        user_id="user123",
        metadata={"auth_token": "token123"},
    )

    complex_request = AgentRequest(
        message="This is a very complex request with lots of details and specifications "
        * 10,
        user_id="user456",
        session_id="session789",
        metadata={
            "auth_token": "token456",
            "additional_data": {"key1": "value1", "key2": "value2"},
        },
    )

    print("简单请求 (动态调度效果):")
    print(f"  消息: {simple_request.message}")
    features = smart_chain.feature_analyzer.analyze(simple_request)
    print(f"  特征分析: {json.dumps(features, indent=2)}")

    print("\n复杂请求 (动态调度效果):")
    print(f"  消息长度: {len(complex_request.message)} 字符")
    features = smart_chain.feature_analyzer.analyze(complex_request)
    print(f"  特征分析: {json.dumps(features, indent=2)}")

    # ========================================================================
    # 演示4: 中间件链性能分析
    # ========================================================================
    print("\n\n4. 中间件链性能分析演示")
    print("-" * 40)

    analyzer = MiddlewareChainAnalyzer(chain)

    # 模拟多次请求
    requests = [
        AgentRequest(
            message=f"Test message {i}",
            user_id=f"user{i % 3}",
            metadata={"auth_token": "token123"},
        )
        for i in range(5)
    ]

    print("模拟5次请求执行...")
    for i, req in enumerate(requests):
        print(f"  请求 {i + 1}: {req.message}")
        await analyzer.analyze_execution(req, agent.process)

    # 生成性能报告
    report = analyzer.generate_performance_report()
    print(f"\n性能报告:")
    print(f"  总执行次数: {report['total_executions']}")
    print(f"  成功率: {report['success_rate']:.2%}")
    print(f"  错误数量: {report['error_count']}")

    if report["average_execution_times"]:
        print("  平均执行时间:")
        for mw_key, avg_time in report["average_execution_times"].items():
            print(f"    {mw_key}: {avg_time:.4f}秒")

    # ========================================================================
    # 演示5: 中间件编排最佳实践总结
    # ========================================================================
    print("\n\n5. 中间件编排最佳实践总结")
    print("-" * 40)

    best_practices = [
        "1. 执行顺序原则: 认证 -> 限流 -> 验证 -> 业务逻辑 -> 缓存 -> 日志",
        "2. 优先级设计: 安全相关中间件优先级最高，性能相关中间件次之",
        "3. 错误处理: 中间件应正确处理错误，避免影响整个链的执行",
        "4. 性能优化: 禁用不必要的中间件，使用缓存减少重复计算",
        "5. 动态调度: 根据请求特征动态调整中间件执行顺序和启用状态",
        "6. 监控告警: 监控中间件链执行性能，设置合理的告警阈值",
        "7. 测试策略: 编写全面的中间件链测试，覆盖各种执行场景",
        "8. 文档维护: 详细记录中间件链配置和执行顺序设计决策",
    ]

    for practice in best_practices:
        print(practice)

    print("\n" + "=" * 80)
    print("演示完成!")
    print("=" * 80)


async def main_demo() -> None:
    """主演示函数"""
    try:
        await demonstrate_middleware_chain()
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main_demo())
