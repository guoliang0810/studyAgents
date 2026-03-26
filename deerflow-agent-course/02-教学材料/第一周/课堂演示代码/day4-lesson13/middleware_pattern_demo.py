#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 4 Lesson 13: 中间件设计模式精讲 - 课堂演示代码

本文件演示中间件设计模式的完整实现，包括：
1. 中间件架构与接口定义（责任链模式）
2. 基础中间件实现（认证、日志、验证等）
3. 中间件链编排与执行引擎
4. 中间件工程化分析与最佳实践

适用对象: DeerFlow Python Agent架构师训练营学员
版本: v1.0
作者: 张老师（10年AI系统架构经验，DeerFlow核心贡献者）
最后更新: 2024年3月28日
"""

import asyncio
import time
import json
import logging
import hashlib
import uuid
from typing import Dict, Any, Optional, List, Callable, Union, Awaitable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
from collections import deque, defaultdict
from abc import ABC, abstractmethod
from functools import wraps


# ============================================================================
# 第一部分：中间件架构与接口定义
# ============================================================================


class MiddlewareError(Exception):
    """中间件基础异常类"""

    def __init__(self, message: str, middleware_name: str = "unknown"):
        super().__init__(message)
        self.middleware_name = middleware_name
        self.timestamp = time.time()


class AuthenticationError(MiddlewareError):
    """认证中间件异常"""

    pass


class ValidationError(MiddlewareError):
    """验证中间件异常"""

    pass


class MiddlewareExecutionError(MiddlewareError):
    """中间件执行异常"""

    pass


@dataclass
class AgentRequest:
    """Agent请求数据类"""

    # 基础信息
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    session_id: Optional[str] = None

    # 请求内容
    message: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 上下文信息
    context: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)

    # 时间信息
    created_at: float = field(default_factory=time.time)
    received_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentRequest":
        """从字典创建"""
        return cls(**data)

    def clone(self) -> "AgentRequest":
        """创建副本"""
        return AgentRequest(
            request_id=self.request_id,
            user_id=self.user_id,
            thread_id=self.thread_id,
            session_id=self.session_id,
            message=self.message,
            parameters=self.parameters.copy(),
            metadata=self.metadata.copy(),
            context=self.context.copy(),
            headers=self.headers.copy(),
            created_at=self.created_at,
            received_at=self.received_at,
        )


@dataclass
class AgentResponse:
    """Agent响应数据类"""

    # 基础信息
    request_id: str
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # 响应内容
    success: bool = True
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    error_code: Optional[str] = None

    # 上下文信息
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 时间信息
    created_at: float = field(default_factory=time.time)
    processing_time: float = 0.0

    # 中间件信息
    middleware_execution_info: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentResponse":
        """从字典创建"""
        return cls(**data)

    def add_middleware_info(
        self,
        middleware_name: str,
        execution_time: float,
        success: bool,
        error: Optional[str] = None,
    ):
        """添加中间件执行信息"""
        self.middleware_execution_info.append(
            {
                "middleware_name": middleware_name,
                "execution_time": execution_time,
                "success": success,
                "error": error,
                "timestamp": time.time(),
            }
        )


class AgentMiddleware(ABC):
    """中间件抽象基类 - 遵循责任链模式"""

    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__
        self.enabled: bool = True
        self.priority: int = 0  # 优先级，值越小越先执行
        self.config: Dict[str, Any] = {}

        # 性能监控
        self.execution_count: int = 0
        self.total_execution_time: float = 0.0
        self.error_count: int = 0

    @abstractmethod
    async def before_agent(self, request: AgentRequest) -> Optional[AgentResponse]:
        """
        在Agent处理前执行

        Args:
            request: Agent请求对象

        Returns:
            如果不为None，则直接返回响应，不再执行后续中间件和Agent
            如果为None，则继续执行后续中间件
        """
        pass

    @abstractmethod
    async def after_agent(
        self, request: AgentRequest, response: AgentResponse
    ) -> AgentResponse:
        """
        在Agent处理后执行

        Args:
            request: 原始请求对象
            response: Agent返回的响应对象

        Returns:
            修改后的响应对象
        """
        pass

    async def on_error(
        self, error: Exception, request: AgentRequest
    ) -> Optional[AgentResponse]:
        """
        处理中间件执行错误

        Args:
            error: 发生的异常
            request: 请求对象

        Returns:
            如果不为None，则返回错误响应
            如果为None，则继续传播错误
        """
        self.error_count += 1
        return None

    def update_config(self, config: Dict[str, Any]):
        """更新配置"""
        self.config.update(config)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        avg_time = (
            self.total_execution_time / self.execution_count
            if self.execution_count > 0
            else 0
        )

        return {
            "name": self.name,
            "enabled": self.enabled,
            "priority": self.priority,
            "execution_count": self.execution_count,
            "total_execution_time": self.total_execution_time,
            "average_execution_time": avg_time,
            "error_count": self.error_count,
            "error_rate": (
                self.error_count / self.execution_count
                if self.execution_count > 0
                else 0
            ),
        }

    def _record_execution(self, execution_time: float, success: bool = True):
        """记录执行统计"""
        self.execution_count += 1
        self.total_execution_time += execution_time

        if not success:
            self.error_count += 1


class MiddlewareChain:
    """中间件链管理器"""

    def __init__(self):
        self.middlewares: List[AgentMiddleware] = []
        self._sorted: bool = False

    def add_middleware(self, middleware: AgentMiddleware):
        """添加中间件"""
        self.middlewares.append(middleware)
        self._sorted = False

    def remove_middleware(self, name: str):
        """移除中间件"""
        self.middlewares = [m for m in self.middlewares if m.name != name]

    def get_middleware(self, name: str) -> Optional[AgentMiddleware]:
        """获取中间件"""
        for middleware in self.middlewares:
            if middleware.name == name:
                return middleware
        return None

    def sort_middlewares(self):
        """按优先级排序中间件"""
        self.middlewares.sort(key=lambda m: m.priority)
        self._sorted = True

    async def execute_before_chain(
        self, request: AgentRequest
    ) -> Optional[AgentResponse]:
        """
        执行before链

        Returns:
            如果任何中间件返回响应，则立即返回该响应
            否则返回None，继续执行Agent
        """
        if not self._sorted:
            self.sort_middlewares()

        for middleware in self.middlewares:
            if not middleware.enabled:
                continue

            start_time = time.time()
            try:
                result = await middleware.before_agent(request)
                execution_time = time.time() - start_time
                middleware._record_execution(execution_time, True)

                if result is not None:
                    # 中间件返回了响应，停止执行后续中间件
                    result.add_middleware_info(middleware.name, execution_time, True)
                    return result

            except Exception as e:
                execution_time = time.time() - start_time
                middleware._record_execution(execution_time, False)

                # 调用中间件的错误处理
                error_response = await middleware.on_error(e, request)
                if error_response is not None:
                    error_response.add_middleware_info(
                        middleware.name, execution_time, False, str(e)
                    )
                    return error_response
                else:
                    # 继续传播错误
                    raise MiddlewareExecutionError(
                        f"中间件执行失败: {middleware.name}", middleware.name
                    ) from e

        return None

    async def execute_after_chain(
        self, request: AgentRequest, response: AgentResponse
    ) -> AgentResponse:
        """
        执行after链

        Returns:
            处理后的响应对象
        """
        if not self._sorted:
            self.sort_middlewares()

        current_response = response

        for middleware in reversed(self.middlewares):
            if not middleware.enabled:
                continue

            start_time = time.time()
            try:
                current_response = await middleware.after_agent(
                    request, current_response
                )
                execution_time = time.time() - start_time
                middleware._record_execution(execution_time, True)

                current_response.add_middleware_info(
                    middleware.name, execution_time, True
                )

            except Exception as e:
                execution_time = time.time() - start_time
                middleware._record_execution(execution_time, False)

                # 调用中间件的错误处理
                error_response = await middleware.on_error(e, request)
                if error_response is not None:
                    error_response.add_middleware_info(
                        middleware.name, execution_time, False, str(e)
                    )
                    current_response = error_response
                else:
                    # 记录错误但继续执行后续中间件
                    current_response.add_middleware_info(
                        middleware.name, execution_time, False, str(e)
                    )
                    current_response.success = False
                    current_response.error = str(e)

        return current_response


# ============================================================================
# 第二部分：基础中间件实现
# ============================================================================


class AuthenticationMiddleware(AgentMiddleware):
    """认证中间件 - 验证用户身份和权限"""

    def __init__(self, name: str = "AuthenticationMiddleware"):
        super().__init__(name)
        self.priority = 10  # 高优先级，先执行认证

        # 配置
        self.config = {
            "require_authentication": True,
            "token_header": "Authorization",
            "token_prefix": "Bearer ",
            "allowed_users": None,  # None表示允许所有用户
            "admin_users": set(),
            "token_cache": {},
            "token_cache_ttl": 300,  # 5分钟
        }

    async def before_agent(self, request: AgentRequest) -> Optional[AgentResponse]:
        """在Agent处理前验证身份"""
        start_time = time.time()

        # 检查是否启用认证
        if not self.config["require_authentication"]:
            return None

        # 获取Token
        token = self._extract_token(request)
        if not token:
            execution_time = time.time() - start_time
            self._record_execution(execution_time, False)

            return AgentResponse(
                request_id=request.request_id,
                success=False,
                error="未提供认证Token",
                error_code="UNAUTHENTICATED",
                processing_time=execution_time,
            )

        # 验证Token
        user_info = await self._validate_token(token)
        if not user_info:
            execution_time = time.time() - start_time
            self._record_execution(execution_time, False)

            return AgentResponse(
                request_id=request.request_id,
                success=False,
                error="无效的认证Token",
                error_code="INVALID_TOKEN",
                processing_time=execution_time,
            )

        # 检查用户权限
        if not self._check_user_permission(user_info):
            execution_time = time.time() - start_time
            self._record_execution(execution_time, False)

            return AgentResponse(
                request_id=request.request_id,
                success=False,
                error="用户权限不足",
                error_code="PERMISSION_DENIED",
                processing_time=execution_time,
            )

        # 设置用户信息到请求上下文
        request.user_id = user_info["user_id"]
        request.context["user"] = user_info

        # 如果是管理员用户，设置管理员标志
        if user_info["user_id"] in self.config.get("admin_users", set()):
            request.context["is_admin"] = True

        execution_time = time.time() - start_time
        self._record_execution(execution_time, True)
        return None

    async def after_agent(
        self, request: AgentRequest, response: AgentResponse
    ) -> AgentResponse:
        """在Agent处理后清理认证信息"""
        # 可以在这里添加审计日志等
        # 例如记录谁在什么时候执行了什么操作

        if "user" in request.context:
            response.metadata["authenticated_user"] = request.context["user"]["user_id"]
            response.metadata["authentication_time"] = time.time()

        return response

    async def on_error(
        self, error: Exception, request: AgentRequest
    ) -> Optional[AgentResponse]:
        """认证错误处理"""
        if isinstance(error, AuthenticationError):
            return AgentResponse(
                request_id=request.request_id,
                success=False,
                error=f"认证失败: {str(error)}",
                error_code="AUTH_ERROR",
                processing_time=0.0,
            )
        return None

    def _extract_token(self, request: AgentRequest) -> Optional[str]:
        """从请求中提取Token"""
        # 1. 从headers中获取
        token_header = self.config["token_header"]
        token_prefix = self.config["token_prefix"]

        if token_header in request.headers:
            token_value = request.headers[token_header]
            if token_value.startswith(token_prefix):
                return token_value[len(token_prefix) :]

        # 2. 从parameters中获取
        if "token" in request.parameters:
            return request.parameters["token"]

        # 3. 从metadata中获取
        if "token" in request.metadata:
            return request.metadata["token"]

        return None

    async def _validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证Token有效性"""
        # 检查缓存
        cache_key = f"token_{hashlib.sha256(token.encode()).hexdigest()[:16]}"
        cached_info = self.config["token_cache"].get(cache_key)

        if (
            cached_info
            and time.time() - cached_info["timestamp"] < self.config["token_cache_ttl"]
        ):
            return cached_info["user_info"]

        # 模拟Token验证 - 实际项目中会调用认证服务
        await asyncio.sleep(0.01)  # 模拟网络延迟

        # 简单验证逻辑：Token格式为 "user_id|timestamp|signature"
        parts = token.split("|")
        if len(parts) != 3:
            return None

        user_id, timestamp_str, signature = parts

        try:
            timestamp = float(timestamp_str)
            # 检查Token是否过期（假设Token有效期为1小时）
            if time.time() - timestamp > 3600:
                return None
        except ValueError:
            return None

        # 验证签名（简化）
        expected_signature = hashlib.sha256(
            f"{user_id}|{timestamp_str}|secret".encode()
        ).hexdigest()[:8]
        if signature != expected_signature:
            return None

        # 获取用户信息（模拟）
        user_info = {
            "user_id": user_id,
            "username": f"user_{user_id}",
            "roles": ["user"],
            "permissions": ["read", "write"],
            "created_at": timestamp,
        }

        # 如果是特殊用户，添加管理员角色
        if user_id in ["admin", "root", "superuser"]:
            user_info["roles"].append("admin")
            user_info["permissions"].append("admin")

        # 更新缓存
        self.config["token_cache"][cache_key] = {
            "user_info": user_info,
            "timestamp": time.time(),
        }

        # 清理过期缓存
        self._clean_expired_cache()

        return user_info

    def _check_user_permission(self, user_info: Dict[str, Any]) -> bool:
        """检查用户权限"""
        allowed_users = self.config["allowed_users"]
        if allowed_users is None:
            return True

        return user_info["user_id"] in allowed_users

    def _clean_expired_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key
            for key, value in self.config["token_cache"].items()
            if current_time - value["timestamp"] > self.config["token_cache_ttl"]
        ]

        for key in expired_keys:
            del self.config["token_cache"][key]


class LoggingMiddleware(AgentMiddleware):
    """日志中间件 - 记录请求和响应的详细信息"""

    def __init__(self, name: str = "LoggingMiddleware"):
        super().__init__(name)
        self.priority = 20  # 在认证之后执行

        # 配置
        self.config = {
            "log_level": "INFO",
            "log_request": True,
            "log_response": True,
            "log_errors": True,
            "log_performance": True,
            "max_log_size": 1000,
            "log_storage": [],  # 内存存储，实际项目会用文件或数据库
        }

        # 配置日志格式
        self.logger = logging.getLogger(f"Middleware.{self.name}")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(getattr(logging, self.config["log_level"]))

    async def before_agent(self, request: AgentRequest) -> Optional[AgentResponse]:
        """记录请求信息"""
        if self.config["log_request"]:
            log_entry = {
                "type": "request",
                "request_id": request.request_id,
                "user_id": request.user_id,
                "thread_id": request.thread_id,
                "message_preview": request.message[:100]
                + ("..." if len(request.message) > 100 else ""),
                "timestamp": time.time(),
                "metadata": request.metadata,
            }

            self._store_log(log_entry)

            self.logger.info(
                f"请求接收 - ID: {request.request_id}, "
                f"用户: {request.user_id or 'unknown'}, "
                f"消息: {log_entry['message_preview']}"
            )

        return None

    async def after_agent(
        self, request: AgentRequest, response: AgentResponse
    ) -> AgentResponse:
        """记录响应信息"""
        if self.config["log_response"]:
            log_entry = {
                "type": "response",
                "request_id": request.request_id,
                "response_id": response.response_id,
                "success": response.success,
                "processing_time": response.processing_time,
                "timestamp": time.time(),
                "error": response.error,
            }

            self._store_log(log_entry)

            if response.success:
                self.logger.info(
                    f"响应成功 - 请求ID: {request.request_id}, "
                    f"处理时间: {response.processing_time:.3f}秒"
                )
            else:
                self.logger.error(
                    f"响应失败 - 请求ID: {request.request_id}, 错误: {response.error}"
                )

        # 记录性能信息
        if self.config["log_performance"]:
            performance_entry = {
                "type": "performance",
                "request_id": request.request_id,
                "total_middlewares": len(response.middleware_execution_info),
                "total_execution_time": response.processing_time,
                "middleware_times": [
                    {"name": info["middleware_name"], "time": info["execution_time"]}
                    for info in response.middleware_execution_info
                ],
                "timestamp": time.time(),
            }

            self._store_log(performance_entry)

            # 找出最耗时的中间件
            if response.middleware_execution_info:
                slowest = max(
                    response.middleware_execution_info,
                    key=lambda x: x["execution_time"],
                )
                self.logger.debug(
                    f"性能统计 - 请求ID: {request.request_id}, "
                    f"总时间: {response.processing_time:.3f}秒, "
                    f"最慢中间件: {slowest['middleware_name']} ({slowest['execution_time']:.3f}秒)"
                )

        return response

    async def on_error(
        self, error: Exception, request: AgentRequest
    ) -> Optional[AgentResponse]:
        """记录错误信息"""
        if self.config["log_errors"]:
            error_entry = {
                "type": "error",
                "request_id": request.request_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "timestamp": time.time(),
                "stack_trace": self._format_stack_trace(error),
            }

            self._store_log(error_entry)

            self.logger.error(
                f"中间件错误 - 请求ID: {request.request_id}, "
                f"错误类型: {type(error).__name__}, "
                f"错误信息: {str(error)}"
            )

        return None

    def _store_log(self, log_entry: Dict[str, Any]):
        """存储日志条目"""
        self.config["log_storage"].append(log_entry)

        # 限制日志大小
        if len(self.config["log_storage"]) > self.config["max_log_size"]:
            self.config["log_storage"] = self.config["log_storage"][
                -self.config["max_log_size"] :
            ]

    def _format_stack_trace(self, error: Exception) -> str:
        """格式化堆栈跟踪"""
        import traceback

        return "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )

    def get_logs(
        self,
        log_type: Optional[str] = None,
        since: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """获取日志"""
        logs = self.config["log_storage"]

        # 过滤
        if log_type:
            logs = [log for log in logs if log.get("type") == log_type]

        if since:
            logs = [log for log in logs if log.get("timestamp", 0) >= since]

        # 限制数量
        return logs[-limit:] if limit > 0 else logs

    def clear_logs(self):
        """清空日志"""
        self.config["log_storage"].clear()


class ValidationMiddleware(AgentMiddleware):
    """输入验证中间件 - 验证请求参数的完整性和格式"""

    def __init__(self, name: str = "ValidationMiddleware"):
        super().__init__(name)
        self.priority = 30  # 在认证和日志之后执行

        # 配置验证规则
        self.config = {
            "validate_message_length": True,
            "max_message_length": 1000,
            "min_message_length": 1,
            "validate_parameters": True,
            "required_parameters": [],
            "parameter_rules": {},  # 参数名 -> 验证函数
            "validate_metadata": False,
            "allowed_metadata_keys": [],
        }

        # 内置验证函数
        self.validators = {
            "not_empty": self._validate_not_empty,
            "is_int": self._validate_is_int,
            "is_float": self._validate_is_float,
            "is_bool": self._validate_is_bool,
            "is_string": self._validate_is_string,
            "in_range": self._validate_in_range,
            "matches_pattern": self._validate_matches_pattern,
        }

    async def before_agent(self, request: AgentRequest) -> Optional[AgentResponse]:
        """验证请求参数"""
        validation_errors = []

        # 验证消息长度
        if self.config["validate_message_length"]:
            if len(request.message) < self.config["min_message_length"]:
                validation_errors.append(
                    f"消息长度不能小于{self.config['min_message_length']}个字符"
                )

            if len(request.message) > self.config["max_message_length"]:
                validation_errors.append(
                    f"消息长度不能超过{self.config['max_message_length']}个字符"
                )

        # 验证必需参数
        if self.config["validate_parameters"]:
            for param_name in self.config["required_parameters"]:
                if param_name not in request.parameters:
                    validation_errors.append(f"缺少必需参数: {param_name}")

        # 验证参数规则
        for param_name, rule in self.config["parameter_rules"].items():
            if param_name in request.parameters:
                param_value = request.parameters[param_name]
                error = await self._apply_validation_rule(param_name, param_value, rule)
                if error:
                    validation_errors.append(error)

        # 验证metadata
        if self.config["validate_metadata"]:
            allowed_keys = self.config["allowed_metadata_keys"]
            if allowed_keys:
                for key in request.metadata:
                    if key not in allowed_keys:
                        validation_errors.append(f"不允许的metadata键: {key}")

        # 如果有验证错误，返回错误响应
        if validation_errors:
            return AgentResponse(
                request_id=request.request_id,
                success=False,
                error="输入验证失败",
                error_code="VALIDATION_ERROR",
                data={"validation_errors": validation_errors},
                processing_time=0.0,
            )

        return None

    async def after_agent(
        self, request: AgentRequest, response: AgentResponse
    ) -> AgentResponse:
        """验证响应数据"""
        # 可以在这里验证响应数据的格式等
        # 例如检查响应是否包含必需字段

        if response.success and "data" in response.data:
            # 简单验证：确保响应数据是字典
            if not isinstance(response.data["data"], dict):
                response.success = False
                response.error = "响应数据格式错误"
                response.error_code = "RESPONSE_VALIDATION_ERROR"

        return response

    async def _apply_validation_rule(
        self, param_name: str, param_value: Any, rule: Union[str, Dict, Callable]
    ) -> Optional[str]:
        """应用验证规则"""
        try:
            if callable(rule):
                # 自定义验证函数
                result = rule(param_value)
                if isinstance(result, Awaitable):
                    result = await result

                if not result:
                    return f"参数验证失败: {param_name}"

            elif isinstance(rule, str):
                # 内置验证器名称
                if rule in self.validators:
                    validator = self.validators[rule]
                    if not validator(param_value):
                        return f"参数验证失败: {param_name} 不符合规则: {rule}"
                else:
                    return f"未知验证规则: {rule}"

            elif isinstance(rule, dict):
                # 复杂规则，如 {'type': 'int', 'min': 0, 'max': 100}
                rule_type = rule.get("type", "string")

                if rule_type == "int":
                    if not self._validate_is_int(param_value):
                        return f"参数必须为整数: {param_name}"

                    if "min" in rule and param_value < rule["min"]:
                        return f"参数{param_name}不能小于{rule['min']}"

                    if "max" in rule and param_value > rule["max"]:
                        return f"参数{param_name}不能大于{rule['max']}"

                elif rule_type == "float":
                    if not self._validate_is_float(param_value):
                        return f"参数必须为浮点数: {param_name}"

                    if "min" in rule and param_value < rule["min"]:
                        return f"参数{param_name}不能小于{rule['min']}"

                    if "max" in rule and param_value > rule["max"]:
                        return f"参数{param_name}不能大于{rule['max']}"

                elif rule_type == "string":
                    if not self._validate_is_string(param_value):
                        return f"参数必须为字符串: {param_name}"

                    if "min_length" in rule and len(param_value) < rule["min_length"]:
                        return f"参数{param_name}长度不能小于{rule['min_length']}"

                    if "max_length" in rule and len(param_value) > rule["max_length"]:
                        return f"参数{param_name}长度不能大于{rule['max_length']}"

                    if "pattern" in rule:
                        import re

                        if not re.match(rule["pattern"], param_value):
                            return f"参数{param_name}格式不正确"

                elif rule_type == "enum":
                    allowed_values = rule.get("values", [])
                    if param_value not in allowed_values:
                        return f"参数{param_name}必须为: {allowed_values}"

            return None

        except Exception as e:
            return f"参数验证异常: {param_name} - {str(e)}"

    # 内置验证函数
    def _validate_not_empty(self, value: Any) -> bool:
        return bool(value) if isinstance(value, str) else value is not None

    def _validate_is_int(self, value: Any) -> bool:
        if isinstance(value, int):
            return True
        if isinstance(value, str):
            try:
                int(value)
                return True
            except ValueError:
                return False
        return False

    def _validate_is_float(self, value: Any) -> bool:
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, str):
            try:
                float(value)
                return True
            except ValueError:
                return False
        return False

    def _validate_is_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return True
        if isinstance(value, str):
            return value.lower() in ["true", "false", "yes", "no", "1", "0"]
        if isinstance(value, int):
            return value in [0, 1]
        return False

    def _validate_is_string(self, value: Any) -> bool:
        return isinstance(value, str)

    def _validate_in_range(
        self, value: Any, min_val: float = 0, max_val: float = 100
    ) -> bool:
        try:
            num = float(value)
            return min_val <= num <= max_val
        except (ValueError, TypeError):
            return False

    def _validate_matches_pattern(self, value: Any, pattern: str) -> bool:
        import re

        if not isinstance(value, str):
            return False
        return bool(re.match(pattern, value))


class RateLimitingMiddleware(AgentMiddleware):
    """速率限制中间件 - 限制请求频率"""

    def __init__(self, name: str = "RateLimitingMiddleware"):
        super().__init__(name)
        self.priority = 40  # 在验证之后执行

        # 配置
        self.config = {
            "enabled": True,
            "default_limit": 10,  # 默认每秒请求数
            "limits_by_user": {},  # 用户特定限制
            "limits_by_endpoint": {},  # 端点特定限制
            "window_size": 1.0,  # 时间窗口大小（秒）
            "storage": defaultdict(list),  # 存储请求时间戳
        }

    async def before_agent(self, request: AgentRequest) -> Optional[AgentResponse]:
        """检查速率限制"""
        if not self.config["enabled"]:
            return None

        # 确定限制键（用户ID + 端点）
        user_id = request.user_id or "anonymous"
        endpoint = request.metadata.get("endpoint", "default")
        limit_key = f"{user_id}:{endpoint}"

        # 获取限制值
        limit = self._get_limit(user_id, endpoint)

        # 检查速率
        current_time = time.time()
        window_start = current_time - self.config["window_size"]

        # 获取该键的请求记录
        request_times = self.config["storage"][limit_key]

        # 移除过期的记录
        request_times[:] = [t for t in request_times if t > window_start]

        # 检查是否超过限制
        if len(request_times) >= limit:
            wait_time = request_times[0] + self.config["window_size"] - current_time

            return AgentResponse(
                request_id=request.request_id,
                success=False,
                error=f"请求过于频繁，请等待{wait_time:.1f}秒后重试",
                error_code="RATE_LIMIT_EXCEEDED",
                data={
                    "limit": limit,
                    "window_size": self.config["window_size"],
                    "current_requests": len(request_times),
                    "wait_time": wait_time,
                },
                processing_time=0.0,
            )

        # 记录本次请求
        request_times.append(current_time)

        # 设置速率限制信息到请求上下文
        request.context["rate_limit"] = {
            "limit": limit,
            "remaining": limit - len(request_times),
            "reset_time": current_time + self.config["window_size"],
        }

        return None

    async def after_agent(
        self, request: AgentRequest, response: AgentResponse
    ) -> AgentResponse:
        """添加速率限制信息到响应"""
        if "rate_limit" in request.context:
            response.metadata["rate_limit"] = request.context["rate_limit"]

        return response

    def _get_limit(self, user_id: str, endpoint: str) -> int:
        """获取限制值"""
        # 1. 检查用户特定限制
        if user_id in self.config["limits_by_user"]:
            return self.config["limits_by_user"][user_id]

        # 2. 检查端点特定限制
        if endpoint in self.config["limits_by_endpoint"]:
            return self.config["limits_by_endpoint"][endpoint]

        # 3. 返回默认限制
        return self.config["default_limit"]

    def set_user_limit(self, user_id: str, limit: int):
        """设置用户特定限制"""
        self.config["limits_by_user"][user_id] = limit

    def set_endpoint_limit(self, endpoint: str, limit: int):
        """设置端点特定限制"""
        self.config["limits_by_endpoint"][endpoint] = limit

    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """获取速率限制统计"""
        stats = {}

        for key, request_times in self.config["storage"].items():
            current_time = time.time()
            window_start = current_time - self.config["window_size"]

            # 计算当前窗口内的请求数
            recent_requests = [t for t in request_times if t > window_start]
            stats[key] = {
                "total_requests": len(request_times),
                "recent_requests": len(recent_requests),
                "limit": self._get_limit(*key.split(":", 1)),
                "last_request": request_times[-1] if request_times else None,
            }

        return stats


# ============================================================================
# 第三部分：中间件链编排与执行引擎
# ============================================================================


class MiddlewareExecutionEngine:
    """中间件执行引擎 - 管理中间件链的执行"""

    def __init__(self):
        self.middleware_chain = MiddlewareChain()
        self.agent_handler = None  # Agent处理函数

        # 执行统计
        self.execution_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_execution_time": 0.0,
            "middleware_execution_counts": defaultdict(int),
            "error_distribution": defaultdict(int),
        }

    def register_middleware(self, middleware: AgentMiddleware):
        """注册中间件"""
        self.middleware_chain.add_middleware(middleware)

    def unregister_middleware(self, name: str):
        """取消注册中间件"""
        self.middleware_chain.remove_middleware(name)

    def set_agent_handler(
        self, handler: Callable[[AgentRequest], Awaitable[Dict[str, Any]]]
    ):
        """设置Agent处理函数"""
        self.agent_handler = handler

    async def execute(self, request: AgentRequest) -> AgentResponse:
        """
        执行完整请求处理流程：
        1. 执行before中间件链
        2. 执行Agent处理
        3. 执行after中间件链
        """
        start_time = time.time()
        self.execution_stats["total_requests"] += 1

        try:
            # 1. 执行before中间件链
            before_result = await self.middleware_chain.execute_before_chain(request)

            if before_result is not None:
                # 中间件已经返回响应，直接返回
                before_result.processing_time = time.time() - start_time

                # 更新统计
                self.execution_stats["failed_requests"] += 1
                self.execution_stats["total_execution_time"] += (
                    before_result.processing_time
                )

                return before_result

            # 2. 执行Agent处理
            agent_start_time = time.time()

            if self.agent_handler is None:
                # 如果没有设置Agent处理函数，使用模拟处理
                agent_response_data = await self._mock_agent_handler(request)
            else:
                agent_response_data = await self.agent_handler(request)

            agent_execution_time = time.time() - agent_start_time

            # 创建初始响应
            response = AgentResponse(
                request_id=request.request_id,
                success=True,
                message="处理成功",
                data=agent_response_data,
                processing_time=agent_execution_time,
            )

            # 3. 执行after中间件链
            response = await self.middleware_chain.execute_after_chain(
                request, response
            )

            total_time = time.time() - start_time
            response.processing_time = total_time

            # 更新统计
            if response.success:
                self.execution_stats["successful_requests"] += 1
            else:
                self.execution_stats["failed_requests"] += 1

            self.execution_stats["total_execution_time"] += total_time

            return response

        except Exception as e:
            # 处理未捕获的异常
            error_time = time.time() - start_time

            error_response = AgentResponse(
                request_id=request.request_id,
                success=False,
                error=f"系统错误: {str(e)}",
                error_code="INTERNAL_ERROR",
                processing_time=error_time,
            )

            # 更新统计
            self.execution_stats["failed_requests"] += 1
            self.execution_stats["total_execution_time"] += error_time
            self.execution_stats["error_distribution"][type(e).__name__] += 1

            return error_response

    async def _mock_agent_handler(self, request: AgentRequest) -> Dict[str, Any]:
        """模拟Agent处理函数"""
        await asyncio.sleep(0.05)  # 模拟处理时间

        return {
            "processed_message": f"已处理: {request.message}",
            "timestamp": time.time(),
            "request_id": request.request_id,
            "user_id": request.user_id,
        }

    def get_middleware_stats(self) -> Dict[str, Any]:
        """获取中间件统计信息"""
        stats = {}

        for middleware in self.middleware_chain.middlewares:
            stats[middleware.name] = middleware.get_stats()

            # 更新引擎的统计
            self.execution_stats["middleware_execution_counts"][middleware.name] = (
                middleware.execution_count
            )

        return stats

    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        total_requests = self.execution_stats["total_requests"]

        stats = self.execution_stats.copy()

        if total_requests > 0:
            stats["success_rate"] = (
                self.execution_stats["successful_requests"] / total_requests * 100
            )
            stats["average_execution_time"] = (
                self.execution_stats["total_execution_time"] / total_requests
            )
        else:
            stats["success_rate"] = 0.0
            stats["average_execution_time"] = 0.0

        return stats

    def clear_stats(self):
        """清空统计"""
        self.execution_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_execution_time": 0.0,
            "middleware_execution_counts": defaultdict(int),
            "error_distribution": defaultdict(int),
        }

        # 清空中间件统计
        for middleware in self.middleware_chain.middlewares:
            middleware.execution_count = 0
            middleware.total_execution_time = 0.0
            middleware.error_count = 0


class MiddlewareRegistry:
    """中间件注册表 - 管理中间件的注册、发现和配置"""

    def __init__(self):
        self.middleware_classes: Dict[str, type] = {}
        self.middleware_instances: Dict[str, AgentMiddleware] = {}
        self.middleware_configs: Dict[str, Dict[str, Any]] = {}

    def register_class(self, name: str, middleware_class: type):
        """注册中间件类"""
        if not issubclass(middleware_class, AgentMiddleware):
            raise TypeError(f"{middleware_class} 必须继承自 AgentMiddleware")

        self.middleware_classes[name] = middleware_class

    def create_instance(
        self,
        name: str,
        instance_name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> AgentMiddleware:
        """创建中间件实例"""
        if name not in self.middleware_classes:
            raise KeyError(f"未注册的中间件类: {name}")

        middleware_class = self.middleware_classes[name]
        instance = middleware_class(instance_name or name)

        if config:
            instance.update_config(config)
            self.middleware_configs[instance.name] = config.copy()

        self.middleware_instances[instance.name] = instance
        return instance

    def get_instance(self, name: str) -> Optional[AgentMiddleware]:
        """获取中间件实例"""
        return self.middleware_instances.get(name)

    def update_instance_config(self, name: str, config: Dict[str, Any]):
        """更新中间件实例配置"""
        if name in self.middleware_instances:
            self.middleware_instances[name].update_config(config)
            if name in self.middleware_configs:
                self.middleware_configs[name].update(config)
            else:
                self.middleware_configs[name] = config.copy()

    def get_available_middlewares(self) -> List[Dict[str, Any]]:
        """获取可用的中间件信息"""
        middlewares = []

        for name, cls in self.middleware_classes.items():
            middlewares.append(
                {
                    "name": name,
                    "class_name": cls.__name__,
                    "description": getattr(cls, "__doc__", "").strip().split("\n")[0]
                    if cls.__doc__
                    else "",
                    "has_instance": any(
                        isinstance(instance, cls)
                        for instance in self.middleware_instances.values()
                    ),
                    "instance_count": sum(
                        1
                        for instance in self.middleware_instances.values()
                        if isinstance(instance, cls)
                    ),
                }
            )

        return middlewares

    def export_configuration(self) -> Dict[str, Any]:
        """导出配置"""
        return {
            "middleware_classes": list(self.middleware_classes.keys()),
            "middleware_instances": {
                name: {
                    "class": instance.__class__.__name__,
                    "config": instance.config,
                    "enabled": instance.enabled,
                    "priority": instance.priority,
                }
                for name, instance in self.middleware_instances.items()
            },
            "configurations": self.middleware_configs,
        }

    def import_configuration(self, config: Dict[str, Any]):
        """导入配置"""
        # 清空现有配置
        self.middleware_instances.clear()
        self.middleware_configs.clear()

        # 导入实例配置
        for name, instance_config in config.get("middleware_instances", {}).items():
            class_name = instance_config["class"]

            # 找到对应的类
            middleware_class = None
            for cls_name, cls in self.middleware_classes.items():
                if cls.__name__ == class_name:
                    middleware_class = cls
                    break

            if middleware_class:
                instance = middleware_class(name)
                instance.enabled = instance_config.get("enabled", True)
                instance.priority = instance_config.get("priority", 0)
                instance.update_config(instance_config.get("config", {}))

                self.middleware_instances[name] = instance

        # 导入配置
        self.middleware_configs.update(config.get("configurations", {}))


# ============================================================================
# 第四部分：中间件工程化分析与最佳实践
# ============================================================================


class MiddlewarePerformanceAnalyzer:
    """中间件性能分析器"""

    def __init__(self, execution_engine: MiddlewareExecutionEngine):
        self.execution_engine = execution_engine
        self.performance_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000

    def record_execution(self, request: AgentRequest, response: AgentResponse):
        """记录执行性能"""
        entry = {
            "request_id": request.request_id,
            "timestamp": time.time(),
            "total_time": response.processing_time,
            "success": response.success,
            "user_id": request.user_id,
            "middleware_performance": [],
        }

        # 收集中间件性能数据
        for info in response.middleware_execution_info:
            entry["middleware_performance"].append(
                {
                    "name": info["middleware_name"],
                    "time": info["execution_time"],
                    "success": info["success"],
                }
            )

        self.performance_history.append(entry)

        # 限制历史记录大小
        if len(self.performance_history) > self.max_history_size:
            self.performance_history = self.performance_history[
                -self.max_history_size :
            ]

    def get_performance_summary(self, window_seconds: float = 300) -> Dict[str, Any]:
        """获取性能摘要"""
        current_time = time.time()
        window_start = current_time - window_seconds

        # 筛选时间窗口内的记录
        recent_entries = [
            entry
            for entry in self.performance_history
            if entry["timestamp"] >= window_start
        ]

        if not recent_entries:
            return {"total_requests": 0, "average_time": 0.0}

        # 计算基本统计
        total_requests = len(recent_entries)
        successful_requests = sum(1 for entry in recent_entries if entry["success"])
        total_time = sum(entry["total_time"] for entry in recent_entries)
        average_time = total_time / total_requests

        # 计算中间件性能统计
        middleware_stats = defaultdict(lambda: {"total_time": 0.0, "count": 0})

        for entry in recent_entries:
            for perf in entry["middleware_performance"]:
                middleware_stats[perf["name"]]["total_time"] += perf["time"]
                middleware_stats[perf["name"]]["count"] += 1

        # 转换为平均时间
        middleware_avg_times = {}
        for name, stats in middleware_stats.items():
            if stats["count"] > 0:
                middleware_avg_times[name] = stats["total_time"] / stats["count"]

        # 找出性能瓶颈
        sorted_middleware = sorted(
            middleware_avg_times.items(), key=lambda x: x[1], reverse=True
        )

        bottlenecks = []
        if sorted_middleware:
            max_time = sorted_middleware[0][1]
            for name, avg_time in sorted_middleware:
                if avg_time > average_time * 0.3:  # 超过总时间的30%
                    bottlenecks.append(
                        {
                            "name": name,
                            "average_time": avg_time,
                            "percentage_of_total": (avg_time / average_time * 100)
                            if average_time > 0
                            else 0,
                        }
                    )

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "success_rate": (successful_requests / total_requests * 100)
            if total_requests > 0
            else 0,
            "total_time": total_time,
            "average_time": average_time,
            "middleware_average_times": middleware_avg_times,
            "bottlenecks": bottlenecks,
            "time_window": window_seconds,
        }

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """检测性能异常"""
        if len(self.performance_history) < 10:
            return []

        anomalies = []

        # 计算最近10个请求的平均时间
        recent_entries = self.performance_history[-10:]
        recent_avg_time = sum(entry["total_time"] for entry in recent_entries) / 10

        # 计算历史平均时间（排除最近10个）
        if len(self.performance_history) > 10:
            historical_entries = self.performance_history[:-10]
            historical_avg_time = sum(
                entry["total_time"] for entry in historical_entries
            ) / len(historical_entries)

            # 如果最近平均时间比历史平均时间高50%，则检测到异常
            if recent_avg_time > historical_avg_time * 1.5:
                anomalies.append(
                    {
                        "type": "performance_degradation",
                        "description": f"最近请求平均时间({recent_avg_time:.3f}s)比历史平均时间({historical_avg_time:.3f}s)高50%以上",
                        "severity": "warning",
                        "timestamp": time.time(),
                    }
                )

        # 检测错误率异常
        recent_errors = sum(1 for entry in recent_entries if not entry["success"])
        recent_error_rate = recent_errors / len(recent_entries)

        if recent_error_rate > 0.2:  # 错误率超过20%
            anomalies.append(
                {
                    "type": "high_error_rate",
                    "description": f"最近错误率({recent_error_rate:.1%})超过20%",
                    "severity": "error",
                    "timestamp": time.time(),
                }
            )

        return anomalies

    def generate_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """生成优化建议"""
        suggestions = []

        # 获取性能摘要
        summary = self.get_performance_summary()

        if not summary["middleware_average_times"]:
            return suggestions

        # 分析中间件性能
        total_avg_time = summary["average_time"]

        for name, avg_time in summary["middleware_average_times"].items():
            percentage = (avg_time / total_avg_time * 100) if total_avg_time > 0 else 0

            if percentage > 30:
                suggestions.append(
                    {
                        "middleware": name,
                        "issue": f"中间件执行时间占总时间的{percentage:.1f}%",
                        "suggestion": "考虑优化该中间件的实现，或将其拆分为多个更小的中间件",
                        "priority": "high",
                    }
                )
            elif percentage > 10:
                suggestions.append(
                    {
                        "middleware": name,
                        "issue": f"中间件执行时间占总时间的{percentage:.1f}%",
                        "suggestion": "监控该中间件的性能，考虑是否有优化空间",
                        "priority": "medium",
                    }
                )

        # 检查中间件执行顺序
        middleware_times = list(summary["middleware_average_times"].items())

        if len(middleware_times) > 1:
            # 找出执行时间长的中间件是否在链的前面
            sorted_by_time = sorted(middleware_times, key=lambda x: x[1], reverse=True)

            for i, (name, avg_time) in enumerate(sorted_by_time):
                if i == 0 and avg_time > total_avg_time * 0.4:
                    suggestions.append(
                        {
                            "middleware": name,
                            "issue": f"最耗时的中间件({name})可能阻塞整个执行链",
                            "suggestion": "考虑将该中间件移到链的后面，或实现异步执行",
                            "priority": "high",
                        }
                    )

        return suggestions


class MiddlewareBestPractices:
    """中间件最佳实践指南"""

    @staticmethod
    def get_design_principles() -> List[str]:
        """获取设计原则"""
        return [
            "单一职责原则：每个中间件只负责一个明确的功能",
            "开闭原则：中间件应该对扩展开放，对修改关闭",
            "接口隔离原则：中间件接口应该小而专注",
            "依赖倒置原则：中间件应该依赖抽象，而不是具体实现",
            "链式执行原则：中间件应该支持链式执行，保持执行顺序可控",
        ]

    @staticmethod
    def get_implementation_guidelines() -> List[str]:
        """获取实现指南"""
        return [
            "异步优先：中间件应该尽可能使用异步实现，避免阻塞",
            "错误处理：中间件应该有完善的错误处理和恢复机制",
            "性能监控：中间件应该记录执行时间和资源使用",
            "配置驱动：中间件行为应该通过配置控制，而不是硬编码",
            "可测试性：中间件应该易于单元测试和集成测试",
            "文档完整：中间件应该有完整的API文档和使用示例",
        ]

    @staticmethod
    def get_security_best_practices() -> List[str]:
        """获取安全最佳实践"""
        return [
            "输入验证：对所有输入进行严格验证和清理",
            "身份认证：在链的早期进行身份认证",
            "权限检查：根据用户角色和权限执行操作",
            "敏感数据处理：谨慎处理敏感数据，避免泄露",
            "日志安全：确保日志不包含敏感信息",
            "防攻击措施：实现速率限制和请求验证",
        ]

    @staticmethod
    def get_performance_optimizations() -> List[str]:
        """获取性能优化建议"""
        return [
            "缓存优化：对重复计算进行缓存，避免重复工作",
            "批量处理：支持批量操作，减少频繁调用",
            "懒加载：延迟加载非必要资源",
            "连接池：对数据库和外部服务使用连接池",
            "压缩传输：对大响应数据进行压缩",
            "异步执行：使用异步操作提高并发性能",
        ]

    @staticmethod
    def get_common_antipatterns() -> List[str]:
        """获取常见反模式"""
        return [
            "上帝中间件：一个中间件做太多事情，职责不明确",
            "过度抽象：过度设计中间件接口，增加复杂度",
            "同步阻塞：在中间件中执行同步阻塞操作",
            "忽略错误：没有正确处理和传播错误",
            "硬编码配置：将配置硬编码在中间件中",
            "缺乏监控：没有监控中间件性能和健康状况",
        ]


class MiddlewareFactory:
    """中间件工厂 - 创建和配置中间件"""

    def __init__(self, registry: Optional[MiddlewareRegistry] = None):
        self.registry = registry or MiddlewareRegistry()

        # 注册内置中间件
        self._register_builtin_middlewares()

    def _register_builtin_middlewares(self):
        """注册内置中间件"""
        self.registry.register_class("authentication", AuthenticationMiddleware)
        self.registry.register_class("logging", LoggingMiddleware)
        self.registry.register_class("validation", ValidationMiddleware)
        self.registry.register_class("rate_limiting", RateLimitingMiddleware)

    def create_standard_chain(self) -> MiddlewareChain:
        """创建标准中间件链"""
        chain = MiddlewareChain()

        # 认证中间件
        auth_middleware = self.registry.create_instance(
            "authentication",
            "AuthMiddleware",
            {
                "require_authentication": True,
                "token_header": "Authorization",
                "admin_users": {"admin", "root"},
            },
        )
        auth_middleware.priority = 10
        chain.add_middleware(auth_middleware)

        # 日志中间件
        logging_middleware = self.registry.create_instance(
            "logging",
            "AppLoggingMiddleware",
            {
                "log_level": "INFO",
                "log_request": True,
                "log_response": True,
                "max_log_size": 1000,
            },
        )
        logging_middleware.priority = 20
        chain.add_middleware(logging_middleware)

        # 验证中间件
        validation_middleware = self.registry.create_instance(
            "validation",
            "InputValidationMiddleware",
            {
                "validate_message_length": True,
                "max_message_length": 1000,
                "required_parameters": ["action"],
                "parameter_rules": {
                    "count": {"type": "int", "min": 1, "max": 100},
                },
            },
        )
        validation_middleware.priority = 30
        chain.add_middleware(validation_middleware)

        # 速率限制中间件
        rate_limit_middleware = self.registry.create_instance(
            "rate_limiting",
            "RateLimitMiddleware",
            {
                "enabled": True,
                "default_limit": 10,
                "window_size": 1.0,
            },
        )
        rate_limit_middleware.priority = 40
        chain.add_middleware(rate_limit_middleware)

        return chain

    def create_custom_middleware(
        self, name: str, config: Dict[str, Any]
    ) -> AgentMiddleware:
        """创建自定义中间件"""
        # 这里可以根据需要扩展，支持动态创建中间件类
        # 目前只支持已注册的中间件类

        if name not in self.registry.middleware_classes:
            raise ValueError(f"未知的中间件类型: {name}")

        return self.registry.create_instance(name, f"Custom{name}", config)

    def get_configuration_template(self, middleware_type: str) -> Dict[str, Any]:
        """获取配置模板"""
        if middleware_type == "authentication":
            return {
                "require_authentication": True,
                "token_header": "Authorization",
                "token_prefix": "Bearer ",
                "allowed_users": None,
                "admin_users": set(),
                "token_cache_ttl": 300,
            }
        elif middleware_type == "logging":
            return {
                "log_level": "INFO",
                "log_request": True,
                "log_response": True,
                "log_errors": True,
                "log_performance": True,
                "max_log_size": 1000,
            }
        elif middleware_type == "validation":
            return {
                "validate_message_length": True,
                "max_message_length": 1000,
                "min_message_length": 1,
                "validate_parameters": True,
                "required_parameters": [],
                "parameter_rules": {},
                "validate_metadata": False,
                "allowed_metadata_keys": [],
            }
        elif middleware_type == "rate_limiting":
            return {
                "enabled": True,
                "default_limit": 10,
                "limits_by_user": {},
                "limits_by_endpoint": {},
                "window_size": 1.0,
            }
        else:
            return {}


# ============================================================================
# 主演示函数
# ============================================================================


async def simulate_agent_execution(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """模拟Agent执行函数"""
    await asyncio.sleep(0.05)  # 模拟处理时间

    return {
        "result": "success",
        "message": f"已处理请求: {request_data.get('message', '')}",
        "processed_at": time.time(),
        "request_id": request_data.get("request_id", "unknown"),
    }


async def main_demo():
    """主演示函数"""
    print("=" * 70)
    print("中间件设计模式精讲 - 完整演示")
    print("=" * 70)

    # 1. 创建中间件工厂和注册表
    print("\n1. 创建中间件工厂和注册表...")
    factory = MiddlewareFactory()
    registry = factory.registry

    print(f"   已注册中间件类: {list(registry.middleware_classes.keys())}")

    # 2. 创建标准中间件链
    print("\n2. 创建标准中间件链...")
    middleware_chain = factory.create_standard_chain()
    print(f"   中间件链中的中间件数量: {len(middleware_chain.middlewares)}")

    for middleware in middleware_chain.middlewares:
        print(
            f"     - {middleware.name} (优先级: {middleware.priority}, 启用: {middleware.enabled})"
        )

    # 3. 创建执行引擎
    print("\n3. 创建执行引擎...")
    execution_engine = MiddlewareExecutionEngine()

    # 注册中间件
    for middleware in middleware_chain.middlewares:
        execution_engine.register_middleware(middleware)

    # 设置Agent处理函数
    execution_engine.set_agent_handler(simulate_agent_execution)

    # 4. 创建性能分析器
    print("\n4. 创建性能分析器...")
    performance_analyzer = MiddlewarePerformanceAnalyzer(execution_engine)

    # 5. 模拟多个请求
    print("\n5. 模拟请求处理...")

    requests = [
        {
            "message": "Hello, world!",
            "user_id": "user123",
            "parameters": {"action": "greet", "count": 5},
            "headers": {"Authorization": "Bearer user123|1711612800|abc123def"},
            "metadata": {"endpoint": "chat", "priority": "normal"},
        },
        {
            "message": "This is a test message",
            "user_id": "admin",
            "parameters": {"action": "test", "count": 150},  # 超过限制
            "headers": {"Authorization": "Bearer admin|1711612800|admin456"},
            "metadata": {"endpoint": "admin", "priority": "high"},
        },
        {
            "message": "Invalid request",
            "user_id": "user456",
            "parameters": {},  # 缺少必需参数
            "headers": {"Authorization": "Bearer invalid_token"},
            "metadata": {"endpoint": "chat", "priority": "normal"},
        },
        {
            "message": "Rate limit test",
            "user_id": "user789",
            "parameters": {"action": "query", "count": 10},
            "headers": {"Authorization": "Bearer user789|1711612800|xyz789abc"},
            "metadata": {"endpoint": "api", "priority": "normal"},
        },
    ]

    for i, request_data in enumerate(requests, 1):
        print(f"\n  请求 {i}:")
        print(f"    用户: {request_data['user_id']}")
        print(f"    消息: {request_data['message'][:50]}...")

        # 创建请求对象
        request = AgentRequest(
            user_id=request_data["user_id"],
            message=request_data["message"],
            parameters=request_data["parameters"],
            headers=request_data["headers"],
            metadata=request_data["metadata"],
        )

        # 执行请求
        start_time = time.time()
        response = await execution_engine.execute(request)
        execution_time = time.time() - start_time

        # 记录性能
        performance_analyzer.record_execution(request, response)

        # 显示结果
        status = "✓ 成功" if response.success else "✗ 失败"
        print(f"    结果: {status}")
        print(f"    处理时间: {execution_time:.3f}秒")

        if response.error:
            print(f"    错误: {response.error}")

        if response.metadata:
            print(f"    元数据: {list(response.metadata.keys())}")

    # 6. 显示统计信息
    print("\n" + "=" * 70)
    print("执行统计")
    print("=" * 70)

    # 引擎统计
    engine_stats = execution_engine.get_execution_stats()
    print(f"\n引擎统计:")
    print(f"  总请求数: {engine_stats['total_requests']}")
    print(f"  成功请求数: {engine_stats['successful_requests']}")
    print(f"  失败请求数: {engine_stats['failed_requests']}")
    print(f"  成功率: {engine_stats.get('success_rate', 0):.1f}%")
    print(f"  平均执行时间: {engine_stats.get('average_execution_time', 0):.3f}秒")

    # 中间件统计
    middleware_stats = execution_engine.get_middleware_stats()
    print(f"\n中间件统计:")
    for name, stats in middleware_stats.items():
        print(f"  {name}:")
        print(f"    执行次数: {stats['execution_count']}")
        print(f"    平均时间: {stats['average_execution_time']:.3f}秒")
        print(f"    错误数: {stats['error_count']}")
        print(f"    错误率: {stats['error_rate']:.1%}")

    # 性能分析
    print(f"\n性能分析:")
    performance_summary = performance_analyzer.get_performance_summary()
    print(f"  时间窗口: {performance_summary['time_window']}秒")
    print(f"  总请求数: {performance_summary['total_requests']}")
    print(f"  成功率: {performance_summary['success_rate']:.1f}%")
    print(f"  平均时间: {performance_summary['average_time']:.3f}秒")

    if performance_summary["bottlenecks"]:
        print(f"  性能瓶颈:")
        for bottleneck in performance_summary["bottlenecks"]:
            print(
                f"    {bottleneck['name']}: {bottleneck['average_time']:.3f}秒 "
                f"({bottleneck['percentage_of_total']:.1f}%)"
            )

    # 优化建议
    suggestions = performance_analyzer.generate_optimization_suggestions()
    if suggestions:
        print(f"\n优化建议:")
        for suggestion in suggestions:
            priority = suggestion["priority"].upper()
            print(f"  [{priority}] {suggestion['middleware']}: {suggestion['issue']}")
            print(f"      建议: {suggestion['suggestion']}")

    # 7. 显示最佳实践
    print("\n" + "=" * 70)
    print("中间件最佳实践")
    print("=" * 70)

    best_practices = MiddlewareBestPractices()

    print(f"\n设计原则:")
    for principle in best_practices.get_design_principles():
        print(f"  • {principle}")

    print(f"\n实现指南:")
    for guideline in best_practices.get_implementation_guidelines():
        print(f"  • {guideline}")

    print(f"\n安全最佳实践:")
    for practice in best_practices.get_security_best_practices():
        print(f"  • {practice}")

    # 8. 演示动态配置更新
    print("\n" + "=" * 70)
    print("动态配置更新演示")
    print("=" * 70)

    # 获取日志中间件
    logging_middleware = execution_engine.middleware_chain.get_middleware(
        "AppLoggingMiddleware"
    )
    if logging_middleware:
        print(f"\n更新日志中间件配置...")
        logging_middleware.update_config(
            {"log_level": "DEBUG", "log_performance": False}
        )
        print(
            f"  新配置: log_level={logging_middleware.config['log_level']}, "
            f"log_performance={logging_middleware.config['log_performance']}"
        )

    # 获取认证中间件
    auth_middleware = execution_engine.middleware_chain.get_middleware("AuthMiddleware")
    if auth_middleware:
        print(f"\n更新认证中间件配置...")
        auth_middleware.update_config({"require_authentication": False})
        print(
            f"  新配置: require_authentication={auth_middleware.config['require_authentication']}"
        )

    # 9. 演示中间件禁用/启用
    print(f"\n禁用验证中间件...")
    validation_middleware = execution_engine.middleware_chain.get_middleware(
        "InputValidationMiddleware"
    )
    if validation_middleware:
        validation_middleware.enabled = False
        print(f"  验证中间件已禁用")

    # 10. 运行一个测试请求验证配置更新
    print(f"\n运行测试请求验证配置更新...")
    test_request = AgentRequest(
        user_id="test_user",
        message="Test message after configuration update",
        parameters={"action": "test"},
        headers={},  # 无Token，但认证已禁用
    )

    test_response = await execution_engine.execute(test_request)
    print(f"  结果: {'成功' if test_response.success else '失败'}")
    print(f"  处理时间: {test_response.processing_time:.3f}秒")

    print("\n" + "=" * 70)
    print("演示完成!")
    print("=" * 70)


async def quick_demo():
    """快速演示函数 - 用于课堂演示"""
    print("中间件设计模式 - 快速演示")
    print("-" * 40)

    # 创建简单的中间件链
    chain = MiddlewareChain()

    # 添加认证中间件
    auth_middleware = AuthenticationMiddleware()
    auth_middleware.config["require_authentication"] = False  # 禁用认证便于演示
    chain.add_middleware(auth_middleware)

    # 添加日志中间件
    logging_middleware = LoggingMiddleware()
    chain.add_middleware(logging_middleware)

    # 创建测试请求
    request = AgentRequest(
        user_id="demo_user",
        message="Hello from classroom demo!",
        parameters={"action": "demo"},
        metadata={"demo": True},
    )

    print(f"请求: {request.message}")
    print(f"用户: {request.user_id}")

    # 执行before链
    print("\n执行before中间件链...")
    before_result = await chain.execute_before_chain(request)

    if before_result:
        print(f"中间件返回响应: {before_result.error}")
        return

    print("所有before中间件执行完成")

    # 模拟Agent处理
    print("\n模拟Agent处理...")
    await asyncio.sleep(0.1)

    # 创建模拟响应
    response = AgentResponse(
        request_id=request.request_id,
        success=True,
        message="处理成功",
        data={"result": "demo completed"},
        processing_time=0.1,
    )

    # 执行after链
    print("\n执行after中间件链...")
    final_response = await chain.execute_after_chain(request, response)

    print(f"\n最终响应:")
    print(f"  成功: {final_response.success}")
    print(f"  消息: {final_response.message}")
    print(f"  处理时间: {final_response.processing_time:.3f}秒")

    # 显示中间件执行信息
    if final_response.middleware_execution_info:
        print(f"\n中间件执行信息:")
        for info in final_response.middleware_execution_info:
            status = "✓" if info["success"] else "✗"
            print(
                f"  {status} {info['middleware_name']}: {info['execution_time']:.3f}秒"
            )


if __name__ == "__main__":
    print("选择演示模式:")
    print("1. 完整演示 (包含所有功能和统计)")
    print("2. 快速演示 (适合课堂演示)")
    print("3. 运行测试")

    choice = input("请输入选择 (1/2/3): ").strip()

    if choice == "1":
        asyncio.run(main_demo())
    elif choice == "2":
        asyncio.run(quick_demo())
    elif choice == "3":
        # 运行测试
        print("运行测试...")
        # 这里可以添加单元测试
        print("测试完成!")
    else:
        print("无效选择，使用默认的完整演示")
        asyncio.run(main_demo())
